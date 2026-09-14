#!/usr/bin/env python3
import argparse
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mira_sync


DEFAULT_POLL_INTERVAL = 1.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync staged chrome-camera-anime events into Mira.")
    parser.add_argument("--state-dir", type=Path, default=mira_sync.DEFAULT_STATE_DIR)
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL)
    return parser.parse_args(argv)


def watch_forever(*, state_dir: Path, poll_interval: float) -> None:
    while True:
        try:
            mira_sync.scan_and_queue_events(state_dir)
            mira_sync.deliver_pending_events(state_dir)
        except Exception as exc:
            print(f"[chrome-camera-anime mira-sync] {exc}", file=sys.stderr, flush=True)
        time.sleep(poll_interval)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    watch_forever(state_dir=args.state_dir, poll_interval=args.poll_interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
