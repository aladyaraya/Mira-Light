#!/usr/bin/env python3
"""Standalone person tracking for Mira Light on RDK X5.

This script runs directly on the RDK X5 board, independent of the full
Mira Light runtime. It:
1. Opens the camera (/dev/video0)
2. Detects faces using Haar cascade
3. Maps face position to servo angles
4. Sends servo commands via TCP to rdk_bus_servo_tcp_bridge (port 9527)

Usage:
    python3 standalone_tracker.py                    # default: low profile
    python3 standalone_tracker.py --profile minimal  # ultra low resource
    python3 standalone_tracker.py --camera 1          # use /dev/video1
    python3 standalone_tracker.py --dry-run            # test without sending servo

Resource profiles:
    default : 640x480 @ 15fps  (~50MB RAM, low CPU)
    low     : 320x240 @ 8fps   (~20MB RAM, very low CPU)  [RECOMMENDED for RDK X5]
    minimal : 160x120 @ 4fps   (~10MB RAM, minimal CPU)
"""

from __future__ import annotations

import argparse
import math
import socket
import struct
import sys
import time
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Servo protocol (compatible with rdk_bus_servo_tcp_bridge)
# ---------------------------------------------------------------------------

SERVO_HOST = "127.0.0.1"
SERVO_PORT = 9527

# Servo IDs used by Mira Light
SERVO_ID_HEAD_YAW = 1    # servo1: head left/right
SERVO_ID_HEAD_PITCH = 2  # servo2: head up/down
SERVO_ID_LIFT = 3         # servo3: body lift
SERVO_ID_REACH = 4        # servo4: arm reach

# PWM range for bus servos (1000-2000, 1500 = center)
PWM_MIN = 1000
PWM_MAX = 2000
PWM_CENTER = 1500

# Default center PWM values
SERVO_CENTER = {
    SERVO_ID_HEAD_YAW:   1500,
    SERVO_ID_HEAD_PITCH: 1500,
    SERVO_ID_LIFT:       1500,
    SERVO_ID_REACH:      1500,
}


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


class ServoClient:
    """Send servo commands via TCP to rdk_bus_servo_tcp_bridge.

    The bridge uses a one-shot request-response model: each connection
    handles a single command and then closes. So we open a new connection
    for each batch of servo updates.
    """

    def __init__(self, host: str = SERVO_HOST, port: int = SERVO_PORT, dry_run: bool = False) -> None:
        self.host = host
        self.port = port
        self.dry_run = dry_run
        self._current: dict[int, int] = dict(SERVO_CENTER)

    def connect(self) -> None:
        if self.dry_run:
            print("[servo] DRY-RUN mode - no TCP connection")
            return
        # Verify the bridge is reachable
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.host, self.port))
            s.close()
            print(f"[servo] bridge reachable at {self.host}:{self.port}")
        except Exception as e:
            print(f"[servo] bridge not reachable: {e}")

    def close(self) -> None:
        pass  # No persistent connection to close

    def send_batch(self, commands: dict[int, tuple[int, int]]) -> bool:
        """Send multiple servo commands in a single connection.

        Args:
            commands: {servo_id: (pwm, duration_ms)}
        """
        if self.dry_run:
            for sid, (pwm, dur) in commands.items():
                print(f"[servo] DRY id={sid} pwm={pwm} dur={dur}")
            return True

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.host, self.port))

            # Build multi-servo command: {#001P1500T0200!#002P1500T0200!}
            frames = []
            for sid, (pwm, dur) in commands.items():
                frames.append(f"#{sid:03d}P{pwm:04d}T{dur:04d}!")
            cmd = "{" + "".join(frames) + "}\n"
            s.sendall(cmd.encode())

            # Read response
            resp = s.recv(1024).decode().strip()
            s.close()
            return resp.startswith("OK")
        except Exception as e:
            print(f"[servo] send error: {e}")
            return False

    def update_servos(self, targets: dict[int, int], duration_ms: int = 200) -> bool:
        """Smooth and send servo updates.

        Args:
            targets: {servo_id: target_pwm}
        """
        commands: dict[int, tuple[int, int]] = {}
        for sid, target_pwm in targets.items():
            target_pwm = max(PWM_MIN, min(PWM_MAX, int(target_pwm)))
            prev = self._current.get(sid, PWM_CENTER)
            smoothed = int(prev + (target_pwm - prev) * 0.4)
            smoothed = max(PWM_MIN, min(PWM_MAX, smoothed))
            self._current[sid] = smoothed
            commands[sid] = (smoothed, duration_ms)
        return self.send_batch(commands)


class FaceDetector:
    """Haar cascade face detector."""

    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.cascade = cv2.CascadeClassifier(cascade_path)
        if self.cascade.empty():
            raise RuntimeError(f"Cannot load cascade: {cascade_path}")

    def detect(self, frame: np.ndarray) -> list[DetectedFace]:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = self.cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        faces = []
        for (x, y, fw, fh) in rects:
            faces.append(DetectedFace(
                x=x / w, y=y / h, width=fw / w, height=fh / h, confidence=0.7,
            ))
        return faces


