#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import rokid_watch_daemon


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage the Rokid watch daemon toggle.")
    parser.add_argument("--config-path", type=Path, default=rokid_watch_daemon.DEFAULT_CONFIG_PATH)
    parser.add_argument("--enabled", choices=("true", "false"), required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = rokid_watch_daemon.set_enabled(args.config_path, args.enabled == "true")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
