#!/usr/bin/env python3
import os
import signal
import subprocess
import time
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline

DEFAULT_INTERVAL_SECONDS = 5.0
DEFAULT_BINARY_NAME = "expression_monitor"
DEFAULT_PID_FILENAME = "expression-monitor.pid"
DEFAULT_STDOUT_LOG = "expression-monitor.stdout.log"
DEFAULT_STDERR_LOG = "expression-monitor.stderr.log"
DEFAULT_OUTPUT_RELATIVE_PATH = Path("expression-monitor") / "latest.json"
DEFAULT_HISTORY_RELATIVE_PATH = Path("expression-monitor") / "history.jsonl"
DEFAULT_FRAME_RELATIVE_PATH = Path("expression-monitor") / "latest.jpg"


def binary_path(root: Path = ROOT) -> Path:
    return root / DEFAULT_BINARY_NAME


def pid_path(state_dir: Path) -> Path:
    return state_dir / DEFAULT_PID_FILENAME


def latest_output_path(state_dir: Path) -> Path:
    return state_dir / DEFAULT_OUTPUT_RELATIVE_PATH


def history_output_path(state_dir: Path) -> Path:
    return state_dir / DEFAULT_HISTORY_RELATIVE_PATH


def latest_frame_path(state_dir: Path) -> Path:
    return state_dir / DEFAULT_FRAME_RELATIVE_PATH


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_running_pid(state_dir: Path) -> int | None:
    path = pid_path(state_dir)
    if not path.is_file():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        path.unlink(missing_ok=True)
        return None
    if not _pid_is_running(pid):
        path.unlink(missing_ok=True)
        return None
    return pid


def start_expression_monitor(
    state_dir: Path,
    *,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    root: Path = ROOT,
) -> dict[str, object]:
    existing_pid = read_running_pid(state_dir)
    if existing_pid is not None:
        return {"pid": existing_pid, "already_running": True}

    target_binary = binary_path(root)
    if not target_binary.is_file():
        raise FileNotFoundError(f"missing expression monitor binary: {target_binary}")

    state_dir.mkdir(parents=True, exist_ok=True)
    latest_output_path(state_dir).parent.mkdir(parents=True, exist_ok=True)
    latest_output_path(state_dir).unlink(missing_ok=True)
    latest_frame_path(state_dir).unlink(missing_ok=True)
    stdout_handle = open(state_dir / DEFAULT_STDOUT_LOG, "ab")
    stderr_handle = open(state_dir / DEFAULT_STDERR_LOG, "ab")
    process = subprocess.Popen(
        [
            str(target_binary),
            "--interval-seconds",
            str(interval_seconds),
            "--output-path",
            str(latest_output_path(state_dir)),
            "--history-path",
            str(history_output_path(state_dir)),
            "--frame-output-path",
            str(latest_frame_path(state_dir)),
            "--quiet",
        ],
        cwd=str(root),
        stdout=stdout_handle,
        stderr=stderr_handle,
        start_new_session=True,
    )
    pid_path(state_dir).write_text(str(process.pid), encoding="utf-8")
    return {"pid": process.pid, "already_running": False}


def stop_expression_monitor(state_dir: Path) -> dict[str, object]:
    path = pid_path(state_dir)
    pid = read_running_pid(state_dir)
    if pid is None:
        path.unlink(missing_ok=True)
        return {"stopped": False, "reason": "not_running"}

    os.kill(pid, signal.SIGTERM)
    path.unlink(missing_ok=True)
    return {"stopped": True, "pid": pid}


def capture_from_expression_monitor(
    state_dir: Path,
    *,
    artifact_dir: Path,
    timeout_seconds: float = 12.0,
    poll_interval: float = 0.25,
) -> dict[str, object] | None:
    if read_running_pid(state_dir) is None:
        return None

    deadline = time.time() + timeout_seconds
    latest_json_path = latest_output_path(state_dir)
    frame_path = latest_frame_path(state_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    while time.time() < deadline:
        if latest_json_path.is_file() and frame_path.is_file():
            try:
                payload = json.loads(latest_json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                time.sleep(poll_interval)
                continue

            if payload.get("face_detected") is True:
                staged_path = artifact_dir / "capture-expression-monitor.jpg"
                shutil.copy2(frame_path, staged_path)
                detection = pipeline.detect_faces(
                    staged_path,
                    pipeline.DEFAULT_FACE_DETECTOR,
                    runner=subprocess.run,
                )
                subject_selection = pipeline.select_best_available_subject(detection)
                if subject_selection is None:
                    time.sleep(poll_interval)
                    continue
                return {
                    "portrait_path": str(staged_path),
                    "portrait_detection": detection,
                    "subject_selection": subject_selection,
                    "expression_monitor_sample": payload,
                }
        time.sleep(poll_interval)

    raise ValueError("No primary subject detected in expression monitor sample")
