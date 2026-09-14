#!/usr/bin/env python3
"""Scene 13: Curious Peek - 好奇探头.

Mira notices something interesting and curiously peeks at it.
All 4 servos engaged: base rotates toward target, tilt leans in, height extends,
lateral tilt gives inquisitive head cocking.
Speed: quick darting movements (200-350) with pauses, like a curious animal.

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


def build_steps(*, peek_cycles: int, direction: str, pause_seconds: float) -> list[RemoteStep]:
    # Target direction for base rotation (servo 0)
    if direction == "left":
        base_target = 2350
        base_far = 2450
        base_back = 2250
        tilt_target = 2400
        tilt_far = 2500
        tilt_back = 2300
    elif direction == "right":
        base_target = 1750
        base_far = 1650
        base_back = 1850
        tilt_target = 1850
        tilt_far = 1750
        tilt_back = 1950
    else:  # center - alternate
        base_target = 2350
        base_far = 2450
        base_back = 2250
        tilt_target = 2400
        tilt_far = 2500
        tilt_back = 2300

    steps: list[RemoteStep] = [
        # Phase 1: Alert notice - quick snap to attention (fast speed)
        pose("alert - snap attention", 2048, 2100, 2100, 2130, 250, 180, 200, 250),
        led("all", 255, 230, 190, 110),
        hold("alert hold", 0.15),
        # Quick turn toward target (servo 0 + 3 fast)
        pose("quick turn to target", base_target, 2120, 2050, tilt_target, 280, 200, 220, 280),
        hold("target hold", 0.2),
    ]

    # Phase 2: Peek cycles - dart in, pull back, cock head (varied speeds)
    for i in range(peek_cycles):
        if direction == "center":
            mult = 1 if i % 2 == 0 else -1
            b_t = 2048 + int(300 * mult)
            b_f = 2048 + int(400 * mult)
            b_b = 2048 + int(200 * mult)
            t_t = 2130 + int(270 * mult)
            t_f = 2130 + int(370 * mult)
            t_b = 2130 + int(170 * mult)
        else:
            b_t, b_f, b_b = base_target, base_far, base_back
            t_t, t_f, t_b = tilt_target, tilt_far, tilt_back

        # Fast lean in (all 4 servos, high speed)
        steps.append(pose(f"peek {i+1} dart in", b_t, 2050, 2200, t_t, 320, 260, 300, 320))
        steps.append(hold(f"peek {i+1} close", 0.12))
        # Medium pull back (slower, cautious)
        steps.append(pose(f"peek {i+1} pull back", b_b, 2180, 1950, t_b, 180, 140, 160, 180))
        steps.append(hold(f"peek {i+1} back hold", pause_seconds))
        # Quick head cock - curious (servo 3 fast, others slow)
        steps.append(pose(f"peek {i+1} cock head", b_b, 2150, 2000, t_f, 100, 80, 90, 350))
        steps.append(hold(f"peek {i+1} cock hold", 0.15))
        # Return to peek ready
        steps.append(pose(f"peek {i+1} ready", b_t, 2120, 2050, t_t, 200, 150, 170, 200))
        steps.append(hold(f"peek {i+1} ready hold", 0.1))

    # Phase 3: Satisfied conclusion (medium speed)
    steps.extend([
        pose("satisfied - lean back", 2048, 2150, 2100, 2130, 150, 120, 130, 150),
        hold("satisfied hold", 0.2),
        # Happy nod
        RemoteStep("satisfied nod",
            f"python3 {DESKTOP}/servo_2_nod_1900_2200.py --cycles 1 --low 2000 --high 2120 --return-target 2080 --pre-target 2130 --speed 150 --pause 0.06"),
        pose("return neutral", 2048, 2150, 2048, 2130, 180, 130, 130, 180),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 13: Curious Peek - inquisitive investigation, all 4 servos, varied speed.")
    parser.add_argument("--peek-cycles", type=int, default=3, help="Number of peek cycles (default 3)")
    parser.add_argument("--direction", choices=["left", "right", "center"], default="left", help="Peek direction")
    parser.add_argument("--pause-seconds", type=float, default=0.25, help="Pause between peeks")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        peek_cycles=args.peek_cycles,
        direction=args.direction,
        pause_seconds=args.pause_seconds,
    ))


if __name__ == "__main__":
    main()
