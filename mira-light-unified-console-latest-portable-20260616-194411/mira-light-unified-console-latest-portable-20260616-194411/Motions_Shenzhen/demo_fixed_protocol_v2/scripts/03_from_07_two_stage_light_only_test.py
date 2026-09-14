#!/usr/bin/env python3

from __future__ import annotations

from common import RemoteStep, build_parser, exit_from_plan


def led(command: str) -> str:
    return f"python3 /home/sunrise/Desktop/send_uart3_led_cmd.py {command}"


def white_spin(brightness: int = 150) -> str:
    return led(f"spin 255 255 255 0 1 {brightness}")


def build_steps(*, stage1_seconds: float, stage2_seconds: float, final_mode: str) -> list[RemoteStep]:
    stage1_hold = max(0.0, stage1_seconds)
    stage2_hold = max(0.0, stage2_seconds)

    steps: list[RemoteStep] = [
        RemoteStep("light-only safety note", "echo '[03-from-07 light only] no servo motion commands in this script'"),
        RemoteStep("stage 1 soft white palm rotation", white_spin(150)),
        RemoteStep("stage 1 hold white rotation", f"sleep {stage1_hold:.2f}"),
        RemoteStep("stage 2 bright white palm rotation", white_spin(155)),
        RemoteStep("stage 2 hold white rotation", f"sleep {stage2_hold:.2f}"),
    ]

    if final_mode == "breathe":
        steps.append(RemoteStep("finish in soft white rotation", white_spin(125)))
    elif final_mode == "steady":
        steps.append(RemoteStep("finish in steady white light", led("all 255 255 255 120")))

    return steps


def main() -> None:
    parser = build_parser("Light-only test for scene 03 from 07: continuous white spin.")
    parser.add_argument("--stage1-seconds", type=float, default=3.5)
    parser.add_argument("--stage2-seconds", type=float, default=3.5)
    parser.add_argument("--final-mode", choices=("keep-spin", "breathe", "steady"), default="keep-spin")
    args = parser.parse_args()
    exit_from_plan(
        args=args,
        steps=build_steps(
            stage1_seconds=args.stage1_seconds,
            stage2_seconds=args.stage2_seconds,
            final_mode=args.final_mode,
        ),
    )


if __name__ == "__main__":
    main()
