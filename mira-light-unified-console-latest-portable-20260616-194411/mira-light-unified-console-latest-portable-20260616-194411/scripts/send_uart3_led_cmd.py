#!/usr/bin/env python3
"""LED control script for RDK X5 (LCKFB) board.

Controls WS2812/UART3 LED strip. Provides the same CLI interface as the
original send_uart3_led_cmd.py:

  off                              - turn off all LEDs
  all R G B BRIGHTNESS             - set all LEDs to color
  spin R G B BRIGHTNESS SPEED COUNT - spinning animation
  spin --rainbow 0 1 SPEED         - rainbow spinning animation

If pyserial is not available or /dev/ttyS3 is not accessible, the script
prints a skip message and exits 0 (graceful degradation).
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional


DEFAULT_DEVICE = "/dev/ttyS3"
DEFAULT_BAUDRATE = 115200
LED_COUNT = 40


def open_serial(device: str, baudrate: int):
    try:
        import serial
        return serial.Serial(device, baudrate, timeout=0.1)
    except Exception as exc:
        print(f"[skip] LED serial not available: {exc}", file=sys.stderr)
        return None


def cmd_off(device: str, baudrate: int) -> int:
    ser = open_serial(device, baudrate)
    if ser is None:
        return 0
    # Send all-off command
    data = bytes([0x00] * (LED_COUNT * 3 + 4))
    ser.write(data)
    ser.flush()
    ser.close()
    print("OK led off")
    return 0


def cmd_all(r: int, g: int, b: int, brightness: int, device: str, baudrate: int) -> int:
    ser = open_serial(device, baudrate)
    if ser is None:
        return 0
    # Scale by brightness (0-255)
    scale = max(0, min(255, int(brightness))) / 255.0
    r_val = int(r * scale)
    g_val = int(g * scale)
    b_val = int(b * scale)
    # Build frame: header + RGB data for each LED
    header = bytes([0xAA, LED_COUNT & 0xFF, (LED_COUNT >> 8) & 0xFF])
    pixel_data = bytes([g_val, r_val, b_val] * LED_COUNT)
    ser.write(header + pixel_data)
    ser.flush()
    ser.close()
    print(f"OK led all r={r} g={g} b={b} brightness={brightness}")
    return 0


def cmd_spin(r: int, g: int, b: int, brightness: int, speed: int, count: int,
             rainbow: bool, device: str, baudrate: int) -> int:
    ser = open_serial(device, baudrate)
    if ser is None:
        return 0

    scale = max(0, min(255, int(brightness))) / 255.0
    delay = 1.0 / max(1, int(speed)) if speed > 0 else 0.05

    for frame in range(max(1, int(count)) * LED_COUNT):
        header = bytes([0xAA, LED_COUNT & 0xFF, (LED_COUNT >> 8) & 0xFF])
        pixel_data = bytearray()
        for i in range(LED_COUNT):
            if rainbow:
                hue = ((i + frame) * 360 // LED_COUNT) % 360
                rr, gg, bb = hsv_to_rgb(hue, 1.0, scale)
            else:
                rr = int(r * scale)
                gg = int(g * scale)
                bb = int(b * scale)
            pixel_data.extend([gg, rr, bb])
        ser.write(header + bytes(pixel_data))
        ser.flush()
        time.sleep(delay)

    ser.close()
    print(f"OK led spin rainbow={rainbow} speed={speed} count={count}")
    return 0


def hsv_to_rgb(h: int, s: float, v: float) -> tuple[int, int, int]:
    """Convert HSV (h: 0-360, s: 0-1, v: 0-1) to RGB (0-255)."""
    c = v * s
    x = c * (1 - abs(((h / 60.0) % 2) - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LED control for RDK X5 board.")
    parser.add_argument("--device", default="/dev/ttyS3")
    parser.add_argument("--baudrate", type=int, default=DEFAULT_BAUDRATE)

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("off", help="Turn off all LEDs")

    all_parser = sub.add_parser("all", help="Set all LEDs to a color")
    all_parser.add_argument("r", type=int)
    all_parser.add_argument("g", type=int)
    all_parser.add_argument("b", type=int)
    all_parser.add_argument("brightness", type=int)

    spin_parser = sub.add_parser("spin", help="Spinning animation")
    spin_parser.add_argument("--rainbow", action="store_true")
    spin_parser.add_argument("r", type=int, nargs="?", default=0)
    spin_parser.add_argument("g", type=int, nargs="?", default=0)
    spin_parser.add_argument("b", type=int, nargs="?", default=0)
    spin_parser.add_argument("brightness", type=int, nargs="?", default=0)
    spin_parser.add_argument("speed", type=int, nargs="?", default=150)
    spin_parser.add_argument("count", type=int, nargs="?", default=1)

    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()

    if args.command == "off":
        return cmd_off(args.device, args.baudrate)
    elif args.command == "all":
        return cmd_all(args.r, args.g, args.b, args.brightness, args.device, args.baudrate)
    elif args.command == "spin":
        return cmd_spin(args.r, args.g, args.b, args.brightness, args.speed, args.count,
                        args.rainbow, args.device, args.baudrate)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
