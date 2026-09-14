#!/usr/bin/env python3
"""Scene 12: Sad Comfort - 难过安慰.

Mira senses sadness and does a gentle comforting motion.
All 4 servos engaged: base slowly turns toward user, head tilts down sympathetically,
height lowers, lateral tilt gives a compassionate lean.
Speed: very slow throughout (40-80), conveying gentleness.

Servo layout:
  0 = base rotation, center 2048, range 1700-2400
  1 = forward-back tilt, center 2150, range 1800-2400
  2 = vertical height, center 2048, range 1800-2900
  3 = lateral tilt, center 2130, range 1800-2500
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


def build_steps(*, comfort_cycles: int, linger_seconds: float) -> list[RemoteStep]:
    steps: list[RemoteStep] = [
        # Phase 1: Notice - slow turn toward user (servo 0 leads)
        pose("notice - slow turn toward user", 2200, 2150, 2048, 2130, 50, 40, 40, 50),
        led("all", 255, 200, 160, 60),
        hold("notice hold", 0.6),
        # Phase 2: Empathetic lean - all 4 servos move slowly
        pose("empathetic lean - lower and tilt", 2200, 2250, 1900, 2300, 45, 35, 40, 45),
        led("all", 255, 210, 170, 75),
        hold("lean hold", 0.5),
    ]

    # Phase 3: Comfort cycles - slow rocking motion using all 4 servos
    for i in range(comfort_cycles):
        left = i % 2 == 0
        base = 2280 if left else 2120
        tilt = 2350 if left else 2050
        steps.extend([
            # Slow gentle rock to one side (all 4 servos)
            pose(f"comfort {i+1} rock {'L' if left else 'R'}", base, 2220, 1880, tilt, 40, 30, 35, 40),
            hold(f"comfort {i+1} rock hold", 0.5),
            # Gentle sympathetic nod (servo 1+2)
            pose(f"comfort {i+1} gentle nod down", base, 2280, 1850, tilt, 35, 28, 30, 35),
            hold(f"comfort {i+1} nod hold", 0.35),
            # Return to center-ish
            pose(f"comfort {i+1} return", 2200, 2230, 1900, 2200, 40, 32, 35, 40),
            hold(f"comfort {i+1} pause", 0.3),
        ])

    # Phase 4: Slow recovery
    steps.extend([
        pose("slow recovery - rise gently", 2200, 2180, 2000, 2180, 50, 40, 45, 50),
        led("all", 255, 215, 175, 85),
        hold("recovery hold", linger_seconds),
        # Final gentle nod - "it will be ok"
        pose("final nod - reassurance", 2200, 2240, 1950, 2130, 45, 35, 38, 45),
        hold("final nod hold", 0.3),
        # Slow return to neutral
        pose("return neutral", 2048, 2150, 2048, 2130, 60, 45, 50, 60),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 12: Sad Comfort - gentle empathetic response, all 4 servos, slow speed.")
    parser.add_argument("--comfort-cycles", type=int, default=2, help="Number of comfort cycles (default 2)")
    parser.add_argument("--linger-seconds", type=float, default=0.8, help="Recovery hold time")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        comfort_cycles=args.comfort_cycles,
        linger_seconds=args.linger_seconds,
    ))


if __name__ == "__main__":
    main()
