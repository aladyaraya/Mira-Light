#!/usr/bin/env python3
"""PC-side person tracker and gesture recognizer for Mira Light.

Runs on an external PC with a webcam. Detects faces and hand gestures
locally using OpenCV, then sends servo commands over TCP to the RDK X5
board's servo bridge.

Architecture:
    PC webcam -> OpenCV face/gesture detection -> servo mapping
    -> TCP -> RDK X5 servo bridge (port 9527) -> /dev/ttyS1 -> bus servos

Features:
    - Face tracking: head yaw/pitch follows face position
    - Lift servo: keeps Mira in a head-up "watching" position
    - Hold position: doesn't reset when face is lost
    - Gesture recognition: open palm, fist, point, wave
    - Voice conflict avoidance: pauses when voice system is active
    - Servo offset correction: per-servo PWM offset

Usage:
    python pc_tracker.py                              # default
    python pc_tracker.py --lift-pwm 1700              # higher head-up
    python pc_tracker.py --no-gesture                 # disable gestures
    python pc_tracker.py --servo-offset 1,-50         # correct servo 1
    python pc_tracker.py --hold-seconds 999           # never reset (hold forever)
    python pc_tracker.py --voice-port 19783           # enable voice conflict check
"""

from __future__ import annotations

import argparse
import math
import os
import socket
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import cv2
import mediapipe as mp
import numpy as np


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Servo IDs on the RDK X5 board (0-indexed, matching four_servo_control.py)
SERVO_ID_HEAD_YAW = 0    # servo 0: head left/right
SERVO_ID_HEAD_PITCH = 1  # servo 1: head up/down
SERVO_ID_LIFT = 2         # servo 2: body lift (controls head height)
SERVO_ID_REACH = 3        # servo 3: arm reach

# PWM range for Feetech STS bus servos (1000-2000, 1500 = center)
PWM_MIN = 1000
PWM_MAX = 2000
PWM_CENTER = 1500

# Default servo positions
# Lift is set high so Mira looks UP toward the PC camera (usually at eye level+)
SERVO_DEFAULT: dict[int, int] = {
    SERVO_ID_HEAD_YAW:   1500,
    SERVO_ID_HEAD_PITCH: 1500,
    SERVO_ID_LIFT:       1700,  # raised position - head up
    SERVO_ID_REACH:      1500,
}

# Board connection defaults
BOARD_IP = "192.168.0.183"
BOARD_PORT = 9527

# Voice system bridge port (for conflict detection)
VOICE_BRIDGE_PORT = 19783


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DetectedFace:
    x: float
    y: float
    width: float
    height: float
    confidence: float

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class GestureResult:
    """Result of gesture recognition."""
    gesture: str = "none"  # "open_palm", "fist", "point", "wave", "snap", "none"
    hand_x: float = 0.5    # normalized hand center x
    hand_y: float = 0.5    # normalized hand center y
    hand_area: float = 0.0  # normalized hand area
    finger_count: int = 0


# ---------------------------------------------------------------------------
# Face detection
# ---------------------------------------------------------------------------

