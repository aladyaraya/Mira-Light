#!/usr/bin/env python3
"""Compatibility wrapper for the Mira Light spoken-answer demo timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CONSOLE_DIR = Path(__file__).resolve().parent
if str(CONSOLE_DIR) not in sys.path:
    sys.path.insert(0, str(CONSOLE_DIR))

from voice_motion_demos import (  # noqa: E402
    ANSWER_AUDIO_DELAY_SECONDS as AUDIO_DELAY_SECONDS,
    CLAMP_HI,
    CLAMP_LO,
    DEFAULT_SPEEDS,
    NEUTRAL,
    SERVO_CONTROL_PATH,
    clamp,
    demo_payload,
    normalized_timeline as _normalized_timeline,
    render_board_script as _render_board_script,
)

TIMELINE = _normalized_timeline("answer")


def normalized_timeline() -> list[tuple[float, list[int], str]]:
    return _normalized_timeline("answer")

def render_board_script(
    *,
    servo_control_path: str = SERVO_CONTROL_PATH,
    speeds: tuple[int, int, int, int] = DEFAULT_SPEEDS,
) -> str:
    del speeds
    return _render_board_script("answer", servo_control_path=servo_control_path)


def dry_run_payload() -> dict:
    payload = demo_payload("answer", include_script=False)
    payload["boardScript"] = render_board_script()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print generated board script and metadata")
    args = parser.parse_args()
    if args.dry_run:
        payload = dry_run_payload()
        print(json.dumps({k: v for k, v in payload.items() if k != "boardScript"}, indent=2, ensure_ascii=False))
        print("\n--- board script ---")
        print(payload["boardScript"])
        return 0
    print(render_board_script())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
