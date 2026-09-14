#!/usr/bin/env python3

from __future__ import annotations

from common import RemoteStep, build_parser, exit_from_plan


START_POSE = (2360, 2300, 2376, 2130)
START_SPEEDS_OLD03_2X = (240, 150, 150, 220)


def led(command: str) -> str:
    return f"python3 /home/sunrise/Desktop/send_uart3_led_cmd.py {command}"


def white_spin(brightness: int = 150) -> str:
    return led(f"spin 255 255 255 0 1 {brightness}")


def pose(label: str, positions: tuple[int, int, int, int], speeds: tuple[int, int, int, int]) -> RemoteStep:
    p0, p1, p2, p3 = positions
    s0, s1, s2, s3 = speeds
    return RemoteStep(
        label,
        f"python3 /home/sunrise/Desktop/four_servo_control.py pose {p0} {p1} {p2} {p3} --speeds {s0} {s1} {s2} {s3}",
    )


def build_white_rotation(total_seconds: float) -> list[RemoteStep]:
    hold = max(0.0, total_seconds)
    return [
        RemoteStep("stage 2 bright white palm rotation", white_spin(155)),
        RemoteStep("stage 2 hold white rotation", f"sleep {hold:.2f}"),
    ]


def build_steps(*, stage1_seconds: float, stage2_seconds: float, skip_start_pose: bool) -> list[RemoteStep]:
    stage1_hold = max(0.0, stage1_seconds)
    stage2_hold = max(0.0, stage2_seconds)

    steps: list[RemoteStep] = [
        RemoteStep("03 from 07 safety note", "echo '[03-from-07] start pose only, no later nuzzle motion yet'"),
    ]
    if not skip_start_pose:
        steps.append(pose("set 03 initial pose from 07 end", START_POSE, START_SPEEDS_OLD03_2X))

    steps.extend(
        [
            RemoteStep("stage 1 soft white palm rotation", white_spin(150)),
            RemoteStep("stage 1 hold white rotation", f"sleep {stage1_hold:.2f}"),
        ]
    )
    steps.extend(build_white_rotation(stage2_hold))

    return steps


def main() -> None:
    parser = build_parser("Test scene 03 from scene 07 end pose, with only the agreed two-stage light behavior.")
    parser.add_argument("--stage1-seconds", type=float, default=3.5)
    parser.add_argument("--stage2-seconds", type=float, default=3.5)
    parser.add_argument("--skip-start-pose", action="store_true", help="Do not send the start-pose command if already in 07 end pose.")
    args = parser.parse_args()
    exit_from_plan(
        args=args,
        steps=build_steps(
            stage1_seconds=args.stage1_seconds,
            stage2_seconds=args.stage2_seconds,
            skip_start_pose=args.skip_start_pose,
        ),
    )


if __name__ == "__main__":
    main()
