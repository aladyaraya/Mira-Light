#!/usr/bin/env python3
"""Minimal audio bridge for Mira Light touch system.

精简版音频桥 —— 专门给 Mira-3 触觉系统服务。

设计目标：
  - 自包含（不依赖原 Mira-Light-Voice-Full-Ready 那套庞大代码）
  - 单一职责（只接 HTTP trigger，播 .aiff 文件）
  - 易部署（双击 .command 即起）
  - 触摸松手能立刻停音（v16 行为）

接口：
  POST /v1/mira-light/trigger
    body: {"event": "long_touch_comfort", "payload": {"asset_name": "speech/foo.aiff", ...}}
  POST /v1/mira-light/trigger
    body: {"event": "stop_comfort_sound"}
  GET  /v1/mira-light/status
    返回当前是否正在播

板端的 touch_dispatcher.py 用 bridge_url 指向本服务（默认端口 9783）。
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = HERE / "bridge_config.json"
DEFAULT_ASSETS_ROOT = HERE / "assets"


# ──────────────────────────────────────────────────────────────────────────────
# Audio player —— 包了一层 afplay，能 stop 当前播放任务
# ──────────────────────────────────────────────────────────────────────────────


class AudioPlayer:
    def __init__(self, assets_root: Path) -> None:
        self.assets_root = assets_root.resolve()
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._current_asset: Optional[str] = None
        self._started_at: Optional[float] = None

    def resolve_asset(self, asset_name: str) -> Path:
        """从 asset_name (如 'speech/foo.aiff') 解出本地绝对路径。

        防 path traversal —— resolve 后必须在 assets_root 下。
        """
        candidate = (self.assets_root / asset_name).resolve()
        try:
            candidate.relative_to(self.assets_root)
        except ValueError:
            raise ValueError(f"asset path escapes assets root: {asset_name}")
        if not candidate.is_file():
            raise FileNotFoundError(f"asset not found: {candidate}")
        return candidate

    def play(self, asset_name: str) -> dict[str, Any]:
        with self._lock:
            self._stop_locked()
            path = self.resolve_asset(asset_name)
            try:
                self._proc = subprocess.Popen(
                    ["afplay", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                raise RuntimeError("afplay not found (this bridge is macOS-only)")
            self._current_asset = asset_name
            self._started_at = time.time()
            return {
                "ok": True,
                "asset": asset_name,
                "path": str(path),
                "pid": self._proc.pid,
                "started_at": self._started_at,
            }

    def stop(self) -> dict[str, Any]:
        with self._lock:
            stopped = self._stop_locked()
            return {
                "ok": True,
                "stopped": stopped,
                "ts": time.time(),
            }

    def _stop_locked(self) -> bool:
        proc = self._proc
        if proc is None:
            return False
        if proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass
        self._proc = None
        self._current_asset = None
        self._started_at = None
        return True

    def status(self) -> dict[str, Any]:
        with self._lock:
            playing = self._proc is not None and self._proc.poll() is None
            if not playing:
                # cleanup zombies
                self._stop_locked()
            return {
                "playing": playing,
                "asset": self._current_asset if playing else None,
                "started_at": self._started_at if playing else None,
                "elapsed_ms": int((time.time() - self._started_at) * 1000)
                if (playing and self._started_at)
                else 0,
                "assets_root": str(self.assets_root),
            }


# ──────────────────────────────────────────────────────────────────────────────
# Event handlers —— 把 event name 映射到 player 动作
# ──────────────────────────────────────────────────────────────────────────────


DEFAULT_COMFORT_ASSET = "speech/cute_robot_comfort.aiff"

COMFORT_EVENT_KEYS = {"long_touch_comfort", "comfort_sound"}
STOP_COMFORT_KEYS = {"stop_comfort_sound", "stop_comfort", "comfort_stop"}


def handle_trigger(player: AudioPlayer, body: dict[str, Any]) -> dict[str, Any]:
    event = body.get("event") or body.get("name")
    if not isinstance(event, str) or not event:
        raise ValueError("event is required")
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    event_key = event.strip().lower()

    if event_key in STOP_COMFORT_KEYS:
        # v16 行为：触摸松手 → 立即停音
        reason = payload.get("release_reason", "unknown")
        result = player.stop()
        result["event"] = event_key
        result["release_reason"] = reason
        log(f"[trigger] stop_comfort_sound (release_reason={reason})")
        return result

    if event_key in COMFORT_EVENT_KEYS:
        asset_name = str(payload.get("asset_name") or DEFAULT_COMFORT_ASSET)
        elapsed_ms = payload.get("elapsed_ms")
        log(f"[trigger] {event_key} -> play({asset_name}) elapsed={elapsed_ms}ms")
        try:
            audio_result = player.play(asset_name)
        except FileNotFoundError as e:
            log(f"[trigger] asset missing: {e}")
            return {"ok": False, "event": event_key, "error": "asset_not_found", "detail": str(e)}
        except Exception as e:
            log(f"[trigger] play failed: {e}")
            return {"ok": False, "event": event_key, "error": str(e)}
        return {
            "ok": True,
            "event": event_key,
            "asset": asset_name,
            "elapsed_ms": elapsed_ms,
            "audio": audio_result,
        }

    return {"ok": False, "event": event_key, "error": "unsupported_event"}


# ──────────────────────────────────────────────────────────────────────────────
# HTTP server
# ──────────────────────────────────────────────────────────────────────────────


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} {msg}", flush=True)


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "MiraTouchAudioBridge/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Avoid BaseHTTPRequestHandler.address_string(): reverse DNS can hang
        # LAN requests long enough for the board-side touch POST to time out.
        client = self.client_address[0] if self.client_address else "-"
        log(f"[http] {client} - {format % args}")

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError("invalid JSON body")
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        player: AudioPlayer = self.server.player  # type: ignore[attr-defined]
        if path == "/v1/mira-light/status" or path == "/health":
            self._send_json(200, {"ok": True, "audio": player.status()})
            return
        self._send_json(404, {"ok": False, "error": "not_found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        player: AudioPlayer = self.server.player  # type: ignore[attr-defined]
        try:
            body = self._read_json_body()
        except ValueError as e:
            self._send_json(400, {"ok": False, "error": str(e)})
            return
        if path == "/v1/mira-light/trigger":
            try:
                result = handle_trigger(player, body)
            except ValueError as e:
                self._send_json(400, {"ok": False, "error": str(e)})
                return
            except Exception as e:
                log(f"[trigger] unexpected error: {e}")
                self._send_json(500, {"ok": False, "error": "internal", "detail": str(e)})
                return
            self._send_json(200 if result.get("ok") else 400, result)
            return
        if path == "/v1/mira-light/stop":
            self._send_json(200, {"ok": True, "audio": player.stop()})
            return
        self._send_json(404, {"ok": False, "error": "not_found", "path": path})


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[config] failed to parse {path}: {e}")
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Mira Light touch audio bridge (minimal)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH,
                        help="JSON config file (default: ./bridge_config.json)")
    parser.add_argument("--host", default=None, help="override listen host")
    parser.add_argument("--port", type=int, default=None, help="override listen port")
    parser.add_argument("--assets-root", type=Path, default=None,
                        help="override assets root (default: ./assets)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    host = args.host or cfg.get("listenHost") or "0.0.0.0"
    port = args.port or int(cfg.get("listenPort") or 9783)
    assets_root = args.assets_root or Path(
        os.path.expanduser(str(cfg.get("assetsRoot") or DEFAULT_ASSETS_ROOT))
    )

    if not assets_root.is_dir():
        log(f"[fatal] assets root not found: {assets_root}")
        return 2

    player = AudioPlayer(assets_root)
    server = ThreadingHTTPServer((host, port), BridgeHandler)
    server.player = player  # type: ignore[attr-defined]

    def _shutdown(signum: int, _frame: Any) -> None:
        log(f"[signal] received {signum}, shutting down...")
        player.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    log(f"[ready] listening on http://{host}:{port}")
    log(f"[ready] assets_root={assets_root}")
    log(f"[ready] default_comfort_asset={DEFAULT_COMFORT_ASSET}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        player.stop()
        log("[bye] server stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
