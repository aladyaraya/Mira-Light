#!/usr/bin/env python3
"""Scene 25: Bow Thanks - 鞠躬致谢.

Mira expresses gratitude with a respectful bow, then rises gracefully.
All 4 servos engaged: base holds facing forward, tilt dips down deeply for bow,
height lowers respectfully, lateral tilt stays centered and stable.
Speed: slow dignified bow down (50-80), medium rise (120-160), warm finish.

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


def build_steps(*, bow_cycles: int, bow_depth: str, hold_seconds: float) -> list[RemoteStep]:
    if bow_depth == "deep":
        tilt_low = 2380
        height_low = 1800
        bow_speed = 50
    elif bow_depth == "shallow":
        tilt_low = 2250
        height_low = 1950
        bow_speed = 80
    else:  # medium
        tilt_low = 2320
        height_low = 1880
        bow_speed = 65

    steps: list[RemoteStep] = []

    # Phase 1: Prepare - straighten up respectfully (slow, all 4 servos)
    steps.extend([
        pose("prepare - stand straight", 2048, 2050, 2200, 2130, 80, 60, 65, 80),
        led("all", 255, 230, 190, 100),
        hold("prepare hold", 0.3),
    ])

    # Phase 2: Bow cycles - slow deep bow, hold, rise (all 4 servos)
    for i in range(bow_cycles):
        steps.extend([
            # Slow deep bow - tilt forward + height lowers (very slow, dignified)
            pose(f"bow {i+1} down", 2048, tilt_low, height_low, 2130, bow_speed, int(bow_speed * 0.75), int(bow_speed * 0.8), bow_speed),
            led("all", 255, 220, 180, 90),
            hold(f"bow {i+1} bottom hold", hold_seconds),
            # Slow rise back up (dignified, slightly faster)
            pose(f"bow {i+1} rise", 2048, 2050, 2200, 2130, int(bow_speed * 1.5), int(bow_speed * 1.2), int(bow_speed * 1.3), int(bow_speed * 1.5)),
            led("all", 255, 235, 195, 105),
            hold(f"bow {i+1} rise hold", 0.2),
        ])

    # Phase 3: Grateful nod - small thankful nod (medium-slow, all 4 servos)
    steps.extend([
        pose("grateful nod down", 2048, 2180, 2100, 2130, 100, 75, 80, 100),
        hold("grateful hold", 0.15),
        pose("grateful nod up", 2048, 2080, 2200, 2130, 100, 75, 80, 100),
        hold("grateful up hold", 0.1),
    ])

    # Phase 4: Warm finish - gentle sway of contentment (slow, all 4 servos)
    steps.extend([
        pose("content sway left", 2100, 2100, 2150, 2200, 70, 50, 55, 70),
        hold("sway left hold", 0.2),
        pose("content sway right", 1990, 2100, 2150, 2060, 70, 50, 55, 70),
        hold("sway right hold", 0.2),
        pose("return neutral", 2048, 2150, 2048, 2130, 80, 55, 55, 80),
        led("all", 255, 225, 185, 105),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 25: Bow Thanks - grateful respectful bow, all 4 servos, slow dignified.")
    parser.add_argument("--bow-cycles", type=int, default=2, help="Number of bow cycles (default 2)")
    parser.add_argument("--bow-depth", choices=["shallow", "medium", "deep"], default="medium", help="Bow depth")
    parser.add_argument("--hold-seconds", type=float, default=0.6, help="Hold time at bottom of bow")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        bow_cycles=args.bow_cycles,
        bow_depth=args.bow_depth,
        hold_seconds=args.hold_seconds,
    ))


if __name__ == "__main__":
    main()
