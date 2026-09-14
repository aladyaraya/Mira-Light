#!/usr/bin/env python3
"""Scene 20: Proud Chest - 骄傲自信.

Mira accomplishes something and puffs up with pride, chest out and head high.
All 4 servos engaged: base holds tall, tilt leans back confidently, height rises to max,
lateral tilt spreads wide.
Speed: slow dignified (60-120) with proud pauses, medium final flourish (180-220).

Servo layout:
  0 = base rotation (left-right head turn), center 2048, range 1700-2400
  1 = forward-back tilt (nod/lift), center 2150, range 1800-2400
  2 = vertical height (up-down), center 2048, range 1800-2900
  3 = lateral tilt (head tilt), center 2130, range 1800-2500
"""

from __future__ import annotations

from common import RemoteStep, build_parser, exit_from_plan

DESKTOP = "/home/sunrise/Desktop"


def pose(label: str, s0: int, s1: int, s2: int, s3: int, sp0: int, sp1: int, sp2: int, sp3: int) -> RemoteStep:
    # Clamp speeds to minimum 120 so all 4 servos always move visibly
    sp0 = max(sp0, 120)
    sp1 = max(sp1, 120)
    sp2 = max(sp2, 120)
    sp3 = max(sp3, 120)
    return RemoteStep(label, f"python3 {DESKTOP}/four_servo_control.py pose {s0} {s1} {s2} {s3} --speeds {sp0} {sp1} {sp2} {sp3}")


def hold(label: str, seconds: float) -> RemoteStep:
    return RemoteStep(label, f"sleep {seconds:g}")


def led(cmd: str, *args) -> RemoteStep:
    return RemoteStep("light", f"python3 {DESKTOP}/send_uart3_led_cmd.py {cmd} {' '.join(str(a) for a in args)}")


def build_steps(*, proud_cycles: int, hold_seconds: float) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Realize achievement - slow lift, all 4 servos rise (slow dignified)
    steps.extend([
        pose("realize achievement", 2048, 2150, 2048, 2130, 100, 70, 70, 90),
        led("all", 255, 220, 180, 80),
        hold("realize hold", 0.3),
        # Slow puff up - all 4 servos expand upward and outward (slow, dignified)
        pose("puff up - chest out", 2048, 1950, 2300, 1950, 70, 55, 65, 70),
        led("all", 255, 240, 200, 110),
        hold("puff up hold", 0.4),
        # Rise higher - confident height (slow)
        pose("rise high - confident", 2048, 1850, 2500, 1900, 60, 50, 60, 60),
        led("all", 255, 250, 210, 130),
        hold("confident high hold", 0.5),
    ])

    # Phase 2: Proud display cycles - slow scan left and right (all 4 servos, dignified)
    for i in range(proud_cycles):
        side = 1 if i % 2 == 0 else -1
        base_scan = 2048 + int(200 * side)
        tilt_scan = 2130 - int(120 * side)

        steps.extend([
            # Slow proud scan to one side (all 4 servos, very slow and dignified)
            pose(f"proud {i+1} scan {'left' if side > 0 else 'right'}", base_scan, 1880, 2480, tilt_scan, 65, 50, 55, 65),
            hold(f"proud {i+1} scan hold", 0.4),
            # Subtle nod of satisfaction (medium-slow)
            pose(f"proud {i+1} satisfied nod", base_scan, 2000, 2400, tilt_scan, 90, 70, 75, 90),
            hold(f"proud {i+1} nod hold", 0.2),
            pose(f"proud {i+1} nod back", base_scan, 1880, 2480, tilt_scan, 80, 60, 65, 80),
            hold(f"proud {i+1} back hold", 0.15),
        ])

    # Phase 3: Final proud flourish - medium speed, all 4 servos (confident)
    steps.extend([
        pose("flourish - center high", 2048, 1850, 2550, 1900, 200, 160, 180, 200),
        led("all", 255, 255, 220, 140),
        hold("flourish hold", hold_seconds),
        # Slow proud settle (dignified)
        pose("proud settle - lower slightly", 2048, 1950, 2300, 2000, 80, 60, 65, 80),
        hold("settle hold", 0.2),
        pose("return neutral - dignified", 2048, 2150, 2048, 2130, 90, 60, 60, 90),
        led("all", 255, 225, 185, 110),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 20: Proud Chest - proud confident display, all 4 servos, slow dignified.")
    parser.add_argument("--proud-cycles", type=int, default=2, help="Number of proud scan cycles (default 2)")
    parser.add_argument("--hold-seconds", type=float, default=0.8, help="Final flourish hold time")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        proud_cycles=args.proud_cycles,
        hold_seconds=args.hold_seconds,
    ))


if __name__ == "__main__":
    main()
