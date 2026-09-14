"""Tests for the enhanced Lingzhu SDK."""

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from scripts.mira_lingzhu_sdk import (
    LingzhuConfig,
    LingzhuError,
    LingzhuMessage,
    LingzhuSDK,
    MultimodalMessageBuilder,
    SessionManager,
    StreamingResponseHandler,
)


# ---------------------------------------------------------------------------
# Mock server for integration-style tests
# ---------------------------------------------------------------------------

class _MockLingzhuHandler(BaseHTTPRequestHandler):
    """Mock Lingzhu adapter that simulates /v1/chat and SSE responses."""

    last_request: dict[str, Any] | None = None

    def do_GET(self):  # noqa: N802
        if "/health" in self.path:
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body)
        _MockLingzhuHandler.last_request = {
            "path": self.path,
            "payload": payload,
        }

        if "/v1/chat" in self.path:
            response = {
                "ok": True,
                "text": "你好呀，我是 Mira",
                "upstream": {"model": "test-model"},
            }
            encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        elif "/metis/agent/api/sse" in self.path:
            # Simulate SSE response
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for token in ["你好", "呀", "，", "我是", " Mira"]:
                event = f"data: {json.dumps({'text': token})}\n\n"
                self.wfile.write(event.encode("utf-8"))
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):  # noqa: A003
        return


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class LingzhuConfigTest(unittest.TestCase):
    def test_from_env_defaults(self):
        config = LingzhuConfig.from_env()
        self.assertEqual(config.agent_id, "main")
        self.assertEqual(config.protocol, "auto")
        self.assertTrue(config.stream_enabled)
        self.assertTrue(config.health_check_enabled)

    def test_from_env_override(self):
        import os
        old = os.environ.get("MIRA_LIGHT_LINGZHU_AGENT_ID")
        os.environ["MIRA_LIGHT_LINGZHU_AGENT_ID"] = "test-agent"
        try:
            config = LingzhuConfig.from_env()
            self.assertEqual(config.agent_id, "test-agent")
        finally:
            if old is not None:
                os.environ["MIRA_LIGHT_LINGZHU_AGENT_ID"] = old
            else:
                os.environ.pop("MIRA_LIGHT_LINGZHU_AGENT_ID", None)


class MultimodalMessageBuilderTest(unittest.TestCase):
    def test_build_text_only_message(self):
        msg = MultimodalMessageBuilder.build_vision_message("你好")
        self.assertEqual(msg.text, "你好")
        self.assertEqual(msg.images, [])
        self.assertEqual(msg.role, "user")

    def test_build_with_vision_context(self):
        ctx = {"vision_context": {"scene_summary": "一个人在喝咖啡"}}
        msg = MultimodalMessageBuilder.build_vision_message("看看这是什么", vision_context=ctx)
        self.assertIn("视觉感知", msg.text)
        self.assertIn("一个人在喝咖啡", msg.text)

    def test_encode_frame(self):
        import numpy as np
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:] = (50, 100, 150)
        data_uri = MultimodalMessageBuilder.encode_frame(frame, max_width=50)
        self.assertTrue(data_uri.startswith("data:image/jpeg;base64,"))


class SessionManagerTest(unittest.TestCase):
    def test_create_and_get_session(self):
        mgr = SessionManager()
        session = mgr.create_session(user_id="user-1", additional_user_ids=["ctx-1"])
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, "user-1")
        self.assertEqual(session.additional_user_ids, ["ctx-1"])

        retrieved = mgr.get_session(session.session_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.session_id, session.session_id)

    def test_bind_memory_context(self):
        mgr = SessionManager()
        session = mgr.create_session()
        mgr.bind_memory_context(session, ["mira-light-bridge", "mira-vision-context"])
        self.assertIn("mira-light-bridge", session.additional_user_ids)
        self.assertIn("mira-vision-context", session.additional_user_ids)

    def test_unbind_memory_context(self):
        mgr = SessionManager()
        session = mgr.create_session(additional_user_ids=["a", "b", "c"])
        mgr.unbind_memory_context(session, ["b"])
        self.assertEqual(session.additional_user_ids, ["a", "c"])

    def test_end_session(self):
        mgr = SessionManager()
        session = mgr.create_session()
        ended = mgr.end_session(session.session_id)
        self.assertIsNotNone(ended)
        self.assertIsNone(mgr.get_session(session.session_id))

    def test_history_tracking(self):
        mgr = SessionManager()
        session = mgr.create_session()
        session.add_message(LingzhuMessage(role="user", text="你好"))
        session.add_message(LingzhuMessage(role="assistant", text="你好呀"))
        history = mgr.get_history(session.session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].text, "你好")
        self.assertEqual(history[1].text, "你好呀")


