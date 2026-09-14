#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONSOLE_DIR="$ROOT_DIR/mira-light-shenzhen-console"
SOURCE_SCRIPTS_DIR="/Users/thomasjwang/Documents/GitHub/Mira-Light/Motions_Shenzhen/demo_fixed_protocol_v2/scripts"
REPO_LOCAL_SCRIPTS_DIR="$ROOT_DIR/Motions_Shenzhen/demo_fixed_protocol_v2/scripts"

CONSOLE_HOST="${MIRA_SHENZHEN_CONSOLE_HOST:-127.0.0.1}"
CONSOLE_PORT="${MIRA_SHENZHEN_CONSOLE_PORT:-8777}"
CONSOLE_URL="http://${CONSOLE_HOST}:${CONSOLE_PORT}/"
BOARD_HOST="${MIRA_SHENZHEN_BOARD_HOST:-192.168.0.183}"
BOARD_PORT="${MIRA_SHENZHEN_BOARD_PORT:-22}"
BOARD_USER="${MIRA_SHENZHEN_BOARD_USER:-root}"
OPEN_BROWSER="${MIRA_SHENZHEN_OPEN_BROWSER:-1}"

if [ -z "${MIRA_SHENZHEN_BOARD_PASSWORD+x}" ]; then
  export MIRA_SHENZHEN_BOARD_PASSWORD=""
fi

if [ -z "${MIRA_SHENZHEN_SCRIPTS_DIR:-}" ]; then
  if [ -d "$REPO_LOCAL_SCRIPTS_DIR" ]; then
    export MIRA_SHENZHEN_SCRIPTS_DIR="$REPO_LOCAL_SCRIPTS_DIR"
  else
    export MIRA_SHENZHEN_SCRIPTS_DIR="$SOURCE_SCRIPTS_DIR"
  fi
fi

export MIRA_SHENZHEN_DIGUA_OUTPUT_DIR="${MIRA_SHENZHEN_DIGUA_OUTPUT_DIR:-$CONSOLE_DIR/runtime/digua-console-output}"

CONSOLE_PID=""

echo "== Mira Light Shenzhen Demo Console =="
echo "Repo:      $ROOT_DIR"
echo "Console:   $CONSOLE_URL"
echo "Board:     ${BOARD_USER}@${BOARD_HOST}:${BOARD_PORT}"
echo "Scripts:   $MIRA_SHENZHEN_SCRIPTS_DIR"
echo "Password:  $([ -n "${MIRA_SHENZHEN_BOARD_PASSWORD:-}" ] && echo configured || echo empty)"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 was not found in PATH."
  read -r -p "Press Enter to close this window..."
  exit 1
fi

probe_url() {
  python3 - "$1" <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=1.2) as response:
        raise SystemExit(0 if 200 <= response.status < 500 else 1)
except Exception:
    raise SystemExit(1)
PY
}

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local pid="${3:-}"
  for _ in {1..80}; do
    if probe_url "$url"; then
      echo "$label: OK"
      return 0
    fi
    if [ -n "$pid" ] && ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "ERROR: $label exited before it became ready."
      wait "$pid"
      return 1
    fi
    sleep 0.25
  done
  echo "ERROR: $label did not become ready at $url"
  return 1
}

should_open_browser() {
  case "$(printf '%s' "$OPEN_BROWSER" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

open_console_url() {
  if should_open_browser; then
    open "$CONSOLE_URL" >/dev/null 2>&1 || true
  else
    echo "Browser auto-open disabled; open manually: $CONSOLE_URL"
  fi
}

stop_pid() {
  local pid="$1"
  local label="$2"
  if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
    echo "Stopping $label..."
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" 2>/dev/null || true
  fi
}

cleanup() {
  echo
  stop_pid "$CONSOLE_PID" "Mira Light Shenzhen console"
}
trap cleanup INT TERM EXIT

require_file() {
  if [ ! -f "$1" ]; then
    echo "ERROR: required file was not found."
    echo "Expected: $1"
    read -r -p "Press Enter to close this window..."
    exit 1
  fi
}

require_file "$CONSOLE_DIR/shenzhen_console.py"
require_file "$CONSOLE_DIR/scene_registry.json"
require_file "$CONSOLE_DIR/web/index.html"

if [ ! -d "$MIRA_SHENZHEN_SCRIPTS_DIR" ]; then
  echo "ERROR: Shenzhen motion scripts directory was not found."
  echo "Expected: $MIRA_SHENZHEN_SCRIPTS_DIR"
  read -r -p "Press Enter to close this window..."
  exit 1
fi

if probe_url "$CONSOLE_URL"; then
  echo "Shenzhen console: already running at $CONSOLE_URL"
  open_console_url
  read -r -p "Press Enter to close this window..."
  exit 0
fi

if port_in_use "$CONSOLE_PORT"; then
  echo "ERROR: console port $CONSOLE_PORT is in use, but $CONSOLE_URL is not reachable."
  read -r -p "Press Enter to close this window..."
  exit 1
fi

echo "Starting Shenzhen console server..."
python3 "$CONSOLE_DIR/shenzhen_console.py" \
  --host "$CONSOLE_HOST" \
  --port "$CONSOLE_PORT" \
  --board-host "$BOARD_HOST" \
  --board-port "$BOARD_PORT" \
  --board-user "$BOARD_USER" &
CONSOLE_PID=$!

wait_for_url "$CONSOLE_URL" "Shenzhen console" "$CONSOLE_PID"
open_console_url

echo
echo "Leave this Terminal window open while using the Shenzhen console."
echo "Preview buttons do not touch the device; run buttons send SSH commands to the board."
echo "Press Ctrl-C here to stop the console."
echo
wait "$CONSOLE_PID"
