#!/usr/bin/env python3
"""Scene 17: Greeting Wave - 打招呼挥手.

Mira greets someone, turning toward them and waving hello with a friendly motion.
All 4 servos engaged: base rotates toward visitor, tilt nods hello, height rises cheerfully,
lateral tilt waves side to side.
Speed: cheerful medium speed (150-250), with quick wave swings (250-300).

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


def build_steps(*, wave_cycles: int, direction: str, hold_seconds: float) -> list[RemoteStep]:
    # Direction determines which way to turn and wave
    if direction == "left":
        base_face = 2250   # turn left to face visitor
        wave_side = 2400   # servo 3 waves to the left
        wave_back = 1950   # servo 3 returns
    elif direction == "right":
        base_face = 1850
        wave_side = 1850
        wave_back = 2350
    else:  # center
        base_face = 2048
        wave_side = 2400
        wave_back = 1950

    steps: list[RemoteStep] = []

    # Phase 1: Notice visitor - perk up, all 4 servos (medium speed)
    steps.extend([
        pose("notice visitor - perk up", base_face, 2100, 2100, 2100, 200, 150, 160, 180),
        led("all", 255, 225, 185, 110),
        hold("perk hold", 0.2),
        # Raise hand to wave - all 4 servos move into wave ready pose
        pose("raise to wave", base_face, 1950, 2250, wave_side, 180, 140, 160, 200),
        hold("wave ready hold", 0.15),
    ])

    # Phase 2: Wave cycles - servo 3 swings side to side, all others subtly follow
    for i in range(wave_cycles):
        swing_out = wave_side if i % 2 == 0 else wave_back
        swing_back = wave_back if i % 2 == 0 else wave_side
        # Subtle base sway during wave (servo 0 moves slightly)
        base_sway = base_face + (30 if i % 2 == 0 else -30)
        # Height bobs cheerfully (servo 2)
        height_bob = 2250 if i % 2 == 0 else 2150

        steps.extend([
            # Fast swing out (all 4 servos, quick cheerful)
            pose(f"wave {i+1} swing out", base_sway, 1950, height_bob, swing_out, 280, 200, 220, 300),
            hold(f"wave {i+1} out hold", 0.1),
            # Fast swing back
            pose(f"wave {i+1} swing back", base_face - (30 if i % 2 == 0 else -30), 1980, 2200, swing_back, 260, 190, 210, 280),
            hold(f"wave {i+1} back hold", 0.08),
        ])

    # Phase 3: Finish wave - cheerful nod hello (medium speed)
    steps.extend([
        # Bring hand down while nodding - all 4 servos
        pose("finish wave - nod hello", base_face, 2050, 2100, 2200, 200, 150, 160, 180),
        hold("nod hold", 0.15),
        pose("nod down", base_face, 2200, 2000, 2130, 180, 130, 140, 160),
        hold("nod down hold", 0.12),
        pose("nod up", base_face, 2080, 2150, 2130, 180, 130, 140, 160),
        led("all", 255, 230, 190, 115),
        hold("greeting pose", hold_seconds),
    ])

    # Phase 4: Happy sway - all 4 servos sway side to side (medium-slow)
    steps.extend([
        pose("happy sway left", 2150, 2140, 2100, 2250, 150, 110, 120, 150),
        hold("sway left hold", 0.2),
        pose("happy sway right", 1950, 2140, 2100, 2000, 150, 110, 120, 150),
        hold("sway right hold", 0.2),
        pose("happy sway center", 2048, 2150, 2050, 2130, 130, 100, 100, 130),
        hold("center hold", 0.15),
        # Final return to neutral (slow, warm)
        pose("return neutral", 2048, 2150, 2048, 2130, 100, 70, 70, 100),
        led("all", 255, 220, 180, 100),
    ])
    return steps


def main() -> None:
    parser = build_parser("Scene 17: Greeting Wave - friendly hello wave, all 4 servos, medium speed.")
    parser.add_argument("--wave-cycles", type=int, default=3, help="Number of wave cycles (default 3)")
    parser.add_argument("--direction", choices=["left", "right", "center"], default="left", help="Wave direction")
    parser.add_argument("--hold-seconds", type=float, default=0.5, help="Greeting hold time")
    args = parser.parse_args()
    exit_from_plan(args=args, steps=build_steps(
        wave_cycles=args.wave_cycles,
        direction=args.direction,
        hold_seconds=args.hold_seconds,
    ))


if __name__ == "__main__":
    main()
