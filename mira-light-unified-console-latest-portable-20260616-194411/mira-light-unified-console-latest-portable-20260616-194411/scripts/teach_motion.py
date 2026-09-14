#!/usr/bin/env python3
"""Clean and export Mira Light lead-through teaching trajectories.

This host-side tool works with JSON files produced by ``teach_motion_board.py``.
It intentionally avoids touching hardware; the board script handles UART,
torque, and playback safety. This script keeps the reviewable artifacts clean:

- normalize raw sampled frames
- remove duplicate / implausible frames
- lightly smooth positions
- export a fixed Shenzhen demo script that can be previewed before execution
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SERVO_IDS = ("0", "1", "2", "3")
SERVO_MIN = 0
SERVO_MAX = 4095
DEFAULT_SAMPLE_MS = 40
DEFAULT_MAX_STEP = 180
DEFAULT_SMOOTHING_ALPHA = 0.35
DEFAULT_EXPORT_SPEED = 260
DEFAULT_START_SPEED = 180


class TrajectoryError(ValueError):
    """Raised when a trajectory cannot be normalized safely."""


def load_trajectory(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TrajectoryError("trajectory root must be an object")
    return payload


def save_trajectory(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_positions(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise TrajectoryError("frame positions must be an object")
    result: dict[str, int] = {}
    for servo_id in SERVO_IDS:
        if servo_id not in raw:
            raise TrajectoryError(f"missing servo {servo_id}")
        value = int(raw[servo_id])
        if value < SERVO_MIN or value > SERVO_MAX:
            raise TrajectoryError(f"servo {servo_id} out of range: {value}")
        result[servo_id] = value
    return result


def normalize_frames(payload: dict[str, Any]) -> list[dict[str, Any]]:
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise TrajectoryError("trajectory must contain at least one frame")

    normalized: list[dict[str, Any]] = []
    previous_t = -1
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        try:
            positions = normalize_positions(frame.get("positions"))
        except (TypeError, ValueError, TrajectoryError):
            continue
        raw_t = frame.get("tMs", frame.get("t", index * DEFAULT_SAMPLE_MS))
        t_ms = int(round(float(raw_t)))
        if t_ms <= previous_t:
            t_ms = previous_t + 1
        previous_t = t_ms
        normalized.append({"tMs": t_ms, "positions": positions})

    if not normalized:
        raise TrajectoryError("trajectory does not contain any valid frames")
    first_t = normalized[0]["tMs"]
    for frame in normalized:
        frame["tMs"] = int(frame["tMs"] - first_t)
    return normalized


def frame_delta(a: dict[str, int], b: dict[str, int]) -> int:
    return max(abs(int(a[servo_id]) - int(b[servo_id])) for servo_id in SERVO_IDS)


def smooth_positions(previous: dict[str, int], current: dict[str, int], alpha: float) -> dict[str, int]:
    if alpha <= 0:
        return dict(current)
    if alpha >= 1:
        return dict(previous)
    return {
        servo_id: int(round(previous[servo_id] + (current[servo_id] - previous[servo_id]) * (1.0 - alpha)))
        for servo_id in SERVO_IDS
    }


def clean_trajectory(
    payload: dict[str, Any],
    *,
    min_interval_ms: int = DEFAULT_SAMPLE_MS,
    max_step: int = DEFAULT_MAX_STEP,
    smoothing_alpha: float = DEFAULT_SMOOTHING_ALPHA,
) -> dict[str, Any]:
    """Return a cleaned trajectory with conservative safety metadata."""

    raw_frames = normalize_frames(payload)
    kept: list[dict[str, Any]] = []
    rejected = {"duplicate": 0, "jump": 0, "interval": 0}

    for frame in raw_frames:
        positions = frame["positions"]
        if kept:
            previous = kept[-1]
            if positions == previous["positions"]:
                rejected["duplicate"] += 1
                continue
            if int(frame["tMs"]) - int(previous["tMs"]) < min_interval_ms:
                rejected["interval"] += 1
                continue
            if frame_delta(previous["positions"], positions) > max_step:
                rejected["jump"] += 1
                continue
            positions = smooth_positions(previous["positions"], positions, smoothing_alpha)
        kept.append({"tMs": int(frame["tMs"]), "positions": positions})

    if not kept:
        raise TrajectoryError("all frames were rejected")

    if kept[0]["tMs"] != 0:
        first_t = kept[0]["tMs"]
        for frame in kept:
            frame["tMs"] = int(frame["tMs"] - first_t)

    return {
        "version": 1,
        "source": payload.get("source", "mira-light-teach-motion"),
        "servos": list(SERVO_IDS),
        "frameCount": len(kept),
        "durationMs": kept[-1]["tMs"] if kept else 0,
        "safety": {
            "minPosition": SERVO_MIN,
            "maxPosition": SERVO_MAX,
            "minIntervalMs": int(min_interval_ms),
            "maxStep": int(max_step),
            "smoothingAlpha": float(smoothing_alpha),
            "rejected": rejected,
            "playbackDefaultSpeedScale": 0.5,
        },
        "frames": kept,
    }


def sanitize_identifier(raw: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip()).strip("_").lower()
    if not value:
        value = "taught_motion"
    if value[0].isdigit():
        value = f"motion_{value}"
    return value


def pose_command(positions: dict[str, int], *, speed: int, time_ms: int | None = None) -> str:
    p0, p1, p2, p3 = (int(positions[servo_id]) for servo_id in SERVO_IDS)
    command = (
        "python3 /home/sunrise/Desktop/four_servo_control.py "
        f"pose {p0} {p1} {p2} {p3} --speeds {speed} {speed} {speed} {speed}"
    )
    if time_ms is not None:
        command += f" --time {max(0, int(time_ms))}"
    return command


def export_fixed_script(
    trajectory: dict[str, Any],
    *,
    name: str,
    title: str | None = None,
    speed: int = DEFAULT_EXPORT_SPEED,
    start_speed: int = DEFAULT_START_SPEED,
) -> str:
    frames = normalize_frames(trajectory)
    safe_name = sanitize_identifier(name)
    display_title = title or safe_name.replace("_", " ")
    lines = [
        "#!/usr/bin/env python3",
        "",
        "from __future__ import annotations",
        "",
        "from common import RemoteStep, build_parser, exit_from_plan",
        "",
        "",
        f'TITLE = "{display_title}"',
        "",
        "",
        "def build_steps() -> list[RemoteStep]:",
        "    return [",
        "        RemoteStep(",
        '            "move gently to taught start pose",',
        f'            "{pose_command(frames[0]["positions"], speed=start_speed, time_ms=900)}",',
        "        ),",
        '        RemoteStep("settle before playback", "sleep 0.45"),',
    ]

    previous = frames[0]
    for index, frame in enumerate(frames[1:], start=1):
        delta_ms = max(20, int(frame["tMs"]) - int(previous["tMs"]))
        lines.extend(
            [
                "        RemoteStep(",
                f'            "taught frame {index:03d} at {int(frame["tMs"])} ms",',
                f'            "{pose_command(frame["positions"], speed=speed, time_ms=delta_ms)}",',
                "        ),",
            ]
        )
        previous = frame

    lines.extend(
        [
            "    ]",
            "",
            "",
            "def main() -> None:",
            f'    parser = build_parser("Taught motion playback: {display_title}.")',
            "    args = parser.parse_args()",
            "    exit_from_plan(args=args, steps=build_steps())",
            "",
            "",
            'if __name__ == "__main__":',
            "    main()",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean/export Mira Light taught motion trajectories.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    clean_parser = subparsers.add_parser("clean", help="Clean a raw trajectory JSON file")
    clean_parser.add_argument("input", type=Path)
    clean_parser.add_argument("output", type=Path)
    clean_parser.add_argument("--min-interval-ms", type=int, default=DEFAULT_SAMPLE_MS)
    clean_parser.add_argument("--max-step", type=int, default=DEFAULT_MAX_STEP)
    clean_parser.add_argument("--smoothing-alpha", type=float, default=DEFAULT_SMOOTHING_ALPHA)

    export_parser = subparsers.add_parser("export-script", help="Export a cleaned trajectory as a fixed demo script")
    export_parser.add_argument("input", type=Path)
    export_parser.add_argument("output", type=Path)
    export_parser.add_argument("--name", default="")
    export_parser.add_argument("--title", default="")
    export_parser.add_argument("--speed", type=int, default=DEFAULT_EXPORT_SPEED)
    export_parser.add_argument("--start-speed", type=int, default=DEFAULT_START_SPEED)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "clean":
        cleaned = clean_trajectory(
            load_trajectory(args.input),
            min_interval_ms=args.min_interval_ms,
            max_step=args.max_step,
            smoothing_alpha=args.smoothing_alpha,
        )
        save_trajectory(args.output, cleaned)
        print(f"wrote {args.output} ({cleaned['frameCount']} frames)")
        return 0

    if args.command == "export-script":
        payload = load_trajectory(args.input)
        script = export_fixed_script(
            payload,
            name=args.name or args.output.stem,
            title=args.title or None,
            speed=args.speed,
            start_speed=args.start_speed,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(script, encoding="utf-8")
        args.output.chmod(0o755)
        print(f"wrote {args.output}")
        return 0

    raise TrajectoryError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
