#!/usr/bin/env python3
"""Scene 24: Confused Lost - 困惑迷茫.

Mira doesn't understand something and looks around in confusion.
All 4 servos engaged: base searches left and right uncertainly, tilt nods in puzzlement,
height shifts up and down, lateral tilt cocks head at odd angles.
Speed: medium uncertain (100-180) with hesitant pauses, then slow realization (60-90).

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


def build_steps(*, confused_cycles: int, resolve: bool) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Hear confusing thing - puzzled reaction (medium, all 4 servos)
    steps.extend([
        pose("huh? - puzzled reaction", 2048, 2100, 2100, 1950, 150, 110, 120, 150),
        led("all", 255, 200, 180, 80),
        hold("puzzled hold", 0.25),
        # Cock head - confused (medium, servo 3 tilts sharply)
        pose("cock head - confused", 2048, 2120, 2050, 2400, 130, 100, 110, 160),
        hold("cock hold", 0.3),
    ])

    # Phase 2: Confused search cycles - look around uncertainly (all 4 servos)
    for i in range(confused_cycles):
        side = 1 if i % 2 == 0 else -1
        base_search = 2048 + int(280 * side)
        tilt_search = 2130 + int(220 * side)

        steps.extend([
            # Look to one side - searching for answer (medium, uncertain)
            pose(f"confused {i+1} look {'left' if side > 0 else 'right'}", base_search, 2080, 2150, tilt_search, 140, 100, 120, 140),
            hold(f"confused {i+1} look hold", 0.2),
            # Hesitate - pull back slightly (medium-slow)
            pose(f"confused {i+1} hesitate", 2048 + int(100 * side), 2150, 2050, 2130 + int(80 * side), 100, 75, 85, 100),
            hold(f"confused {i+1} hesitate hold", 0.15),
            # Look the other way - still confused (medium)
            pose(f"confused {i+1} look other way", 2048 - int(250 * side), 2100, 2100, 2130 - int(200 * side), 130, 95, 110, 130),
            hold(f"confused {i+1} other hold", 0.2),
            # Shrug - all 4 servos (medium-slow)
            pose(f"confused {i+1} shrug", 2048, 2000, 2200, 1950, 110, 80, 90, 110),
            hold(f"confused {i+1} shrug hold", 0.15),
            pose(f"confused {i+1} shrug down", 2048, 2200, 1950, 2300, 100, 75, 85, 100),
            hold(f"confused {i+1} shrug down hold", 0.1),
        ])

    # Phase 3: Resolution or still confused
    if resolve:
        # Slow realization - "oh I see" (slow, all 4 servos)
        steps.extend([
            pose("oh! - slow realization", 2048, 2080, 2200, 2100, 80, 60, 70, 80),
            led("all", 255, 220, 190, 100),
            hold("realization hold", 0.3),
            # Understanding nod (medium-slow)
            pose("understanding nod", 2048, 2200, 2000, 2130, 100, 75, 85, 100),
            hold("nod hold", 0.15),
            pose("nod up - got it", 2048, 2050, 2200, 2130, 90, 70, 80, 90),
            led("all", 255, 230, 195, 110),
            hold("got it hold", 0.2),
        ])
    else:
        # Still confused - give up shrug (slow, all 4 servos)
        steps.extend([
            pose("still confused - big shrug", 2048, 1950, 2250, 1900, 90, 65, 75, 90),
            hold("big shrug hold", 0.2),
            pose("still confused - drop", 2048, 2250, 1900, 2350, 80, 60, 70, 80),
            led("all", 255, 195, 165, 75),
            hold("drop hold", 0.25),
        ])

    # Phase 4: Return to neutral (slow)
    steps.extend([
        pose("return neutral", 2048, 2150, 2048, 2130, 80, 55, 55, 80),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 24: Confused Lost - uncertain confused search, all 4 servos, medium.")
    parser.add_argument("--confused-cycles", type=int, default=2, help="Number of confused search cycles (default 2)")
    parser.add_argument("--resolve", action="store_true", default=True, help="End with realization (default True)")
    parser.add_argument("--no-resolve", dest="resolve", action="store_false", help="End still confused")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        confused_cycles=args.confused_cycles,
        resolve=args.resolve,
    ))


if __name__ == "__main__":
    main()
