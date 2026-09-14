#!/usr/bin/env python3
"""Real-time person tracking for Mira Light using OpenCV.

This module provides face/person detection from a live camera stream and
generates tracking events compatible with MiraLightRuntime.apply_tracking_event().

Architecture:
    Camera -> FaceDetector -> TargetSelector -> TrackingEventBuilder -> MiraLightRuntime

Usage:
    # Standalone test
    python person_tracker.py --camera 0 --preview

    # Integrated with Mira Light runtime
    from person_tracker import PersonTracker, TrackingController
    tracker = PersonTracker(camera_index=0)
    controller = TrackingController(runtime, tracker)
    controller.start()
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Detection models
# ---------------------------------------------------------------------------

# OpenCV DNN face detector model files (optional, falls back to Haar cascade)
DNN_PROTO_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
DNN_MODEL_URL = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"

# Haar cascade is bundled with OpenCV
HAAR_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


@dataclass
class DetectedFace:
    """A detected face with normalized coordinates."""
    x: float          # normalized left   [0, 1]
    y: float          # normalized top    [0, 1]
    width: float      # normalized width  [0, 1]
    height: float     # normalized height [0, 1]
    confidence: float # detection confidence [0, 1]

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def edge_margin(self) -> float:
        """Minimum distance from face edges to image borders."""
        return min(self.x, self.y, 1.0 - (self.x + self.width), 1.0 - (self.y + self.height))


# ---------------------------------------------------------------------------
# FaceDetector
# ---------------------------------------------------------------------------

class FaceDetector:
    """Detect faces in an image frame.

    Supports three backends:
    - "dnn": OpenCV DNN face detector (most accurate, requires model files)
    - "haar": Haar cascade (fast, built-in, less accurate)
    - "swift": Call the existing detect_faces.swift script (macOS only)
    """

    def __init__(self, backend: str = "haar", *, swift_script: Path | None = None) -> None:
        self.backend = backend
        self.swift_script = swift_script
        self._dnn_net: cv2.dnn.Net | None = None
        self._haar_cascade: cv2.CascadeClassifier | None = None
        self._init_backend()

    def _init_backend(self) -> None:
        if self.backend == "dnn":
            self._init_dnn()
        elif self.backend == "haar":
            self._init_haar()
        elif self.backend == "swift":
            if not self.swift_script or not self.swift_script.is_file():
                raise RuntimeError("Swift backend requires --swift-script path")
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _init_dnn(self) -> None:
        proto = Path.home() / ".cache" / "mira-light" / "face_detector.prototxt"
        model = Path.home() / ".cache" / "mira-light" / "face_detector.caffemodel"
        if not proto.is_file() or not model.is_file():
            proto.parent.mkdir(parents=True, exist_ok=True)
            self._download_file(DNN_PROTO_URL, proto)
            self._download_file(DNN_MODEL_URL, model)
        self._dnn_net = cv2.dnn.readNetFromCaffe(str(proto), str(model))

    @staticmethod
    def _download_file(url: str, dest: Path) -> None:
        import urllib.request
        print(f"[tracker] downloading {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)

    def _init_haar(self) -> None:
        self._haar_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
        if self._haar_cascade.empty():
            raise RuntimeError(f"Failed to load Haar cascade: {HAAR_CASCADE_PATH}")

    def detect(self, frame: np.ndarray) -> list[DetectedFace]:
        if self.backend == "dnn":
            return self._detect_dnn(frame)
        if self.backend == "haar":
            return self._detect_haar(frame)
        if self.backend == "swift":
            return self._detect_swift(frame)
        return []

    def _detect_dnn(self, frame: np.ndarray) -> list[DetectedFace]:
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
        assert self._dnn_net is not None
        self._dnn_net.setInput(blob)
        detections = self._dnn_net.forward()

        faces: list[DetectedFace] = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < 0.5:
                continue
            x1 = float(detections[0, 0, i, 3])
            y1 = float(detections[0, 0, i, 4])
            x2 = float(detections[0, 0, i, 5])
            y2 = float(detections[0, 0, i, 6])
            faces.append(DetectedFace(
                x=max(0.0, x1),
                y=max(0.0, y1),
                width=min(1.0, x2 - x1),
                height=min(1.0, y2 - y1),
                confidence=confidence,
            ))
        return faces

    def _detect_haar(self, frame: np.ndarray) -> list[DetectedFace]:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        assert self._haar_cascade is not None
        rects = self._haar_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        faces: list[DetectedFace] = []
        for (x, y, fw, fh) in rects:
            faces.append(DetectedFace(
                x=x / w,
                y=y / h,
                width=fw / w,
                height=fh / h,
                confidence=0.7,
            ))
        return faces

    def _detect_swift(self, frame: np.ndarray) -> list[DetectedFace]:
        import tempfile
        import subprocess
        h, w = frame.shape[:2]
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = f.name
        try:
            cv2.imwrite(temp_path, frame)
            assert self.swift_script is not None
            cmd = ["swift", str(self.swift_script), temp_path]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            data = json.loads(result.stdout)
            faces: list[DetectedFace] = []
            for face in data.get("faces", []):
                faces.append(DetectedFace(
                    x=float(face.get("x", 0)),
                    y=float(face.get("y", 0)),
                    width=float(face.get("width", 0)),
                    height=float(face.get("height", 0)),
                    confidence=0.8,
                ))
            return faces
        finally:
            Path(temp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# TargetSelector
# ---------------------------------------------------------------------------

class TargetSelector:
    """Select the primary target face from a list of detections.

    Selection strategy:
    1. If exactly one face, select it.
    2. Otherwise, prefer the face that is largest AND closest to center.
    3. Lock onto a face for a short period to avoid jitter.
    """

    def __init__(
        self,
        *,
        min_area_ratio: float = 0.02,
        center_weight: float = 2.0,
        size_weight: float = 1.0,
        lock_frames: int = 5,
    ) -> None:
        self.min_area_ratio = min_area_ratio
        self.center_weight = center_weight
        self.size_weight = size_weight
        self.lock_frames = lock_frames
        self._locked_face: DetectedFace | None = None
        self._lock_counter: int = 0
        self._lock_id: int = 0

    def select(self, faces: list[DetectedFace]) -> DetectedFace | None:
        if not faces:
            self._clear_lock()
            return None

        # Score each face: larger and more centered is better
        def score(face: DetectedFace) -> float:
            center_dist = math.hypot(face.center_x - 0.5, face.center_y - 0.5)
            return self.size_weight * face.area - self.center_weight * center_dist

        candidates = [f for f in faces if f.area >= self.min_area_ratio]
        if not candidates:
            candidates = faces

        best = max(candidates, key=score)

        # Simple lock: if best is close to locked face, keep lock
        if self._locked_face is not None:
            dx = abs(best.center_x - self._locked_face.center_x)
            dy = abs(best.center_y - self._locked_face.center_y)
            if dx < 0.15 and dy < 0.15:
                self._lock_counter = min(self._lock_counter + 1, self.lock_frames)
                if self._lock_counter >= 2:
                    # Smooth the locked position
                    alpha = 0.6
                    best = DetectedFace(
                        x=self._lerp(self._locked_face.x, best.x, alpha),
                        y=self._lerp(self._locked_face.y, best.y, alpha),
                        width=self._lerp(self._locked_face.width, best.width, alpha),
                        height=self._lerp(self._locked_face.height, best.height, alpha),
                        confidence=best.confidence,
                    )
            else:
                self._lock_counter -= 1
                if self._lock_counter <= 0:
                    self._locked_face = None
                else:
                    return self._locked_face

        self._locked_face = best
        self._lock_counter = 1
        return best

    def _clear_lock(self) -> None:
        self._locked_face = None
        self._lock_counter = 0

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t


# ---------------------------------------------------------------------------
# TrackingEventBuilder
# ---------------------------------------------------------------------------

class TrackingEventBuilder:
    """Convert a detected face into a tracking event for MiraLightRuntime."""

    def __init__(
        self,
        *,
        yaw_gain: float = 1.8,
        pitch_gain: float = 1.2,
        lift_gain: float = 0.8,
        reach_gain: float = 0.6,
        distance_near_threshold: float = 0.15,
        distance_far_threshold: float = 0.05,
    ) -> None:
        self.yaw_gain = yaw_gain
        self.pitch_gain = pitch_gain
        self.lift_gain = lift_gain
        self.reach_gain = reach_gain
        self.distance_near_threshold = distance_near_threshold
        self.distance_far_threshold = distance_far_threshold

    def build_event(self, face: DetectedFace | None, frame_shape: tuple[int, ...]) -> dict[str, Any]:
        if face is None:
            return {
                "event_type": "tracking_update",
                "tracking": {
                    "target_present": False,
                },
                "control_hint": {},
            }

        # Normalized offsets from center
        yaw_error = (face.center_x - 0.5) * 2.0 * self.yaw_gain   # [-1.8, 1.8]
        pitch_error = (face.center_y - 0.5) * 2.0 * self.pitch_gain  # [-1.2, 1.2]

        # Distance band based on face area
        area = face.area
        if area > self.distance_near_threshold:
            distance_band = "near"
        elif area > self.distance_far_threshold:
            distance_band = "mid"
        else:
            distance_band = "far"

        # Horizontal zone
        if face.center_x < 0.35:
            horizontal_zone = "left"
        elif face.center_x > 0.65:
            horizontal_zone = "right"
        else:
            horizontal_zone = "center"

        # Vertical zone
        if face.center_y < 0.35:
            vertical_zone = "top"
        elif face.center_y > 0.65:
            vertical_zone = "bottom"
        else:
            vertical_zone = "center"

        # Lift intent: higher when face is lower in frame (person is closer/lower)
        lift_intent = 0.5 + (face.center_y - 0.5) * self.lift_gain
        lift_intent = max(0.0, min(1.0, lift_intent))

        # Reach intent: higher when face is larger (closer)
        reach_intent = 0.3 + (area / 0.2) * self.reach_gain
        reach_intent = max(0.0, min(1.0, reach_intent))

        return {
            "event_type": "tracking_update",
            "tracking": {
                "target_present": True,
                "target_class": "face",
                "target_mode": "single",
                "target_count": 1,
                "distance_band": distance_band,
                "horizontal_zone": horizontal_zone,
                "vertical_zone": vertical_zone,
                "confidence": round(face.confidence, 3),
                "bbox_norm": {
                    "x": round(face.x, 4),
                    "y": round(face.y, 4),
                    "w": round(face.width, 4),
                    "h": round(face.height, 4),
                },
                "center_norm": {
                    "x": round(face.center_x, 4),
                    "y": round(face.center_y, 4),
                },
            },
            "control_hint": {
                "yaw_error_norm": round(yaw_error, 4),
                "pitch_error_norm": round(pitch_error, 4),
                "lift_intent": round(lift_intent, 4),
                "reach_intent": round(reach_intent, 4),
            },
        }


# ---------------------------------------------------------------------------
# PersonTracker
# ---------------------------------------------------------------------------

class PersonTracker:
    """High-level tracker: captures video, detects faces, selects target.

    Resource profiles:
        - "default" : 640x480 @ 15fps, Haar cascade  (~50MB, low CPU)
        - "low"     : 320x240 @ 8fps,  Haar cascade  (~20MB, very low CPU)
        - "minimal" : 160x120 @ 4fps,  Haar cascade  (~10MB, minimal CPU)
    """

    PRESETS: dict[str, dict[str, Any]] = {
        "default": {"frame_width": 640, "frame_height": 480, "fps_limit": 15, "backend": "haar"},
        "low":     {"frame_width": 320, "frame_height": 240, "fps_limit": 8,  "backend": "haar"},
        "minimal": {"frame_width": 160, "frame_height": 120, "fps_limit": 4,  "backend": "haar"},
    }

    def __init__(
        self,
        camera_index: int = 0,
        *,
        backend: str = "haar",
        swift_script: Path | None = None,
        frame_width: int = 640,
        frame_height: int = 480,
        fps_limit: int = 15,
        profile: str | None = None,
        skip_frames: int = 0,
    ) -> None:
        """Args:
            profile: Override width/height/fps/backend with a preset ("low", "minimal").
            skip_frames: Detect only every N+1 frames (0 = every frame). Saves CPU.
        """
        if profile and profile in self.PRESETS:
            p = self.PRESETS[profile]
            frame_width = p["frame_width"]
            frame_height = p["frame_height"]
            fps_limit = p["fps_limit"]
            backend = p["backend"]

        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps_limit = fps_limit
        self.skip_frames = max(0, skip_frames)
        self.detector = FaceDetector(backend=backend, swift_script=swift_script)
        self.selector = TargetSelector()
        self.event_builder = TrackingEventBuilder()
        self._cap: cv2.VideoCapture | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._latest_frame: np.ndarray | None = None
        self._latest_event: dict[str, Any] | None = None
        self._lock = threading.Lock()
        self._frame_counter: int = 0
        self._last_event: dict[str, Any] | None = None

    def start(self) -> None:
        if self._running:
            return
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print(f"[tracker] camera {self.camera_index} started ({self.frame_width}x{self.frame_height} @ {self.fps_limit}fps, skip={self.skip_frames})")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
            self._cap = None
        print("[tracker] stopped")

    def _capture_loop(self) -> None:
        interval = 1.0 / self.fps_limit
        while self._running:
            t0 = time.monotonic()
            if self._cap is None:
                break
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Optionally resize frame before detection to save CPU
            if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))

            # Skip-frame logic: reuse last event to reduce detection cost
            self._frame_counter += 1
            if self.skip_frames > 0 and (self._frame_counter - 1) % (self.skip_frames + 1) != 0:
                event = self._last_event
            else:
                faces = self.detector.detect(frame)
                target = self.selector.select(faces)
                event = self.event_builder.build_event(target, frame.shape)
                self._last_event = event

            with self._lock:
                self._latest_frame = frame.copy()
                self._latest_event = event

            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_latest_event(self) -> dict[str, Any] | None:
        with self._lock:
            return self._latest_event.copy() if self._latest_event else None

    def get_latest_frame(self) -> np.ndarray | None:
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def is_running(self) -> bool:
        return self._running


# ---------------------------------------------------------------------------
# TrackingController
# ---------------------------------------------------------------------------

class TrackingController:
    """Bridge between PersonTracker and MiraLightRuntime.

    Runs a control loop that reads tracking events from the camera and
    forwards them to the runtime's apply_tracking_event() method.
    """

    def __init__(
        self,
        runtime: Any,  # MiraLightRuntime
        tracker: PersonTracker,
        *,
        update_interval_ms: float = 120.0,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.runtime = runtime
        self.tracker = tracker
        self.update_interval_ms = update_interval_ms
        self.on_event = on_event
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._running:
            return
        self.tracker.start()
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()
        print("[tracking-controller] started")

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        self.tracker.stop()
        print("[tracking-controller] stopped")

    def _control_loop(self) -> None:
        while not self._stop_event.is_set():
            event = self.tracker.get_latest_event()
            if event is not None:
                try:
                    self.runtime.apply_tracking_event(event, source="vision")
                    if self.on_event:
                        self.on_event(event)
                except Exception as exc:
                    print(f"[tracking-controller] error: {exc}")
            self._stop_event.wait(self.update_interval_ms / 1000.0)

    def is_running(self) -> bool:
        return self._running


# ---------------------------------------------------------------------------
# Standalone test / preview
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Person tracker for Mira Light")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--backend", choices=["haar", "dnn", "swift"], default="haar")
    parser.add_argument("--swift-script", type=Path, default=None)
    parser.add_argument("--preview", action="store_true", help="Show OpenCV preview window")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    args = parser.parse_args(argv)

    tracker = PersonTracker(
        camera_index=args.camera,
        backend=args.backend,
        swift_script=args.swift_script,
        frame_width=args.width,
        frame_height=args.height,
        fps_limit=args.fps,
    )
    tracker.start()

    try:
        while True:
            event = tracker.get_latest_event()
            if event:
                tracking = event.get("tracking", {})
                hint = event.get("control_hint", {})
                print(
                    f"\rzone={tracking.get('horizontal_zone', '-'):6s} "
                    f"dist={tracking.get('distance_band', '-'):4s} "
                    f"yaw={hint.get('yaw_error_norm', 0):+.2f} "
                    f"pitch={hint.get('pitch_error_norm', 0):+.2f} "
                    f"present={tracking.get('target_present', False)}",
                    end="",
                    flush=True,
                )

            if args.preview:
                frame = tracker.get_latest_frame()
                if frame is not None and event:
                    tracking = event.get("tracking", {})
                    bbox = tracking.get("bbox_norm", {})
                    if bbox and tracking.get("target_present"):
                        h, w = frame.shape[:2]
                        x = int(bbox["x"] * w)
                        y = int(bbox["y"] * h)
                        bw = int(bbox["w"] * w)
                        bh = int(bbox["h"] * h)
                        cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                        cx = int(tracking["center_norm"]["x"] * w)
                        cy = int(tracking["center_norm"]["y"] * h)
                        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
                    cv2.imshow("Person Tracker", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        tracker.stop()
        if args.preview:
            cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
