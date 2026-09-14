#!/usr/bin/env python3
"""Servo 3 (head) shake script for RDK X5 board.

Shakes servo 3 (head) left and right for a specified number of cycles.

Usage:
    python3 servo_3_shake_2100_2000.py --cycles 2 --left 2360 --right 1980 \
        --return-target 2130 --speed 260 --pause 0.05 --max-segment-wait 3.0
"""

from __future__ import annotations

import argparse
import sys
import time


DEFAULT_DEVICE = "/dev/ttyS1"
DEFAULT_BAUDRATE = 1_000_000
SERVO_ID = 3
TARGET_POSITION = 0x2A  # register 42


def checksum(payload: bytes | bytearray) -> int:
    return (~(sum(payload) & 0xFF)) & 0xFF


def pack_s16(value: int) -> bytes:
    return int(value).to_bytes(2, byteorder="little", signed=True)


def build_write_packet(servo_id: int, address: int, data: bytes) -> bytes:
    params = bytes((address, len(data))) + data
    body = bytes((servo_id, len(params) + 2, 0x03)) + params  # 0x03 = WRITE
    return bytes((0xFF, 0xFF)) + body + bytes((checksum(body),))


def build_move_packet(servo_id: int, position: int, speed: int) -> bytes:
    return build_write_packet(servo_id, TARGET_POSITION, pack_s16(position) + pack_s16(0) + pack_s16(speed))


def move_servo(ser, position: int, speed: int) -> None:
    packet = build_move_packet(SERVO_ID, position, speed)
    ser.reset_input_buffer()
    ser.write(packet)
    ser.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Shake servo 3 (head) left and right.")
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--left", type=int, default=2360)
    parser.add_argument("--right", type=int, default=1980)
    parser.add_argument("--return-target", type=int, default=2130)
    parser.add_argument("--speed", type=int, default=260)
    parser.add_argument("--pause", type=float, default=0.05)
    parser.add_argument("--max-segment-wait", type=float, default=3.0)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--baudrate", type=int, default=DEFAULT_BAUDRATE)
    args = parser.parse_args()

    try:
        import serial
    except ImportError:
        print("ERROR: pyserial required", file=sys.stderr)
        return 1

    try:
        ser = serial.Serial(args.device, args.baudrate, timeout=0.1)
    except Exception as exc:
        print(f"ERROR: cannot open {args.device}: {exc}", file=sys.stderr)
        return 1

    for cycle in range(args.cycles):
        move_servo(ser, args.left, args.speed)
        time.sleep(args.max_segment_wait)
        time.sleep(args.pause)
        move_servo(ser, args.right, args.speed)
        time.sleep(args.max_segment_wait)
        time.sleep(args.pause)

    move_servo(ser, args.return_target, args.speed)
    time.sleep(args.max_segment_wait)
    ser.close()

    print(f"OK shake servo {SERVO_ID} cycles={args.cycles} left={args.left} right={args.right}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
