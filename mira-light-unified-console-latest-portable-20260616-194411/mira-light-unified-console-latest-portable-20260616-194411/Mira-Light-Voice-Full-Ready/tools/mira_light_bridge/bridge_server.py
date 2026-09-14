#!/usr/bin/env python3
"""Local HTTP bridge for Mira Light.

This follows the same architectural pattern already used elsewhere in the Mira /
Javis ecosystem:

- a local bridge stays close to the physical device
- a stable HTTP surface is exposed on loopback
- remote OpenClaw can reach that surface later through an SSH reverse tunnel

Why not let remote OpenClaw hit the ESP32 directly?

- the lamp is usually inside a private LAN
- the lamp API itself is intentionally simple and not release-hardened
- booth control needs a stable scene-first bridge surface, not raw device access
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_light_runtime import DEFAULT_TIMEOUT_SECONDS, MiraLightRuntime  # noqa: E402
from mira_light_signal_delivery import build_signal_delivery_contract, load_signal_delivery_schema  # noqa: E402
from scenes import POSES, PROFILE_INFO, SCENES, SERVO_CALIBRATION  # noqa: E402
from embodied_memory_client import EmbodiedMemoryClient  # noqa: E402
from stepfun_llm_planner import (  # noqa: E402
    build_action_manifest,
    build_local_structured_plan,
    normalize_plan_shape,
    plan_from_text,
    validate_plan,
)
from mira_config_env import load_simple_env_file  # noqa: E402


DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("bridge_config.json")
FIXED_LAMP_BASE_URL = "tcp://192.168.0.183:9527"
POST_ONLY_ENDPOINT_EXAMPLES: dict[str, dict[str, Any]] = {
    "/v1/mira-light/run-scene": {"scene": "celebrate", "async": True},
    "/v1/mira-light/trigger": {"event": "praise_detected", "payload": {}},
    "/v1/mira-light/speak": {"text": "啾。"},
    "/v1/mira-light/control": {"joints": []},
    "/v1/mira-light/led": {"mode": "breathing"},
    "/v1/mira-light/sensors": {"headCapacitive": 0},
    "/v1/mira-light/action": {"name": "dance"},
    "/v1/mira-light/config": {"dryRun": True},
    "/v1/mira-light/tracking/start": {"cameraIndex": 0, "backend": "haar", "profile": "low", "skipFrames": 1},
    "/v1/mira-light/tracking/stop": {},
}


def load_bridge_config(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"Invalid bridge config: {path}")
    return parsed


def parse_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def ensure_stepfun_env_loaded() -> None:
    load_simple_env_file(ROOT / "config" / "windows-voice-stepfun.env", override=False)


def read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def summarize_voice_trace_data(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "transcript": "",
            "reply": "",
            "emotion": "",
            "intent": "",
            "action": None,
            "audioMetrics": None,
        }

    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    speech = plan.get("speech") if isinstance(plan.get("speech"), dict) else {}

    transcript = str(
        data.get("transcript")
        or data.get("text")
        or summary.get("userTranscript")
        or summary.get("transcript")
        or ""
    )
    reply = str(
        data.get("reply")
        or data.get("replyText")
        or summary.get("assistantText")
        or plan.get("reply")
        or speech.get("text")
        or ""
    )
    emotion = str(data.get("emotion") or plan.get("emotion") or "")

    raw_intent = data.get("intent") or plan.get("intent") or ""
    if isinstance(raw_intent, dict):
        intent = str(raw_intent.get("name") or raw_intent.get("type") or raw_intent.get("label") or "")
    else:
        intent = str(raw_intent or "")

    trigger_result = data.get("triggerResult") if isinstance(data.get("triggerResult"), dict) else {}
    action = None
    if isinstance(trigger_result.get("action"), dict):
        action = trigger_result.get("action")
    elif isinstance(data.get("action"), dict):
        action = data.get("action")
    elif isinstance(plan.get("action"), dict):
        action = plan.get("action")

    audio_metrics = data.get("audioMetrics") if isinstance(data.get("audioMetrics"), dict) else None
    if audio_metrics is None and isinstance(summary.get("audioMetrics"), dict):
        audio_metrics = summary.get("audioMetrics")

    return {
        "transcript": transcript,
        "reply": reply,
        "emotion": emotion,
        "intent": intent,
        "action": action,
        "audioMetrics": audio_metrics,
    }


def latest_voice_trace_snapshot() -> dict[str, Any]:
    runtime_root = ROOT / "runtime"
    candidates: list[Path] = []
    for folder in [
        "realtime-voice-interaction",
        "windows-voice-realtime",
        "windows-realtime-dialogue",
        "windows-voice-sync",
        "windows-voice-planner",
    ]:
        base = runtime_root / folder
        if not base.exists():
            continue
        try:
            sessions = sorted(
                [path for path in base.iterdir() if path.is_dir()],
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )[:12]
        except OSError:
            sessions = []
        for session in sessions:
            for name in ["session.json", "warmup.json", "actions.jsonl", "events.jsonl", "plan.mira.json"]:
                path = session / name
                if path.is_file():
                    candidates.append(path)
            try:
                turn_dirs = sorted(
                    [path for path in session.iterdir() if path.is_dir() and path.name.startswith("turn-")],
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )[:4]
            except OSError:
                turn_dirs = []
            for turn_dir in turn_dirs:
                for name in [
                    "turn.json",
                    "transcript.json",
                    "transcript.stepfun.json",
                    "transcript.realtime.json",
                    "reply.api.json",
                    "reply.audio.json",
                    "plan.mira.json",
                ]:
                    path = turn_dir / name
                    if path.is_file():
                        candidates.append(path)

    if not candidates:
        return {"ok": True, "found": False, "runtimeRoot": str(runtime_root)}

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    data = read_json_file(latest) if latest.suffix.lower() == ".json" else None
    text = ""
    if latest.suffix.lower() == ".jsonl":
        try:
            lines = latest.read_text(encoding="utf-8").splitlines()
            text = lines[-1] if lines else ""
            data = json.loads(text) if text.strip().startswith("{") else None
        except (OSError, json.JSONDecodeError):
            data = None

    summary = summarize_voice_trace_data(data)

    return {
        "ok": True,
        "found": True,
        "path": str(latest),
        "kind": latest.name,
        "updatedAt": datetime.fromtimestamp(latest.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        "transcript": summary["transcript"],
        "reply": summary["reply"],
        "emotion": summary["emotion"],
        "intent": summary["intent"],
        "action": summary["action"],
        "audioMetrics": summary["audioMetrics"],
        "data": data,
        "rawTail": text,
    }


class BridgeHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address,
        handler_class,
        runtime: MiraLightRuntime,
        token: str,
        ingest_root: Path,
        memory_client: EmbodiedMemoryClient | None = None,
    ):
        super().__init__(server_address, handler_class)
        self.runtime = runtime
        self.token = token
        self.ingest_root = ingest_root
        self.memory_client = memory_client


class DeviceIngestStore:
    """Persist incoming device reports under a stable local runtime folder."""

    def __init__(self, root: Path):
        self.root = root
        self.inbox_dir = self.root / "inbox"
        self.snapshots_dir = self.root / "snapshots"
        self.events_dir = self.root / "events"
        self.errors_dir = self.root / "errors"

        for directory in [self.root, self.inbox_dir, self.snapshots_dir, self.events_dir, self.errors_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def now(self) -> datetime:
        return datetime.now(timezone.utc).astimezone()

    def storage_info(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "inboxDir": str(self.inbox_dir),
            "snapshotsDir": str(self.snapshots_dir),
            "eventsDir": str(self.events_dir),
            "errorsDir": str(self.errors_dir),
        }

    def _safe_device_id(self, device_id: str | None) -> str:
        raw = (device_id or "unknown-device").strip()
        if not raw:
            raw = "unknown-device"
        return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "-" for ch in raw)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def persist_report(self, report_type: str, body: dict[str, Any]) -> dict[str, Any]:
        now = self.now()
        date_part = now.strftime("%Y-%m-%d")
        ts_part = now.strftime("%Y-%m-%dT%H-%M-%S")
        device_id = self._safe_device_id(body.get("deviceId"))

        enriched = {
            "receivedAt": now.isoformat(timespec="seconds"),
            "reportType": report_type,
            "deviceId": device_id,
            "payload": body,
        }

        inbox_path = self.inbox_dir / date_part / f"{ts_part}_{device_id}_{report_type}.json"
        self._write_json(inbox_path, enriched)

        if report_type in {"hello", "heartbeat", "status"}:
            snapshot_path = self.snapshots_dir / f"{device_id}.{report_type}.latest.json"
            self._write_json(snapshot_path, enriched)

        event_record = {
            "ts": now.isoformat(timespec="seconds"),
            "type": report_type,
            "deviceId": device_id,
            "payload": body,
        }
        self._append_jsonl(self.events_dir / f"{date_part}.jsonl", event_record)

        event_type = str(body.get("eventType", "")).lower()
        if report_type == "event" and event_type in {"error", "warning"}:
            self._append_jsonl(self.errors_dir / f"{date_part}.jsonl", event_record)

        return {
            "stored": True,
            "deviceId": device_id,
            "reportType": report_type,
            "inboxPath": str(inbox_path),
        }


class BridgeHandler(BaseHTTPRequestHandler):
    server: BridgeHTTPServer

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        self.server.runtime.log(f"[bridge-http] {self.address_string()} - {format % args}")

    def _send_json(self, status_code: int, payload: dict, *, headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _root_status_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "mira-light-bridge",
            "message": "Mira Light action bridge is running.",
            "runtime": self.server.runtime.get_runtime_state(),
            "profile": PROFILE_INFO,
            "links": {
                "health": "/health",
                "runtime": "/v1/mira-light/runtime",
                "scenes": "/v1/mira-light/scenes",
                "actions": "/v1/mira-light/actions",
                "logs": "/v1/mira-light/logs",
                "profile": "/v1/mira-light/profile",
                "voiceLab": "/voice-lab",
            },
        }

    def _root_status_html(self, payload: dict[str, Any]) -> str:
        runtime = payload.get("runtime", {})
        links = payload.get("links", {})
        link_items = "\n".join(
            f'<li><a href="{escape(str(path))}">{escape(name)}</a></li>'
            for name, path in links.items()
        )
        runtime_rows = "\n".join(
            f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
            for key, value in runtime.items()
            if key in {"baseUrl", "dryRun", "running", "runningScene", "lastError", "sceneCount", "deviceOnline"}
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mira Light Action Bridge</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #1f2933; }}
    main {{ max-width: 880px; }}
    h1 {{ font-size: 28px; margin-bottom: 8px; }}
    .ok {{ color: #137333; font-weight: 600; }}
    table {{ border-collapse: collapse; margin: 20px 0; width: 100%; }}
    th, td {{ border: 1px solid #d7dde5; padding: 8px 10px; text-align: left; }}
    th {{ width: 180px; background: #f4f6f8; }}
    a {{ color: #0b57d0; }}
    code {{ background: #eef2f6; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <main>
    <h1>Mira Light Action Bridge</h1>
    <p class="ok">Running</p>
    <p>This page is a read-only status entry for the local voice-action bridge.</p>
    <table>{runtime_rows}</table>
    <h2>Read-only endpoints</h2>
    <ul>{link_items}</ul>
    <p>Voice actions are sent to <code>/v1/mira-light/run-scene</code> or <code>/v1/mira-light/trigger</code>.</p>
  </main>
</body>
</html>
"""

    def _voice_lab_status_payload(self) -> dict[str, Any]:
        ensure_stepfun_env_loaded()
        runtime = self.server.runtime.get_runtime_state()
        trace = latest_voice_trace_snapshot()
        planner_provider = os.environ.get("MIRA_LIGHT_PLANNER_PROVIDER", "deepseek").strip().lower() or "deepseek"
        planner_key_set = bool(
            os.environ.get("DEEPSEEK_API_KEY")
            or os.environ.get("MIRA_LIGHT_PLANNER_API_KEY")
            or os.environ.get("STEPFUN_API_KEY")
            or os.environ.get("STEP_API_KEY")
        )
        planner_model = os.environ.get(
            "MIRA_LIGHT_PLANNER_MODEL",
            os.environ.get("DEEPSEEK_LLM_MODEL", os.environ.get("STEPFUN_LLM_MODEL", "deepseek-v4-flash")),
        )
        diagnostics = {
            "bridge": "ok",
            "transport": "ok" if runtime.get("lastError") is None else "error",
            "planner": f"{planner_provider}-ready" if planner_key_set else "local-only",
            "trace": "ready" if trace.get("found") else "waiting",
            "currentError": runtime.get("lastError"),
        }
        return {
            "ok": True,
            "service": "mira-light-voice-lab",
            "runtime": runtime,
            "trace": trace,
            "diagnostics": diagnostics,
            "planner": {
                "provider": planner_provider,
                "model": planner_model,
                "plannerKey": "set" if planner_key_set else "unset",
                "actionManifest": build_action_manifest(),
                "schema": {
                    "reply": "short Mira utterance",
                    "emotion": "curious|shy|close|alert|happy|sleepy|warm_caring|gentle",
                    "action": {"type": "scene|trigger|none", "name": ""},
                },
            },
            "pipeline": [
                {"id": "audio", "label": "Audio", "target": "Windows microphone / saved input.wav"},
                {"id": "asr", "label": "ASR", "target": "StepAudio ASR or StepAudio 2.5 Realtime"},
                {"id": "llm", "label": "LLM", "target": f"{planner_model} structured planner"},
                {"id": "action", "label": "Action", "target": "/v1/mira-light/run-scene or /trigger"},
                {"id": "bridge", "label": "Bridge", "target": "Mira Light dry-run/runtime bridge"},
            ],
        }

    def _voice_lab_html(self) -> str:
        return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mira Voice Lab</title>
  <style>
    :root {
      --paper: #f6f3ec;
      --ink: #202018;
      --muted: #67604f;
      --line: #d8d0bf;
      --panel: #fffdf7;
      --mint: #3b8068;
      --coral: #d95f45;
      --amber: #d99b2b;
      --coal: #26231d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        linear-gradient(90deg, rgba(32,32,24,.045) 1px, transparent 1px),
        linear-gradient(180deg, rgba(32,32,24,.035) 1px, transparent 1px),
        var(--paper);
      background-size: 28px 28px;
      color: var(--ink);
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      letter-spacing: 0;
    }
    .shell { max-width: 1320px; margin: 0 auto; padding: 22px; }
    header {
      display: grid;
      grid-template-columns: minmax(260px, 1fr) auto;
      gap: 16px;
      align-items: end;
      border-bottom: 2px solid var(--coal);
      padding-bottom: 14px;
    }
    h1 { margin: 0; font-size: 30px; line-height: 1.05; font-weight: 750; }
    .status-strip { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .pill { border: 1px solid var(--coal); padding: 7px 10px; background: var(--panel); font-size: 13px; }
    .grid { display: grid; grid-template-columns: 1.08fr .92fr; gap: 16px; margin-top: 16px; }
    section, .card {
      background: rgba(255,253,247,.94);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 28px rgba(48,42,28,.08);
    }
    section { padding: 14px; }
    h2 { margin: 0 0 10px; font-size: 15px; text-transform: uppercase; color: var(--muted); }
    .pipeline { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
    .stage { min-height: 104px; padding: 10px; border: 1px solid var(--line); background: #fbf7ed; border-radius: 7px; }
    .stage b { display: block; font-size: 14px; margin-bottom: 8px; }
    .stage span { color: var(--muted); font-size: 12px; line-height: 1.35; display: block; }
    .stage.active { border-color: var(--mint); box-shadow: inset 0 0 0 2px rgba(59,128,104,.16); }
    .meter { height: 72px; display: flex; align-items: end; gap: 3px; padding: 8px; border: 1px solid var(--line); border-radius: 7px; background: #f0eadc; }
    .bar { flex: 1; min-width: 4px; background: var(--mint); transform-origin: bottom; opacity: .82; }
    textarea {
      width: 100%; min-height: 92px; resize: vertical; border: 1px solid var(--coal);
      border-radius: 8px; background: #fffaf0; color: var(--ink); padding: 12px; font: inherit;
    }
    .toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
    button {
      border: 1px solid var(--coal); border-radius: 7px; background: var(--coal); color: #fffaf0;
      min-height: 36px; padding: 0 12px; font-weight: 650; cursor: pointer;
    }
    button.secondary { background: #fffaf0; color: var(--coal); }
    button.warn { background: var(--coral); }
    pre {
      margin: 0; white-space: pre-wrap; overflow: auto; max-height: 340px;
      background: #1f211c; color: #f8f1df; border-radius: 8px; padding: 12px; font-size: 12px;
    }
    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .kv { display: grid; grid-template-columns: 110px 1fr; gap: 7px; font-size: 13px; }
    .kv div:nth-child(odd) { color: var(--muted); }
    .readout { min-height: 88px; padding: 10px; border: 1px solid var(--line); border-radius: 7px; background: #fbf7ed; }
    .reply { font-size: 28px; font-weight: 750; }
    .emotion { color: var(--coral); font-weight: 750; }
    @media (max-width: 940px) {
      header, .grid, .split, .pipeline { grid-template-columns: 1fr; }
      .status-strip { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>Mira Voice Lab</h1>
      </div>
      <div class="status-strip">
        <div class="pill" id="bridge-pill">bridge -</div>
        <div class="pill" id="dry-pill">dry-run -</div>
        <div class="pill" id="key-pill">stepfun -</div>
        <div class="pill" id="transport-pill">transport -</div>
      </div>
    </header>

    <section>
      <h2>Pipeline</h2>
      <div class="pipeline" id="pipeline"></div>
    </section>

    <div class="grid">
      <section>
        <h2>Audio / ASR Monitor</h2>
        <div class="meter" id="meter"></div>
        <div class="kv" style="margin-top:10px">
          <div>trace</div><div id="trace-path">-</div>
          <div>transcript</div><div id="trace-transcript">-</div>
          <div>intent</div><div id="trace-intent">-</div>
          <div>emotion</div><div id="trace-emotion">-</div>
          <div>reply</div><div id="trace-reply">-</div>
          <div>action</div><div id="trace-action">-</div>
        </div>
      </section>

      <section>
        <h2>Structured Test</h2>
        <textarea id="transcript">Mira 跳个舞吧</textarea>
        <div class="toolbar">
          <button id="local-btn">Local Plan + Dispatch</button>
          <button class="secondary" id="llm-btn">StepFun LLM + Dispatch</button>
          <button class="warn" id="stop-btn">Stop Scene</button>
        </div>
      </section>

      <section>
        <h2>Mira Output</h2>
        <div class="split">
          <div class="readout"><div>reply</div><div class="reply" id="reply">-</div></div>
          <div class="readout"><div>emotion</div><div class="emotion" id="emotion">-</div></div>
        </div>
      </section>

      <section>
        <h2>Delivery</h2>
        <div class="kv">
          <div>target</div><div id="delivery-target">-</div>
          <div>action</div><div id="delivery-action">-</div>
          <div>runtime</div><div id="delivery-runtime">-</div>
        </div>
      </section>

      <section>
        <h2>Plan JSON</h2>
        <pre id="plan-json">{}</pre>
      </section>

      <section>
        <h2>Status JSON</h2>
        <pre id="status-json">{}</pre>
      </section>
    </div>
  </div>
  <script>
    const $ = (id) => document.getElementById(id);
    function meter(metrics) {
      const base = Number(metrics?.rms || metrics?.peak || 0.04);
      const cv = Number(metrics?.rmsCv || metrics?.cv || 0.35);
      $("meter").innerHTML = Array.from({length: 28}, (_, i) => {
        const h = 16 + Math.round(52 * Math.abs(Math.sin(i * .55 + cv * 2)) * Math.min(1, base * 18 + .25));
        return `<div class="bar" style="height:${h}px"></div>`;
      }).join("");
    }
    function renderStatus(data) {
      $("bridge-pill").textContent = data.runtime?.baseUrl || "bridge -";
      $("dry-pill").textContent = data.runtime?.dryRun ? "dry-run on" : "dry-run off";
      $("key-pill").textContent = `stepfun ${data.planner?.stepfunKey || "-"}`;
      $("transport-pill").textContent = `transport ${data.diagnostics?.transport || "-"}`;
      $("pipeline").innerHTML = (data.pipeline || []).map((p, i) =>
        `<div class="stage ${i < 3 ? "active" : ""}"><b>${p.label}</b><span>${p.target}</span></div>`
      ).join("");
      const trace = data.trace || {};
      $("trace-path").textContent = trace.path || "-";
      $("trace-transcript").textContent = trace.transcript || "-";
      $("trace-intent").textContent = trace.intent || "-";
      $("trace-emotion").textContent = trace.emotion || "-";
      $("trace-reply").textContent = trace.reply || "-";
      $("trace-action").textContent = JSON.stringify(trace.action || {});
      meter(trace.audioMetrics || {});
      $("status-json").textContent = JSON.stringify(data, null, 2);
    }
    function renderPlan(data) {
      const plan = data.plan || {};
      $("reply").textContent = plan.reply || plan.speech?.text || "-";
      $("emotion").textContent = typeof plan.emotion === "string" ? plan.emotion : JSON.stringify(plan.emotion || "-");
      $("delivery-target").textContent = data.delivery?.target || "-";
      $("delivery-action").textContent = JSON.stringify(plan.action || {});
      $("delivery-runtime").textContent = data.delivery?.response?.runtime?.dryRun === true ? "dry-run accepted" : JSON.stringify(data.delivery?.response || {});
      $("plan-json").textContent = JSON.stringify(data, null, 2);
    }
    async function refresh() {
      const res = await fetch("/v1/mira-light/voice-lab/status");
      renderStatus(await res.json());
    }
    async function plan(useStepFun) {
      const res = await fetch("/v1/mira-light/voice-lab/plan", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({transcript: $("transcript").value, useStepFun, dispatch: true})
      });
      renderPlan(await res.json());
      refresh();
    }
    $("local-btn").onclick = () => plan(false);
    $("llm-btn").onclick = () => plan(true);
    $("stop-btn").onclick = async () => { await fetch("/v1/mira-light/stop", {method:"POST", body:"{}", headers:{"Content-Type":"application/json"}}); refresh(); };
    refresh();
    setInterval(refresh, 1800);
  </script>
</body>
</html>"""

    def _dispatch_voice_lab_plan(self, plan: dict[str, Any], transcript: str, *, provider: str) -> dict[str, Any]:
        action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
        action_type = str(action.get("type") or "none")
        action_name = str(action.get("name") or "")
        payload = {
            "source": "voice-lab",
            "transcript": transcript,
            "reply": str(plan.get("reply") or ""),
            "emotion": str(plan.get("emotion") or ""),
            "provider": provider,
        }
        if action_type == "none":
            return {"ok": True, "skipped": True, "reason": "none-action", "target": None, "payload": payload}
        if action_type == "scene":
            if self.server.runtime.get_runtime_state().get("running"):
                self.server.runtime.stop_scene()
            response = self.server.runtime.start_scene(
                action_name,
                scene_context=payload,
                cue_mode="scene",
                silent_mode=False,
                allow_unavailable=False,
            )
            return {
                "ok": True,
                "target": "/v1/mira-light/run-scene",
                "payload": {"scene": action_name, "context": payload, "async": True},
                "response": {"ok": True, "runtime": response},
            }
        if action_type == "trigger":
            response = self.server.runtime.trigger_event(action_name, payload)
            return {
                "ok": True,
                "target": "/v1/mira-light/trigger",
                "payload": {"event": action_name, "payload": payload},
                "response": {"ok": True, "runtime": response},
            }
        return {"ok": False, "error": f"Unsupported action type: {action_type}", "target": None, "payload": payload}

    def _handle_voice_lab_plan(self, body: dict[str, Any]) -> dict[str, Any]:
        transcript = str(body.get("transcript") or "").strip()
        if not transcript:
            return {"ok": False, "error": "transcript is required"}
        use_stepfun = bool(body.get("useStepFun", False))
        runtime_state = self.server.runtime.get_runtime_state()
        if use_stepfun:
            ensure_stepfun_env_loaded()
            plan_result = plan_from_text(
                transcript,
                provider=os.environ.get("MIRA_LIGHT_PLANNER_PROVIDER", "deepseek"),
                api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("MIRA_LIGHT_PLANNER_API_KEY") or None,
                endpoint=os.environ.get("MIRA_LIGHT_PLANNER_ENDPOINT", os.environ.get("DEEPSEEK_LLM_ENDPOINT", "")),
                model=os.environ.get("MIRA_LIGHT_PLANNER_MODEL", os.environ.get("DEEPSEEK_LLM_MODEL", "")),
                runtime_state=runtime_state,
                proxy_url=os.environ.get("STEPFUN_PROXY_URL", "").strip() or None,
            )
            provider = str(plan_result.get("provider") or "stepfun")
            plan = normalize_plan_shape(plan_result.get("plan") if isinstance(plan_result.get("plan"), dict) else {})
            validation = plan_result.get("validation") if isinstance(plan_result.get("validation"), dict) else validate_plan(plan)
        else:
            provider = "local-structured"
            plan = build_local_structured_plan(transcript, reason="voice-lab-local-preview")
            validation = validate_plan(plan)
            plan_result = {
                "ok": bool(validation.get("ok")),
                "provider": provider,
                "transcript": transcript,
                "plan": plan,
                "validation": validation,
            }
        delivery = None
        if bool(body.get("dispatch", True)) and validation.get("ok"):
            delivery = self._dispatch_voice_lab_plan(plan, transcript, provider=provider)
        return {
            "ok": bool(validation.get("ok")) and (delivery is None or bool(delivery.get("ok"))),
            "provider": provider,
            "transcript": transcript,
            "plan": plan,
            "validation": validation,
            "delivery": delivery,
            "plannerResult": plan_result,
        }

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)

    @property
    def ingest_store(self) -> DeviceIngestStore:
        return DeviceIngestStore(self.server.ingest_root)

    def _authorize(self) -> bool:
        if not self.server.token:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {self.server.token}"

    def _guard(self) -> bool:
        if self.path == "/health":
            return True
        if self._authorize():
            return True
        self._send_json(401, {"ok": False, "error": "Unauthorized"})
        return False

    def _record_device_outcome(self, report_type: str, body: dict[str, Any], stored: dict[str, Any]) -> None:
        client = self.server.memory_client
        if client is None:
            return
        try:
            client.record_device_report(report_type=report_type, payload=body, stored=stored)
        except Exception as exc:  # noqa: BLE001
            self.server.runtime.log(f"[memory-warning] device outcome write failed: {exc}")

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(200)
            self.end_headers()
            return
        if not self._authorize():
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._guard():
            return

        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/":
                payload = self._root_status_payload()
                accept = self.headers.get("Accept", "")
                if "text/html" in accept:
                    self._send_html(200, self._root_status_html(payload))
                else:
                    self._send_json(200, payload)
                return

            if path == "/voice-lab":
                self._send_html(200, self._voice_lab_html())
                return

            if path == "/health":
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "service": "mira-light-bridge",
                        "runtime": self.server.runtime.get_runtime_state(),
                        "profile": PROFILE_INFO,
                    },
                )
                return

            if path == "/v1/mira-light/status":
                self._send_json(200, {"ok": True, "data": self.server.runtime.get_status()})
                return

            if path == "/v1/mira-light/led":
                self._send_json(200, {"ok": True, "data": self.server.runtime.get_led()})
                return

            if path == "/v1/mira-light/sensors":
                self._send_json(200, {"ok": True, "data": self.server.runtime.get_sensors()})
                return

            if path == "/v1/mira-light/actions":
                self._send_json(200, {"ok": True, "data": self.server.runtime.get_actions()})
                return

            if path == "/v1/mira-light/signal-delivery":
                self._send_json(200, {"ok": True, "data": build_signal_delivery_contract()})
                return

            if path == "/v1/mira-light/signal-delivery/schema":
                self._send_json(200, {"ok": True, "data": load_signal_delivery_schema(root=ROOT)})
                return

            if path == "/v1/mira-light/runtime":
                self._send_json(200, {"ok": True, "runtime": self.server.runtime.get_runtime_state()})
                return

            if path == "/v1/mira-light/voice-lab/status":
                self._send_json(200, self._voice_lab_status_payload())
                return

            if path == "/v1/mira-light/logs":
                self._send_json(200, {"ok": True, "items": self.server.runtime.get_logs()})
                return

            if path == "/v1/mira-light/scenes":
                self._send_json(200, {"ok": True, "items": self.server.runtime.list_scenes()})
                return

            if path == "/v1/mira-light/profile":
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "profile": {
                            "info": PROFILE_INFO,
                            "servoCalibration": SERVO_CALIBRATION,
                            "poses": POSES,
                        },
                    },
                )
                return

            if path == "/v1/mira-light/device/storage-info":
                self._send_json(200, {"ok": True, "storage": self.ingest_store.storage_info()})
                return

            if path in POST_ONLY_ENDPOINT_EXAMPLES:
                self._send_json(
                    405,
                    {
                        "ok": False,
                        "error": "method_not_allowed",
                        "message": "This endpoint accepts POST with a JSON body. Browser address bars send GET.",
                        "method": "POST",
                        "path": path,
                        "example": POST_ONLY_ENDPOINT_EXAMPLES[path],
                    },
                    headers={"Allow": "POST"},
                )
                return

            self._send_json(404, {"ok": False, "error": "Unknown endpoint"})
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        if not self._guard():
            return

        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/v1/mira-light/run-scene":
                body = self._read_json_body()
                scene_name = body.get("scene") or body.get("name")
                if not isinstance(scene_name, str) or not scene_name:
                    self._send_json(400, {"ok": False, "error": "scene is required"})
                    return

                async_run = bool(body.get("async", True))
                scene_context = body.get("context") if isinstance(body.get("context"), dict) else None
                cue_mode = str(body.get("cueMode") or "scene")
                silent_mode = bool(body.get("silentMode", False))
                allow_unavailable = bool(body.get("allowUnavailable", False))
                if async_run:
                    runtime_state = self.server.runtime.start_scene(
                        scene_name,
                        scene_context=scene_context,
                        cue_mode=cue_mode,
                        silent_mode=silent_mode,
                        allow_unavailable=allow_unavailable,
                    )
                else:
                    runtime_state = self.server.runtime.run_scene_blocking(
                        scene_name,
                        scene_context=scene_context,
                        cue_mode=cue_mode,
                        silent_mode=silent_mode,
                        allow_unavailable=allow_unavailable,
                    )
                self._send_json(200, {"ok": True, "runtime": runtime_state})
                return

            if path == "/v1/mira-light/trigger":
                body = self._read_json_body()
                event_name = body.get("event") or body.get("name")
                if not isinstance(event_name, str) or not event_name:
                    self._send_json(400, {"ok": False, "error": "event is required"})
                    return
                payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
                async_run = bool(body.get("async", True))
                runtime_state = self.server.runtime.trigger_event(event_name, payload, async_run=async_run)
                self._send_json(200, {"ok": True, "runtime": runtime_state})
                return

            if path == "/v1/mira-light/speak":
                body = self._read_json_body()
                self._send_json(200, {"ok": True, "data": self.server.runtime.speak_text(body)})
                return

            if path == "/v1/mira-light/stop":
                self._send_json(200, {"ok": True, "runtime": self.server.runtime.stop_scene()})
                return

            if path == "/v1/mira-light/reset":
                self._send_json(200, {"ok": True, "data": self.server.runtime.reset_lamp()})
                return

            if path == "/v1/mira-light/apply-pose":
                body = self._read_json_body()
                pose_name = body.get("pose")
                if not isinstance(pose_name, str) or not pose_name:
                    self._send_json(400, {"ok": False, "error": "pose is required"})
                    return
                self._send_json(200, {"ok": True, "data": self.server.runtime.apply_pose(pose_name)})
                return

            if path == "/v1/mira-light/operator/stop-to-neutral":
                self._send_json(200, {"ok": True, "runtime": self.server.runtime.stop_to_pose("neutral")})
                return

            if path == "/v1/mira-light/operator/stop-to-sleep":
                self._send_json(200, {"ok": True, "runtime": self.server.runtime.stop_to_pose("sleep")})
                return

            if path == "/v1/mira-light/control":
                body = self._read_json_body()
                self._send_json(200, {"ok": True, "data": self.server.runtime.control_joints(body)})
                return

            if path == "/v1/mira-light/led":
                body = self._read_json_body()
                self._send_json(200, {"ok": True, "data": self.server.runtime.set_led_state(body)})
                return

            if path == "/v1/mira-light/sensors":
                body = self._read_json_body()
                self._send_json(200, {"ok": True, "data": self.server.runtime.set_sensors_state(body)})
                return

            if path == "/v1/mira-light/action":
                body = self._read_json_body()
                self._send_json(200, {"ok": True, "data": self.server.runtime.get_client().run_action(body)})
                return

            if path == "/v1/mira-light/config":
                body = self._read_json_body()
                runtime_state = self.server.runtime.update_config(
                    base_url=body.get("baseUrl"),
                    dry_run=body.get("dryRun"),
                    auto_recover_pose=body.get("autoRecoverPose"),
                )
                self._send_json(200, {"ok": True, "runtime": runtime_state})
                return

            if path == "/v1/mira-light/tracking/start":
                body = self._read_json_body()
                runtime_state = self.server.runtime.start_tracking(
                    camera_index=int(body.get("cameraIndex", 0)),
                    backend=str(body.get("backend", "haar")),
                    update_interval_ms=float(body.get("updateIntervalMs", 120.0)),
                    frame_width=int(body.get("frameWidth", 640)),
                    frame_height=int(body.get("frameHeight", 480)),
                    fps_limit=int(body.get("fpsLimit", 15)),
                    profile=body.get("profile"),
                    skip_frames=int(body.get("skipFrames", 0)),
                )
                self._send_json(200, {"ok": True, "runtime": runtime_state})
                return

            if path == "/v1/mira-light/tracking/stop":
                runtime_state = self.server.runtime.stop_tracking()
                self._send_json(200, {"ok": True, "runtime": runtime_state})
                return

            if path == "/v1/mira-light/voice-lab/plan":
                body = self._read_json_body()
                result = self._handle_voice_lab_plan(body)
                self._send_json(200 if result.get("ok") else 400, result)
                return

            if path == "/v1/mira-light/profile/capture-pose":
                body = self._read_json_body()
                pose_name = body.get("name") or body.get("pose")
                if not isinstance(pose_name, str) or not pose_name:
                    self._send_json(400, {"ok": False, "error": "pose name is required"})
                    return
                data = self.server.runtime.capture_pose_to_profile(
                    pose_name,
                    notes=str(body.get("notes") or ""),
                    verified=bool(body.get("verified", False)),
                )
                self._send_json(200, {"ok": True, "data": data})
                return

            if path == "/v1/mira-light/profile/set-servo-meta":
                body = self._read_json_body()
                servo_name = body.get("servo")
                if not isinstance(servo_name, str) or not servo_name:
                    self._send_json(400, {"ok": False, "error": "servo is required"})
                    return
                updates = {
                    "label": body.get("label"),
                    "neutral": body.get("neutral"),
                    "hard_range": body.get("hardRange"),
                    "rehearsal_range": body.get("rehearsalRange"),
                    "notes": body.get("notes"),
                    "verified": body.get("verified"),
                }
                data = self.server.runtime.update_servo_meta_in_profile(servo_name, updates)
                self._send_json(200, {"ok": True, "data": data})
                return

            if path == "/v1/mira-light/device/hello":
                body = self._read_json_body()
                stored = self.ingest_store.persist_report("hello", body)
                self._record_device_outcome("hello", body, stored)
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "stored": stored,
                        "serverTime": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                    },
                )
                return

            if path == "/v1/mira-light/device/heartbeat":
                body = self._read_json_body()
                stored = self.ingest_store.persist_report("heartbeat", body)
                self._record_device_outcome("heartbeat", body, stored)
                self._send_json(200, {"ok": True, "stored": stored})
                return

            if path == "/v1/mira-light/device/status":
                body = self._read_json_body()
                stored = self.ingest_store.persist_report("status", body)
                self._record_device_outcome("status", body, stored)
                self._send_json(200, {"ok": True, "stored": stored})
                return

            if path == "/v1/mira-light/device/event":
                body = self._read_json_body()
                stored = self.ingest_store.persist_report("event", body)
                self._record_device_outcome("event", body, stored)
                self._send_json(200, {"ok": True, "stored": stored})
                return

            self._send_json(404, {"ok": False, "error": "Unknown endpoint"})
        except KeyError as exc:
            self._send_json(404, {"ok": False, "error": str(exc)})
        except RuntimeError as exc:
            message = str(exc)
            status_code = 409 if "already running" in message or "while a scene is running" in message else 400
            self._send_json(status_code, {"ok": False, "error": message})
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"ok": False, "error": str(exc)})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Mira Light bridge service.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to bridge_config.json")
    parser.add_argument("--host", help="Override listen host")
    parser.add_argument("--port", type=int, help="Override listen port")
    parser.add_argument("--base-url", help="Override lamp base URL")
    parser.add_argument("--dry-run", action="store_true", help="Do not send real lamp requests")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_bridge_config(Path(args.config))
    host = args.host or config.get("listenHost", "127.0.0.1")
    port = int(args.port or config.get("listenPort", 9783))
    base_url = args.base_url or config.get("lampBaseUrl", FIXED_LAMP_BASE_URL)
    timeout_seconds = float(config.get("requestTimeoutSeconds", DEFAULT_TIMEOUT_SECONDS))
    dry_run = bool(args.dry_run or config.get("dryRun", False))
    ingest_root = Path(os.path.expanduser(config.get("deviceIngestRoot", "~/Documents/Mira-Light-Runtime"))).resolve()

    token_env_name = config.get("bridgeTokenEnv", "MIRA_LIGHT_BRIDGE_TOKEN")
    token = os.environ.get(token_env_name, "")

    memory_cfg = config.get("memoryContext", {}) if isinstance(config.get("memoryContext"), dict) else {}
    memory_enabled = parse_truthy(
        os.environ.get("MIRA_LIGHT_MEMORY_CONTEXT_ENABLED", memory_cfg.get("enabled", False))
    )
    memory_base_url = str(
        os.environ.get("MIRA_LIGHT_MEMORY_CONTEXT_URL", "")
        or memory_cfg.get("baseUrl", "")
    ).rstrip("/")
    memory_auth_token_env = str(memory_cfg.get("authTokenEnv", "MIRA_MEMORY_CONTEXT_AUTH_TOKEN"))
    memory_auth_token = os.environ.get(memory_auth_token_env, "")
    memory_user_id = str(memory_cfg.get("userId", "mira-light-bridge"))
    memory_timeout_seconds = float(memory_cfg.get("requestTimeoutSeconds", 2.0))
    memory_device_status_ttl_seconds = int(memory_cfg.get("deviceStatusTtlSeconds", 900))
    memory_failure_ttl_seconds = int(memory_cfg.get("failureTtlSeconds", 3600))

    memory_client = EmbodiedMemoryClient(
        base_url=memory_base_url,
        auth_token=memory_auth_token,
        user_id=memory_user_id,
        request_timeout_seconds=memory_timeout_seconds,
        device_status_ttl_seconds=memory_device_status_ttl_seconds,
        failure_ttl_seconds=memory_failure_ttl_seconds,
        enabled=memory_enabled,
        emit=None,
    ) if memory_base_url else None

    runtime = MiraLightRuntime(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        dry_run=dry_run,
        embodied_memory_client=memory_client,
    )
    if memory_client is not None:
        memory_client.emit = lambda message: runtime.log(f"[memory] {message}")
    runtime.log(f"[bridge] starting at http://{host}:{port}")
    runtime.log(f"[bridge] lamp base url {base_url}")
    runtime.log(f"[bridge] auth env {token_env_name} present={bool(token)}")
    runtime.log(f"[bridge] device ingest root {ingest_root}")
    runtime.log(f"[bridge] memory context enabled={bool(memory_client and memory_client.enabled)} base={memory_base_url or '-'}")

    server = BridgeHTTPServer(
        (host, port),
        BridgeHandler,
        runtime=runtime,
        token=token,
        ingest_root=ingest_root,
        memory_client=memory_client,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        runtime.log("[bridge] shutdown requested")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
