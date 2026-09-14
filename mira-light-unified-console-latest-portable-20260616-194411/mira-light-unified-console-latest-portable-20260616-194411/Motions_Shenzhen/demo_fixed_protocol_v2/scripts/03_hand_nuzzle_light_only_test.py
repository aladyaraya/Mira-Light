#!/usr/bin/env python3

from __future__ import annotations

from common import RemoteStep, build_parser, exit_from_plan


def led(command: str) -> str:
    return f"python3 /home/sunrise/Desktop/send_uart3_led_cmd.py {command}"


def white_spin(brightness: int = 150) -> str:
    return led(f"spin 255 255 255 0 1 {brightness}")


def build_steps(*, linger_seconds: float, pulse_cycles: int) -> list[RemoteStep]:
    linger = max(0.0, linger_seconds)
    cycles = max(1, min(pulse_cycles, 6))

    steps: list[RemoteStep] = [
        RemoteStep("light-only safety note", "echo '[light only] no servo motion commands in this script'"),
        RemoteStep("stage 1 soft white palm rotation", white_spin(150)),
        RemoteStep("stage 1 hold white rotation", f"sleep {linger:.2f}"),
    ]

    for idx in range(cycles):
        cycle = idx + 1
        steps.extend(
            [
                RemoteStep(f"stage 2 white rotation {cycle} slightly brighter", white_spin(160)),
                RemoteStep(f"stage 2 white rotation {cycle} bright hold", "sleep 0.28"),
                RemoteStep(f"stage 2 white rotation {cycle} soft settle", white_spin(130)),
                RemoteStep(f"stage 2 white rotation {cycle} soft hold", "sleep 0.24"),
            ]
        )

    return steps


def main() -> None:
    parser = build_parser("Light-only test for scene 03 hand nuzzle with white rotating lighting.")
    parser.add_argument("--linger-seconds", type=float, default=3.5)
    parser.add_argument("--pulse-cycles", type=int, default=2)
    args = parser.parse_args()
    exit_from_plan(
        args=args,
        steps=build_steps(
            linger_seconds=args.linger_seconds,
            pulse_cycles=args.pulse_cycles,
        ),
    )


if __name__ == "__main__":
    main()
