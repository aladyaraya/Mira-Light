#!/usr/bin/env python3
"""Scene 18: Thinking Ponder - 思考发呆.

Mira is asked a question and goes into deep thinking mode.
All 4 servos engaged: base slowly looks around searching for answers, tilt nods while thinking,
height shifts contemplatively, lateral tilt cocks head in curiosity.
Speed: very slow contemplative (30-70), with sudden eureka burst (250-350).

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


def build_steps(*, think_cycles: int, ponder_seconds: float, eureka: bool) -> list[RemoteStep]:
    steps: list[RemoteStep] = []

    # Phase 1: Receive question - attention shift, all 4 servos (slow-medium)
    steps.extend([
        pose("receive question - attention", 2048, 2130, 2030, 2110, 120, 80, 80, 100),
        led("all", 255, 195, 155, 70),
        hold("attention hold", 0.3),
        # Look up - begin thinking, all 4 servos shift (slow)
        pose("look up - begin thinking", 2048, 2050, 2200, 2100, 60, 45, 55, 60),
        hold("think pose hold", 0.4),
    ])

    # Phase 2: Thinking cycles - slow contemplative exploration with all 4 servos
    for i in range(think_cycles):
        side = 1 if i % 2 == 0 else -1
        base_look = 2048 + int(250 * side)
        tilt_look = 2130 + int(200 * side)
        base_away = 2048 - int(200 * side)
        tilt_away = 2130 - int(180 * side)

        steps.extend([
            # Slow contemplative look to one side (all 4 servos, very slow)
            pose(f"think {i+1} look {'left' if side > 0 else 'right'}", base_look, 2070, 2100, tilt_look, 45, 35, 40, 45),
            hold(f"think {i+1} look hold", ponder_seconds),
            # Slow considering nod (servo 1+2 move, others hold)
            pose(f"think {i+1} considering nod", base_look, 2150, 2000, tilt_look, 35, 28, 30, 35),
            hold(f"think {i+1} nod hold", 0.2),
            pose(f"think {i+1} nod return", base_look, 2080, 2100, tilt_look, 35, 28, 30, 35),
            hold(f"think {i+1} pause", 0.25),
            # Look away - deep in thought, opposite direction (very slow)
            pose(f"think {i+1} look away", base_away, 2100, 2050, tilt_away, 40, 30, 35, 40),
            hold(f"think {i+1} away hold", 0.35),
            # Head cock - curious thought (servo 3 tilts, slow)
            pose(f"think {i+1} head cock", base_away, 2080, 2080, 2130 + int(250 * side), 35, 28, 30, 50),
            hold(f"think {i+1} cock hold", 0.3),
        ])

    # Phase 3: Eureka or still thinking
    if eureka:
        # EUREKA - sudden realization, all 4 servos perk up fast
        steps.extend([
            pose("EUREKA - sudden perk up", 2048, 1900, 2400, 1950, 350, 280, 320, 350),
            led("all", 255, 240, 200, 130),
            hold("eureka hold", 0.2),
            # Excited quick look around - all 4 servos (fast)
            pose("eureka look left", 2300, 1950, 2350, 2200, 300, 240, 260, 300),
            hold("eureka left hold", 0.1),
            pose("eureka look right", 1800, 1950, 2350, 2000, 300, 240, 260, 300),
            hold("eureka right hold", 0.1),
            # Happy excited nod (medium-fast)
            pose("eureka excited nod", 2048, 2100, 2200, 2130, 250, 200, 220, 250),
            hold("eureka nod hold", 0.15),
            pose("eureka nod down", 2048, 2200, 2050, 2130, 220, 180, 200, 220),
            hold("eureka down hold", 0.1),
            pose("eureka nod up", 2048, 2000, 2300, 2130, 250, 200, 220, 250),
            hold("eureka up hold", 0.2),
        ])
    else:
        # Still thinking - no answer yet, slow uncertain (all 4 servos)
        steps.extend([
            pose("still thinking - uncertain", 2048, 2100, 2050, 2200, 50, 40, 40, 50),
            led("all", 255, 205, 165, 80),
            hold("uncertain hold", 0.4),
            # Slow shrug - all 4 servos (very slow)
            pose("uncertain shrug", 2048, 2000, 2150, 1950, 45, 35, 40, 45),
            hold("shrug hold", 0.3),
            pose("shrug return", 2048, 2100, 2050, 2130, 50, 40, 40, 50),
            hold("shrug return hold", 0.2),
        ])

    # Phase 4: Settle from thinking - all 4 servos return to neutral (slow)
    steps.extend([
        pose("settle - ease back", 2048, 2120, 2080, 2150, 60, 45, 50, 60),
        hold("settle hold", 0.2),
        pose("return neutral", 2048, 2150, 2048, 2130, 80, 55, 55, 80),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 18: Thinking Ponder - contemplative thinking, all 4 servos, slow speed.")
    parser.add_argument("--think-cycles", type=int, default=3, help="Number of thinking cycles (default 3)")
    parser.add_argument("--ponder-seconds", type=float, default=0.5, help="Hold time per ponder")
    parser.add_argument("--eureka", action="store_true", default=True, help="Include eureka moment (default True)")
    parser.add_argument("--no-eureka", dest="eureka", action="store_false", help="No eureka moment")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        think_cycles=args.think_cycles,
        ponder_seconds=args.ponder_seconds,
        eureka=args.eureka,
    ))


if __name__ == "__main__":
    main()
