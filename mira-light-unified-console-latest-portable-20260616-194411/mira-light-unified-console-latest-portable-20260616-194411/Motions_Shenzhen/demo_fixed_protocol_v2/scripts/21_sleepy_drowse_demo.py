#!/usr/bin/env python3
"""Scene 21: Sleepy Drowse - 困倦打盹.

Mira is getting sleepy, head droops slowly, fights to stay awake, then nods off.
All 4 servos engaged: base sways with drowsiness, tilt nods down, height sinks,
lateral tilt tilts with exhaustion.
Speed: very slow drooping (30-60), with sudden micro-alerts (150-200) fighting sleep.

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


def build_steps(*, drowse_cycles: int, final_sleep: bool) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: First drowsiness - slow sag, all 4 servos droop (very slow)
    steps.extend([
        pose("first drowsy - slow sag", 2048, 2180, 2000, 2180, 50, 35, 40, 50),
        led("all", 255, 200, 160, 70),
        hold("drowsy hold", 0.5),
        # Head droops down - tilt and height sink (very slow)
        pose("head droops", 2080, 2250, 1900, 2200, 40, 30, 35, 40),
        led("all", 255, 180, 140, 55),
        hold("droop hold", 0.6),
    ])

    # Phase 2: Fight sleep cycles - jerk awake then droop again
    for i in range(drowse_cycles):
        side = 1 if i % 2 == 0 else -1
        base_sway = 2048 + int(120 * side)
        tilt_sway = 2130 + int(100 * side)

        steps.extend([
            # Sudden jerk awake - micro alert (fast, all 4 servos)
            pose(f"drowse {i+1} jerk awake", base_sway, 2050, 2200, tilt_sway, 180, 140, 160, 180),
            led("all", 255, 220, 180, 90),
            hold(f"drowse {i+1} awake hold", 0.2),
            # Slow losing battle - head sways (very slow)
            pose(f"drowse {i+1} losing battle", 2048 + int(180 * side), 2150, 2050, 2130 + int(150 * side), 45, 32, 38, 45),
            hold(f"drowse {i+1} sway hold", 0.4),
            # Head drops again - fighting sleep (very slow)
            pose(f"drowse {i+1} drop again", 2048 + int(80 * side), 2280, 1850, 2200 + int(60 * side), 35, 25, 30, 35),
            led("all", 255, 170, 130, 45),
            hold(f"drowse {i+1} drop hold", 0.5),
        ])

    # Phase 3: Final nod off or recover
    if final_sleep:
        # Fall asleep - all 4 servos slowly fold into sleep pose (very slow)
        steps.extend([
            pose("final nod off - sinking", 2048, 2300, 1800, 2200, 30, 20, 25, 30),
            led("all", 255, 150, 110, 30),
            hold("nod off hold", 0.6),
            pose("deep sleep fold", 2048, 2400, 1800, 2250, 25, 15, 20, 25),
            led("all", 255, 120, 80, 15),
            hold("deep sleep", 1.0),
        ])
    else:
        # Recover - shake it off (medium speed, all 4 servos)
        steps.extend([
            pose("recover - shake off sleep", 2048, 2050, 2200, 2000, 150, 120, 130, 150),
            led("all", 255, 230, 190, 100),
            hold("recover hold", 0.2),
            pose("recover - stretch up", 2048, 1950, 2300, 1950, 120, 90, 100, 120),
            hold("stretch hold", 0.15),
            pose("return neutral", 2048, 2150, 2048, 2130, 80, 55, 55, 80),
            led("all", 255, 220, 180, 100),
        ])
    return steps


def main() -> None:
    parser = build_parser("Scene 21: Sleepy Drowse - fighting sleep, all 4 servos, very slow.")
    parser.add_argument("--drowse-cycles", type=int, default=3, help="Number of drowse cycles (default 3)")
    parser.add_argument("--final-sleep", action="store_true", default=True, help="End with falling asleep (default True)")
    parser.add_argument("--no-sleep", dest="final_sleep", action="store_false", help="End with recovery instead of sleep")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        drowse_cycles=args.drowse_cycles,
        final_sleep=args.final_sleep,
    ))


if __name__ == "__main__":
    main()
