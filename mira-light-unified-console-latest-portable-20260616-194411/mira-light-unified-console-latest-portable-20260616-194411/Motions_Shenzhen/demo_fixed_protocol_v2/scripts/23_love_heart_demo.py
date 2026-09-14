#!/usr/bin/env python3
"""Scene 23: Love Heart - 爱心表白.

Mira expresses love and affection, with gentle heart-shaped movements.
All 4 servos engaged: base sways in gentle arc, tilt leans toward user,
height pulses like a heartbeat, lateral tilt forms gentle waves.
Speed: slow gentle throughout (40-100), with soft heartbeat pulses (120-150).

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


def build_steps(*, heartbeats: int, linger_seconds: float) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Feel love - slow gentle turn toward user (all 4 servos, very slow)
    steps.extend([
        pose("feel love - gentle turn", 2200, 2150, 2050, 2200, 50, 40, 45, 50),
        led("all", 255, 180, 160, 90),
        hold("turn hold", 0.4),
        # Lean toward user - tilt forward gently (slow)
        pose("lean toward you", 2200, 2080, 2150, 2250, 45, 35, 40, 45),
        led("all", 255, 200, 170, 100),
        hold("lean hold", 0.3),
    ])

    # Phase 2: Heartbeat pulses - height pulses like a beating heart (all 4 servos)
    for i in range(heartbeats):
        side = 1 if i % 2 == 0 else -1
        base_sway = 2200 + int(50 * side)
        tilt_sway = 2250 + int(40 * side)

        steps.extend([
            # Heartbeat pulse 1 - quick up (medium-fast, all 4 servos)
            pose(f"heart {i+1} beat 1", base_sway, 2050, 2250, tilt_sway, 140, 110, 130, 140),
            hold(f"heart {i+1} beat 1 hold", 0.08),
            # Heartbeat pulse 2 - quick up again (double-beat)
            pose(f"heart {i+1} beat 2", base_sway, 2030, 2300, tilt_sway, 130, 100, 120, 130),
            hold(f"heart {i+1} beat 2 hold", 0.06),
            # Slow relax back down (very slow, gentle)
            pose(f"heart {i+1} relax", base_sway, 2100, 2100, 2200, 50, 40, 45, 50),
            hold(f"heart {i+1} relax hold", 0.2),
        ])

    # Phase 3: Gentle sway - loving arc motion (slow, all 4 servos)
    steps.extend([
        pose("love sway left", 2300, 2100, 2150, 2350, 60, 45, 50, 60),
        hold("sway left hold", 0.3),
        pose("love sway right", 2100, 2100, 2150, 2100, 55, 40, 45, 55),
        hold("sway right hold", 0.3),
        pose("love sway center", 2200, 2080, 2150, 2250, 50, 40, 45, 50),
        hold("center hold", 0.2),
    ])

    # Phase 4: Final loving pose - hold toward user (slow, warm)
    steps.extend([
        pose("final loving pose", 2200, 2080, 2200, 2250, 45, 35, 40, 45),
        led("all", 255, 210, 180, 110),
        hold("loving hold", linger_seconds),
        # Slow gentle return (very slow)
        pose("gentle return", 2100, 2120, 2100, 2180, 40, 30, 35, 40),
        hold("gentle hold", 0.2),
        pose("return neutral", 2048, 2150, 2048, 2130, 60, 45, 45, 60),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 23: Love Heart - gentle loving expression, all 4 servos, slow gentle.")
    parser.add_argument("--heartbeats", type=int, default=3, help="Number of heartbeat pulse cycles (default 3)")
    parser.add_argument("--linger-seconds", type=float, default=0.8, help="Final loving pose hold time")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        heartbeats=args.heartbeats,
        linger_seconds=args.linger_seconds,
    ))


if __name__ == "__main__":
    main()