class TargetSelector:
    """Select the best face to track."""

    def __init__(self) -> None:
        self._locked: DetectedFace | None = None
        self._lock_count: int = 0

    def select(self, faces: list[DetectedFace]) -> DetectedFace | None:
        if not faces:
            self._locked = None
            self._lock_count = 0
            return None

        def score(f: DetectedFace) -> float:
            dist = math.hypot(f.center_x - 0.5, f.center_y - 0.5)
            return f.area * 2.0 - dist

        best = max(faces, key=score)

        if self._locked is not None:
            dx = abs(best.center_x - self._locked.center_x)
            dy = abs(best.center_y - self._locked.center_y)
            if dx < 0.15 and dy < 0.15:
                alpha = 0.6
                best = DetectedFace(
                    x=self._locked.x + (best.x - self._locked.x) * alpha,
                    y=self._locked.y + (best.y - self._locked.y) * alpha,
                    width=self._locked.width + (best.width - self._locked.width) * alpha,
                    height=self._locked.height + (best.height - self._locked.height) * alpha,
                    confidence=best.confidence,
                )
            else:
                self._lock_count -= 1
                if self._lock_count > 0:
                    return self._locked

        self._locked = best
        self._lock_count = 5
        return best


def face_to_servo_pwm(face: DetectedFace) -> dict[int, int]:
    """Convert face position to servo PWM values.

    PWM 1000-2000, center=1500.
    """
    # Yaw: face center_x maps to servo1 PWM (left=1000, right=2000)
    yaw = PWM_CENTER + (face.center_x - 0.5) * 800  # range ~1100..1900

    # Pitch: face center_y maps to servo2 PWM (top=1000, bottom=2000)
    pitch = PWM_CENTER + (face.center_y - 0.5) * 600  # range ~1200..1800

    # Lift: based on face size (larger = closer = lower lift PWM)
    lift = PWM_CENTER - (face.area - 0.05) * 1000
    lift = max(PWM_MIN, min(PWM_MAX, lift))

    # Reach: based on face size (larger = closer = more reach PWM)
    reach = PWM_CENTER + (face.area - 0.05) * 1500
    reach = max(PWM_MIN, min(PWM_MAX, reach))

    return {
        SERVO_ID_HEAD_YAW: int(yaw),
        SERVO_ID_HEAD_PITCH: int(pitch),
        SERVO_ID_LIFT: int(lift),
        SERVO_ID_REACH: int(reach),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mira Light standalone person tracker")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--profile", choices=["default", "low", "minimal"], default="low")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--servo-host", default="127.0.0.1")
    parser.add_argument("--servo-port", type=int, default=9527)
    parser.add_argument("--update-ms", type=int, default=200, help="Servo update interval (ms)")
    args = parser.parse_args()

    # Profile settings
    profiles = {
        "default": (640, 480, 15),
        "low":     (320, 240, 8),
        "minimal": (160, 120, 4),
    }
    width, height, fps = profiles[args.profile]
    interval = 1.0 / fps

    print(f"[tracker] profile={args.profile} resolution={width}x{height} fps={fps}")
    print(f"[tracker] camera=/dev/video{args.camera} servo={args.servo_host}:{args.servo_port}")

    # Initialize
    detector = FaceDetector()
    selector = TargetSelector()
    servo = ServoClient(host=args.servo_host, port=args.servo_port, dry_run=args.dry_run)
    servo.connect()

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"[tracker] ERROR: cannot open /dev/video{args.camera}")
        return 1
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    print("[tracker] running... press Ctrl+C to stop")

    last_servo_time = 0.0
    no_face_count = 0

    try:
        while True:
            t0 = time.monotonic()

            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Resize if needed
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))

            faces = detector.detect(frame)
            target = selector.select(faces)

            now = time.monotonic()

            if target is not None:
                no_face_count = 0
                pwms = face_to_servo_pwm(target)

                # Update servo at controlled rate
                if (now - last_servo_time) * 1000 >= args.update_ms:
                    servo.update_servos(pwms, duration_ms=200)
                    last_servo_time = now

                # Status line
                print(
                    f"\r[track] face={target.center_x:.2f},{target.center_y:.2f} "
                    f"area={target.area:.3f} "
                    f"yaw={pwms[SERVO_ID_HEAD_YAW]:4d} "
                    f"pitch={pwms[SERVO_ID_HEAD_PITCH]:4d} "
                    f"lift={pwms[SERVO_ID_LIFT]:4d} "
                    f"reach={pwms[SERVO_ID_REACH]:4d}",
                    end="", flush=True,
                )
            else:
                no_face_count += 1
                # Return to center after 30 frames without face
                if no_face_count > 30:
                    if (now - last_servo_time) * 1000 >= args.update_ms:
                        servo.update_servos(dict(SERVO_CENTER), duration_ms=200)
                        last_servo_time = now
                    print("\r[track] no face - returning to center", end="", flush=True)

            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[tracker] stopping...")
    finally:
        # Return to center before stopping
        servo.update_servos(dict(SERVO_CENTER), duration_ms=300)
        time.sleep(0.3)
        cap.release()
        servo.close()
        print("[tracker] stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
