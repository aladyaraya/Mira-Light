#!/usr/bin/env python3
"""Scene 26: Excited Bounce - 兴奋激动.

Mira is super excited about something, bouncing energetically with flashing lights.
All 4 servos engaged: base rapidly oscillates, tilt bobs fast, height bounces high,
lateral tilt swings wildly.
Speed: very fast energetic bursts (350-500) with brief pauses, building intensity.

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


def build_steps(*, bounce_cycles: int, peak_seconds: float) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Build excitement - medium speed escalation (all 4 servos)
    steps.extend([
        pose("ooh! - notice exciting thing", 2048, 2100, 2100, 2200, 200, 160, 180, 200),
        led("all", 255, 240, 200, 100),
        hold("notice hold", 0.1),
        # Quick perk up - getting excited (medium-fast)
        pose("perk up - getting excited", 2048, 2000, 2250, 2000, 280, 220, 250, 280),
        led("all", 255, 245, 210, 120),
        hold("perk hold", 0.08),
    ])

    # Phase 2: Excited bounce cycles - escalating energy (all 4 servos, very fast)
    for i in range(bounce_cycles):
        side = 1 if i % 2 == 0 else -1
        # Escalate speed and range with each cycle
        speed = 350 + i * 30
        base_range = 300 + i * 30
        tilt_range = 250 + i * 25
        height_range = 300 + i * 30

        steps.extend([
            # Fast bounce up + side (all 4 servos, very fast)
            pose(f"excited {i+1} bounce up",
                 2048 + int(base_range * side), 1950, 2048 + height_range, 2130 + int(tilt_range * side),
                 speed, int(speed * 0.85), int(speed * 0.9), speed),
            hold(f"excited {i+1} up hold", 0.04),
            # Fast bounce down + opposite (all 4 servos)
            pose(f"excited {i+1} bounce down",
                 2048 - int(base_range * side), 2250, 2048 - int(height_range * 0.7), 2130 - int(tilt_range * side),
                 int(speed * 0.95), int(speed * 0.8), int(speed * 0.85), int(speed * 0.95)),
            hold(f"excited {i+1} down hold", 0.03),
            # Quick center pop (all 4 servos, fastest)
            pose(f"excited {i+1} pop",
                 2048, 2000, 2300, 2130, speed + 50, int(speed * 0.9), speed + 30, speed + 50),
            hold(f"excited {i+1} pop hold", 0.03),
        ])

    # Phase 3: Peak excitement - maximum energy burst (all 4 servos, max speed)
    steps.extend([
        led("spin", "--rainbow", 0, 1, 100),
        pose("PEAK - max excitement burst", 2300, 1900, 2500, 2400, 500, 450, 480, 500),
        hold("peak hold", 0.05),
        pose("PEAK - opposite burst", 1800, 1900, 2500, 1850, 500, 450, 480, 500),
        hold("peak 2 hold", 0.05),
        pose("PEAK - center high", 2048, 1850, 2600, 2130, 480, 430, 460, 480),
        led("all", 255, 255, 230, 150),
        hold("peak center hold", peak_seconds),
    ])

    # Phase 4: Wind down - gradual deceleration (medium → slow, all 4 servos)
    steps.extend([
        pose("wind down 1 - still buzzing", 2100, 2000, 2300, 2200, 250, 200, 220, 250),
        hold("wind 1 hold", 0.1),
        pose("wind down 2 - slowing", 2080, 2100, 2150, 2180, 180, 140, 160, 180),
        led("all", 255, 240, 205, 120),
        hold("wind 2 hold", 0.12),
        pose("wind down 3 - almost calm", 2050, 2130, 2080, 2150, 120, 90, 100, 120),
        hold("wind 3 hold", 0.15),
        pose("return neutral", 2048, 2150, 2048, 2130, 90, 60, 60, 90),
        led("all", 255, 225, 185, 105),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 26: Excited Bounce - energetic excitement, all 4 servos, very fast.")
    parser.add_argument("--bounce-cycles", type=int, default=3, help="Number of escalating bounce cycles (default 3)")
    parser.add_argument("--peak-seconds", type=float, default=0.3, help="Peak excitement hold time")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        bounce_cycles=args.bounce_cycles,
        peak_seconds=args.peak_seconds,
    ))


if __name__ == "__main__":
    main()
