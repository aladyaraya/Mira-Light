#!/usr/bin/env python3
"""Scene 22: Laugh Giggle - 大笑欢乐.

Mira hears something funny and starts laughing, with bouncy rhythmic movements.
All 4 servos engaged: base wobbles side to side, tilt bobs up and down rhythmically,
height bounces, lateral tilt swings with laughter.
Speed: rhythmic medium-fast bounces (200-350) with pauses between giggles.

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


def build_steps(*, laugh_cycles: int, intensity: str) -> list[RemoteStep]:
    if intensity == "high":
        bounce_speed = 380
        bounce_range = 400
    elif intensity == "low":
        bounce_speed = 200
        bounce_range = 200
    else:  # medium
        bounce_speed = 300
        bounce_range = 300

    steps: list[RemoteStep] = []

    # Phase 1: Hear joke - initial snort, all 4 servos twitch (medium-fast)
    steps.extend([
        pose("hear joke - snort", 2048, 2100, 2100, 2200, 250, 200, 220, 250),
        led("all", 255, 240, 200, 110),
        hold("snort hold", 0.15),
        # Try to hold it in - slight tremor (medium)
        pose("hold it in - tremor", 2048, 2120, 2080, 2100, 150, 110, 120, 150),
        hold("tremor hold", 0.2),
    ])

    # Phase 2: Laugh cycles - rhythmic bouncy giggles (all 4 servos, medium-fast)
    for i in range(laugh_cycles):
        side = 1 if i % 2 == 0 else -1
        base_wobble = 2048 + int(bounce_range * 0.4 * side)
        tilt_wobble = 2130 + int(bounce_range * 0.35 * side)

        steps.extend([
            # Laugh bounce up - all 4 servos bounce (fast, rhythmic)
            pose(f"laugh {i+1} bounce up", base_wobble, 1950, 2200 + int(bounce_range * 0.3), tilt_wobble,
                 bounce_speed, int(bounce_speed * 0.8), int(bounce_speed * 0.85), bounce_speed),
            hold(f"laugh {i+1} up hold", 0.06),
            # Laugh bounce down - all 4 servos drop (fast)
            pose(f"laugh {i+1} bounce down", 2048 - int(bounce_range * 0.3 * side), 2250, 1950, 2130 - int(bounce_range * 0.3 * side),
                 int(bounce_speed * 0.9), int(bounce_speed * 0.75), int(bounce_speed * 0.8), int(bounce_speed * 0.9)),
            hold(f"laugh {i+1} down hold", 0.05),
            # Quick wobble - giggling (fast)
            pose(f"laugh {i+1} wobble", 2048 + int(bounce_range * 0.2 * side), 2100, 2050, 2130 + int(bounce_range * 0.25 * side),
                 int(bounce_speed * 0.85), int(bounce_speed * 0.7), int(bounce_speed * 0.75), int(bounce_speed * 0.85)),
            hold(f"laugh {i+1} wobble hold", 0.08),
        ])

    # Phase 3: Winding down - giggles slow (medium-slow, all 4 servos)
    steps.extend([
        pose("winding down - last giggle", 2100, 2150, 2020, 2200, 180, 130, 140, 180),
        hold("last giggle hold", 0.15),
        pose("winding down - sigh", 2048, 2200, 1980, 2130, 120, 90, 100, 120),
        led("all", 255, 235, 195, 105),
        hold("sigh hold", 0.2),
        # Happy settle - still amused (slow)
        pose("happy settle", 2048, 2150, 2050, 2150, 100, 70, 75, 100),
        hold("settle hold", 0.15),
        pose("return neutral", 2048, 2150, 2048, 2130, 90, 60, 60, 90),
        led("all", 255, 225, 185, 105),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 22: Laugh Giggle - bouncy laughter, all 4 servos, rhythmic fast.")
    parser.add_argument("--laugh-cycles", type=int, default=4, help="Number of laugh bounce cycles (default 4)")
    parser.add_argument("--intensity", choices=["low", "medium", "high"], default="medium", help="Laugh intensity")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        laugh_cycles=args.laugh_cycles,
        intensity=args.intensity,
    ))


if __name__ == "__main__":
    main()
