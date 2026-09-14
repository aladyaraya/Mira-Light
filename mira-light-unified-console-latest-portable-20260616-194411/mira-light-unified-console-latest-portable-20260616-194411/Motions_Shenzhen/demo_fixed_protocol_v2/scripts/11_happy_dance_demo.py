#!/usr/bin/env python3
"""Scene 11: Happy Dance - 开心跳舞.

Mira hears good news or gets praised, does a happy dance with colorful lights.
All 4 servos engaged: base sways side-to-side, head nods up-down, tilt swings left-right.
Speed varies: slow anticipation -> fast bouncy -> medium celebration.

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


def build_steps(*, bounce_cycles: int, hold_seconds: float, light_style: str) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Slow anticipation (speeds 80-120)
    steps.extend([
        pose("anticipate - lean back slightly", 2048, 2200, 1950, 2130, 80, 60, 60, 80),
        led("all", 255, 200, 160, 60),
        hold("anticipate hold", 0.3),
        # All 4 servos begin to move - slow build-up
        pose("build-up - rise and turn left", 2200, 2050, 2200, 2300, 100, 80, 90, 100),
        hold("build-up hold", 0.15),
    ])

    # Phase 2: Fast bouncy dance (speeds 300-500)
    if light_style == "rainbow":
        steps.append(led("spin", "--rainbow", 0, 1, 200))
    elif light_style == "warm":
        steps.append(led("spin", 255, 220, 150, 0, 1, 200))
    else:
        steps.append(led("spin", "--rainbow", 0, 1, 200))

    for i in range(bounce_cycles):
        left = i % 2 == 0
        base = 2250 if left else 1850
        tilt = 2400 if left else 1900
        steps.extend([
            # Fast bounce up + side (all 4 servos move aggressively)
            pose(f"bounce {i+1} up-{('L' if left else 'R')}", base, 1900, 2400, tilt, 400, 350, 380, 400),
            hold(f"bounce {i+1} peak", 0.08),
            # Fast bounce down + opposite side
            pose(f"bounce {i+1} down-{('R' if left else 'L')}", 4096 - base, 2250, 1800, 4096 - tilt, 420, 360, 400, 420),
            hold(f"bounce {i+1} valley", 0.06),
            # Quick center pop
            pose(f"bounce {i+1} center pop", 2048, 1950, 2500, 2130, 450, 400, 420, 350),
            hold(f"bounce {i+1} pop hold", 0.05),
        ])

    # Phase 3: Medium-speed celebration (speeds 200-280)
    steps.extend([
        # Big head shake celebration - fast servo 0 + 3
        RemoteStep("celebration head shake",
            f"python3 {DESKTOP}/servo_3_shake_2100_2000.py --cycles 3 --left 2400 --right 1900 --return-target 2130 --speed 350 --pause 0.03"),
        # Simultaneous nod - servo 1 + 2
        RemoteStep("celebration nod",
            f"python3 {DESKTOP}/servo_2_nod_1900_2200.py --cycles 2 --low 1850 --high 2250 --return-target 2048 --pre-target 2048 --speed 280 --pause 0.04"),
        # Big finish - all 4 servos to extreme happy pose, medium speed
        pose("big finish - reach high and wide", 2048, 1850, 2600, 2130, 250, 220, 240, 250),
        led("all", 255, 240, 200, 130),
        hold("finish hold", hold_seconds),
    ])

    # Phase 4: Slow cool-down (speeds 60-100)
    steps.extend([
        pose("cool down - gentle settle", 2048, 2050, 2200, 2200, 80, 60, 70, 80),
        hold("cool down hold", 0.3),
        pose("cool down - center", 2048, 2100, 2100, 2130, 70, 55, 60, 70),
        hold("center hold", 0.2),
        pose("return neutral", 2048, 2150, 2048, 2130, 100, 70, 70, 100),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 11: Happy Dance - bouncy celebration with party lights, all 4 servos.")
    parser.add_argument("--bounce-cycles", type=int, default=3, help="Number of bounce cycles (default 3)")
    parser.add_argument("--hold-seconds", type=float, default=1.0, help="Hold time at finish pose")
    parser.add_argument("--light-style", choices=["spin", "rainbow", "warm"], default="spin", help="Light effect style")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        bounce_cycles=args.bounce_cycles,
        hold_seconds=args.hold_seconds,
        light_style=args.light_style,
    ))


if __name__ == "__main__":
    main()
