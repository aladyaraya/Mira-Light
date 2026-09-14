#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

from common import RemoteStep, build_parser, exit_from_plan


REPO_ROOT = Path(__file__).resolve().parents[3]
CONSOLE_DIR = REPO_ROOT / "mira-light-unified-director-console"
if str(CONSOLE_DIR) not in sys.path:
    sys.path.insert(0, str(CONSOLE_DIR))

import voice_motion_demos  # noqa: E402


def build_steps(demo_id: str, *, time_scale: float) -> list[RemoteStep]:
    demo = voice_motion_demos.get_demo(demo_id)
    return [
        RemoteStep(
            f"voice motion demo: {demo.title}",
            voice_motion_demos.render_board_script(demo, time_scale=time_scale),
        )
    ]


def main() -> None:
    parser = build_parser("Run a Mira Light voice-state motion demo through the standard scene queue.")
    parser.add_argument("demo", choices=sorted(voice_motion_demos.DEMOS))
    parser.add_argument("--time-scale", type=float, help="0.5 plays the timeline twice as fast. Defaults to 1.0 for answer, 0.5 otherwise.")
    args = parser.parse_args()
    time_scale = args.time_scale if args.time_scale is not None else (1.0 if args.demo == "answer" else 0.5)
    exit_from_plan(args=args, steps=build_steps(args.demo, time_scale=time_scale))


if __name__ == "__main__":
    main()