class LingzhuSDKIntegrationTest(unittest.TestCase):
    """Integration tests using a mock HTTP server."""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _MockLingzhuHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)
        cls.server.server_close()

    def _make_sdk(self) -> LingzhuSDK:
        config = LingzhuConfig(
            base_url=f"http://127.0.0.1:{self.port}",
            auth_ak="test-ak",
            agent_id="test-agent",
            protocol="v1",
            stream_enabled=True,
            health_check_enabled=False,
            auto_reconnect=False,
            max_retries=1,
        )
        return LingzhuSDK(config)

    def test_health_check(self):
        config = LingzhuConfig(
            base_url=f"http://127.0.0.1:{self.port}",
            health_check_enabled=False,
        )
        sdk = LingzhuSDK(config)
        self.assertTrue(sdk.check_health())
        self.assertTrue(sdk.is_healthy)

    def test_basic_chat(self):
        sdk = self._make_sdk()
        response = sdk.chat("你好")
        self.assertEqual(response.text, "你好呀，我是 Mira")
        self.assertEqual(response.model, "test-model")

    def test_chat_with_session(self):
        sdk = self._make_sdk()
        session = sdk.create_session(user_id="test-user")
        sdk.bind_embodied_memory(session)
        response = sdk.chat_in_session(session, "你好")
        self.assertEqual(response.text, "你好呀，我是 Mira")
        self.assertEqual(len(session.history), 2)  # user + assistant

    def test_streaming_chat(self):
        sdk = self._make_sdk()
        tokens = list(sdk.chat_stream("讲个故事"))
        full_text = "".join(tokens)
        self.assertIn("你好", full_text)
        self.assertIn("Mira", full_text)

    def test_multimodal_chat(self):
        import numpy as np
        sdk = self._make_sdk()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        response = sdk.chat_with_image("看看这是什么", frame=frame)
        self.assertEqual(response.text, "你好呀，我是 Mira")
        # Verify images were sent in the request
        self.assertIsNotNone(_MockLingzhuHandler.last_request)
        payload = _MockLingzhuHandler.last_request["payload"]
        messages = payload.get("message", [])
        # The last message should have images
        last_msg = messages[-1] if messages else {}
        self.assertIn("images", last_msg)
        self.assertTrue(len(last_msg["images"]) > 0)

    def test_retry_on_failure(self):
        # Point to a non-existent server to trigger retries
        config = LingzhuConfig(
            base_url="http://127.0.0.1:1",  # port 1 should fail
            auth_ak="test-ak",
            health_check_enabled=False,
            auto_reconnect=False,
            max_retries=2,
            retry_delay=0.1,
        )
        sdk = LingzhuSDK(config)
        with self.assertRaises(LingzhuError):
            sdk.chat("你好")


class StreamingResponseHandlerTest(unittest.TestCase):
    def test_extract_text_from_various_formats(self):
        self.assertEqual(StreamingResponseHandler._extract_text({"text": "hello"}), "hello")
        self.assertEqual(StreamingResponseHandler._extract_text({"content": "world"}), "world")
        self.assertEqual(StreamingResponseHandler._extract_text({"choices": [{"text": "choice"}]}), "choice")
        self.assertEqual(StreamingResponseHandler._extract_text({"delta": {"text": "delta"}}), "delta")
        self.assertEqual(StreamingResponseHandler._extract_text({"foo": "bar"}), "")


if __name__ == "__main__":
    unittest.main()
