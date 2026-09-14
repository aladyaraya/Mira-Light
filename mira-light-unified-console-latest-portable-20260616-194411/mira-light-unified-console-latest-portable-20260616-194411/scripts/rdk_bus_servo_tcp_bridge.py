#!/usr/bin/env python3
"""TCP bridge from Mira Light text servo frames to RDK X5 UART bus servos."""

from __future__ import annotations

import argparse
import re
import socketserver
import subprocess
import threading
from dataclasses import dataclass
from typing import Iterable


HEADER = bytes((0xFF, 0xFF))
BROADCAST_ID = 0xFE
SYNC_WRITE = 0x83
TARGET_POSITION = 0x2A
SINGLE_FRAME_RE = re.compile(r"#(?P<id>\d{3})P(?P<pwm>\d{4})T(?P<time>\d{4})!")


@dataclass(frozen=True)
class ServoFrame:
    servo_id: int
    pwm: int
    time_ms: int


@dataclass(frozen=True)
class BridgeConfig:
    device: str
    baudrate: int
    timeout: float
    center_positions: dict[int, int]
    neutral_pwm: int
    steps_per_1000p: int
    speed: int
    four_servo_control: str


def checksum(payload: bytes | bytearray) -> int:
    return (~(sum(payload) & 0xFF)) & 0xFF


def pack_u16(value: int) -> bytes:
    return int(value).to_bytes(2, byteorder="little", signed=False)


def pack_s16(value: int) -> bytes:
    return int(value).to_bytes(2, byteorder="little", signed=True)


def build_packet(servo_id: int, instruction: int, parameters: Iterable[int]) -> bytes:
    params = bytes(parameters)
    body = bytes((servo_id, len(params) + 2, instruction)) + params
    return HEADER + body + bytes((checksum(body),))


def build_sync_write_packet(address: int, data_len: int, items: Iterable[tuple[int, bytes]]) -> bytes:
    params = bytearray((address, data_len))
    count = 0
    for servo_id, data in items:
        if len(data) != data_len:
            raise ValueError(f"sync-write data length mismatch for servo {servo_id}")
        params.append(int(servo_id))
        params.extend(data)
        count += 1
    if count == 0:
        raise ValueError("sync-write requires at least one servo frame")
    return build_packet(BROADCAST_ID, SYNC_WRITE, params)


def build_move_data(position: int, run_time: int, speed: int) -> bytes:
    return pack_s16(position) + pack_u16(run_time) + pack_s16(speed)


def parse_text_frames(raw: str) -> list[ServoFrame]:
    command = raw.strip()
    if not command:
        raise ValueError("empty servo command")
    if command.startswith("{") or command.endswith("}"):
        if not (command.startswith("{") and command.endswith("}")):
            raise ValueError("multi-servo command must be fully wrapped in braces")
        command = command[1:-1]

    matches = list(SINGLE_FRAME_RE.finditer(command))
    if not matches:
        raise ValueError("no valid servo frames found")
    rebuilt = "".join(match.group(0) for match in matches)
    if rebuilt != command:
        raise ValueError("servo command contains malformed frame data")
    return [
        ServoFrame(
            servo_id=int(match.group("id")),
            pwm=int(match.group("pwm")),
            time_ms=int(match.group("time")),
        )
        for match in matches
    ]


def pwm_to_position(pwm: int, *, servo_id: int, config: BridgeConfig) -> int:
    center_position = int(config.center_positions.get(int(servo_id), 2048))
    offset = round((int(pwm) - config.neutral_pwm) * config.steps_per_1000p / 1000.0)
    return max(0, min(4095, center_position + offset))


def frames_to_packet(frames: list[ServoFrame], config: BridgeConfig) -> bytes:
    moves = []
    for frame in frames:
        position = pwm_to_position(frame.pwm, servo_id=frame.servo_id, config=config)
        run_time = max(0, min(9999, int(frame.time_ms)))
        moves.append((frame.servo_id, build_move_data(position, run_time, config.speed)))
    return build_sync_write_packet(TARGET_POSITION, 6, moves)


def parse_center_positions(raw: str) -> dict[int, int]:
    values = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    if not values:
        raise ValueError("center positions must not be empty")
    if len(values) == 1:
        center = int(values[0])
        return {servo_id: center for servo_id in range(4)}
    if len(values) != 4:
        raise ValueError("center positions must be one value or four comma-separated values")
    return {servo_id: int(value) for servo_id, value in enumerate(values)}


class ServoBridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler_cls: type[socketserver.BaseRequestHandler], config: BridgeConfig):
        super().__init__(server_address, handler_cls)
        self.config = config
        self.serial_lock = threading.Lock()


class ServoBridgeHandler(socketserver.BaseRequestHandler):
    server: ServoBridgeServer

    def handle(self) -> None:
        chunks: list[bytes] = []
        while True:
            chunk = self.request.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break

        raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
        try:
            if raw.strip().upper() in {"READ", "READ-POS", "READ-POS-ALL"}:
                self.request.sendall(self._read_positions())
                return
            frames = parse_text_frames(raw)
            packet = frames_to_packet(frames, self.server.config)
            self._write_packet(packet)
        except Exception as exc:  # noqa: BLE001
            self.request.sendall(f"ERR,{exc}\n".encode("utf-8"))
            return

        ids = ",".join(str(frame.servo_id) for frame in frames)
        self.request.sendall(f"OK,ids={ids},bytes={len(packet)}\n".encode("utf-8"))

    def _read_positions(self) -> bytes:
        helper = self.server.config.four_servo_control
        result = subprocess.run(
            ["python3", helper, "read-pos-all"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "read-pos-all failed").strip()
            return f"ERR,read-pos-all,{detail}\n".encode("utf-8", errors="replace")
        output = result.stdout.strip()
        return f"OK,read-pos-all\n{output}\n".encode("utf-8", errors="replace")

    def _write_packet(self, packet: bytes) -> None:
        import serial

        config = self.server.config
        with self.server.serial_lock:
            with serial.Serial(config.device, config.baudrate, timeout=config.timeout) as ser:
                ser.reset_input_buffer()
                ser.write(packet)
                ser.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge Mira Light TCP servo text frames to RDK X5 UART bus servos.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9527)
    parser.add_argument("--device", default="/dev/ttyS1")
    parser.add_argument("--baudrate", type=int, default=1_000_000)
    parser.add_argument("--timeout", type=float, default=0.2)
    parser.add_argument("--center-position", type=int, default=None, help="Legacy single center position for all servos.")
    parser.add_argument("--center-positions", default="2048,2150,2048,2130")
    parser.add_argument("--neutral-pwm", type=int, default=1500)
    parser.add_argument("--steps-per-1000p", type=int, default=1536)
    parser.add_argument("--speed", type=int, default=1000)
    parser.add_argument("--four-servo-control", default="/home/sunrise/Desktop/four_servo_control.py")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = BridgeConfig(
        device=args.device,
        baudrate=args.baudrate,
        timeout=args.timeout,
        center_positions=parse_center_positions(args.center_position if args.center_position is not None else args.center_positions),
        neutral_pwm=args.neutral_pwm,
        steps_per_1000p=args.steps_per_1000p,
        speed=args.speed,
        four_servo_control=args.four_servo_control,
    )
    with ServoBridgeServer((args.host, args.port), ServoBridgeHandler, config) as server:
        print(
            f"RDK bus-servo TCP bridge listening on {args.host}:{args.port} "
            f"-> {args.device} @ {args.baudrate}",
            flush=True,
        )
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
