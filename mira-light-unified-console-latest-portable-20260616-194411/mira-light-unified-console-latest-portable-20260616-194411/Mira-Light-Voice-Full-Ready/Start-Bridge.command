#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"
export MIRA_LIGHT_ACTION_SPEED_MULTIPLIER="${MIRA_LIGHT_ACTION_SPEED_MULTIPLIER:-1.5}"

echo "== Mira Light Bridge =="
echo "Folder: $ROOT_DIR"
echo "Bridge: ${MIRA_LIGHT_BRIDGE_URL:-http://127.0.0.1:${MIRA_LIGHT_BRIDGE_PORT:-9783}}"
echo "Lamp:   ${MIRA_LIGHT_LAMP_BASE_URL:-tcp://192.168.31.10:9527}"
echo "Speed:  ${MIRA_LIGHT_ACTION_SPEED_MULTIPLIER}x"
echo

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Missing .venv. Running setup first..."
  /bin/bash "$ROOT_DIR/commands/Setup.command"
fi

/bin/bash "$ROOT_DIR/scripts/ensure_mira_light_bridge.sh"

echo
echo "Bridge is ready. You can close this window; the bridge keeps running in the background."
