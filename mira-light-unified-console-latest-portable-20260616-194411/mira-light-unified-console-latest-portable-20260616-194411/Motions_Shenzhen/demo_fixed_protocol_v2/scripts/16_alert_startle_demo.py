#!/usr/bin/env python3
"""Scene 16: Alert Startle - 受惊吓.

Mira hears a sudden loud sound and gets startled, then slowly recovers.
All 4 servos engaged: base snaps to one side, tilt jerks back, height jumps up,
lateral tilt flinches. Then slow cautious recovery with all 4 servos.
Speed: very fast startle (400-550), then slow recovery (50-120).

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


def build_steps(*, recover_seconds: float, intensity: str) -> list[RemoteStep]:
    if intensity == "high":
        startle_offset = 380
        flash_brightness = 255
        recover_speed = 50
    elif intensity == "low":
        startle_offset = 220
        flash_brightness = 180
        recover_speed = 100
    else:  # medium
        startle_offset = 300
        flash_brightness = 220
        recover_speed = 70

    steps: list[RemoteStep] = []

    # Phase 1: Calm before startle - all 4 servos at neutral (medium speed)
    steps.extend([
        pose("calm before startle", 2048, 2150, 2048, 2130, 150, 100, 100, 130),
        led("all", 255, 220, 180, 100),
        hold("calm hold", 0.3),
    ])

    # Phase 2: STARTLE - all 4 servos jerk at maximum speed
    # Base snaps right, tilt jerks back, height jumps up, lateral tilt flinches
    steps.extend([
        pose("STARTLE - all 4 servos jerk",
             2048 - startle_offset, 2048 - startle_offset, 2048 + startle_offset, 2048 - startle_offset,
             550, 500, 520, 550),
        led("all", 255, 255, 255, flash_brightness),
        hold("startle hold", 0.15),
        # Quick shake - frightened tremor (fast, all 4 servos)
        pose("frightened tremor - snap left",
             2048 + startle_offset, 2048 - startle_offset, 2048 + startle_offset, 2048 + startle_offset,
             480, 450, 460, 480),
        hold("tremor hold", 0.08),
        pose("frightened tremor - snap right again",
             2048 - startle_offset, 2050, 2048 + int(startle_offset * 0.7), 2048 - int(startle_offset * 0.7),
             450, 400, 420, 450),
        led("all", 200, 200, 255, 80),
        hold("tremor 2 hold", 0.1),
    ])

    # Phase 3: Slow cautious recovery - all 4 servos ease down (very slow)
    steps.extend([
        pose("slow recovery - ease down", 2048, 2100, 2100, 2080, recover_speed, 55, 60, recover_speed),
        hold("cautious hold", 0.4),
        # Small nervous tremor (medium speed)
        pose("nervous tremor", 2080, 2120, 2080, 2200, 120, 90, 90, 120),
        hold("tremor hold", 0.15),
        pose("nervous settle", 2060, 2130, 2090, 2100, 80, 60, 60, 80),
        hold("settle hold", 0.2),
    ])

    # Phase 4: Cautious look around - servo 0 + 3 explore (slow, wary)
    steps.extend([
        pose("cautious look left", 2250, 2120, 2050, 2300, 90, 65, 65, 90),
        hold("look left hold", 0.3),
        pose("cautious look right", 1850, 2120, 2050, 1950, 90, 65, 65, 90),
        hold("look right hold", 0.3),
        pose("cautious look up - check around", 2048, 2050, 2200, 2130, 80, 60, 70, 80),
        hold("look up hold", 0.25),
    ])

    # Phase 5: Gradual calm down - all 4 servos return to neutral (slow)
    steps.extend([
        pose("gradual calm - center", 2048, 2140, 2050, 2130, 70, 50, 55, 70),
        led("all", 255, 215, 175, 90),
        hold("recovery hold", recover_seconds),
        # Final relief - gentle nod (medium-slow)
        pose("relief nod", 2048, 2200, 2000, 2130, 100, 70, 70, 100),
        hold("relief hold", 0.2),
        pose("return neutral", 2048, 2150, 2048, 2130, 90, 60, 60, 90),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 16: Alert Startle - startled response with recovery, all 4 servos.")
    parser.add_argument("--recover-seconds", type=float, default=1.0, help="Recovery hold time")
    parser.add_argument("--intensity", choices=["low", "medium", "high"], default="medium", help="Startle intensity")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        recover_seconds=args.recover_seconds,
        intensity=args.intensity,
    ))


if __name__ == "__main__":
    main()
