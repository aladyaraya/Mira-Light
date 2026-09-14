#!/usr/bin/env python3
"""Scene 14: Shy Blush - 害羞脸红.

Mira receives praise or a compliment and acts shy, turning away then peeking back.
All 4 servos engaged: base rotates away (avert gaze), tilt dips down, height lowers,
lateral tilt gives coy head cocking.
Speed: slow throughout (50-120), with brief quick peeks at 150-180.

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


def build_steps(*, shy_cycles: int, linger_seconds: float) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Hear compliment - slight start, all 4 servos flinch slightly (slow)
    steps.extend([
        pose("hear compliment - slight flinch", 2048, 2120, 2020, 2100, 120, 80, 80, 100),
        led("all", 255, 180, 170, 90),
        hold("start hold", 0.3),
        # Turn away shyly - servo 0 rotates away + servo 3 tilts + servo 2 dips
        pose("turn away - avert gaze left", 2250, 2200, 1850, 2300, 70, 55, 60, 70),
        led("all", 255, 160, 150, 80),
        hold("shy dip hold", 0.5),
    ])

    # Phase 2: Shy peek cycles - slow dip, quick peek, slow retreat
    for i in range(shy_cycles):
        side = 1 if i % 2 == 0 else -1
        base_away = 2048 + int(250 * side)
        base_peek = 2048 + int(120 * side)
        tilt_away = 2130 + int(200 * side)
        tilt_peek = 2130 + int(100 * side)

        steps.extend([
            # Quick peek up toward user (faster speed - curious but shy)
            pose(f"shy {i+1} peek up", base_peek, 2080, 2050, tilt_peek, 150, 110, 120, 150),
            hold(f"shy {i+1} peek hold", 0.2),
            # Slow retreat back down - embarrassed (very slow)
            pose(f"shy {i+1} retreat down", base_away, 2210, 1830, tilt_away, 60, 45, 50, 60),
            hold(f"shy {i+1} down hold", 0.35),
            # Coy side tilt - servo 3 tilts while others hold (slow, coy)
            pose(f"shy {i+1} coy tilt", base_away, 2180, 1850, 2130 - int(150 * side), 50, 40, 45, 55),
            hold(f"shy {i+1} tilt hold", 0.25),
        ])

    # Phase 3: Slow recovery - gentle come back up, all 4 servos
    steps.extend([
        pose("recovery - gentle rise", 2150, 2150, 1950, 2180, 70, 55, 55, 70),
        led("all", 255, 200, 170, 85),
        hold("recovery hold", linger_seconds),
        # Final tiny shy nod - quick little dip
        pose("final shy nod", 2100, 2190, 1980, 2150, 100, 70, 70, 90),
        hold("nod hold", 0.2),
        # Slow return to neutral - all 4 servos ease back
        pose("return neutral", 2048, 2150, 2048, 2130, 80, 60, 60, 80),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 14: Shy Blush - coy response to praise, all 4 servos, slow speed.")
    parser.add_argument("--shy-cycles", type=int, default=2, help="Number of shy peek-dip cycles (default 2)")
    parser.add_argument("--linger-seconds", type=float, default=0.6, help="Recovery hold time")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        shy_cycles=args.shy_cycles,
        linger_seconds=args.linger_seconds,
    ))


if __name__ == "__main__":
    main()
