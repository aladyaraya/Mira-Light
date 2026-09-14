from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


VOICE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = VOICE_ROOT / "tools" / "mira_light_bridge"
SCRIPTS_DIR = VOICE_ROOT / "scripts"
for path in [str(TOOLS_DIR), str(SCRIPTS_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from bridge_server import BridgeHTTPServer, BridgeHandler, summarize_voice_trace_data  # noqa: E402
from mira_light_runtime import MiraLightRuntime  # noqa: E402


class MiraLightBridgeRootTest(unittest.TestCase):
    def start_bridge(self, tmpdir: str) -> tuple[BridgeHTTPServer, threading.Thread]:
        runtime = MiraLightRuntime(base_url="tcp://127.0.0.1:9527", dry_run=True)
        server = BridgeHTTPServer(
            ("127.0.0.1", 0),
            BridgeHandler,
            runtime=runtime,
            token="",
            ingest_root=Path(tmpdir) / "ingest",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def test_root_returns_operator_status_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server, thread = self.start_bridge(tmpdir)
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/"
                request = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(request, timeout=3) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "mira-light-bridge")
        self.assertEqual(payload["links"]["health"], "/health")
        self.assertEqual(payload["links"]["scenes"], "/v1/mira-light/scenes")
        self.assertEqual(payload["links"]["voiceLab"], "/voice-lab")
        self.assertTrue(payload["runtime"]["dryRun"])

    def test_voice_lab_page_renders_pipeline_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server, thread = self.start_bridge(tmpdir)
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/voice-lab"
                request = urllib.request.Request(url, headers={"Accept": "text/html"})
                with urllib.request.urlopen(request, timeout=3) as response:
                    html = response.read().decode("utf-8")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertIn("Mira Voice Lab", html)
        self.assertIn("/v1/mira-light/voice-lab/status", html)
        self.assertIn("/v1/mira-light/voice-lab/plan", html)
        self.assertIn("trace-emotion", html)

    def test_voice_trace_summary_extracts_nested_planner_result(self) -> None:
        summary = summarize_voice_trace_data(
            {
                "transcript": "我好累啊",
                "plan": {
                    "reply": "累了吗？休息吧",
                    "emotion": "warm_caring",
                    "intent": {"name": "sleep", "confidence": 0.9},
                    "action": {"type": "scene", "name": "voice_demo_tired"},
                },
            }
        )

        self.assertEqual(summary["transcript"], "我好累啊")
        self.assertEqual(summary["reply"], "累了吗？休息吧")
        self.assertEqual(summary["emotion"], "warm_caring")
        self.assertEqual(summary["intent"], "sleep")
        self.assertEqual(summary["action"], {"type": "scene", "name": "voice_demo_tired"})

    def test_voice_lab_plan_dispatches_structured_local_plan_to_dry_run_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server, thread = self.start_bridge(tmpdir)
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/v1/mira-light/voice-lab/plan"
                body = json.dumps(
                    {
                        "transcript": "Mira 跳个舞吧",
                        "useStepFun": False,
                        "dispatch": True,
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                request = urllib.request.Request(
                    url,
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["plan"]["reply"], "啾。")
        self.assertEqual(payload["plan"]["emotion"], "happy")
        self.assertEqual(payload["plan"]["action"], {"type": "scene", "name": "celebrate"})
        self.assertEqual(payload["delivery"]["target"], "/v1/mira-light/run-scene")
        self.assertTrue(payload["delivery"]["response"]["runtime"]["dryRun"])

    def test_get_post_only_scene_endpoint_returns_method_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server, thread = self.start_bridge(tmpdir)
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/v1/mira-light/run-scene"
                request = urllib.request.Request(url, headers={"Accept": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=3)
                body = raised.exception.read().decode("utf-8")
                payload = json.loads(body)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertEqual(raised.exception.code, 405)
        self.assertEqual(payload["error"], "method_not_allowed")
        self.assertEqual(payload["method"], "POST")
        self.assertEqual(payload["example"]["scene"], "celebrate")

    def test_trigger_endpoint_can_run_synchronously_for_hardware_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server, thread = self.start_bridge(tmpdir)
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/v1/mira-light/trigger"
                body = json.dumps(
                    {
                        "event": "voice_tired",
                        "async": False,
                        "payload": {"transcript": "我好累啊", "silentMode": True},
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                request = urllib.request.Request(
                    url,
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["runtime"]["running"])
        self.assertEqual(payload["runtime"]["lastFinishedScene"], "voice_demo_tired")
        self.assertIsNone(payload["runtime"]["lastError"])


if __name__ == "__main__":
    unittest.main()
