#!/usr/bin/env python3
"""Scene 19: Angry Pout - 愤怒生气.

Mira gets frustrated or annoyed, does angry stamping and turning away.
All 4 servos engaged: base turns away sharply, tilt pushes forward aggressively,
height stamps down, lateral tilt juts out.
Speed: fast aggressive bursts (300-500) with abrupt stops, then slow simmer (80-120).

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


def build_steps(*, anger_cycles: int, simmer_seconds: float) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Trigger - sudden irritation, all 4 servos jolt (fast)
    steps.extend([
        pose("trigger - irritation jolt", 2048, 2200, 1950, 2300, 350, 300, 320, 350),
        led("all", 255, 80, 60, 120),
        hold("jolt hold", 0.15),
        # Turn away angrily - servo 0 + 3 sharp turn (fast)
        pose("turn away angry", 2350, 2150, 2048, 2400, 400, 300, 320, 400),
        led("all", 255, 60, 40, 130),
        hold("turn away hold", 0.2),
    ])

    # Phase 2: Angry stamping cycles - fast stamp down + sharp turn (all 4 servos)
    for i in range(anger_cycles):
        side = 1 if i % 2 == 0 else -1
        base_turn = 2048 + int(300 * side)
        tilt_jut = 2130 + int(200 * side)

        steps.extend([
            # Fast stamp down - height drops aggressively (all 4 servos, fast)
            pose(f"anger {i+1} stamp down", base_turn, 2250, 1850, tilt_jut, 450, 380, 420, 450),
            hold(f"anger {i+1} stamp hold", 0.08),
            # Sharp turn away (fast, aggressive)
            pose(f"anger {i+1} snap away", 2048 - int(250 * side), 2150, 2000, 2130 - int(180 * side), 480, 350, 380, 480),
            hold(f"anger {i+1} away hold", 0.12),
            # Forward jut - angry push (fast)
            pose(f"anger {i+1} push forward", 2048 - int(100 * side), 2050, 2200, 2130 + int(150 * side), 400, 320, 360, 400),
            hold(f"anger {i+1} push hold", 0.1),
        ])

    # Phase 3: Slow simmer - angry brooding (slow, all 4 servos)
    steps.extend([
        pose("simmer - brooding turn", 2250, 2180, 1980, 2280, 100, 70, 80, 100),
        led("all", 255, 70, 50, 110),
        hold("simmer hold", simmer_seconds),
        # Small angry twitch (medium-fast)
        pose("angry twitch", 2150, 2200, 1950, 2200, 200, 150, 160, 200),
        hold("twitch hold", 0.15),
        pose("twitch back", 2250, 2180, 1980, 2280, 150, 100, 110, 150),
        hold("twitch back hold", 0.2),
    ])

    # Phase 4: Slow cool down - grudging recovery (slow, all 4 servos)
    steps.extend([
        pose("cool down - reluctant turn back", 2150, 2150, 2020, 2200, 80, 55, 60, 80),
        led("all", 255, 120, 80, 100),
        hold("cool down hold", 0.3),
        pose("cool down - almost neutral", 2080, 2150, 2040, 2160, 70, 50, 55, 70),
        led("all", 255, 180, 140, 100),
        hold("almost neutral hold", 0.2),
        pose("return neutral", 2048, 2150, 2048, 2130, 90, 60, 60, 90),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 19: Angry Pout - frustrated angry response, all 4 servos, fast aggressive.")
    parser.add_argument("--anger-cycles", type=int, default=3, help="Number of angry stamp cycles (default 3)")
    parser.add_argument("--simmer-seconds", type=float, default=0.8, help="Brooding simmer hold time")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        anger_cycles=args.anger_cycles,
        simmer_seconds=args.simmer_seconds,
    ))


if __name__ == "__main__":
    main()
