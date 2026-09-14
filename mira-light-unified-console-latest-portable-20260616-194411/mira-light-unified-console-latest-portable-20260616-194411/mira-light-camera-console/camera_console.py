#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, Callable
from urllib.parse import unquote, urlparse


CONSOLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CONSOLE_DIR.parent
WEB_ROOT = CONSOLE_DIR / "web"
RUNTIME_DIR = REPO_ROOT / "Chrome-Camera-Anime"

if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

import digua_remote_render_pipeline  # noqa: E402


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8788
DEFAULT_BOARD_HOST = "192.168.0.183"
DEFAULT_BOARD_PORT = 22
DEFAULT_BOARD_USER = "root"
DEFAULT_INTERVAL_SECONDS = 10.0
DEFAULT_DATA_DIR = Path.home() / "Documents" / "Mira-Light-Camera-Console"


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8", errors="replace")
    if not raw.strip():
        return {}
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


class CameraSampler:
    def __init__(
        self,
        *,
        board_host: str,
        board_port: int,
        board_user: str,
        board_password: str,
        interval_seconds: float,
        capture_dir: Path,
        remote_device: str,
        input_format: str,
        video_size: str,
        remote_temp_path: str,
        camera_controls: str,
        bind_address: str,
        known_hosts_path: Path,
        connect_timeout: int,
        capture_timeout: int,
        ssh_retries: int,
        ssh_retry_delay_seconds: float,
        after_capture: Callable[[Path, dict[str, Any]], dict[str, Any] | None] | None = None,
    ) -> None:
        self.board_host = board_host
        self.board_port = board_port
        self.board_user = board_user
        self.board_password = board_password
        self.interval_seconds = max(2.0, interval_seconds)
        self.capture_dir = capture_dir
        self.remote_device = remote_device
        self.input_format = input_format
        self.video_size = video_size
        self.remote_temp_path = remote_temp_path
        self.camera_controls = digua_remote_render_pipeline.normalize_camera_controls(camera_controls)
        self.bind_address = bind_address
        self.known_hosts_path = known_hosts_path
        self.connect_timeout = connect_timeout
        self.capture_timeout = capture_timeout
        self.ssh_retries = ssh_retries
        self.ssh_retry_delay_seconds = ssh_retry_delay_seconds
        self.after_capture = after_capture

        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._capture_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._capture_in_progress = False
        self._latest: dict[str, Any] | None = None
        self._last_error: dict[str, Any] | None = None

    def set_after_capture(
        self,
        callback: Callable[[Path, dict[str, Any]], dict[str, Any] | None] | None,
    ) -> None:
        with self._lock:
            self.after_capture = callback

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._running:
                return self.snapshot()
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, name="mira-camera-sampler", daemon=True)
            self._thread.start()
            return self.snapshot()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._running = False
            self._stop_event.set()
            return self.snapshot()

    def set_interval(self, interval_seconds: float) -> dict[str, Any]:
        with self._lock:
            self.interval_seconds = max(2.0, float(interval_seconds))
            self._stop_event.set()
            return self.snapshot()

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
                interval = self.interval_seconds

            started = time.monotonic()
            try:
                self.capture_once()
            except RuntimeError as exc:
                if "capture already in progress" not in str(exc):
                    self._record_error(exc)
            except Exception as exc:  # noqa: BLE001 - keep the watch loop alive across transient camera failures.
                self._record_error(exc)
            elapsed = time.monotonic() - started
            wait_seconds = max(0.1, interval - elapsed)
            if self._stop_event.wait(wait_seconds):
                self._stop_event.clear()

    def _record_error(self, exc: BaseException) -> None:
        with self._lock:
            self._last_error = {
                "message": str(exc),
                "at": datetime.now().isoformat(timespec="seconds"),
            }

    def capture_once(self) -> dict[str, Any]:
        if not self._capture_lock.acquire(blocking=False):
            raise RuntimeError("capture already in progress")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        started = time.monotonic()
        with self._lock:
            self._capture_in_progress = True
        try:
            image_path = digua_remote_render_pipeline.capture_remote_image(
                host=self.board_host,
                user=self.board_user,
                port=self.board_port,
                password=self.board_password,
                bind_address=self.bind_address,
                known_hosts_path=self.known_hosts_path,
                connect_timeout=self.connect_timeout,
                remote_device=self.remote_device,
                input_format=self.input_format,
                video_size=self.video_size,
                remote_temp_path=self.remote_temp_path,
                camera_controls=self.camera_controls,
                capture_dir=self.capture_dir,
                timestamp=timestamp,
                timeout=self.capture_timeout,
                ssh_retries=self.ssh_retries,
                ssh_retry_delay_seconds=self.ssh_retry_delay_seconds,
            )
            stat = image_path.stat()
            captured_at = datetime.now().isoformat(timespec="seconds")
            frame = {
                "capturedAt": captured_at,
                "durationSeconds": round(time.monotonic() - started, 3),
                "filename": image_path.name,
                "path": str(image_path),
                "sizeBytes": stat.st_size,
                "imageUrl": f"/api/frame/image/{image_path.name}?v={int(stat.st_mtime_ns)}",
            }
            callback = self.after_capture
            if callback is not None:
                try:
                    callback_result = callback(image_path, frame)
                    if isinstance(callback_result, dict):
                        frame["postCapture"] = callback_result
                except Exception as exc:  # noqa: BLE001 - capture succeeded; surface callback failure without stopping the camera loop.
                    frame["postCapture"] = {"ok": False, "error": str(exc)}
            with self._lock:
                self._latest = frame
                self._last_error = None
            return frame
        except Exception as exc:
            self._record_error(exc)
            raise
        finally:
            with self._lock:
                self._capture_in_progress = False
            self._capture_lock.release()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "running": self._running,
                "captureInProgress": self._capture_in_progress,
                "intervalSeconds": self.interval_seconds,
                "latestFrame": self._latest,
                "lastError": self._last_error,
                "config": {
                    "boardHost": self.board_host,
                    "boardPort": self.board_port,
                    "boardUser": self.board_user,
                    "passwordConfigured": bool(self.board_password),
                    "remoteDevice": self.remote_device,
                    "inputFormat": self.input_format,
                    "videoSize": self.video_size,
                    "cameraControls": self.camera_controls,
                    "captureDir": str(self.capture_dir),
                },
            }

    def frame_path(self, filename: str) -> Path | None:
        safe_name = Path(filename).name
        candidate = (self.capture_dir / safe_name).resolve()
        capture_root = self.capture_dir.resolve()
        if not str(candidate).startswith(str(capture_root)) or not candidate.is_file():
            return None
        return candidate


