#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  /bin/bash "$ROOT_DIR/commands/Setup.command"
fi

/bin/bash "$ROOT_DIR/setup/register_mira_voice_spark.sh" "$ROOT_DIR"
