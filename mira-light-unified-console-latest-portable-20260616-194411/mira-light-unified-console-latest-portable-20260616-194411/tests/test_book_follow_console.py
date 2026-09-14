from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
CONSOLE_DIR = ROOT / "mira-light-unified-director-console"

if str(CONSOLE_DIR) not in sys.path:
    sys.path.insert(0, str(CONSOLE_DIR))

import shenzhen_console


VALID_JPEG_BYTES = b"\xff\xd8" + (b"\x00" * 600) + b"\xff\xd9"


class DummyCameraSampler:
    def snapshot(self) -> dict:
        return {"ok": True, "latestFrame": None}


class RunningProcess:
    pid = 12345

    def poll(self) -> None:
        return None


def start_receiver(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class BookFollowConsoleTest(unittest.TestCase):
    def test_book_follow_default_receiver_avoids_common_port_collision(self) -> None:
        config = shenzhen_console.coerce_book_follow_config()

        self.assertEqual(config["receiverPort"], 18000)

    def test_book_follow_config_accepts_field_tuning_values(self) -> None:
        config = shenzhen_console.coerce_book_follow_config(
            {
                "receiverPort": "18000",
                "minSaturation": "55",
                "minColorRatio": "0.30",
                "tabletopTrackingUpdateMs": "160",
            }
        )

        self.assertEqual(config["receiverPort"], 18000)
        self.assertEqual(config["minSaturation"], "55")
        self.assertEqual(config["minColorRatio"], "0.30")
        self.assertEqual(config["tabletopTrackingUpdateMs"], "160")

    def test_book_follow_env_targets_yellow_book_tabletop_stack(self) -> None:
        config = shenzhen_console.coerce_book_follow_config({"minSaturation": "70"})
        env = shenzhen_console.build_book_follow_env(config)

        self.assertEqual(env["MIRA_LIGHT_DEFAULT_TARGET_MODE"], "tabletop_follow")
        self.assertEqual(env["MIRA_LIGHT_SCENE_ALLOWED_DETECTORS"], "book_cover_color")
        self.assertEqual(env["MIRA_LIGHT_TRACKING_ALLOWED_DETECTORS"], "book_cover_color")
        self.assertEqual(env["MIRA_LIGHT_TOUCH_HAND_ARM_MIN_CONFIDENCE"], "2.0")
        self.assertEqual(env["MIRA_LIGHT_HAND_AVOID_MIN_CONFIDENCE"], "2.0")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_COLOR_ENABLED"], "1")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_HUE_MIN"], "14")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_HUE_MAX"], "43")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_MIN_SATURATION"], "70")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_TRACKING_UPDATE_MS"], "160")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_MIN_COLOR_RATIO"], "0.22")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_MIN_RECTANGULARITY"], "0.46")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_MIN_SOLIDITY"], "0.72")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_MAX_ASPECT_RATIO"], "4.2")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_MIN_INNER_EDGE_RATIO"], "0.012")
        self.assertEqual(env["MIRA_LIGHT_TABLETOP_BOOK_MAX_CORNER_COUNT"], "6")

    def test_book_follow_summary_surfaces_detector_and_bridge_decision(self) -> None:
        event = {
            "tracking": {
                "target_present": True,
                "detector": "book_cover_color",
                "target_class": "book_cover_color",
                "target_subclass": "yellow_book",
                "target_mode": "tabletop_follow",
                "confidence": 0.91,
            },
            "control_hint": {"feedback_profile": "tabletop_book", "recommended_update_ms": 160},
        }
        bridge_state = {
            "lastDecision": {"action": "apply_tracking", "actionReason": "tabletop_book"},
            "runtimeState": {"trackingActive": True, "trackingTarget": {"profile": "tabletop_book"}},
        }

        summary = shenzhen_console.summarize_book_follow_event(event, bridge_state)

        self.assertTrue(summary["targetPresent"])
        self.assertEqual(summary["detector"], "book_cover_color")
        self.assertEqual(summary["targetSubclass"], "yellow_book")
        self.assertEqual(summary["feedbackProfile"], "tabletop_book")
        self.assertEqual(summary["recommendedUpdateMs"], 160)
        self.assertEqual(summary["bridgeAction"], "apply_tracking")

    def test_book_follow_forward_posts_latest_camera_frame_to_receiver(self) -> None:
        received: dict[str, object] = {}

        class ReceiverHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or "0")
                received["path"] = self.path
                received["seq"] = self.headers.get("X-Seq")
                received["body"] = self.rfile.read(length)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")

            def log_message(self, fmt: str, *args: object) -> None:
                return

        receiver, receiver_thread = start_receiver(ReceiverHandler)
        console_server = shenzhen_console.ShenzhenConsoleServer(
            ("127.0.0.1", 0),
            shenzhen_console.ShenzhenConsoleHandler,
            registry={"scenes": []},
            host="127.0.0.1",
            board_port=22,
            user="root",
            timeout_seconds=1.0,
            password="",
            camera_sampler=DummyCameraSampler(),
        )
        try:
            port = receiver.server_address[1]
            console_server.book_follow_config = shenzhen_console.coerce_book_follow_config(
                {"receiverHost": "127.0.0.1", "receiverPort": str(port)}
            )
            console_server.book_follow_process = RunningProcess()

            with TemporaryDirectory() as tmpdir:
                frame = Path(tmpdir) / "yellow-book.jpg"
                frame.write_bytes(VALID_JPEG_BYTES)

                result = console_server.forward_camera_frame_to_book_follow(frame, {})

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], 200)
            self.assertEqual(received["path"], "/upload")
            self.assertEqual(received["seq"], "yellow-book")
            self.assertEqual(received["body"], VALID_JPEG_BYTES)
            self.assertEqual(console_server.book_follow_last_forward["filename"], "yellow-book.jpg")
        finally:
            console_server.server_close()
            receiver.shutdown()
            receiver.server_close()
            receiver_thread.join(timeout=3)

    def test_book_follow_forward_skips_invalid_camera_frame(self) -> None:
        console_server = shenzhen_console.ShenzhenConsoleServer(
            ("127.0.0.1", 0),
            shenzhen_console.ShenzhenConsoleHandler,
            registry={"scenes": []},
            host="127.0.0.1",
            board_port=22,
            user="root",
            timeout_seconds=1.0,
            password="",
            camera_sampler=DummyCameraSampler(),
        )
        try:
            console_server.book_follow_config = shenzhen_console.coerce_book_follow_config({"receiverPort": 18000})
            console_server.book_follow_process = RunningProcess()

            with TemporaryDirectory() as tmpdir:
                frame = Path(tmpdir) / "bad-frame.jpg"
                frame.write_bytes(b"not a jpeg")

                result = console_server.forward_camera_frame_to_book_follow(frame, {})

            self.assertFalse(result["ok"])
            self.assertTrue(result["skipped"])
            self.assertEqual(result["reason"], "invalid JPEG frame")
            self.assertEqual(console_server.book_follow_last_forward["filename"], "bad-frame.jpg")
        finally:
            console_server.server_close()

    def test_camera_sampler_runs_after_capture_callback_without_breaking_capture(self) -> None:
        camera_console = shenzhen_console.camera_console_module
        original_capture = camera_console.digua_remote_render_pipeline.capture_remote_image
        callback_paths: list[str] = []

        def fake_capture_remote_image(**kwargs):
            image_path = Path(kwargs["capture_dir"]) / "frame.jpg"
            image_path.write_bytes(b"jpeg payload")
            return image_path

        with TemporaryDirectory() as tmpdir:
            camera_console.digua_remote_render_pipeline.capture_remote_image = fake_capture_remote_image
            sampler = camera_console.CameraSampler(
                board_host="127.0.0.1",
                board_port=22,
                board_user="root",
                board_password="",
                interval_seconds=2.0,
                capture_dir=Path(tmpdir),
                remote_device="/dev/video0",
                input_format="mjpeg",
                video_size="1280x720",
                remote_temp_path="/tmp/frame.jpg",
                camera_controls="",
                bind_address="",
                known_hosts_path=Path(tmpdir) / "known_hosts",
                connect_timeout=1,
                capture_timeout=1,
                ssh_retries=0,
                ssh_retry_delay_seconds=0.0,
            )
            sampler.set_after_capture(
                lambda image_path, frame: callback_paths.append(image_path.name) or {"ok": True, "target": "book-follow"}
            )
            try:
                frame = sampler.capture_once()
            finally:
                camera_console.digua_remote_render_pipeline.capture_remote_image = original_capture

        self.assertEqual(callback_paths, ["frame.jpg"])
        self.assertEqual(frame["postCapture"]["target"], "book-follow")


if __name__ == "__main__":
    unittest.main()
