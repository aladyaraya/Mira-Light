#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

echo "== Start Mira Light Bridge =="
echo "Folder: $ROOT_DIR"
echo "Bridge: ${MIRA_LIGHT_BRIDGE_URL:-http://127.0.0.1:${MIRA_LIGHT_BRIDGE_PORT:-9783}}"
echo "Lamp:   ${MIRA_LIGHT_LAMP_BASE_URL:-tcp://192.168.31.10:9527}"
echo

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Missing .venv. Running setup first..."
  /bin/bash "$ROOT_DIR/Setup-Mira-Light-Voice.command"
fi

/bin/bash "$ROOT_DIR/scripts/ensure_mira_light_bridge.sh"

echo
echo "Mira Light bridge is ready."
echo "Health: ${MIRA_LIGHT_BRIDGE_URL:-http://127.0.0.1:${MIRA_LIGHT_BRIDGE_PORT:-9783}}/health"
echo
echo "This window can be closed; the bridge keeps running in the background."

