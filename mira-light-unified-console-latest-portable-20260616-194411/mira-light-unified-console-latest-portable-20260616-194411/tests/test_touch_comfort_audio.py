from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
BRIDGE_DIR = ROOT / "tools" / "mira_light_bridge"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

from bridge_server import BridgeHTTPServer, BridgeHandler
from mira_light_runtime import MiraLightRuntime


def request_json(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        finally:
            exc.close()


class TouchComfortAudioTest(unittest.TestCase):
    def _start_server(self, server):
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return thread

    def test_long_touch_comfort_plays_audio_without_device_scene(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = MiraLightRuntime(base_url="http://127.0.0.1:9", dry_run=False, timeout_seconds=0.1)
            bridge_server = BridgeHTTPServer(
                ("127.0.0.1", 0),
                BridgeHandler,
                runtime=runtime,
                token="",
                ingest_root=Path(tmpdir) / "ingest",
            )
            bridge_thread = self._start_server(bridge_server)
            bridge_base_url = f"http://127.0.0.1:{bridge_server.server_address[1]}"

            try:
                with mock.patch.object(
                    runtime.audio_player,
                    "play_asset",
                    return_value={"ok": True, "description": "asset:test"},
                ) as play_asset:
                    status, result = request_json(
                        f"{bridge_base_url}/v1/mira-light/trigger",
                        method="POST",
                        payload={
                            "event": "long_touch_comfort",
                            "payload": {"asset_name": "speech/voice_demo_tired_line.aiff"},
                        },
                    )

                self.assertEqual(status, 200)
                self.assertTrue(result["ok"])
                play_asset.assert_called_once_with(
                    "speech/voice_demo_tired_line.aiff",
                    wait=False,
                    allow_missing=True,
                )
                self.assertEqual(result["runtime"]["lastTrigger"]["scene"], "comfort_sound")
                self.assertIsNone(result["runtime"]["lastError"])
            finally:
                bridge_server.shutdown()
                bridge_server.server_close()
                bridge_thread.join(timeout=3)

    def test_stop_comfort_sound_stops_audio_without_device_scene(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = MiraLightRuntime(base_url="http://127.0.0.1:9", dry_run=False, timeout_seconds=0.1)
            bridge_server = BridgeHTTPServer(
                ("127.0.0.1", 0),
                BridgeHandler,
                runtime=runtime,
                token="",
                ingest_root=Path(tmpdir) / "ingest",
            )
            bridge_thread = self._start_server(bridge_server)
            bridge_base_url = f"http://127.0.0.1:{bridge_server.server_address[1]}"

            try:
                with mock.patch.object(runtime.audio_player, "stop_all") as stop_all:
                    status, result = request_json(
                        f"{bridge_base_url}/v1/mira-light/trigger",
                        method="POST",
                        payload={"event": "stop_comfort_sound", "payload": {"release_reason": "manual"}},
                    )

                self.assertEqual(status, 200)
                self.assertTrue(result["ok"])
                stop_all.assert_called_once_with()
                self.assertEqual(result["runtime"]["lastTrigger"]["scene"], "comfort_sound_stop")
                self.assertIsNone(result["runtime"]["lastError"])
            finally:
                bridge_server.shutdown()
                bridge_server.server_close()
                bridge_thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
