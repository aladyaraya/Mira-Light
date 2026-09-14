#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONSOLE_DIR="$ROOT_DIR/mira-light-director-console"

CONSOLE_HOST="${MIRA_LIGHT_CONSOLE_HOST:-127.0.0.1}"
CONSOLE_PORT="${MIRA_LIGHT_CONSOLE_PORT:-8765}"
CONSOLE_URL="http://${CONSOLE_HOST}:${CONSOLE_PORT}/"

BRIDGE_HOST="${MIRA_LIGHT_BRIDGE_HOST:-127.0.0.1}"
BRIDGE_PORT="${MIRA_LIGHT_BRIDGE_PORT:-9783}"
LOCAL_BRIDGE_URL="http://${BRIDGE_HOST}:${BRIDGE_PORT}"
BRIDGE_URL="${MIRA_LIGHT_CONSOLE_BRIDGE_URL:-$LOCAL_BRIDGE_URL}"

MOCK_HOST="${MIRA_LIGHT_MOCK_LAMP_HOST:-127.0.0.1}"
MOCK_PORT="${MIRA_LIGHT_MOCK_LAMP_PORT:-9791}"
MOCK_URL="http://${MOCK_HOST}:${MOCK_PORT}"
USE_MOCK_LAMP="${MIRA_LIGHT_USE_MOCK_LAMP:-1}"

if [ "$USE_MOCK_LAMP" = "0" ]; then
  LAMP_BASE_URL="${MIRA_LIGHT_LAMP_BASE_URL:-tcp://192.168.31.10:9527}"
else
  LAMP_BASE_URL="${MIRA_LIGHT_LAMP_BASE_URL:-$MOCK_URL}"
fi
export MIRA_LIGHT_LAMP_BASE_URL="$LAMP_BASE_URL"

MOCK_PID=""
BRIDGE_PID=""
CONSOLE_PID=""

echo "== Mira Light One-Click Console =="
echo "Repo:       $ROOT_DIR"
echo "Console:    $CONSOLE_URL"
echo "Bridge:     $BRIDGE_URL"
echo "Lamp target: $LAMP_BASE_URL"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 was not found in PATH."
  echo "Install Python 3, then run this launcher again."
  echo
  read -r -p "Press Enter to close this window..."
  exit 1
fi

probe_url() {
  python3 - "$1" <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=1.0) as response:
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

  for _ in {1..60}; do
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
  stop_pid "$CONSOLE_PID" "console server"
  stop_pid "$BRIDGE_PID" "Mira Light bridge"
  stop_pid "$MOCK_PID" "mock lamp"
}
trap cleanup INT TERM EXIT

require_file() {
  if [ ! -f "$1" ]; then
    echo "ERROR: required file was not found."
    echo "Expected: $1"
    echo
    read -r -p "Press Enter to close this window..."
    exit 1
  fi
}

require_file "$CONSOLE_DIR/scripts/console_server.py"
require_file "$ROOT_DIR/tools/mira_light_bridge/bridge_server.py"
require_file "$ROOT_DIR/scripts/mock_lamp_server.py"

cd "$ROOT_DIR"

if [ "$BRIDGE_URL" = "$LOCAL_BRIDGE_URL" ]; then
  if [ "$USE_MOCK_LAMP" = "0" ]; then
    echo "Mock lamp: skipped; using configured lamp target."
  elif probe_url "$MOCK_URL/health"; then
    echo "Mock lamp: already running at $MOCK_URL"
  else
    if port_in_use "$MOCK_PORT"; then
      echo "ERROR: mock lamp port $MOCK_PORT is already in use, but $MOCK_URL/health is not reachable."
      echo
      read -r -p "Press Enter to close this window..."
      exit 1
    fi
    echo "Starting mock Mira Light lamp at $MOCK_URL..."
    python3 scripts/mock_lamp_server.py --host "$MOCK_HOST" --port "$MOCK_PORT" &
    MOCK_PID=$!
    wait_for_url "$MOCK_URL/health" "Mock lamp" "$MOCK_PID"
  fi

  if probe_url "$BRIDGE_URL/health"; then
    echo "Mira Light bridge: already running at $BRIDGE_URL"
  else
    if port_in_use "$BRIDGE_PORT"; then
      echo "ERROR: bridge port $BRIDGE_PORT is already in use, but $BRIDGE_URL/health is not reachable."
      echo
      read -r -p "Press Enter to close this window..."
      exit 1
    fi
    echo "Starting Mira Light bridge at $BRIDGE_URL..."
    python3 tools/mira_light_bridge/bridge_server.py \
      --config tools/mira_light_bridge/bridge_config.json \
      --host "$BRIDGE_HOST" \
      --port "$BRIDGE_PORT" \
      --base-url "$LAMP_BASE_URL" &
    BRIDGE_PID=$!
    wait_for_url "$BRIDGE_URL/health" "Mira Light bridge" "$BRIDGE_PID"
  fi
else
  echo "External bridge URL configured: $BRIDGE_URL"
  if probe_url "$BRIDGE_URL/health"; then
    echo "Mira Light bridge: OK"
  else
    echo "WARNING: configured bridge is not reachable yet."
  fi
fi

echo
if port_in_use "$CONSOLE_PORT"; then
  if probe_url "$CONSOLE_URL"; then
    echo "Console: already running at $CONSOLE_URL"
    open "$CONSOLE_URL" >/dev/null 2>&1 || true
    echo
    read -r -p "Press Enter to close this window..."
    exit 0
  fi
  echo "ERROR: console port $CONSOLE_PORT is already in use, but $CONSOLE_URL is not reachable."
  echo
  read -r -p "Press Enter to close this window..."
  exit 1
fi

echo "Starting browser console server..."
echo "Leave this Terminal window open while using the console."
echo "Press Ctrl-C here to stop the services started by this launcher."
echo

cd "$CONSOLE_DIR"
python3 scripts/console_server.py \
  --host "$CONSOLE_HOST" \
  --port "$CONSOLE_PORT" \
  --bridge-base-url "$BRIDGE_URL" &
CONSOLE_PID=$!

wait_for_url "$CONSOLE_URL" "Browser console" "$CONSOLE_PID"
open "$CONSOLE_URL" >/dev/null 2>&1 || true

wait "$CONSOLE_PID"
