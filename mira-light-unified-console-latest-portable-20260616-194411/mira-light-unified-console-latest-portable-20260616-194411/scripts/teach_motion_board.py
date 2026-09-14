#!/usr/bin/env python3
"""Board-side lead-through teaching recorder and safe playback tool.

Run this script on the RDK X5 board next to ``four_servo_control.py`` and
``bus_servo_protocol.py``. It records the four UART3 bus servos while torque is
set to a compliant mode, then restores torque in a ``finally`` block.

Default mode is ``damp`` rather than ``off`` because the lamp has load-bearing
joints. Use ``off`` only while physically supporting the arm.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any


DESKTOP = Path("/home/sunrise/Desktop")
if DESKTOP.is_dir() and str(DESKTOP) not in sys.path:
    sys.path.insert(0, str(DESKTOP))

try:
    import serial  # type: ignore
    from bus_servo_protocol import (  # type: ignore
        Address,
        TORQUE_DAMP,
        TORQUE_OFF,
        TORQUE_ON,
        build_read_packet,
        build_torque_packet,
        parse_status_packet,
        unpack_u16,
    )
    from send_uart3_servo_cmd import DEFAULT_BAUDRATE, DEFAULT_DEVICE, DEFAULT_TIMEOUT, read_status_response  # type: ignore
except Exception as exc:  # noqa: BLE001
    serial = None  # type: ignore
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


SERVO_IDS = (0, 1, 2, 3)
SERVO_MIN = 0
SERVO_MAX = 4095
DEFAULT_OUTPUT_DIR = DESKTOP / "teach_motions"
STOP_REQUESTED = False
MAX_CONSECUTIVE_READ_ERRORS = 8
TORQUE_RESTORE_ATTEMPTS = 4


def request_stop(signum: int, _frame: object) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
    print(f"[teach] stop requested by signal {signum}", flush=True)


def require_board_imports() -> None:
    if IMPORT_ERROR is not None:
        raise RuntimeError(f"board servo imports failed: {IMPORT_ERROR}")


def open_serial(device: str, baudrate: int, timeout: float):
    require_board_imports()
    return serial.Serial(device, baudrate, timeout=timeout)  # type: ignore[union-attr]


def write_packet(ser: Any, packet: bytes) -> bytes:
    ser.reset_input_buffer()
    ser.write(packet)
    ser.flush()
    return read_status_response(ser)


def read_position(ser: Any, servo_id: int) -> int:
    response = write_packet(ser, build_read_packet(servo_id, Address.CURRENT_POSITION, 2))
    status = parse_status_packet(response)
    if not status.ok:
        raise RuntimeError(f"servo {servo_id} read error: 0x{status.error:02X}")
    value = unpack_u16(status.parameters)
    if value < SERVO_MIN or value > SERVO_MAX:
        raise RuntimeError(f"servo {servo_id} position out of range: {value}")
    return int(value)


def read_positions(ser: Any, ids: tuple[int, ...]) -> dict[str, int]:
    return {str(servo_id): read_position(ser, servo_id) for servo_id in ids}


def torque_value(mode: str) -> int:
    if mode == "on":
        return TORQUE_ON
    if mode == "off":
        return TORQUE_OFF
    if mode == "damp":
        return TORQUE_DAMP
    raise ValueError(f"unsupported torque mode: {mode}")


def set_torque(ser: Any, ids: tuple[int, ...], mode: str) -> None:
    value = torque_value(mode)
    for servo_id in ids:
        response = write_packet(ser, build_torque_packet(servo_id, value))
        status = parse_status_packet(response)
        if not status.ok:
            raise RuntimeError(f"servo {servo_id} torque {mode} error: 0x{status.error:02X}")


def restore_torque_with_retries(ser: Any, ids: tuple[int, ...]) -> None:
    last_error: Exception | None = None
    for attempt in range(1, TORQUE_RESTORE_ATTEMPTS + 1):
        try:
            set_torque(ser, ids, "on")
            print(f"[teach] torque restored: on (attempt {attempt})", flush=True)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[teach] torque restore attempt {attempt} failed: {exc}", file=sys.stderr, flush=True)
            time.sleep(0.18 * attempt)
    raise RuntimeError(f"failed to restore torque after {TORQUE_RESTORE_ATTEMPTS} attempts: {last_error}")


def timestamp_name(prefix: str) -> str:
    return time.strftime(f"{prefix}_%Y%m%d_%H%M%S.json")


def record(args: argparse.Namespace) -> int:
    output = args.output or (DEFAULT_OUTPUT_DIR / timestamp_name(args.name))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    ids = tuple(args.ids)
    frames: list[dict[str, Any]] = []
    started = time.monotonic()
    stopped_by = "duration"

    with open_serial(args.device, args.baudrate, args.timeout) as ser:
        initial = read_positions(ser, ids)
        print(f"[teach] initial positions: {initial}", flush=True)
        read_errors = 0
        try:
            set_torque(ser, ids, args.torque_mode)
            print(f"[teach] torque mode: {args.torque_mode}", flush=True)
            next_sample = time.monotonic()
            while True:
                now = time.monotonic()
                if STOP_REQUESTED:
                    stopped_by = "signal"
                    break
                if args.duration > 0 and now - started >= args.duration:
                    break
                if now < next_sample:
                    time.sleep(min(0.01, next_sample - now))
                    continue
                try:
                    positions = read_positions(ser, ids)
                    read_errors = 0
                except Exception as exc:  # noqa: BLE001
                    read_errors += 1
                    print(f"[teach] read skipped ({read_errors}/{MAX_CONSECUTIVE_READ_ERRORS}): {exc}", file=sys.stderr, flush=True)
                    if read_errors >= MAX_CONSECUTIVE_READ_ERRORS:
                        stopped_by = "read-error"
                        break
                    next_sample += args.sample_ms / 1000.0
                    continue
                frames.append({"tMs": int(round((time.monotonic() - started) * 1000)), "positions": positions})
                next_sample += args.sample_ms / 1000.0
        finally:
            try:
                restore_torque_with_retries(ser, ids)
            except Exception as exc:  # noqa: BLE001
                print(f"[teach] WARNING: failed to restore torque: {exc}", file=sys.stderr, flush=True)

    payload = {
        "version": 1,
        "source": "mira-light-board-uart3",
        "recordedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "device": args.device,
        "baudrate": args.baudrate,
        "timeout": args.timeout,
        "servos": [str(item) for item in ids],
        "torqueModeDuringRecord": args.torque_mode,
        "sampleMs": args.sample_ms,
        "durationMs": frames[-1]["tMs"] if frames else 0,
        "frameCount": len(frames),
        "stoppedBy": stopped_by,
        "initialPositions": initial,
        "frames": frames,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[teach] wrote {output} ({len(frames)} frames)", flush=True)
    return 0


def build_pose_command(positions: dict[str, int], *, speed: int, time_ms: int) -> list[str]:
    return [
        sys.executable,
        str(DESKTOP / "four_servo_control.py"),
        "pose",
        str(positions["0"]),
        str(positions["1"]),
        str(positions["2"]),
        str(positions["3"]),
        "--speeds",
        str(speed),
        str(speed),
        str(speed),
        str(speed),
        "--time",
        str(max(0, int(time_ms))),
    ]


def run_pose(positions: dict[str, int], *, speed: int, time_ms: int) -> None:
    import subprocess

    command = build_pose_command(positions, speed=speed, time_ms=time_ms)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"pose command failed with exit {result.returncode}")


def load_frames(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise RuntimeError("trajectory has no frames")
    return frames


def play(args: argparse.Namespace) -> int:
    frames = load_frames(args.input)
    first = frames[0]["positions"]
    run_pose(first, speed=args.start_speed, time_ms=args.start_time_ms)
    time.sleep(args.settle_seconds)

    previous = frames[0]
    for frame in frames[1:]:
        delta_ms = max(20, int(frame["tMs"]) - int(previous["tMs"]))
        scaled_ms = int(round(delta_ms / max(args.speed_scale, 0.05)))
        run_pose(frame["positions"], speed=args.speed, time_ms=scaled_ms)
        time.sleep(max(0.0, scaled_ms / 1000.0))
        previous = frame
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record or play Mira Light lead-through taught motions on the board.")
    parser.add_argument("--device", default="/dev/ttyS3")
    parser.add_argument("--baudrate", type=int, default=1_000_000)
    parser.add_argument("--timeout", type=float, default=0.2)
    parser.add_argument("--ids", nargs=4, type=int, default=SERVO_IDS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    record_parser = subparsers.add_parser("record", help="Record a lead-through trajectory")
    record_parser.add_argument("--name", default="teach_motion")
    record_parser.add_argument("--output", type=Path)
    record_parser.add_argument("--duration", type=float, default=12.0)
    record_parser.add_argument("--sample-ms", type=int, default=40)
    record_parser.add_argument("--torque-mode", choices=("damp", "off"), default="damp")

    play_parser = subparsers.add_parser("play", help="Play a cleaned trajectory JSON")
    play_parser.add_argument("input", type=Path)
    play_parser.add_argument("--speed-scale", type=float, default=0.5, help="0.5 means half speed; 1.0 means recorded timing")
    play_parser.add_argument("--speed", type=int, default=220)
    play_parser.add_argument("--start-speed", type=int, default=160)
    play_parser.add_argument("--start-time-ms", type=int, default=900)
    play_parser.add_argument("--settle-seconds", type=float, default=0.45)
    return parser


def main() -> int:
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    args = build_parser().parse_args()
    if args.command == "record":
        return record(args)
    if args.command == "play":
        return play(args)
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
