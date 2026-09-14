#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8795
DEFAULT_BRIDGE_URL = "http://127.0.0.1:9795"
DEFAULT_TIMEOUT = 480.0


class ConsoleHTTPServer(ThreadingHTTPServer):
    def __init__(self, *args, bridge_url: str, timeout_seconds: float, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bridge_url = bridge_url.rstrip("/")
        self.timeout_seconds = timeout_seconds


class Handler(BaseHTTPRequestHandler):
    server: ConsoleHTTPServer

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length else b""

    def _proxy(self, method: str, bridge_path: str, body: bytes | None = None) -> None:
        request = Request(
            f"{self.server.bridge_url}{bridge_path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.server.timeout_seconds) as response:
                raw = response.read()
                status = response.status
        except HTTPError as exc:
            raw = exc.read()
            status = exc.code
        except URLError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": f"Bridge unavailable: {exc.reason}"})
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": str(exc)})
            return

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        if not str(candidate).startswith(str(WEB_ROOT.resolve())) or not candidate.is_file():
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
        mapping = {
            "/api/health": "/health",
            "/api/status": "/v1/camera-render/status",
            "/api/cameras": "/v1/camera-render/cameras",
            "/api/jobs": "/v1/camera-render/jobs",
            "/api/logs": "/v1/camera-render/logs",
        }
        if path in mapping:
            self._proxy("GET", mapping[path])
            return
        if path.startswith("/api/jobs/"):
            self._proxy("GET", path.replace("/api/jobs/", "/v1/camera-render/jobs/", 1))
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        mapping = {
            "/api/capture-render": "/v1/camera-render/capture-render",
            "/api/watch/start": "/v1/camera-render/watch/start",
            "/api/watch/stop": "/v1/camera-render/watch/stop",
            "/api/watch/mode": "/v1/camera-render/watch/mode",
            "/api/print-last": "/v1/camera-render/print-last",
        }
        if path in mapping:
            self._proxy("POST", mapping[path], self._read_body() or b"{}")
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[camera-render-console] {self.address_string()} - {fmt % args}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the Chrome Camera Anime browser console.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--bridge-base-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)
    server = ConsoleHTTPServer(
        (args.host, args.port),
        Handler,
        bridge_url=args.bridge_base_url,
        timeout_seconds=args.timeout,
    )
    print(f"[camera-render-console] listening at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