class FaceDetector:
    """Haar cascade face detector with multi-scale sensitivity."""

    def __init__(self, min_face_size: int = 40) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.cascade = cv2.CascadeClassifier(cascade_path)
        # Also load profile face cascade for side faces
        self.profile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_profileface.xml"
        )
        if self.cascade.empty():
            raise RuntimeError(f"Cannot load Haar cascade: {cascade_path}")
        self.min_face_size = min_face_size
        print(f"[detector] Haar cascade loaded (min_face={min_face_size}px, multi-scale)")

    def detect(self, frame: np.ndarray) -> list[DetectedFace]:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        all_rects: list[tuple[float, float, float, float]] = []

        # Frontal faces - try multiple parameter sets for robustness
        for scale_factor, min_neighbors in [(1.1, 3), (1.15, 2), (1.2, 2)]:
            rects = self.cascade.detectMultiScale(
                gray, scaleFactor=scale_factor, minNeighbors=min_neighbors,
                minSize=(self.min_face_size, self.min_face_size),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            for (x, y, fw, fh) in rects:
                all_rects.append((x, y, fw, fh))

        # Profile faces (left and right)
        if not self.profile_cascade.empty():
            for flip in [None, 1]:  # None = original, 1 = flip horizontally
                search_img = gray if flip is None else cv2.flip(gray, 1)
                rects = self.profile_cascade.detectMultiScale(
                    search_img, scaleFactor=1.15, minNeighbors=3,
                    minSize=(self.min_face_size, self.min_face_size),
                )
                for (x, y, fw, fh) in rects:
                    if flip == 1:
                        x = w - x - fw  # mirror back
                    all_rects.append((x, y, fw, fh))

        # Deduplicate overlapping detections (non-max suppression)
        final_rects = self._nms(all_rects, threshold=0.3)

        faces: list[DetectedFace] = []
        for (x, y, fw, fh) in final_rects:
            faces.append(DetectedFace(
                x=x / w, y=y / h, width=fw / w, height=fh / h, confidence=0.8,
            ))
        return faces

    def _nms(self, rects: list, threshold: float = 0.3) -> list:
        """Non-maximum suppression to merge overlapping detections."""
        if not rects:
            return []
        # Sort by area (largest first)
        rects_sorted = sorted(rects, key=lambda r: r[2] * r[3], reverse=True)
        kept: list = []
        for r in rects_sorted:
            overlap = False
            for k in kept:
                if self._iou(r, k) > threshold:
                    overlap = True
                    break
            if not overlap:
                kept.append(r)
        return kept

    def _iou(self, r1: tuple, r2: tuple) -> float:
        """Calculate intersection over union."""
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        xi = max(x1, x2)
        yi = max(y1, y2)
        xf = min(x1 + w1, x2 + w2)
        yf = min(y1 + h1, y2 + h2)
        if xf <= xi or yf <= yi:
            return 0.0
        inter = (xf - xi) * (yf - yi)
        union = w1 * h1 + w2 * h2 - inter
        return inter / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# Gesture recognition (MediaPipe Hands v0.10+ Tasks API)
# ---------------------------------------------------------------------------

# Default model paths (relative to script directory)
_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
_HAND_LANDMARKER_MODEL = os.path.join(_MODELS_DIR, "hand_landmarker.task")
_GESTURE_RECOGNIZER_MODEL = os.path.join(_MODELS_DIR, "gesture_recognizer.task")


class GestureRecognizer:
    """Recognize hand gestures using MediaPipe HandLandmarker + GestureRecognizer.

    Uses the new MediaPipe Tasks API (v0.10+).
    Accurate 21-landmark hand tracking with built-in gesture classification.
    Also supports custom snap detection (rapid finger close).
    """

    def __init__(self, max_hands: int = 1, min_confidence: float = 0.6) -> None:
        from mediapipe.tasks.python.vision import (
            HandLandmarker, HandLandmarkerOptions,
            GestureRecognizer, GestureRecognizerOptions,
            RunningMode,
        )
        from mediapipe.tasks.python import BaseOptions

        # Create HandLandmarker
        base_opts = BaseOptions(model_asset_path=_HAND_LANDMARKER_MODEL)
        hl_opts = HandLandmarkerOptions(
            base_options=base_opts,
            running_mode=RunningMode.IMAGE,
            num_hands=max_hands,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._hand_landmarker = HandLandmarker.create_from_options(hl_opts)

        # Create GestureRecognizer (built-in gesture classification)
        base_opts_g = BaseOptions(model_asset_path=_GESTURE_RECOGNIZER_MODEL)
        gr_opts = GestureRecognizerOptions(
            base_options=base_opts_g,
            running_mode=RunningMode.IMAGE,
            num_hands=max_hands,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._gesture_recognizer = GestureRecognizer.create_from_options(gr_opts)

        # Snap detection state
        self._finger_history: list[tuple[int, float]] = []
        self._finger_max_len = 20
        self._last_snap_time: float = 0.0

        print("[gesture] MediaPipe HandLandmarker + GestureRecognizer ready")

    def recognize(self, frame: np.ndarray) -> GestureResult:
        """Detect hand and classify gesture using MediaPipe."""
        h, w = frame.shape[:2]
        result = GestureResult()

        # Create MediaPipe Image
        from mediapipe import Image as MpImage
        mp_image = MpImage(image_format=mp.ImageFormat.SRGB, data=frame)

        # Run hand landmarker
        hl_result = self._hand_landmarker.detect(mp_image)

        if not hl_result.hand_landmarks or len(hl_result.hand_landmarks) == 0:
            self._finger_history.clear()
            return result

        # Use first hand
        landmarks = hl_result.hand_landmarks[0]
        handedness = hl_result.handedness[0] if hl_result.handedness else None

        # Get hand center from landmarks
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]
        result.hand_x = sum(xs) / len(xs)
        result.hand_y = sum(ys) / len(ys)
        result.hand_area = (max(xs) - min(xs)) * (max(ys) - min(ys))

        # Count extended fingers
        finger_count = self._count_fingers_from_landmarks(landmarks)
        result.finger_count = finger_count

        # Run gesture recognizer for built-in classification
        gr_result = self._gesture_recognizer.recognize(mp_image, hl_result)
        if gr_result.gestures and len(gr_result.gestures) > 0:
            top_gesture = gr_result.gestures[0][0]
            # Map MediaPipe gesture names to our gesture names
            mp_gesture_name = top_gesture.category_name.lower()
            gesture_map = {
                "open_palm": "open_palm",
                "closed_fist": "fist",
                "pointing_up": "point",
                "victory": "peace",
                "thumb_up": "thumbs_up",
                "thumb_down": "thumbs_down",
                "none": "none",
            }
            result.gesture = gesture_map.get(mp_gesture_name, mp_gesture_name)

            # Override with finger count for accuracy
            if finger_count == 5 and result.gesture != "open_palm":
                result.gesture = "open_palm"
            elif finger_count == 0 and result.gesture != "fist":
                result.gesture = "fist"
            elif finger_count == 2 and result.gesture != "peace":
                result.gesture = "peace"
            elif finger_count == 3:
                result.gesture = "three"
            elif finger_count == 4:
                result.gesture = "four"
        else:
            # Fallback to finger count based classification
            if finger_count == 5:
                result.gesture = "open_palm"
            elif finger_count == 0:
                result.gesture = "fist"
            elif finger_count == 1:
                result.gesture = "point"
            elif finger_count == 2:
                result.gesture = "peace"
            elif finger_count == 3:
                result.gesture = "three"
            elif finger_count == 4:
                result.gesture = "four"

        # Snap detection: rapid finger count transition (5->0 or 4->0)
        now = time.monotonic()
        self._finger_history.append((finger_count, now))
        if len(self._finger_history) > self._finger_max_len:
            self._finger_history.pop(0)

        if len(self._finger_history) >= 4 and (now - self._last_snap_time) > 2.0:
            recent = [(fc, t) for fc, t in self._finger_history if now - t < 0.6]
            if len(recent) >= 3:
                first_fc = recent[0][0]
                last_fc = recent[-1][0]
                time_span = recent[-1][1] - recent[0][1]
                if first_fc >= 4 and last_fc <= 1 and time_span < 0.5:
                    result.gesture = "snap"
                    self._last_snap_time = now
                    self._finger_history.clear()

        return result

    def _count_fingers_from_landmarks(self, landmarks) -> int:
        """Count extended fingers from MediaPipe hand landmarks.

        Finger tips: thumb=4, index=8, middle=12, ring=16, pinky=20
        Finger PIPs:  thumb=3, index=6, middle=10, ring=14, pinky=18
        """
        count = 0
        # Thumb: tip above IP joint (y-axis, lower y = higher on screen)
        if landmarks[4].y < landmarks[3].y:
            count += 1
        # Other 4 fingers: tip y < PIP y means extended
        for tip_id, pip_id in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            if landmarks[tip_id].y < landmarks[pip_id].y:
                count += 1
        return count

    def close(self) -> None:
        self._hand_landmarker.close()
        self._gesture_recognizer.close()


# ---------------------------------------------------------------------------
# Target selection with anti-jitter
# ---------------------------------------------------------------------------

class TargetSelector:
    """Select the best face to track, with smoothing."""

    def __init__(self, lock_frames: int = 5, smooth_alpha: float = 0.5) -> None:
        self._locked: DetectedFace | None = None
        self._lock_count: int = 0
        self.lock_frames = lock_frames
        self.smooth_alpha = smooth_alpha

    def select(self, faces: list[DetectedFace]) -> DetectedFace | None:
        if not faces:
            self._lock_count = max(0, self._lock_count - 1)
            if self._lock_count > 0 and self._locked is not None:
                return self._locked
            self._locked = None
            return None

        def score(f: DetectedFace) -> float:
            dist = math.hypot(f.center_x - 0.5, f.center_y - 0.5)
            return f.area * 2.0 - dist * 1.5

        best = max(faces, key=score)

        if self._locked is not None:
            dx = abs(best.center_x - self._locked.center_x)
            dy = abs(best.center_y - self._locked.center_y)
            if dx < 0.2 and dy < 0.2:
                a = self.smooth_alpha
                best = DetectedFace(
                    x=self._locked.x + (best.x - self._locked.x) * a,
                    y=self._locked.y + (best.y - self._locked.y) * a,
                    width=self._locked.width + (best.width - self._locked.width) * a,
                    height=self._locked.height + (best.height - self._locked.height) * a,
                    confidence=best.confidence,
                )

        self._locked = best
        self._lock_count = self.lock_frames
        return best


# ---------------------------------------------------------------------------
# Color light trigger (HTTP scene calls)
# ---------------------------------------------------------------------------

class ColorLightTrigger:
    """Trigger color light scenes via the bridge HTTP API.

    Sends HTTP requests to the bridge server to activate color light
    scenes in response to gestures or other events.
    """

    def __init__(self, port: int = VOICE_BRIDGE_PORT, timeout: float = 1.0) -> None:
        self.port = port
        self.timeout = timeout
        self._available = False
        self._last_check = 0.0
        self._check_interval = 5.0

    def _check_available(self) -> bool:
        """Check if the bridge server is reachable."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", self.port))
            s.close()
            self._available = (result == 0)
            return self._available
        except Exception:
            self._available = False
            return False

    def is_available(self) -> bool:
        """Check if bridge is available (cached)."""
        now = time.monotonic()
        if now - self._last_check > self._check_interval:
            self._check_available()
            self._last_check = now
        return self._available

    def trigger_scene(self, scene_name: str) -> bool:
        """Trigger a color light scene via HTTP POST.

        Uses the bridge's run-scene endpoint to activate a scene like
        'celebrate' (rainbow lights + dance) or other light-focused scenes.
        """
        if not self.is_available():
            return False
        try:
            import urllib.request
            import json
            url = f"http://127.0.0.1:{self.port}/v1/mira-light/run-scene"
            data = json.dumps({"scene": scene_name, "async": True}).encode()
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[light] scene trigger error: {e}")
            return False

    def trigger_led(self, mode: str, brightness: int = 200,
                    color: dict | None = None) -> bool:
        """Directly control LED via HTTP POST /v1/mira-light/led.

        Args:
            mode: LED mode (off, solid, breathing, rainbow, rainbow_cycle, vector)
            brightness: 0-255
            color: {"r":255,"g":0,"b":0} for solid/breathing modes
        """
        if not self.is_available():
            return False
        try:
            import urllib.request
            import json
            url = f"http://127.0.0.1:{self.port}/v1/mira-light/led"
            payload: dict = {"mode": mode, "brightness": brightness}
            if color:
                payload["color"] = color
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[light] LED control error: {e}")
            return False

    def trigger_led_rainbow(self) -> bool:
        """Shortcut: set LED to rainbow mode."""
        return self.trigger_led("rainbow", brightness=200)

    def trigger_led_solid(self, r: int, g: int, b: int, brightness: int = 150) -> bool:
        """Shortcut: set LED to solid color."""
        return self.trigger_led("solid", brightness=brightness,
                                color={"r": r, "g": g, "b": b})

    def trigger_gesture_light(self, gesture: str) -> bool:
        """Map a gesture to a color light scene and trigger it.

        Args:
            gesture: Recognized gesture name.

        Returns:
            True if triggered, False if no mapping or request failed.
        """
        gesture_scene_map = {
            "open_palm": "celebrate",
            "fist": "sleep",
            "point": "curious_observe",
            "wave": "farewell",
            "snap": "celebrate",
            "peace": "wake_up",
            "three": "daydream",
        }
        scene = gesture_scene_map.get(gesture)
        if not scene:
            return False
        return self.trigger_scene(scene)


# ---------------------------------------------------------------------------
# Voice conflict detector
# ---------------------------------------------------------------------------

class VoiceConflictDetector:
    """Check if the voice system is actively controlling Mira.

    The voice system sends HTTP requests to port 19783 (bridge_server).
    If that port is open and recently received commands, we pause tracking
    to avoid servo conflicts.
    """

    def __init__(self, port: int = VOICE_BRIDGE_PORT, cooldown_s: float = 3.0) -> None:
        self.port = port
        self.cooldown_s = cooldown_s
        self._last_voice_time: float = 0.0
        self._bridge_available = False
        self._check_interval = 2.0
        self._last_check = 0.0

    def check_bridge(self) -> bool:
        """Check if voice bridge is running (port open)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", self.port))
            s.close()
            self._bridge_available = (result == 0)
            return self._bridge_available
        except Exception:
            self._bridge_available = False
            return False

    def is_voice_active(self) -> bool:
        """Check if voice system recently sent commands.

        We probe the bridge's /v1/mira-light/state endpoint to see if
        a scene is currently running.
        """
        now = time.monotonic()

        # Periodically check bridge availability
        if now - self._last_check > self._check_interval:
            self.check_bridge()
            self._last_check = now

        if not self._bridge_available:
            return False

        # Check if a scene is running via HTTP
        try:
            import urllib.request
            url = f"http://127.0.0.1:{self.port}/v1/mira-light/state"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                import json
                data = json.loads(resp.read().decode())
                # If a scene is running, voice has priority
                running_scene = data.get("runtime", {}).get("runningScene")
                if running_scene and running_scene != "track_target":
                    self._last_voice_time = now
                    return True
        except Exception:
            pass

        # Cooldown after voice command
        return (now - self._last_voice_time) < self.cooldown_s


# ---------------------------------------------------------------------------
# Servo bridge client (TCP to RDK X5)
# ---------------------------------------------------------------------------

class RemoteServoClient:
    """Send servo commands to the RDK X5 servo bridge over TCP."""

    def __init__(
        self,
        host: str = BOARD_IP,
        port: int = BOARD_PORT,
        dry_run: bool = False,
        servo_offsets: dict[int, int] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.dry_run = dry_run
        self._current: dict[int, int] = dict(SERVO_DEFAULT)
        self._connected = False
        self.servo_offsets = servo_offsets or {}

    def check_connection(self) -> bool:
        if self.dry_run:
            print(f"[servo] DRY-RUN mode - no TCP connection to {self.host}:{self.port}")
            return True
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((self.host, self.port))
            s.close()
            self._connected = True
            print(f"[servo] board reachable at {self.host}:{self.port}")
            return True
        except Exception as e:
            self._connected = False
            print(f"[servo] board not reachable: {e}")
            return False

    def _apply_offset(self, sid: int, pwm: int) -> int:
        """Apply per-servo offset correction."""
        return max(PWM_MIN, min(PWM_MAX, pwm + self.servo_offsets.get(sid, 0)))

    def send_servos(self, targets: dict[int, int], duration_ms: int = 200) -> bool:
        """Send a batch of servo PWM commands with smoothing."""
        commands: dict[int, tuple[int, int]] = {}
        for sid, target_pwm in targets.items():
            target_pwm = max(PWM_MIN, min(PWM_MAX, int(target_pwm)))
            # Apply offset to target
            target_pwm = self._apply_offset(sid, target_pwm)
            prev = self._current.get(sid, SERVO_DEFAULT.get(sid, PWM_CENTER))
            smoothed = int(prev + (target_pwm - prev) * 0.5)
            smoothed = max(PWM_MIN, min(PWM_MAX, smoothed))
            self._current[sid] = smoothed
            commands[sid] = (smoothed, duration_ms)

        if self.dry_run:
            parts = [f"s{id}={pwm}" for id, (pwm, _) in sorted(commands.items())]
            print(f"[servo] DRY {' '.join(parts)}")
            return True

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.host, self.port))
            frames = []
            for sid, (pwm, dur) in commands.items():
                frames.append(f"#{sid:03d}P{pwm:04d}T{dur:04d}!")
            cmd = "{" + "".join(frames) + "}\n"
            s.sendall(cmd.encode())
            resp = s.recv(1024).decode().strip()
            s.close()
            if not resp.startswith("OK"):
                print(f"[servo] board error: {resp}")
                return False
            return True
        except Exception as e:
            print(f"[servo] send error: {e}")
            return False

    def move_to_default(self, duration_ms: int = 500) -> bool:
        """Move all servos to default (head-up watching) position."""
        return self.send_servos(dict(SERVO_DEFAULT), duration_ms)


# ---------------------------------------------------------------------------
# Face-to-servo mapping
# ---------------------------------------------------------------------------

def face_to_servo_pwm(
    face: DetectedFace,
    yaw_gain: float = 0.8,
    pitch_gain: float = 0.6,
    lift_pwm: int = 1700,
) -> dict[int, int]:
    """Convert face position to servo PWM values.

    - Yaw: face center_x -> head left/right
    - Pitch: face center_y -> head up/down
    - Lift: fixed at lift_pwm (head-up watching position)
    - Reach: based on face size (closer = more reach)
    """
    yaw = PWM_CENTER + (face.center_x - 0.5) * 800 * yaw_gain
    pitch = PWM_CENTER + (face.center_y - 0.5) * 600 * pitch_gain
    # Lift stays at the configured head-up position
    lift = lift_pwm
    # Reach based on face area
    reach = PWM_CENTER + (face.area - 0.05) * 1500
    reach = max(PWM_MIN, min(PWM_MAX, reach))

    return {
        SERVO_ID_HEAD_YAW: int(yaw),
        SERVO_ID_HEAD_PITCH: int(pitch),
        SERVO_ID_LIFT: int(lift),
        SERVO_ID_REACH: int(reach),
    }


def gesture_to_servo_action(gesture: GestureResult) -> dict[int, int] | None:
    """Map a recognized gesture to a servo action.

    Returns None if no action needed.
    """
    if gesture.gesture == "open_palm":
        # Wave back: raise arm and tilt head
        return {
            SERVO_ID_HEAD_YAW: 1500,
            SERVO_ID_HEAD_PITCH: 1400,  # look up slightly
            SERVO_ID_LIFT: 1800,         # raise up
            SERVO_ID_REACH: 1800,        # extend arm (wave)
        }
    elif gesture.gesture == "fist":
        # Acknowledge: nod down slightly
        return {
            SERVO_ID_HEAD_PITCH: 1600,
            SERVO_ID_LIFT: 1700,
            SERVO_ID_REACH: 1300,  # pull arm back
        }
    elif gesture.gesture == "point":
        # Look toward the pointing direction
        return {
            SERVO_ID_HEAD_YAW: int(PWM_CENTER + (gesture.hand_x - 0.5) * 1000),
            SERVO_ID_HEAD_PITCH: int(PWM_CENTER + (gesture.hand_y - 0.5) * 600),
            SERVO_ID_LIFT: 1700,
            SERVO_ID_REACH: 1600,
        }
    elif gesture.gesture == "wave":
        # Excited wave: full body wiggle
        return {
            SERVO_ID_HEAD_YAW: 1500,
            SERVO_ID_HEAD_PITCH: 1400,
            SERVO_ID_LIFT: 1850,
            SERVO_ID_REACH: 1900,
        }
    return None


# ---------------------------------------------------------------------------
# Main tracker
# ---------------------------------------------------------------------------

def parse_servo_offsets(raw: str) -> dict[int, int]:
    """Parse servo offset string like '1,-50' or '0,30;2,-20'."""
    if not raw:
        return {}
    offsets = {}
    for pair in raw.split(";"):
        parts = pair.strip().split(",")
        if len(parts) == 2:
            sid = int(parts[0].strip())
            off = int(parts[1].strip())
            offsets[sid] = off
    return offsets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PC-side person tracker and gesture recognizer for Mira Light",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Camera
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)

    # Board connection
    parser.add_argument("--board-ip", default=BOARD_IP)
    parser.add_argument("--board-port", type=int, default=BOARD_PORT)

    # Tracking behavior
    parser.add_argument("--update-ms", type=int, default=100, help="Servo update interval ms")
    parser.add_argument("--yaw-gain", type=float, default=0.8)
    parser.add_argument("--pitch-gain", type=float, default=0.6)
    parser.add_argument("--min-face", type=int, default=40)

    # Lift servo (head-up position)
    parser.add_argument("--lift-pwm", type=int, default=1700,
                        help="Lift servo PWM for head-up position (default 1700, range 1000-2000)")

    # Hold behavior (don't reset immediately)
    parser.add_argument("--hold-seconds", type=float, default=999.0,
                        help="Seconds to hold position after losing face (default 999=hold forever)")
    parser.add_argument("--no-hold", action="store_true",
                        help="Disable hold - return to default immediately when face lost")

    # Gesture recognition
    parser.add_argument("--no-gesture", action="store_true",
                        help="Disable gesture recognition")
    parser.add_argument("--gesture-cooldown", type=float, default=2.0,
                        help="Cooldown seconds between gesture actions")

    # Servo correction
    parser.add_argument("--servo-offset", default="",
                        help="Servo offset correction, e.g. '1,-50' or '0,30;2,-20'")

    # Voice conflict
    parser.add_argument("--voice-port", type=int, default=0,
                        help="Voice bridge port for conflict detection (0=disabled, default 19783)")
    parser.add_argument("--voice-cooldown", type=float, default=3.0,
                        help="Pause tracking for N seconds after voice command")

    # Color light bridge (for snap gesture -> color light)
    parser.add_argument("--bridge-port", type=int, default=9783,
                        help="Bridge server port for color light scenes (default 9783)")
    parser.add_argument("--snap-scene", default="celebrate",
                        help="Scene to trigger on snap gesture (default: celebrate)")

    # Other
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Parse servo offsets
    servo_offsets = parse_servo_offsets(args.servo_offset)
    if servo_offsets:
        print(f"[config] servo offsets: {servo_offsets}")

    print("=" * 60)
    print("Mira Light PC Tracker + Gesture Recognition")
    print("=" * 60)
    print(f"  Camera:     #{args.camera} ({args.width}x{args.height} @ {args.fps}fps)")
    print(f"  Board:      {args.board_ip}:{args.board_port}")
    print(f"  Update:     every {args.update_ms}ms")
    print(f"  Lift PWM:   {args.lift_pwm} (head-up position)")
    print(f"  Hold:       {args.hold_seconds}s ({'OFF' if args.no_hold else 'ON'})")
    print(f"  Gesture:    {'OFF' if args.no_gesture else 'ON'}")
    print(f"  Voice chk:  {'ON (port %d)' % args.voice_port if args.voice_port else 'OFF'}")
    print(f"  Bridge:     port {args.bridge_port} (snap -> '{args.snap_scene}')")
    print(f"  Dry run:    {'ON' if args.dry_run else 'OFF'}")
    print("=" * 60)

    # Initialize components
    detector = FaceDetector(min_face_size=args.min_face)
    selector = TargetSelector(lock_frames=5, smooth_alpha=0.5)
    servo = RemoteServoClient(
        host=args.board_ip, port=args.board_port,
        dry_run=args.dry_run, servo_offsets=servo_offsets,
    )

    gesture_recognizer = None if args.no_gesture else GestureRecognizer()
    voice_detector = None
    if args.voice_port:
        voice_detector = VoiceConflictDetector(
            port=args.voice_port, cooldown_s=args.voice_cooldown,
        )

    # Color light trigger (for snap gesture -> color light scene)
    light_trigger = ColorLightTrigger(port=args.bridge_port)
    if light_trigger.is_available():
        print(f"[light] bridge available at port {args.bridge_port}")
    else:
        print(f"[light] bridge not available - color light trigger disabled")

    # Check board connection
    if not servo.check_connection():
        print("\nWARNING: Board not reachable. Starting in dry-run mode...")
        servo.dry_run = True

    # Open camera
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {args.camera}")
        return 1
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)

    # Warmup camera (some webcams need a few frames to adjust exposure)
    print("[init] Warming up camera...")
    for _ in range(20):
        cap.read()
        time.sleep(0.05)
    print("[init] Camera ready")

    # Initialize servos to head-up position
    print("\n[init] Moving to head-up watching position...")
    servo.move_to_default(duration_ms=800)
    time.sleep(1.0)

    print("[tracker] running... (press Ctrl+C to stop)")

    interval = 1.0 / args.fps
    last_servo_time = 0.0
    no_face_count = 0
    last_face_time = time.monotonic()
    frame_count = 0
    fps_timer = time.monotonic()
    fps_counter = 0
    current_fps = 0.0

    # Gesture state
    last_gesture = "none"
    last_gesture_time = 0.0
    gesture_action_active = False
    gesture_action_end = 0.0

    # Last servo command (for hold behavior)
    last_servo_targets: dict[int, int] = dict(SERVO_DEFAULT)

    try:
        while True:
            t0 = time.monotonic()

            # Check voice conflict
            voice_active = False
            if voice_detector and voice_detector.is_voice_active():
                voice_active = True
                print("\r[voice] active - tracking paused     ", end="", flush=True)
                # Still read frames to keep camera alive
                ret, frame = cap.read()
                elapsed = time.monotonic() - t0
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                continue

            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frame_count += 1
            fps_counter += 1
            now = time.monotonic()

            # --- Face detection ---
            faces = detector.detect(frame)
            target = selector.select(faces)

            # --- Gesture recognition ---
            gesture = GestureResult()
            if gesture_recognizer and not gesture_action_active:
                gesture = gesture_recognizer.recognize(frame)

                # Handle snap gesture specially - trigger color light scene
                if gesture.gesture == "snap" and (now - last_gesture_time) > args.gesture_cooldown:
                    print(f"\n[SNAP] detected! Triggering color light scene: {args.snap_scene}")
                    # Trigger the color light scene via HTTP
                    success = light_trigger.trigger_scene(args.snap_scene)
                    if success:
                        print(f"[SNAP] scene '{args.snap_scene}' triggered successfully!")
                    else:
                        print(f"[SNAP] scene trigger failed - bridge not available?")
                        # Also try direct LED control as fallback
                        light_trigger.trigger_led_rainbow()
                    # Also do a servo reaction (excited bounce)
                    snap_action = {
                        SERVO_ID_HEAD_YAW: 1500,
                        SERVO_ID_HEAD_PITCH: 1350,  # look up
                        SERVO_ID_LIFT: 1900,         # rise up
                        SERVO_ID_REACH: 1800,        # arms out
                    }
                    servo.send_servos(snap_action, duration_ms=300)
                    last_servo_targets = snap_action
                    gesture_action_active = True
                    gesture_action_end = now + 2.0  # snap reaction lasts 2s
                    last_gesture = "snap"
                    last_gesture_time = now

                # Trigger gesture action for other gestures
                elif (gesture.gesture != "none"
                        and gesture.gesture != last_gesture
                        and gesture.gesture != "snap"
                        and (now - last_gesture_time) > args.gesture_cooldown):
                    print(f"\n[gesture] detected: {gesture.gesture} "
                          f"(fingers={gesture.finger_count}, "
                          f"pos=({gesture.hand_x:.2f},{gesture.hand_y:.2f}))")
                    action = gesture_to_servo_action(gesture)
                    if action:
                        servo.send_servos(action, duration_ms=400)
                        last_servo_targets = action
                        gesture_action_active = True
                        gesture_action_end = now + 1.5  # action lasts 1.5s
                    last_gesture = gesture.gesture
                    last_gesture_time = now
                elif gesture.gesture == "none":
                    last_gesture = "none"

            # End gesture action
            if gesture_action_active and now > gesture_action_end:
                gesture_action_active = False

            # --- Servo control ---
            if not gesture_action_active:
                if target is not None:
                    no_face_count = 0
                    last_face_time = now
                    pwms = face_to_servo_pwm(
                        target,
                        yaw_gain=args.yaw_gain,
                        pitch_gain=args.pitch_gain,
                        lift_pwm=args.lift_pwm,
                    )
                    last_servo_targets = pwms

                    if (now - last_servo_time) * 1000 >= args.update_ms:
                        servo.send_servos(pwms, duration_ms=150)
                        last_servo_time = now

                    print(
                        f"\r[track] face=({target.center_x:.2f},{target.center_y:.2f}) "
                        f"area={target.area:.3f} "
                        f"yaw={pwms[SERVO_ID_HEAD_YAW]:4d} "
                        f"pitch={pwms[SERVO_ID_HEAD_PITCH]:4d} "
                        f"lift={pwms[SERVO_ID_LIFT]:4d} "
                        f"ges={gesture.gesture:10s} "
                        f"fps={current_fps:.0f}",
                        end="", flush=True,
                    )
                else:
                    no_face_count += 1
                    time_since_face = now - last_face_time

                    if args.no_hold:
                        # Return to default immediately
                        if (now - last_servo_time) * 1000 >= args.update_ms:
                            servo.move_to_default(duration_ms=300)
                            last_servo_time = now
                        print(f"\r[track] no face - returning to watch (fps={current_fps:.0f})    ",
                              end="", flush=True)
                    elif time_since_face > args.hold_seconds:
                        # Hold expired - slowly return to default
                        if (now - last_servo_time) * 1000 >= args.update_ms:
                            servo.move_to_default(duration_ms=500)
                            last_servo_time = now
                        print(f"\r[track] no face - returning to watch after {args.hold_seconds}s    ",
                              end="", flush=True)
                    else:
                        # Hold last position - do nothing
                        print(
                            f"\r[track] no face - holding ({time_since_face:.0f}s) "
                            f"ges={gesture.gesture:10s} "
                            f"fps={current_fps:.0f}    ",
                            end="", flush=True,
                        )

            # FPS calculation
            if now - fps_timer >= 1.0:
                current_fps = fps_counter / (now - fps_timer)
                fps_counter = 0
                fps_timer = now

            # Frame rate control
            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[tracker] stopping...")
    finally:
        # Return to default watching position
        print("[tracker] returning to head-up position...")
        servo.move_to_default(duration_ms=800)
        time.sleep(1.0)
        cap.release()
        print("[tracker] stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
