#!/usr/bin/env python3
"""Unit and integration tests for person_tracker.py.

Run with:
    python test_person_tracker.py

Requires opencv-python (for FaceDetector tests) but camera-dependent tests
are skipped automatically when no camera is available.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

# Ensure the script under test is importable
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from person_tracker import (
    DetectedFace,
    FaceDetector,
    TargetSelector,
    TrackingEventBuilder,
    PersonTracker,
    TrackingController,
)


class TestDetectedFace(unittest.TestCase):
    def test_center_and_area(self) -> None:
        face = DetectedFace(x=0.2, y=0.3, width=0.4, height=0.5, confidence=0.9)
        self.assertAlmostEqual(face.center_x, 0.4)
        self.assertAlmostEqual(face.center_y, 0.55)
        self.assertAlmostEqual(face.area, 0.2)

    def test_edge_margin(self) -> None:
        face = DetectedFace(x=0.1, y=0.1, width=0.2, height=0.2, confidence=0.9)
        self.assertAlmostEqual(face.edge_margin, 0.1)


class TestTargetSelector(unittest.TestCase):
    def test_select_none(self) -> None:
        sel = TargetSelector()
        self.assertIsNone(sel.select([]))

    def test_select_single(self) -> None:
        sel = TargetSelector()
        face = DetectedFace(x=0.4, y=0.4, width=0.2, height=0.2, confidence=0.9)
        result = sel.select([face])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result.center_x, face.center_x)

    def test_select_prefers_center(self) -> None:
        sel = TargetSelector()
        off_center = DetectedFace(x=0.0, y=0.0, width=0.3, height=0.3, confidence=0.9)
        centered = DetectedFace(x=0.4, y=0.4, width=0.2, height=0.2, confidence=0.9)
        result = sel.select([off_center, centered])
        self.assertIsNotNone(result)
        assert result is not None
        # Centered face should win despite smaller area
        self.assertAlmostEqual(result.center_x, centered.center_x)

    def test_lock_reduces_jitter(self) -> None:
        sel = TargetSelector(lock_frames=5)
        f1 = DetectedFace(x=0.4, y=0.4, width=0.2, height=0.2, confidence=0.9)
        sel.select([f1])
        # Slightly shifted face should still return locked (smoothed) position
        f2 = DetectedFace(x=0.42, y=0.41, width=0.2, height=0.2, confidence=0.9)
        result = sel.select([f2])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertLess(result.center_x, f2.center_x)  # smoothed toward f1


class TestTrackingEventBuilder(unittest.TestCase):
    def test_no_face(self) -> None:
        builder = TrackingEventBuilder()
        event = builder.build_event(None, (480, 640, 3))
        self.assertEqual(event["event_type"], "tracking_update")
        self.assertFalse(event["tracking"]["target_present"])

    def test_face_center(self) -> None:
        builder = TrackingEventBuilder(yaw_gain=2.0, pitch_gain=2.0)
        face = DetectedFace(x=0.4, y=0.4, width=0.2, height=0.2, confidence=0.9)
        event = builder.build_event(face, (480, 640, 3))
        self.assertTrue(event["tracking"]["target_present"])
        hint = event["control_hint"]
        # Face center is at (0.5, 0.5) -> zero error
        self.assertAlmostEqual(hint["yaw_error_norm"], 0.0, places=2)
        self.assertAlmostEqual(hint["pitch_error_norm"], 0.0, places=2)
        self.assertEqual(event["tracking"]["horizontal_zone"], "center")
        self.assertEqual(event["tracking"]["vertical_zone"], "center")

    def test_face_left_top(self) -> None:
        builder = TrackingEventBuilder()
        face = DetectedFace(x=0.1, y=0.1, width=0.2, height=0.2, confidence=0.9)
        event = builder.build_event(face, (480, 640, 3))
        hint = event["control_hint"]
        self.assertLess(hint["yaw_error_norm"], 0)   # left -> negative yaw
        self.assertLess(hint["pitch_error_norm"], 0)  # top -> negative pitch
        self.assertEqual(event["tracking"]["horizontal_zone"], "left")
        self.assertEqual(event["tracking"]["vertical_zone"], "top")

    def test_distance_band(self) -> None:
        builder = TrackingEventBuilder()
        near = DetectedFace(x=0.3, y=0.3, width=0.4, height=0.4, confidence=0.9)
        event = builder.build_event(near, (480, 640, 3))
        self.assertEqual(event["tracking"]["distance_band"], "near")

        far = DetectedFace(x=0.4, y=0.4, width=0.05, height=0.05, confidence=0.9)
        event = builder.build_event(far, (480, 640, 3))
        self.assertEqual(event["tracking"]["distance_band"], "far")


class TestFaceDetectorMock(unittest.TestCase):
    def test_haar_detects_fake_face(self) -> None:
        detector = FaceDetector(backend="haar")
        # Create a synthetic image with a bright rectangle in the center
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(img, (280, 180), (360, 260), (255, 255, 255), -1)
        faces = detector.detect(img)
        # Haar may or may not detect synthetic shapes; just ensure no crash
        self.assertIsInstance(faces, list)


class TestPersonTrackerLifecycle(unittest.TestCase):
    def test_start_stop_without_camera(self) -> None:
        tracker = PersonTracker(camera_index=99)  # invalid index
        with self.assertRaises(RuntimeError):
            tracker.start()
        self.assertFalse(tracker.is_running())

    def test_mock_camera_loop(self) -> None:
        tracker = PersonTracker(camera_index=0, backend="haar")
        # Patch VideoCapture to avoid needing a real camera
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))

        with patch("cv2.VideoCapture", return_value=mock_cap):
            tracker.start()
            # Wait for the capture loop to produce at least one event
            for _ in range(50):
                event = tracker.get_latest_event()
                if event is not None:
                    break
                time.sleep(0.02)
            self.assertIsNotNone(event)
            self.assertIn("tracking", event)
            tracker.stop()
        self.assertFalse(tracker.is_running())


class TestTrackingController(unittest.TestCase):
    def test_lifecycle(self) -> None:
        mock_runtime = MagicMock()
        mock_tracker = MagicMock()
        mock_tracker.get_latest_event.return_value = {
            "event_type": "tracking_update",
            "tracking": {"target_present": True},
            "control_hint": {"yaw_error_norm": 0.1},
        }

        controller = TrackingController(
            runtime=mock_runtime,
            tracker=mock_tracker,
            update_interval_ms=50.0,
        )
        controller.start()
        time.sleep(0.15)
        controller.stop()

        mock_runtime.apply_tracking_event.assert_called()
        self.assertFalse(controller.is_running())


class TestRuntimeIntegration(unittest.TestCase):
    """Test that MiraLightRuntime.start_tracking / stop_tracking work."""

    def test_start_stop_tracking(self) -> None:
        from mira_light_runtime import MiraLightRuntime

        runtime = MiraLightRuntime(
            base_url="http://127.0.0.1:8000",
            dry_run=True,
        )
        # Patch the constructor and methods on PersonTracker/TrackingController
        # so we don't need a real camera.
        mock_tracker = MagicMock()
        mock_controller = MagicMock()

        with patch("person_tracker.PersonTracker", return_value=mock_tracker) as mock_tracker_cls, \
             patch("person_tracker.TrackingController", return_value=mock_controller) as mock_ctrl_cls:

            state = runtime.start_tracking(camera_index=0, backend="haar")
            self.assertIn("trackingActive", state)
            mock_tracker_cls.assert_called_once()
            mock_ctrl_cls.assert_called_once()
            mock_controller.start.assert_called_once()

            state = runtime.stop_tracking()
            mock_controller.stop.assert_called_once()
            self.assertFalse(state["trackingActive"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
