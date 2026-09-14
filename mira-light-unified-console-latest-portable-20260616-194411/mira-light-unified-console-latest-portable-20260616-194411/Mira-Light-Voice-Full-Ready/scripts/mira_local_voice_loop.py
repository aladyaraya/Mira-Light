#!/usr/bin/env python3
"""Minimal offline Mira voice-to-action loop.

This is the development path for the smallest closed loop:

transcript text -> local Mira soul planner -> safe action bridge -> optional speech

It intentionally does not require StepFun or network access. Realtime voice can
reuse the same orchestrator after ASR produces a final transcript.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mira_realtime_action_orchestrator import (
    DEFAULT_BRIDGE_URL,
    RealtimeActionConfig,
    RealtimeActionOrchestrator,
    post_json_request,
)
from mira_stepfun_realtime_voice_actions import planner_reply_text_from_action


PostJson = Callable[..., dict[str, Any]]
GetJson = Callable[..., dict[str, Any]]


def completed_transcript_event(transcript: str) -> dict[str, str]:
    return {
        "type": "conversation.item.input_audio_transcription.completed",
        "transcript": transcript.strip(),
    }


def get_json_request(url: str, *, token: str = "", timeout_seconds: int = 5) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    return json.loads(body) if body.strip() else {}


def action_response_is_running(actions: list[dict[str, Any]]) -> bool:
    for action in actions:
        response = action.get("response") if isinstance(action.get("response"), dict) else {}
        runtime = response.get("runtime") if isinstance(response.get("runtime"), dict) else {}
        if runtime.get("running") is True:
            return True
    return False


def first_action_response_error(actions: list[dict[str, Any]]) -> str:
    for action in actions:
        response = action.get("response") if isinstance(action.get("response"), dict) else {}
        if response.get("ok") is False:
            return str(response.get("error") or "bridge action failed").strip()
        runtime = response.get("runtime") if isinstance(response.get("runtime"), dict) else {}
        error = str(runtime.get("lastError") or "").strip()
        if error:
            return error
    return ""


def wait_for_bridge_idle(
    *,
    bridge_url: str,
    bridge_token: str,
    timeout_seconds: int,
    poll_interval_seconds: float,
    get_json: GetJson,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(0, timeout_seconds)
    last_health: dict[str, Any] = {}
    while True:
        last_health = get_json(
            f"{bridge_url.rstrip('/')}/health",
            token=bridge_token,
            timeout_seconds=max(1, min(3, int(timeout_seconds) or 1)),
        )
        runtime = last_health.get("runtime") if isinstance(last_health.get("runtime"), dict) else {}
        if runtime.get("running") is not True:
            return last_health
        if time.monotonic() >= deadline:
            return last_health
        time.sleep(max(0.0, float(poll_interval_seconds)))


def dispatch_transcript_once(
    transcript: str,
    *,
    bridge_url: str = DEFAULT_BRIDGE_URL,
    bridge_token: str = "",
    action_timeout_seconds: int = 8,
    post_json: PostJson = post_json_request,
    get_json: GetJson = get_json_request,
    speak_reply: bool = False,
    idle_poll_interval_seconds: float = 0.2,
) -> dict[str, Any]:
    text = transcript.strip()
    if not text:
        raise ValueError("transcript must not be empty")

    orchestrator = RealtimeActionOrchestrator(
        RealtimeActionConfig(
            bridge_url=bridge_url,
            director_url="",
            bridge_token=bridge_token,
            voice_state_enabled=False,
            semantic_actions_enabled=True,
            request_timeout_seconds=int(action_timeout_seconds),
            assistant_action_enabled=False,
        ),
        post_json=post_json,
    )
    actions = orchestrator.handle_event(completed_transcript_event(text))
    reply = ""
    for action in actions:
        reply = planner_reply_text_from_action(action)
        if reply:
            break

    completion_health: dict[str, Any] | None = None
    if action_response_is_running(actions):
        completion_health = wait_for_bridge_idle(
            bridge_url=bridge_url,
            bridge_token=bridge_token,
            timeout_seconds=int(action_timeout_seconds),
            poll_interval_seconds=idle_poll_interval_seconds,
            get_json=get_json,
        )

    completion_runtime = (
        completion_health.get("runtime")
        if isinstance(completion_health, dict) and isinstance(completion_health.get("runtime"), dict)
        else {}
    )
    completion_error = first_action_response_error(actions) or str(completion_runtime.get("lastError") or "").strip()

    speak_result: dict[str, Any] | None = None
    if speak_reply and reply and not completion_error:
        speak_result = post_json(
            f"{bridge_url.rstrip('/')}/v1/mira-light/speak",
            {"text": reply, "voice": "tts", "wait": False},
            token=bridge_token,
            timeout_seconds=int(action_timeout_seconds),
        )
        if completion_health is not None:
            speak_result = {"ok": bool(speak_result.get("ok")), "idleHealth": completion_health, **speak_result}

    ok = not completion_error

    return {
        "ok": ok,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "mode": "local-minimal-voice-loop",
        "transcript": text,
        "bridgeUrl": bridge_url,
        "reply": reply,
        "actions": actions,
        "completion": completion_health,
        "error": completion_error,
        "speak": speak_result,
    }


def default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
    return Path(__file__).resolve().parents[1] / "runtime" / "local-voice-loop" / timestamp / "result.json"


def write_result(result: dict[str, Any], output_path: str | Path | None) -> Path:
    path = Path(output_path).expanduser() if output_path else default_output_path()
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Mira's minimal local transcript-to-action loop.")
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--bridge-token", default="")
    parser.add_argument("--action-timeout-seconds", type=int, default=8)
    parser.add_argument("--speak-reply", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = dispatch_transcript_once(
            args.transcript,
            bridge_url=args.bridge_url,
            bridge_token=args.bridge_token,
            action_timeout_seconds=args.action_timeout_seconds,
            speak_reply=bool(args.speak_reply),
        )
        output_path = write_result(result, args.output)
        result["outputPath"] = str(output_path)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            action = (result.get("actions") or [{}])[0]
            plan = action.get("plan") if isinstance(action.get("plan"), dict) else {}
            inner_plan = plan.get("plan") if isinstance(plan.get("plan"), dict) else plan
            print(f"[mira-local-loop] transcript={result['transcript']}")
            print(f"[mira-local-loop] reply={result.get('reply') or ''}")
            print(f"[mira-local-loop] action={inner_plan.get('action') if isinstance(inner_plan, dict) else {}}")
            if not result.get("ok"):
                print(f"[mira-local-loop-error] {result.get('error') or 'unknown error'}")
            print(f"[mira-local-loop] output={output_path}")
        return 0 if result.get("ok") else 2
    except Exception as exc:  # noqa: BLE001
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[mira-local-loop-error] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
