#!/usr/bin/env python3

from __future__ import annotations

from common import RemoteStep, build_parser, exit_from_plan


WAKE_SPEED_SCALE = 2
WAKE_TIME_SCALE = 0.5


def _speeds(*values: int) -> str:
    return " ".join(str(max(1, int(value) * WAKE_SPEED_SCALE)) for value in values)


def _sleep(seconds: float) -> str:
    return f"sleep {max(0.0, seconds * WAKE_TIME_SCALE):.2f}"


def build_steps(
    *,
    light_mode: str,
    hold_high_seconds: float,
    skip_start_sleep: bool,
    final_look: str,
) -> list[RemoteStep]:
    if light_mode == "warm":
        light_cmd = "python3 /home/sunrise/Desktop/send_uart3_led_cmd.py all 255 220 180 70"
    else:
        light_cmd = "python3 /home/sunrise/Desktop/send_uart3_led_cmd.py wake 255 220 180 150"

    if final_look == "center":
        final_look_cmd = f"python3 /home/sunrise/Desktop/four_servo_control.py pose 2048 2150 2048 2130 --speeds {_speeds(160, 90, 90, 160)}"
        final_look_label = "look forward"
        final_hold_label = "hold forward attention"
    else:
        # Board convention from the earlier tuned script: this is the judge-facing side glance.
        final_look_cmd = f"python3 /home/sunrise/Desktop/four_servo_control.py pose 2365 2150 2048 2686 --speeds {_speeds(180, 150, 150, 180)}"
        final_look_label = "look to judge side"
        final_hold_label = "hold judge-side attention"

    steps: list[RemoteStep] = []
    if not skip_start_sleep:
        steps.extend(
            [
                RemoteStep("start dark", "python3 /home/sunrise/Desktop/send_uart3_led_cmd.py off"),
                RemoteStep(
                    "fold to sleep start pose",
                    f"python3 /home/sunrise/Desktop/four_servo_control.py pose 2048 1821 2912 2130 --speeds {_speeds(2000, 320, 1240, 2000)}",
                ),
                RemoteStep("hold still before waking", _sleep(0.8)),
            ]
        )

    steps.extend(
        [
            RemoteStep("tiny warm pre-glow", "python3 /home/sunrise/Desktop/send_uart3_led_cmd.py all 255 180 120 25"),
            RemoteStep("pause before eye-open effect", _sleep(0.35)),
            RemoteStep("wake light", light_cmd),
            RemoteStep("pause for eye-open effect", _sleep(0.6)),
            RemoteStep(
                "half-awake lift",
                f"python3 /home/sunrise/Desktop/four_servo_control.py pose 2048 1900 2750 2130 --speeds {_speeds(220, 90, 180, 180)}",
            ),
            RemoteStep("half-awake pause", _sleep(0.5)),
            RemoteStep(
                "stretch to high point",
                f"python3 /home/sunrise/Desktop/four_servo_pose_delay_2.py --targets 2048 2400 1700 2130 --speeds {_speeds(1000, 160, 380, 1000)} --delay-ratio 0.25",
            ),
            RemoteStep("hold high point", _sleep(hold_high_seconds)),
            RemoteStep(
                "long stretch accent",
                f"python3 /home/sunrise/Desktop/four_servo_pose_2048_2048_2048_2780_separate.py --speed {250 * WAKE_SPEED_SCALE} --delay 0.05",
            ),
            RemoteStep(
                "settle forward",
                f"python3 /home/sunrise/Desktop/four_servo_control.py pose 2048 2150 2048 2130 --speeds {_speeds(180, 100, 100, 180)}",
            ),
            RemoteStep("pause before shiver", _sleep(0.25)),
            RemoteStep(
                "small wake shiver - vertical",
                f"python3 /home/sunrise/Desktop/servo_2_nod_1900_2200.py --cycles 1 --low 1872 --high 2232 --return-target 2048 --pre-target 2130 --speed {210 * WAKE_SPEED_SCALE} --pause 0.03",
            ),
            RemoteStep(
                "small wake shiver - side",
                f"python3 /home/sunrise/Desktop/servo_3_shake_2100_2000.py --cycles 1 --left 2290 --right 1970 --return-target 2130 --speed {270 * WAKE_SPEED_SCALE} --pause 0.03",
            ),
            RemoteStep(final_look_label, final_look_cmd),
            RemoteStep(final_hold_label, _sleep(0.7)),
            RemoteStep("natural warm light", "python3 /home/sunrise/Desktop/send_uart3_led_cmd.py all 255 220 180 100"),
        ]
    )
    return steps


def main() -> None:
    parser = build_parser("Demo scene 01 v2: video-faithful presence wake.")
    parser.add_argument("--light-mode", choices=("wake", "warm"), default="wake")
    parser.add_argument("--hold-high-seconds", type=float, default=1.2)
    parser.add_argument("--skip-start-sleep", action="store_true", help="Skip the initial fold-to-sleep preparation.")
    parser.add_argument("--final-look", choices=("judge-left", "center"), default="judge-left")
    args = parser.parse_args()
    exit_from_plan(
        args=args,
        steps=build_steps(
            light_mode=args.light_mode,
            hold_high_seconds=args.hold_high_seconds,
            skip_start_sleep=args.skip_start_sleep,
            final_look=args.final_look,
        ),
    )


if __name__ == "__main__":
    main()
