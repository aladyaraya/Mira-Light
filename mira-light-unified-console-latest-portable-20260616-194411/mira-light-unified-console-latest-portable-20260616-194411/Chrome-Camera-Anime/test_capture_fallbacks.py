import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RUNTIME_DIR = Path.home() / ".openclaw-chrome-camera-anime" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

import expression_monitor_control
import pipeline


STRICT_FAILURE_DETECTION_A = {
    "largest_face_area_ratio": 0.07356480744522553,
    "face_count": 2,
    "faces": [
        {
            "center_y": 0.09705998376011848,
            "area_ratio": 0.032369852621004114,
            "y": -0.022884171456098557,
            "x": 0.41897058486938477,
            "width": 0.13493718206882477,
            "center_x": 0.48643917590379715,
            "height": 0.23988831043243408,
            "edge_margin": -0.022884171456098557,
        },
        {
            "center_y": 0.7793998420238495,
            "area_ratio": 0.07356480744522553,
            "y": 0.5985809564590454,
            "x": 0.813334047794342,
            "width": 0.20342124998569489,
            "center_x": 0.9150446727871895,
            "height": 0.36163777112960815,
            "edge_margin": -0.016755297780036926,
        },
    ],
}

STRICT_FAILURE_DETECTION_B = {
    "face_count": 2,
    "largest_face_area_ratio": 0.13348062290939922,
    "faces": [
        {
            "width": 0.2740125060081482,
            "x": 0.019107723608613014,
            "y": 0.3663087487220764,
            "area_ratio": 0.13348062290939922,
            "height": 0.48713332414627075,
            "center_x": 0.1561139766126871,
            "center_y": 0.6098754107952118,
            "edge_margin": 0.019107723608613014,
        },
        {
            "edge_margin": -0.06341363489627838,
            "height": 0.25728318095207214,
            "y": -0.06341363489627838,
            "center_y": 0.06522795557975769,
            "area_ratio": 0.03723448277968666,
            "x": 0.5394119024276733,
            "center_x": 0.6117727980017662,
            "width": 0.14472179114818573,
        },
    ],
}


class CaptureFallbacksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_select_best_available_subject_falls_back_when_strict_selection_fails(self) -> None:
        self.assertIsNone(pipeline.select_primary_subject(STRICT_FAILURE_DETECTION_A))

        selection = pipeline.select_best_available_subject(STRICT_FAILURE_DETECTION_A)

        self.assertIsNotNone(selection)
        self.assertEqual("best_effort_fallback", selection["reason"])
        self.assertEqual(0, selection["selected_face_index"])
        self.assertEqual(2, selection["candidate_face_count"])

    def test_capture_best_portrait_uses_best_effort_subject(self) -> None:
        artifact_dir = self.root / "artifacts"
        latest_image_path = self.root / "latest.jpg"
        latest_image_path.write_bytes(b"seed")
        capture_calls = 0

        def fake_capture(*, capture_script: Path, latest_image_path: Path) -> Path:
            nonlocal capture_calls
            capture_calls += 1
            latest_image_path.write_bytes(f"frame-{capture_calls}".encode("utf-8"))
            return latest_image_path

        result = pipeline.capture_best_portrait(
            artifact_dir=artifact_dir,
            capture_script=self.root / "capture-script",
            latest_image_path=latest_image_path,
            detector_script=self.root / "detector",
            burst_count=1,
            burst_interval_seconds=0.0,
            capture_image=fake_capture,
            detect_faces_impl=lambda *_args, **_kwargs: STRICT_FAILURE_DETECTION_B,
        )

        self.assertEqual("best_effort_fallback", result["subject_selection"]["reason"])
        self.assertEqual(0, result["subject_selection"]["selected_face_index"])
        self.assertTrue(Path(result["portrait_path"]).is_file())

    def test_capture_from_expression_monitor_uses_best_effort_subject(self) -> None:
        state_dir = self.root / "state"
        artifact_dir = self.root / "artifacts"
        state_dir.mkdir(parents=True, exist_ok=True)
        expression_monitor_control.pid_path(state_dir).write_text(str(os.getpid()), encoding="utf-8")
        expression_monitor_control.latest_output_path(state_dir).parent.mkdir(parents=True, exist_ok=True)
        expression_monitor_control.latest_output_path(state_dir).write_text(
            json.dumps({"face_detected": True}),
            encoding="utf-8",
        )
        expression_monitor_control.latest_frame_path(state_dir).write_bytes(b"frame")

        with mock.patch.object(
            pipeline,
            "detect_faces",
            return_value=STRICT_FAILURE_DETECTION_B,
        ):
            result = expression_monitor_control.capture_from_expression_monitor(
                state_dir,
                artifact_dir=artifact_dir,
                timeout_seconds=0.1,
                poll_interval=0.0,
            )

        self.assertEqual("best_effort_fallback", result["subject_selection"]["reason"])
        self.assertEqual(0, result["subject_selection"]["selected_face_index"])
        self.assertTrue(Path(result["portrait_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
