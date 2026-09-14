#!/usr/bin/env python3
"""Scene 15: Stretch Yawn - 伸懒腰打哈欠.

Mira wakes up or takes a break, does a big stretch and yawn motion.
All 4 servos engaged: base rotates side-to-side during stretch, tilt leans back for yawn,
height reaches up tall, lateral tilt stretches outward.
Speed: very slow expansive stretch (60-100), with a quick yawn snap (150-200).

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


def build_steps(*, stretch_cycles: int, hold_seconds: float, yawn_pause: float) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Start from relaxed - slow dim warm-up (all 4 servos at neutral, slow speed)
    steps.extend([
        pose("start relaxed", 2048, 2150, 2048, 2130, 100, 70, 70, 90),
        led("all", 255, 200, 160, 60),
        hold("relaxed hold", 0.4),
        # Begin slow stretch - all 4 servos start to expand outward
        pose("begin stretch - expand outward", 2200, 2000, 2200, 1950, 80, 70, 80, 80),
        led("all", 255, 220, 180, 90),
        hold("stretch begin hold", 0.3),
    ])

    # Phase 2: Stretch cycles - slow big reach, yawn, release, side stretch
    for i in range(stretch_cycles):
        side = 1 if i % 2 == 0 else -1
        base_side = 2048 + int(200 * side)
        tilt_side = 2130 - int(180 * side)

        steps.extend([
            # Big stretch up - all 4 servos reach extreme (very slow)
            pose(f"stretch {i+1} reach high", base_side, 1850, 2400, tilt_side, 70, 60, 70, 70),
            hold(f"stretch {i+1} high hold", 0.25),
            # Yawn - head tilts back further, base holds, height maxes out
            pose(f"stretch {i+1} yawn - head back", base_side, 1800, 2500, tilt_side, 50, 40, 50, 50),
            led("all", 255, 230, 190, 100),
            hold(f"stretch {i+1} yawn hold", yawn_pause),
            # Quick yawn snap - fast close (servo 1+3 snap back)
            pose(f"stretch {i+1} yawn close", base_side, 2050, 2300, 2130, 180, 160, 140, 180),
            hold(f"stretch {i+1} close hold", 0.15),
            # Slow release down - all 4 servos ease back (very slow)
            pose(f"stretch {i+1} release down", 2048, 2100, 2050, 2100, 60, 50, 55, 60),
            hold(f"stretch {i+1} settle", 0.2),
            # Side stretch - opposite direction (slow, expansive)
            pose(f"stretch {i+1} side reach {'L' if side > 0 else 'R'}",
                 2048 - int(200 * side), 1950, 2200, 2130 + int(180 * side), 65, 55, 60, 65),
            hold(f"stretch {i+1} side hold", 0.2),
            # Return to center (slow)
            pose(f"stretch {i+1} return center", 2048, 2100, 2050, 2130, 60, 50, 50, 60),
        ])

    # Phase 3: Final big reach - all 4 servos to max stretch (slow, dramatic)
    steps.extend([
        pose("final big reach up", 2048, 1850, 2500, 1950, 80, 70, 80, 80),
        led("all", 255, 235, 195, 115),
        hold("final stretch hold", hold_seconds),
        # Slow relaxed return - all 4 servos ease to neutral
        pose("slow relaxed return", 2100, 2100, 2100, 2180, 70, 55, 60, 70),
        hold("return hold", 0.2),
        pose("return neutral", 2048, 2150, 2048, 2130, 80, 60, 60, 80),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 15: Stretch Yawn - big stretch with yawn, all 4 servos, slow speed.")
    parser.add_argument("--stretch-cycles", type=int, default=2, help="Number of stretch cycles (default 2)")
    parser.add_argument("--hold-seconds", type=float, default=0.8, help="Final stretch hold time")
    parser.add_argument("--yawn-pause", type=float, default=0.6, help="Yawn hold pause duration")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        stretch_cycles=args.stretch_cycles,
        hold_seconds=args.hold_seconds,
        yawn_pause=args.yawn_pause,
    ))


if __name__ == "__main__":
    main()