class CameraConsoleServer(ThreadingHTTPServer):
    def __init__(self, *args: Any, sampler: CameraSampler, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sampler = sampler


class CameraConsoleHandler(BaseHTTPRequestHandler):
    server: CameraConsoleServer

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "image/jpeg")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        web_root = WEB_ROOT.resolve()
        if not str(candidate).startswith(str(web_root)) or not candidate.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/health", "/api/health", "/api/frame/latest"}:
            self._send_json(HTTPStatus.OK, self.server.sampler.snapshot())
            return
        if path.startswith("/api/frame/image/"):
            filename = unquote(path.removeprefix("/api/frame/image/"))
            frame = self.server.sampler.frame_path(filename)
            if frame is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "frame not found"})
                return
            self._send_file(frame)
            return
        self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/health", "/api/health", "/api/frame/latest"}:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return

        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        web_root = WEB_ROOT.resolve()
        if not str(candidate).startswith(str(web_root)) or not candidate.is_file():
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(candidate.stat().st_size))
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = read_json_body(self)
            if path == "/api/watch/start":
                interval = body.get("intervalSeconds")
                if interval is not None:
                    self.server.sampler.set_interval(float(interval))
                self._send_json(HTTPStatus.OK, self.server.sampler.start())
                return
            if path == "/api/watch/stop":
                self._send_json(HTTPStatus.OK, self.server.sampler.stop())
                return
            if path == "/api/capture":
                frame = self.server.sampler.capture_once()
                self._send_json(HTTPStatus.OK, {"ok": True, "frame": frame, "state": self.server.sampler.snapshot()})
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
        except RuntimeError as exc:
            status = HTTPStatus.CONFLICT if "capture already in progress" in str(exc) else HTTPStatus.BAD_GATEWAY
            self._send_json(status, {"ok": False, "error": str(exc), "state": self.server.sampler.snapshot()})
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": str(exc), "state": self.server.sampler.snapshot()})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[mira-camera-console] {self.address_string()} - {fmt % args}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the Mira Light board camera director console.")
    parser.add_argument("--host", default=os.environ.get("MIRA_CAMERA_CONSOLE_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MIRA_CAMERA_CONSOLE_PORT", DEFAULT_PORT)))
    parser.add_argument("--board-host", default=os.environ.get("MIRA_CAMERA_BOARD_HOST") or os.environ.get("MIRA_SHENZHEN_BOARD_HOST", DEFAULT_BOARD_HOST))
    parser.add_argument("--board-port", type=int, default=int(os.environ.get("MIRA_CAMERA_BOARD_PORT") or os.environ.get("MIRA_SHENZHEN_BOARD_PORT", DEFAULT_BOARD_PORT)))
    parser.add_argument("--board-user", default=os.environ.get("MIRA_CAMERA_BOARD_USER") or os.environ.get("MIRA_SHENZHEN_BOARD_USER", DEFAULT_BOARD_USER))
    parser.add_argument("--password-env", default=os.environ.get("MIRA_CAMERA_PASSWORD_ENV", "MIRA_CAMERA_BOARD_PASSWORD"))
    parser.add_argument("--fallback-password-env", default="MIRA_SHENZHEN_BOARD_PASSWORD")
    parser.add_argument("--interval-seconds", type=float, default=float(os.environ.get("MIRA_CAMERA_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)))
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("MIRA_CAMERA_CONSOLE_DATA_DIR", DEFAULT_DATA_DIR)))
    parser.add_argument("--remote-device", default=os.environ.get("DIGUA_CAMERA_DEVICE", digua_remote_render_pipeline.DEFAULT_DEVICE))
    parser.add_argument("--input-format", default=os.environ.get("DIGUA_CAMERA_INPUT_FORMAT", digua_remote_render_pipeline.DEFAULT_INPUT_FORMAT))
    parser.add_argument("--video-size", default=os.environ.get("DIGUA_CAMERA_VIDEO_SIZE", digua_remote_render_pipeline.DEFAULT_VIDEO_SIZE))
    parser.add_argument("--remote-temp-path", default=os.environ.get("DIGUA_CAMERA_REMOTE_TEMP_PATH", "/tmp/mira-camera-console.jpg"))
    parser.add_argument("--camera-controls", default=os.environ.get("MIRA_CAMERA_V4L2_CTRLS") or os.environ.get("DIGUA_CAMERA_V4L2_CTRLS", ""))
    parser.add_argument("--bind-address", default=os.environ.get("DIGUA_SSH_BIND_ADDRESS", ""))
    parser.add_argument("--known-hosts-path", type=Path, default=digua_remote_render_pipeline.DEFAULT_KNOWN_HOSTS_PATH)
    parser.add_argument("--connect-timeout", type=int, default=digua_remote_render_pipeline.DEFAULT_CONNECT_TIMEOUT)
    parser.add_argument("--capture-timeout", type=int, default=int(os.environ.get("MIRA_CAMERA_CAPTURE_TIMEOUT", "40")))
    parser.add_argument("--ssh-retries", type=int, default=int(os.environ.get("MIRA_CAMERA_SSH_RETRIES", "1")))
    parser.add_argument("--ssh-retry-delay-seconds", type=float, default=float(os.environ.get("MIRA_CAMERA_SSH_RETRY_DELAY_SECONDS", "1.0")))
    parser.add_argument("--start-watch", dest="start_watch", action="store_true")
    parser.add_argument("--no-start-watch", dest="start_watch", action="store_false")
    parser.set_defaults(start_watch=parse_bool(os.environ.get("MIRA_CAMERA_CONSOLE_START_WATCH"), True))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    password = os.environ.get(args.password_env, "") or os.environ.get(args.fallback_password_env, "")
    capture_dir = (args.data_dir.expanduser().resolve() / "frames")
    sampler = CameraSampler(
        board_host=args.board_host,
        board_port=args.board_port,
        board_user=args.board_user,
        board_password=password,
        interval_seconds=args.interval_seconds,
        capture_dir=capture_dir,
        remote_device=args.remote_device,
        input_format=args.input_format,
        video_size=args.video_size,
        remote_temp_path=args.remote_temp_path,
        camera_controls=args.camera_controls,
        bind_address=args.bind_address,
        known_hosts_path=args.known_hosts_path,
        connect_timeout=args.connect_timeout,
        capture_timeout=args.capture_timeout,
        ssh_retries=args.ssh_retries,
        ssh_retry_delay_seconds=args.ssh_retry_delay_seconds,
    )
    server = CameraConsoleServer((args.host, args.port), CameraConsoleHandler, sampler=sampler)
    print(f"[mira-camera-console] open camera director console at http://{args.host}:{args.port}")
    print(f"[mira-camera-console] board ssh {args.board_user}@{args.board_host}:{args.board_port}")
    print(f"[mira-camera-console] device {args.remote_device} {args.input_format} {args.video_size}")
    print(f"[mira-camera-console] controls {sampler.camera_controls or '-'}")
    print(f"[mira-camera-console] interval {sampler.interval_seconds:g}s capture_dir={capture_dir}")
    print(f"[mira-camera-console] password env {args.password_env}/{args.fallback_password_env} configured={bool(password)}")
    if args.start_watch:
        sampler.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mira-camera-console] shutdown requested")
    finally:
        sampler.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
