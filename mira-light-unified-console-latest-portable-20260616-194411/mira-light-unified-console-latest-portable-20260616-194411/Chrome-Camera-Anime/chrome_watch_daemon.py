#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import expression_monitor_control
from job_store import DEFAULT_STATE_DIR, create_job

DEFAULT_STATE_PATH = DEFAULT_STATE_DIR / "watch-state.json"
DEFAULT_POLL_INTERVAL = 0.25
DEFAULT_COOLDOWN_SECONDS = 0.0
DEFAULT_TRIGGER_MODE = "launch_or_focus"


def log_event(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch for Google Chrome launches and trigger the anime pipeline.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--cooldown-seconds", type=float, default=DEFAULT_COOLDOWN_SECONDS)
    parser.add_argument(
        "--trigger-mode",
        choices=("launch", "launch_or_focus"),
        default=DEFAULT_TRIGGER_MODE,
        help="Trigger only when Chrome starts, or also when an already-running Chrome becomes frontmost.",
    )
    return parser.parse_args(argv)


def load_state(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp"
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def is_chrome_running() -> bool:
    for process_name in ("Google Chrome", "Google Chrome for Testing"):
        result = subprocess.run(
            ["pgrep", "-x", process_name],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
    return False


def is_chrome_frontmost() -> bool:
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first application process whose frontmost is true',
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except subprocess.TimeoutExpired:
        return False
    if result.returncode != 0:
        return False
    return result.stdout.strip() in {"Google Chrome", "Google Chrome for Testing"}


def compute_trigger(
    *,
    state: dict,
    chrome_running: bool,
    chrome_frontmost: bool = False,
    now: float,
    cooldown_seconds: float,
    trigger_mode: str = DEFAULT_TRIGGER_MODE,
) -> tuple[bool, dict]:
    was_running = bool(state.get("chrome_running", False))
    was_frontmost = bool(state.get("chrome_frontmost", False))
    last_triggered_at = state.get("last_triggered_at")
    trigger = False

    launch_trigger = chrome_running and not was_running
    focus_trigger = (
        trigger_mode == "launch_or_focus"
        and chrome_running
        and chrome_frontmost
        and not was_frontmost
    )
    if launch_trigger or focus_trigger:
        if last_triggered_at is None or (now - float(last_triggered_at)) >= cooldown_seconds:
            trigger = True
            last_triggered_at = now

    next_state = {
        **state,
        "chrome_running": chrome_running,
        "chrome_frontmost": chrome_frontmost,
    }
    if last_triggered_at is not None:
        next_state["last_triggered_at"] = float(last_triggered_at)
    return trigger, next_state


def run_iteration(
    *,
    state_dir: Path,
    state_path: Path,
    now: float,
    cooldown_seconds: float,
    trigger_mode: str = DEFAULT_TRIGGER_MODE,
    process_checker=is_chrome_running,
    frontmost_checker=is_chrome_frontmost,
    enqueue_job=create_job,
    start_expression_monitor=expression_monitor_control.start_expression_monitor,
) -> dict:
    state = load_state(state_path)
    was_running = bool(state.get("chrome_running", False))
    was_frontmost = bool(state.get("chrome_frontmost", False))
    chrome_running = process_checker()
    chrome_frontmost = frontmost_checker() if chrome_running else False
    if chrome_running != was_running:
        log_event(f"chrome_running changed: {was_running} -> {chrome_running}")
    if chrome_frontmost != was_frontmost:
        log_event(f"chrome_frontmost changed: {was_frontmost} -> {chrome_frontmost}")
    trigger, next_state = compute_trigger(
        state=state,
        chrome_running=chrome_running,
        chrome_frontmost=chrome_frontmost,
        now=now,
        cooldown_seconds=cooldown_seconds,
        trigger_mode=trigger_mode,
    )
    if trigger:
        try:
            job = enqueue_job(
                state_dir,
                trigger="chrome_launch",
                metadata={"app": "Google Chrome"},
            )
            next_state["last_job_id"] = job["job_id"]
            next_state.pop("last_enqueue_error", None)
            log_event(f"queued chrome_launch job: {job['job_id']}")
        except Exception as exc:
            error_text = str(exc).strip()
            next_state["last_enqueue_error"] = error_text
            log_event(f"enqueue failed: {error_text}")
        else:
            next_state["expression_monitor_skipped"] = True
            next_state.pop("last_expression_monitor_error", None)
    write_state(state_path, next_state)
    return next_state


def watch_forever(
    *,
    state_dir: Path,
    state_path: Path,
    poll_interval: float,
    cooldown_seconds: float,
    trigger_mode: str,
) -> None:
    log_event(f"watcher started state_dir={state_dir} state_path={state_path} trigger_mode={trigger_mode}")
    while True:
        run_iteration(
            state_dir=state_dir,
            state_path=state_path,
            now=time.time(),
            cooldown_seconds=cooldown_seconds,
            trigger_mode=trigger_mode,
        )
        time.sleep(poll_interval)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    watch_forever(
        state_dir=args.state_dir,
        state_path=args.state_path,
        poll_interval=args.poll_interval,
        cooldown_seconds=args.cooldown_seconds,
        trigger_mode=args.trigger_mode,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
