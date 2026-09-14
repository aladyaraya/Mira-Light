#!/usr/bin/env python3

from __future__ import annotations

from common import RemoteStep, build_parser, exit_from_plan


def led(command: str) -> str:
    return f"python3 /home/sunrise/Desktop/send_uart3_led_cmd.py {command}"


def white_spin(brightness: int = 150) -> str:
    return led(f"spin 255 255 255 0 1 {brightness}")


def build_steps(*, breathe_seconds: float, spin_seconds: float) -> list[RemoteStep]:
    breathe_hold = max(0.0, breathe_seconds)
    spin_hold = max(0.0, spin_seconds)
    return [
        RemoteStep("light-only safety note", "echo '[light only] right-hand nuzzle light, no servo motion commands'"),
        RemoteStep("D soft white palm rotation", white_spin(145)),
        RemoteStep("D soft white rotation hold", f"sleep {breathe_hold:.2f}"),
        RemoteStep("D stage 2 bright white palm rotation", white_spin(155)),
        RemoteStep("D stage 2 white rotation hold", f"sleep {spin_hold:.2f}"),
    ]


def main() -> None:
    parser = build_parser("Light-only test for right-hand nuzzle D-stage lighting.")
    parser.add_argument("--breathe-seconds", type=float, default=0.2)
    parser.add_argument("--spin-seconds", type=float, default=0.6)
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(breathe_seconds=args.breathe_seconds, spin_seconds=args.spin_seconds))


if __name__ == "__main__":
    main()
