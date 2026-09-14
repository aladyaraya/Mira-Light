#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "Chrome-Camera-Anime"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9795
DEFAULT_CONSOLE_PORT = 8795
DEFAULT_PRINTER_PORT = 9771
ARK_API_KEY_FALLBACK_PATH = Path.home() / ".openclaw-chrome-camera-anime" / "ark_api_key.txt"
DEFAULT_DATA_DIR = Path.home() / "Documents" / "Chrome-Camera-Anime"
VALID_CHROME_TRIGGER_MODES = {"launch", "launch_or_focus"}


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def load_secret_file_env(key: str, path: Path) -> None:
    if os.environ.get(key, "").strip() or not path.is_file():
        return
    value = path.read_text(encoding="utf-8", errors="replace").strip()
    if value:
        os.environ[key] = value


def env_path(name: str, default: Path) -> Path:
    return Path(os.path.expandvars(os.environ.get(name, str(default)))).expanduser()


def run_command(command: list[str], timeout: float = 5.0) -> dict[str, Any]:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "returnCode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def probe_json(url: str, *, token: str = "", timeout: float = 2.0) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw.strip() else {}
            return {"ok": 200 <= response.status < 500, "status": response.status, "payload": payload}
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            body = {}
        return {"ok": False, "status": exc.code, "payload": body, "error": str(exc)}
    except URLError as exc:
        return {"ok": False, "error": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def read_printer_bridge_token() -> str:
    token = os.environ.get("OPENCLAW_PRINTER_BRIDGE_TOKEN", "")
    if token:
        return token
    env_path = Path(
        os.environ.get(
            "OPENCLAW_PRINTER_BRIDGE_ENV",
            Path.home() / ".openclaw-printer-bridge.env",
        )
    )
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("export OPENCLAW_PRINTER_BRIDGE_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def read_tail(path: Path, max_lines: int = 120) -> list[str]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-max_lines:]


def normalize_chrome_trigger_mode(value: str | None) -> str:
    mode = (value or "launch_or_focus").strip()
    if mode not in VALID_CHROME_TRIGGER_MODES:
        return "launch_or_focus"
    return mode


class CameraRenderManager:
    def __init__(
        self,
        *,
        runtime_dir: Path,
        printer_url: str,
        start_watch: bool,
    ) -> None:
        load_dotenv(runtime_dir / ".env")
        load_secret_file_env("ARK_API_KEY", ARK_API_KEY_FALLBACK_PATH)
        self.runtime_dir = runtime_dir.resolve()
        self.printer_url = printer_url.rstrip("/")
        self.data_dir = env_path("CAMERA_RENDER_DATA_DIR", DEFAULT_DATA_DIR).resolve()
        self.state_dir = env_path("CAMERA_RENDER_STATE_DIR", self.data_dir / "state").resolve()
        self.output_dir = env_path("CAMERA_RENDER_OUTPUT_DIR", self.data_dir / "outputs").resolve()
        self.logs_dir = env_path(
            "CAMERA_RENDER_LOGS_DIR",
            env_path("CAMERA_RENDER_LOG_DIR", self.data_dir / "logs"),
        ).resolve()
        self.camera_cache_dir = env_path("CAMERA_RENDER_CAMERA_CACHE_DIR", self.data_dir / "localmac-camera").resolve()
        self.latest_image_path = self.camera_cache_dir / "latest.jpg"
        self.manifest_path = self.runtime_dir / "manifest.json"
        self.detector_script = self.runtime_dir / "detect_faces.swift"
        self.capture_script = self.runtime_dir / "mac-camera-shot"
        self.pipeline_state_path = self.state_dir / "pipeline-state.json"
        self.watch_state_path = self.state_dir / "watch-state.json"
        self.chrome_trigger_mode_path = self.state_dir / "chrome-trigger-mode.json"
        self.camera_name = os.environ.get("CAMERA_RENDER_CAMERA_NAME", "MacBook Air相机")
        self.camera_backend = os.environ.get("CAMERA_RENDER_CAMERA_BACKEND", "imagesnap")
        self.chrome_trigger_mode = normalize_chrome_trigger_mode(os.environ.get("CAMERA_RENDER_CHROME_TRIGGER_MODE"))
        self.auto_print = parse_bool(os.environ.get("CAMERA_RENDER_AUTO_PRINT"), True)
        self.print_media = os.environ.get("CAMERA_RENDER_PRINT_MEDIA", "4x6.Fullbleed")
        self.python = sys.executable or "python3"
        self.watcher: subprocess.Popen[str] | None = None
        self.worker: subprocess.Popen[str] | None = None
        self.ensure_dirs()
        self.chrome_trigger_mode = self.read_chrome_trigger_mode()
        if start_watch:
            self.start_watch()

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.state_dir, self.output_dir, self.logs_dir, self.camera_cache_dir):
            path.mkdir(parents=True, exist_ok=True)

    def read_chrome_trigger_mode(self) -> str:
        if not self.chrome_trigger_mode_path.is_file():
            return self.chrome_trigger_mode
        try:
            payload = json.loads(self.chrome_trigger_mode_path.read_text(encoding="utf-8"))
        except Exception:
            return self.chrome_trigger_mode
        return normalize_chrome_trigger_mode(str(payload.get("mode") or self.chrome_trigger_mode))

    def write_chrome_trigger_mode(self) -> None:
        self.chrome_trigger_mode_path.write_text(
            json.dumps(
                {
                    "mode": self.chrome_trigger_mode,
                    "launchOrFocus": self.chrome_trigger_mode == "launch_or_focus",
                    "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("CAMERA_RENDER_CAMERA_NAME", self.camera_name)
        env.setdefault("CAMERA_RENDER_CAMERA_BACKEND", self.camera_backend)
        env["MAC_CAMERA_BACKEND"] = self.camera_backend
        env["OPENCLAW_MAC_CAMERA_CACHE_DIR"] = str(self.camera_cache_dir)
        env["OPENCLAW_PRINTER_BRIDGE_URL"] = self.printer_url
        env.setdefault("PYTHONUNBUFFERED", "1")
        return env

    def process_payload(self, proc: subprocess.Popen[str] | None) -> dict[str, Any]:
        if proc is None:
            return {"running": False, "pid": None}
        return {"running": proc.poll() is None, "pid": proc.pid, "returnCode": proc.poll()}

    def cameras(self) -> dict[str, Any]:
        imagesnap = shutil.which("imagesnap")
        if not imagesnap:
            return {"ok": False, "items": [], "error": "imagesnap not found"}
        result = run_command([imagesnap, "-l"], timeout=8)
        cameras = []
        for line in str(result.get("stdout", "")).splitlines():
            stripped = line.strip()
            if stripped.startswith("=>"):
                cameras.append(stripped.removeprefix("=>").strip())
        return {"ok": bool(result.get("ok")), "items": cameras, **({"error": result.get("stderr") or result.get("error")} if not result.get("ok") else {})}

    def health(self) -> dict[str, Any]:
        cameras = self.cameras()
        printer_health = probe_json(f"{self.printer_url}/health")
        printer_status = probe_json(
            f"{self.printer_url}/v1/printers/default",
            token=read_printer_bridge_token(),
        )
        cups_queues = run_command(["lpstat", "-e"], timeout=3)
        default_queue = run_command(["lpstat", "-d"], timeout=3)
        checks = {
            "python": {"ok": True, "path": self.python},
            "node": {"ok": bool(shutil.which("node")), "path": shutil.which("node") or ""},
            "swift": {"ok": bool(shutil.which("swift")), "path": shutil.which("swift") or ""},
            "imagesnap": {"ok": bool(shutil.which("imagesnap")), "path": shutil.which("imagesnap") or ""},
            "camera": {
                "ok": bool(cameras.get("items")),
                "requested": self.camera_name,
                "items": cameras.get("items", []),
                "backend": self.camera_backend,
            },
            "api": {"ok": bool(os.environ.get("ARK_API_KEY")), "env": "ARK_API_KEY"},
            "printerBridge": {"ok": bool(printer_health.get("ok")), "url": self.printer_url, **printer_health},
            "printerStatus": printer_status,
            "cups": {
                "ok": bool(cups_queues.get("ok")),
                "queues": [line for line in str(cups_queues.get("stdout", "")).splitlines() if line.strip()],
                "default": default_queue.get("stdout", ""),
            },
            "watcher": self.process_payload(self.watcher),
            "worker": self.process_payload(self.worker),
            "chromeTriggerMode": {
                "ok": True,
                "mode": self.chrome_trigger_mode,
                "launchOrFocus": self.chrome_trigger_mode == "launch_or_focus",
            },
            "outputDir": {"ok": self.output_dir.is_dir(), "path": str(self.output_dir)},
        }
        return {"ok": True, "service": "camera-render-bridge", "checks": checks, "config": self.status()["config"]}

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "config": {
                "runtimeDir": str(self.runtime_dir),
                "dataDir": str(self.data_dir),
                "stateDir": str(self.state_dir),
                "outputDir": str(self.output_dir),
                "logsDir": str(self.logs_dir),
                "cameraCacheDir": str(self.camera_cache_dir),
                "manifestPath": str(self.manifest_path),
                "detectorScript": str(self.detector_script),
                "captureScript": str(self.capture_script),
                "cameraName": self.camera_name,
                "cameraBackend": self.camera_backend,
                "chromeTriggerMode": self.chrome_trigger_mode,
                "chromeLaunchOrFocus": self.chrome_trigger_mode == "launch_or_focus",
                "autoPrint": self.auto_print,
                "printMedia": self.print_media,
                "printerUrl": self.printer_url,
                "apiKeyPresent": bool(os.environ.get("ARK_API_KEY")),
            },
            "watcher": self.process_payload(self.watcher),
            "worker": self.process_payload(self.worker),
            "latestJob": self.latest_job(),
        }

    def start_watch(self) -> dict[str, Any]:
        env = self.build_env()
        if self.watcher is None or self.watcher.poll() is not None:
            watcher_log = open(self.logs_dir / "chrome-watch.log", "a", encoding="utf-8")
            self.watcher = subprocess.Popen(
                [
                    self.python,
                    str(self.runtime_dir / "chrome_watch_daemon.py"),
                    "--state-dir",
                    str(self.state_dir),
                    "--state-path",
                    str(self.watch_state_path),
                    "--trigger-mode",
                    self.chrome_trigger_mode,
                ],
                cwd=str(self.runtime_dir),
                env=env,
                stdout=watcher_log,
                stderr=watcher_log,
                text=True,
            )
        if self.worker is None or self.worker.poll() is not None:
            worker_log = open(self.logs_dir / "worker.log", "a", encoding="utf-8")
            self.worker = subprocess.Popen(
                [
                    self.python,
                    str(self.runtime_dir / "worker_daemon.py"),
                    "--state-dir",
                    str(self.state_dir),
                    "--manifest",
                    str(self.manifest_path),
                    "--landscape-state-path",
                    str(self.pipeline_state_path),
                    "--output-dir",
                    str(self.output_dir),
                    "--capture-script",
                    str(self.capture_script),
                    "--latest-image-path",
                    str(self.latest_image_path),
                    "--detector-script",
                    str(self.detector_script),
                    "--print-submit-delay-seconds",
                    "0",
                ],
                cwd=str(self.runtime_dir),
                env=env,
                stdout=worker_log,
                stderr=worker_log,
                text=True,
            )
        return {"ok": True, "watcher": self.process_payload(self.watcher), "worker": self.process_payload(self.worker)}

    def set_chrome_trigger_mode(self, mode: str) -> dict[str, Any]:
        normalized = normalize_chrome_trigger_mode(mode)
        changed = normalized != self.chrome_trigger_mode
        self.chrome_trigger_mode = normalized
        os.environ["CAMERA_RENDER_CHROME_TRIGGER_MODE"] = normalized
        self.write_chrome_trigger_mode()
        if changed and self.watcher is not None and self.watcher.poll() is None:
            self.stop_process(self.watcher)
            self.watcher = None
            self.start_watch()
        return {
            "ok": True,
            "mode": self.chrome_trigger_mode,
            "launchOrFocus": self.chrome_trigger_mode == "launch_or_focus",
            "changed": changed,
            "watcher": self.process_payload(self.watcher),
            "worker": self.process_payload(self.worker),
        }

    def stop_process(self, proc: subprocess.Popen[str] | None) -> None:
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    def stop_watch(self) -> dict[str, Any]:
        self.stop_process(self.watcher)
        self.stop_process(self.worker)
        return {"ok": True, "watcher": self.process_payload(self.watcher), "worker": self.process_payload(self.worker)}

    def stop(self) -> None:
        self.stop_watch()

    def capture_render(self) -> dict[str, Any]:
        env = self.build_env()
        command = [
            self.python,
            str(self.runtime_dir / "manual_insta_capture.py"),
            "--state-dir",
            str(self.state_dir),
            "--camera-name",
            self.camera_name,
            "--manifest",
            str(self.manifest_path),
            "--landscape-state-path",
            str(self.pipeline_state_path),
            "--output-dir",
            str(self.output_dir / "manual-insta"),
            "--detector-script",
            str(self.detector_script),
            "--print-media",
            self.print_media,
        ]
        if not self.auto_print:
            command.append("--no-print")
        log_path = self.logs_dir / "manual-capture-render.log"
        started = time.time()
        result = subprocess.run(command, cwd=str(self.runtime_dir), env=env, capture_output=True, text=True, timeout=420)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {' '.join(command)}\n")
            handle.write(result.stdout)
            handle.write(result.stderr)
        raw = result.stdout.strip() if result.returncode == 0 else result.stderr.strip() or result.stdout.strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"ok": False, "error": raw or f"manual capture exited {result.returncode}"}
        payload["returnCode"] = result.returncode
        payload["durationSeconds"] = round(time.time() - started, 3)
        return payload

    def jobs(self) -> list[dict[str, Any]]:
        jobs_dir = self.state_dir / "jobs"
        items: list[dict[str, Any]] = []
        for path in sorted(jobs_dir.glob("*/job.json")):
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception as exc:  # noqa: BLE001
                items.append({"job_id": path.parent.name, "status": "read_error", "error": str(exc)})
        return sorted(items, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)

    def latest_job(self) -> dict[str, Any] | None:
        items = self.jobs()
        return items[0] if items else None

    def logs(self) -> dict[str, Any]:
        return {
            "ok": True,
            "items": [
                {"name": path.name, "lines": read_tail(path)}
                for path in sorted(self.logs_dir.glob("*.log"))
            ],
        }

    def print_last(self) -> dict[str, Any]:
        for job in self.jobs():
            output_path = job.get("output_path")
            if output_path and Path(str(output_path)).is_file():
                if str(self.runtime_dir) not in sys.path:
                    sys.path.insert(0, str(self.runtime_dir))
                import print_client  # noqa: PLC0415

                response = print_client.submit_print_job(
                    Path(str(output_path)),
                    media=self.print_media,
                    bridge_url=self.printer_url,
                    token=read_printer_bridge_token(),
                )
                return {"ok": True, "job": job, "printResponse": response}
        return {"ok": False, "error": "no generated output found"}

    def artifact_path(self, name: str) -> Path | None:
        safe_name = Path(name).name
        for root in (self.output_dir, self.state_dir):
            for path in root.rglob(safe_name):
                if path.is_file():
                    return path
        return None


class CameraRenderHTTPServer(ThreadingHTTPServer):
    def __init__(self, *args: Any, manager: CameraRenderManager, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.manager = manager


class Handler(BaseHTTPRequestHandler):
    server: CameraRenderHTTPServer

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        if not raw.strip():
            return {}
        return json.loads(raw)

    def _send_file(self, path: Path) -> None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        manager = self.server.manager
        try:
            if path == "/health":
                self._send_json(HTTPStatus.OK, manager.health())
                return
            if path == "/v1/camera-render/status":
                self._send_json(HTTPStatus.OK, manager.status())
                return
            if path == "/v1/camera-render/cameras":
                self._send_json(HTTPStatus.OK, manager.cameras())
                return
            if path == "/v1/camera-render/jobs":
                self._send_json(HTTPStatus.OK, {"ok": True, "items": manager.jobs()})
                return
            if path.startswith("/v1/camera-render/jobs/"):
                job_id = unquote(path.removeprefix("/v1/camera-render/jobs/"))
                job = next((item for item in manager.jobs() if item.get("job_id") == job_id), None)
                self._send_json(HTTPStatus.OK if job else HTTPStatus.NOT_FOUND, {"ok": bool(job), "job": job})
                return
            if path == "/v1/camera-render/logs":
                self._send_json(HTTPStatus.OK, manager.logs())
                return
            if path.startswith("/v1/camera-render/artifacts/"):
                artifact = manager.artifact_path(unquote(path.removeprefix("/v1/camera-render/artifacts/")))
                if artifact is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "artifact not found"})
                    return
                self._send_file(artifact)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        manager = self.server.manager
        try:
            if path == "/v1/camera-render/capture-render":
                payload = manager.capture_render()
                self._send_json(HTTPStatus.OK if payload.get("ok") else HTTPStatus.BAD_GATEWAY, payload)
                return
            if path == "/v1/camera-render/watch/start":
                self._send_json(HTTPStatus.OK, manager.start_watch())
                return
            if path == "/v1/camera-render/watch/stop":
                self._send_json(HTTPStatus.OK, manager.stop_watch())
                return
            if path == "/v1/camera-render/watch/mode":
                payload = self._read_json()
                mode = str(payload.get("mode") or "")
                if not mode and "launchOrFocus" in payload:
                    mode = "launch_or_focus" if bool(payload.get("launchOrFocus")) else "launch"
                if mode not in VALID_CHROME_TRIGGER_MODES:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "mode must be launch or launch_or_focus"})
                    return
                self._send_json(HTTPStatus.OK, manager.set_chrome_trigger_mode(mode))
                return
            if path == "/v1/camera-render/print-last":
                payload = manager.print_last()
                self._send_json(HTTPStatus.OK if payload.get("ok") else HTTPStatus.BAD_REQUEST, payload)
                return
            if path == "/v1/camera-render/stop":
                self._send_json(HTTPStatus.OK, manager.stop_watch())
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[camera-render-bridge] {self.address_string()} - {fmt % args}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Chrome Camera Anime bridge.")
    parser.add_argument("--host", default=os.environ.get("CAMERA_RENDER_BRIDGE_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CAMERA_RENDER_BRIDGE_PORT", DEFAULT_PORT)))
    parser.add_argument("--runtime-dir", type=Path, default=RUNTIME_DIR)
    parser.add_argument("--printer-url", default=os.environ.get("OPENCLAW_PRINTER_BRIDGE_URL", f"http://127.0.0.1:{DEFAULT_PRINTER_PORT}"))
    parser.add_argument("--start-watch", dest="start_watch", action="store_true")
    parser.add_argument("--no-start-watch", dest="start_watch", action="store_false")
    parser.set_defaults(start_watch=parse_bool(os.environ.get("CAMERA_RENDER_START_WATCH"), True))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manager = CameraRenderManager(
        runtime_dir=args.runtime_dir,
        printer_url=args.printer_url,
        start_watch=args.start_watch,
    )
    server = CameraRenderHTTPServer((args.host, args.port), Handler, manager=manager)

    def handle_stop(_signum: int, _frame: Any) -> None:
        manager.stop()
        server.server_close()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    print(f"[camera-render-bridge] listening at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    finally:
        manager.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
