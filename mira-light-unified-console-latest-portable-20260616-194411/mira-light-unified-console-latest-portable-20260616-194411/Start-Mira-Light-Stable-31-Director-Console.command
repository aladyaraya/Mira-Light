#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONSOLE_DIR="$ROOT_DIR/mira-light-unified-director-console-stable-31"
CONSOLE_HOST="${MIRA_UNIFIED_CONSOLE_HOST:-127.0.0.1}"
CONSOLE_PORT="${MIRA_UNIFIED_CONSOLE_PORT:-8791}"
BOARD_HOST="${MIRA_SHENZHEN_BOARD_HOST:-192.168.31.10}"
BOARD_PORT="${MIRA_SHENZHEN_BOARD_PORT:-22}"
BOARD_USER="${MIRA_SHENZHEN_BOARD_USER:-root}"
CONSOLE_URL="http://${CONSOLE_HOST}:${CONSOLE_PORT}/"

export MIRA_SHENZHEN_BOARD_HOST="$BOARD_HOST"
export MIRA_CAMERA_BOARD_HOST="${MIRA_CAMERA_BOARD_HOST:-$BOARD_HOST}"
export MIRA_LIGHT_BASE_URL="${MIRA_LIGHT_BASE_URL:-tcp://${BOARD_HOST}:9527}"
export MIRA_SHENZHEN_BOARD_PASSWORD="${MIRA_SHENZHEN_BOARD_PASSWORD:-}"
export MIRA_CAMERA_BOARD_PASSWORD="${MIRA_CAMERA_BOARD_PASSWORD:-}"
export MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS="${MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS:-2}"
export MIRA_UNIFIED_CAMERA_START_WATCH="${MIRA_UNIFIED_CAMERA_START_WATCH:-1}"
export MIRA_BOOK_FOLLOW_RECEIVER_PORT="${MIRA_BOOK_FOLLOW_RECEIVER_PORT:-18000}"

if [ -z "${MIRA_SHENZHEN_SCRIPTS_DIR:-}" ]; then
  export MIRA_SHENZHEN_SCRIPTS_DIR="$ROOT_DIR/Motions_Shenzhen/demo_fixed_protocol_v2/scripts"
fi

echo "== Mira Light Stable 31 Director Console =="
echo "Console: $CONSOLE_URL"
echo "Board:   ${BOARD_USER}@${BOARD_HOST}:${BOARD_PORT}"
echo "Lamp:    $MIRA_LIGHT_BASE_URL"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 was not found in PATH."
  read -r -p "Press Enter to close this window..."
  exit 1
fi

if [ ! -f "$CONSOLE_DIR/shenzhen_console.py" ]; then
  echo "ERROR: console backend not found: $CONSOLE_DIR/shenzhen_console.py"
  read -r -p "Press Enter to close this window..."
  exit 1
fi

if lsof -nP -iTCP:"$CONSOLE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $CONSOLE_PORT is already in use. Open: $CONSOLE_URL"
  open "$CONSOLE_URL" >/dev/null 2>&1 || true
  read -r -p "Press Enter to close this window..."
  exit 0
fi

open "$CONSOLE_URL" >/dev/null 2>&1 || true

python3 "$CONSOLE_DIR/shenzhen_console.py" \
  --host "$CONSOLE_HOST" \
  --port "$CONSOLE_PORT" \
  --board-host "$BOARD_HOST" \
  --board-port "$BOARD_PORT" \
  --board-user "$BOARD_USER"
