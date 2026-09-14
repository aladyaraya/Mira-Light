#!/usr/bin/env python3
"""Four-servo control script for RDK X5 (LCKFB) board.

Directly accesses /dev/ttyS1 UART at 1000000 baud to control Feetech
serial bus servos (STS series). Provides the same CLI interface as the
original four_servo_control.py:

  pose P0 P1 P2 P3 --speeds S0 S1 S2 S3   - move 4 servos to positions
  read-pos-all                              - read current positions
  ping-all                                  - ping all 4 servos

This script is self-contained: it does NOT depend on the TCP bridge.
The TCP bridge (rdk_bus_servo_tcp_bridge.py) may call this script for
read-pos-all, so we must NOT create a circular dependency.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional


# ── Feetech protocol constants ──
HEADER = bytes((0xFF, 0xFF))
BROADCAST_ID = 0xFE
SYNC_WRITE = 0x83
PING = 0x01
READ = 0x02
TARGET_POSITION = 0x2A       # register 42: goal position
CURRENT_POSITION = 0x38      # register 56: current position
SERVO_COUNT = 4
DEFAULT_DEVICE = "/dev/ttyS1"
DEFAULT_BAUDRATE = 1_000_000
DEFAULT_TIMEOUT = 0.15
SERVO_IDS = list(range(SERVO_COUNT))  # [0, 1, 2, 3]


def checksum(payload: bytes | bytearray) -> int:
    return (~(sum(payload) & 0xFF)) & 0xFF


def pack_u16(value: int) -> bytes:
    return int(value).to_bytes(2, byteorder="little", signed=False)


def pack_s16(value: int) -> bytes:
    return int(value).to_bytes(2, byteorder="little", signed=True)


def build_packet(servo_id: int, instruction: int, parameters: list[int]) -> bytes:
    params = bytes(parameters)
    body = bytes((servo_id, len(params) + 2, instruction)) + params
    return HEADER + body + bytes((checksum(body),))


def build_sync_write_packet(address: int, data_len: int, items: list[tuple[int, bytes]]) -> bytes:
    params = bytearray((address, data_len))
    for servo_id, data in items:
        if len(data) != data_len:
            raise ValueError(f"sync-write data length mismatch for servo {servo_id}")
        params.append(int(servo_id))
        params.extend(data)
    return build_packet(BROADCAST_ID, SYNC_WRITE, list(params))


def build_move_data(position: int, run_time: int, speed: int) -> bytes:
    return pack_s16(position) + pack_u16(run_time) + pack_s16(speed)


def open_serial(device: str, baudrate: int, timeout: float):
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("pyserial is required. Install: pip install pyserial") from exc
    return serial.Serial(device, baudrate, timeout=timeout)


def cmd_pose(positions: list[int], speeds: list[int], device: str, baudrate: int, timeout: float) -> int:
    """Move 4 servos to target positions using sync write."""
    if len(positions) != SERVO_COUNT:
        print(f"ERROR: expected {SERVO_COUNT} positions, got {len(positions)}", file=sys.stderr)
        return 1
    if len(speeds) != SERVO_COUNT:
        speeds = speeds + [speeds[-1]] * (SERVO_COUNT - len(speeds))

    moves = []
    for servo_id, pos, spd in zip(SERVO_IDS, positions, speeds):
        pos = max(0, min(4095, int(pos)))
        spd = max(0, min(3000, int(spd)))
        # run_time=0 means use speed only; servo firmware handles trajectory
        moves.append((servo_id, build_move_data(pos, 0, spd)))

    packet = build_sync_write_packet(TARGET_POSITION, 6, moves)

    try:
        ser = open_serial(device, baudrate, timeout)
        ser.reset_input_buffer()
        ser.write(packet)
        ser.flush()
        ser.close()
    except Exception as exc:
        print(f"ERROR: failed to send pose command: {exc}", file=sys.stderr)
        return 1

    print(f"OK pose {positions} speeds {speeds}")
    return 0


def cmd_read_pos_all(device: str, baudrate: int, timeout: float) -> int:
    """Read current position of all 4 servos."""
    try:
        ser = open_serial(device, baudrate, timeout)
    except Exception as exc:
        print(f"ERROR: failed to open serial: {exc}", file=sys.stderr)
        return 1

    for servo_id in SERVO_IDS:
        # Read 2 bytes from CURRENT_POSITION register
        packet = build_packet(servo_id, READ, [CURRENT_POSITION, 2])
        ser.reset_input_buffer()
        ser.write(packet)
        ser.flush()
        time.sleep(0.005)

        # Read response: header(2) + id(1) + length(1) + error(1) + data(2) + checksum(1) = 8 bytes
        response = ser.read(8)
        if len(response) < 8 or response[0:2] != HEADER:
            print(f"Read ID : {servo_id}  Position : -  (no response)")
            continue
        resp_id = response[2]
        resp_len = response[3]
        resp_error = response[4]
        if resp_error != 0:
            print(f"Read ID : {servo_id}  Position : -  (error={resp_error})")
            continue
        position = int.from_bytes(response[5:7], byteorder="little", signed=False)
        print(f"Read ID : {servo_id}  Position : {position}")

    ser.close()
    return 0


def cmd_ping_all(device: str, baudrate: int, timeout: float) -> int:
    """Ping all 4 servos."""
    try:
        ser = open_serial(device, baudrate, timeout)
    except Exception as exc:
        print(f"ERROR: failed to open serial: {exc}", file=sys.stderr)
        return 1

    all_ok = True
    for servo_id in SERVO_IDS:
        packet = build_packet(servo_id, PING, [])
        ser.reset_input_buffer()
        ser.write(packet)
        ser.flush()
        time.sleep(0.005)

        # Response: header(2) + id(1) + length(1) + error(1) + checksum(1) = 6 bytes
        response = ser.read(6)
        if len(response) >= 6 and response[0:2] == HEADER and response[2] == servo_id and response[4] == 0:
            print(f"Ping ID : {servo_id}  OK")
        else:
            print(f"Ping ID : {servo_id}  FAIL")
            all_ok = False

    ser.close()
    return 0 if all_ok else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Four-servo control for RDK X5 (Feetech bus servos).")
    parser.add_argument("--device", default=os.environ.get("MIRA_SERVO_DEVICE", DEFAULT_DEVICE))
    parser.add_argument("--baudrate", type=int, default=int(os.environ.get("MIRA_SERVO_BAUDRATE", str(DEFAULT_BAUDRATE))))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)

    sub = parser.add_subparsers(dest="command", required=True)

    pose_parser = sub.add_parser("pose", help="Move 4 servos to target positions")
    pose_parser.add_argument("positions", nargs=4, type=int, help="4 target positions (0-4095)")
    pose_parser.add_argument("--speeds", nargs=4, type=int, default=[1000, 1000, 1000, 1000],
                             help="4 speeds (steps/sec)")

    sub.add_parser("read-pos-all", help="Read current positions of all 4 servos")
    sub.add_parser("ping-all", help="Ping all 4 servos")

    return parser.parse_args(argv)


def main() -> int:
    import os
    args = parse_args()

    if args.command == "pose":
        return cmd_pose(args.positions, args.speeds, args.device, args.baudrate, args.timeout)
    elif args.command == "read-pos-all":
        return cmd_read_pos_all(args.device, args.baudrate, args.timeout)
    elif args.command == "ping-all":
        return cmd_ping_all(args.device, args.baudrate, args.timeout)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import os
    raise SystemExit(main())
