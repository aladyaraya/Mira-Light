#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONSOLE_DIR="$ROOT_DIR/mira-light-camera-console"

CONSOLE_HOST="${MIRA_CAMERA_CONSOLE_HOST:-127.0.0.1}"
CONSOLE_PORT="${MIRA_CAMERA_CONSOLE_PORT:-8788}"
CONSOLE_URL="http://${CONSOLE_HOST}:${CONSOLE_PORT}/"
BOARD_HOST="${MIRA_CAMERA_BOARD_HOST:-${MIRA_SHENZHEN_BOARD_HOST:-192.168.0.183}}"
BOARD_PORT="${MIRA_CAMERA_BOARD_PORT:-${MIRA_SHENZHEN_BOARD_PORT:-22}}"
BOARD_USER="${MIRA_CAMERA_BOARD_USER:-${MIRA_SHENZHEN_BOARD_USER:-root}}"
OPEN_BROWSER="${MIRA_CAMERA_CONSOLE_OPEN_BROWSER:-1}"

if [ -z "${MIRA_CAMERA_BOARD_PASSWORD+x}" ]; then
  export MIRA_CAMERA_BOARD_PASSWORD="${MIRA_SHENZHEN_BOARD_PASSWORD:-}"
fi

echo "== Mira Light Camera Director Console =="
echo "Repo:     $ROOT_DIR"
echo "Console:  $CONSOLE_URL"
echo "Board:    ${BOARD_USER}@${BOARD_HOST}:${BOARD_PORT}"
echo "Device:   ${DIGUA_CAMERA_DEVICE:-/dev/video0}"
echo "Controls: ${MIRA_CAMERA_V4L2_CTRLS:-${DIGUA_CAMERA_V4L2_CTRLS:--}}"
echo "Interval: ${MIRA_CAMERA_INTERVAL_SECONDS:-10}s"
echo "Password: $([ -n "${MIRA_CAMERA_BOARD_PASSWORD:-}" ] && echo configured || echo empty)"
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

CONSOLE_PID=""
cleanup() {
  echo
  stop_pid "$CONSOLE_PID" "Mira Light camera console"
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

require_file "$CONSOLE_DIR/camera_console.py"
require_file "$CONSOLE_DIR/web/index.html"
require_file "$ROOT_DIR/Chrome-Camera-Anime/digua_remote_render_pipeline.py"

if probe_url "$CONSOLE_URL"; then
  echo "Mira Light camera director console: already running at $CONSOLE_URL"
  open_console_url
  read -r -p "Press Enter to close this window..."
  exit 0
fi

if port_in_use "$CONSOLE_PORT"; then
  echo "ERROR: console port $CONSOLE_PORT is in use, but $CONSOLE_URL is not reachable."
  read -r -p "Press Enter to close this window..."
  exit 1
fi

echo "Starting Mira Light camera director console server..."
python3 "$CONSOLE_DIR/camera_console.py" \
  --host "$CONSOLE_HOST" \
  --port "$CONSOLE_PORT" \
  --board-host "$BOARD_HOST" \
  --board-port "$BOARD_PORT" \
  --board-user "$BOARD_USER" &
CONSOLE_PID=$!

wait_for_url "$CONSOLE_URL" "Mira Light camera director console" "$CONSOLE_PID"
open_console_url

echo
echo "Leave this Terminal window open while using the camera director console."
echo "The page displays the newest frame captured from the board camera roughly every 10 seconds."
echo "Press Ctrl-C here to stop the console."
echo
wait "$CONSOLE_PID"
