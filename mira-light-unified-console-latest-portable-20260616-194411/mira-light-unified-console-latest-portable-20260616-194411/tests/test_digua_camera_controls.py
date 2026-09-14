from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
CAMERA_DIR = ROOT / "Chrome-Camera-Anime"

if str(CAMERA_DIR) not in sys.path:
    sys.path.insert(0, str(CAMERA_DIR))

import digua_remote_render_pipeline as camera_pipeline


class DiguaCameraControlsTest(unittest.TestCase):
    def test_remote_capture_script_applies_v4l2_controls_before_ffmpeg(self) -> None:
        script = camera_pipeline.build_remote_capture_script(
            remote_device="/dev/video0",
            input_format="mjpeg",
            video_size="1280x720",
            remote_temp_path="/tmp/frame.jpg",
            camera_controls="white_balance_automatic=1,brightness=96,gamma=105",
        )

        controls_index = script.index("v4l2-ctl")
        ffmpeg_index = script.index("ffmpeg")
        self.assertLess(controls_index, ffmpeg_index)
        self.assertIn("--set-ctrl 'white_balance_automatic=1,brightness=96,gamma=105'", script)
        self.assertIn("capture_device='/dev/video0'", script)

    def test_remote_capture_script_omits_v4l2_controls_when_unset(self) -> None:
        script = camera_pipeline.build_remote_capture_script(
            remote_device="/dev/video0",
            input_format="mjpeg",
            video_size="1280x720",
            remote_temp_path="/tmp/frame.jpg",
            camera_controls="",
        )

        self.assertNotIn("v4l2-ctl", script)
        self.assertIn("ffmpeg", script)

    def test_remote_capture_script_can_auto_probe_video_devices(self) -> None:
        script = camera_pipeline.build_remote_capture_script(
            remote_device="auto",
            input_format="mjpeg",
            video_size="1280x720",
            remote_temp_path="/tmp/frame.jpg",
            camera_controls="",
        )

        self.assertIn("devices=$(ls /dev/video*", script)
        self.assertIn("No /dev/video* camera devices found", script)
        self.assertIn("for device in $devices", script)
        self.assertIn('-i "$device"', script)
        self.assertNotIn("() {", script)

    def test_ssh_command_quotes_remote_script_as_single_shell_argument(self) -> None:
        command = camera_pipeline.build_ssh_command(
            host="192.168.0.183",
            user="root",
            port=22,
            bind_address="",
            known_hosts_path=Path("/tmp/known-hosts"),
            connect_timeout=10,
            remote_script="echo one two\nprintf '%s\\n' done",
            batch_mode=True,
        )

        self.assertEqual(command[-3], "sh")
        self.assertEqual(command[-2], "-lc")
        self.assertIn("printf '\"'\"'%s\\n'\"'\"' done", command[-1])
        self.assertTrue(command[-1].startswith("'echo one two"))

    def test_camera_controls_reject_shell_metacharacters(self) -> None:
        with self.assertRaises(ValueError):
            camera_pipeline.normalize_camera_controls("brightness=96;reboot")

    def test_capture_writer_rejects_non_jpeg_payloads(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "does not look like a JPEG"):
                camera_pipeline.write_capture_image(b"x" * 600, Path(tmpdir), "bad")

    def test_capture_writer_rejects_tiny_payloads(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "too small"):
                camera_pipeline.write_capture_image(b"\xff\xd8\xff\xd9", Path(tmpdir), "tiny")

    def test_remote_capture_failure_summary_prefers_camera_message(self) -> None:
        summary = camera_pipeline.summarize_remote_capture_failure(
            "spawn ssh root@board sh -lc '...'\nroot@board's password:\n"
            "No /dev/video* camera devices found on remote board. Check cable.",
            "",
        )

        self.assertEqual(summary, "No /dev/video* camera devices found on remote board. Check cable.")

    def test_remote_capture_failure_summary_strips_echo_wrapper(self) -> None:
        summary = camera_pipeline.summarize_remote_capture_failure(
            'echo "No /dev/video* camera devices found on remote board. Check cable." >&2',
            "",
        )

        self.assertEqual(summary, "No /dev/video* camera devices found on remote board. Check cable.")


if __name__ == "__main__":
    unittest.main()
