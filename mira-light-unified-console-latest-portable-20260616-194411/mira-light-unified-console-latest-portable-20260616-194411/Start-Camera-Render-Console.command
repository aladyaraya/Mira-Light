#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/Chrome-Camera-Anime"
CONSOLE_DIR="$ROOT_DIR/camera-render-director-console"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 was not found in PATH."
  read -r -p "Press Enter to close this window..."
  exit 1
fi

source_env_file() {
  local env_file="$1"
  if [ -f "$env_file" ]; then
    eval "$(python3 - "$env_file" <<'PY'
import os
import re
import shlex
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[len("export "):].strip()
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        continue
    if key in os.environ:
        continue
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    print(f"export {key}={shlex.quote(value)}")
PY
)"
  fi
}

source_env_file "$RUNTIME_DIR/.env"
source_env_file "$HOME/.openclaw-printer-bridge.env"

load_secret_file_env() {
  local key_name="$1"
  local secret_file="$2"
  if [ -n "${!key_name:-}" ] || [ ! -f "$secret_file" ]; then
    return 0
  fi
  local secret
  secret="$(python3 - "$secret_file" <<'PY'
import sys
from pathlib import Path

value = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").strip()
if value:
    print(value)
PY
)"
  if [ -n "$secret" ]; then
    export "$key_name=$secret"
    echo "Seedream API: loaded existing persisted key from $secret_file"
  fi
}

load_secret_file_env "ARK_API_KEY" "$HOME/.openclaw-chrome-camera-anime/ark_api_key.txt"

CONSOLE_HOST="${CAMERA_RENDER_CONSOLE_HOST:-127.0.0.1}"
CONSOLE_PORT="${CAMERA_RENDER_CONSOLE_PORT:-8795}"
BRIDGE_HOST="${CAMERA_RENDER_BRIDGE_HOST:-127.0.0.1}"
BRIDGE_PORT="${CAMERA_RENDER_BRIDGE_PORT:-9795}"
PRINTER_HOST="${OPENCLAW_PRINTER_BRIDGE_HOST:-127.0.0.1}"
PRINTER_PORT="${OPENCLAW_PRINTER_BRIDGE_PORT:-9771}"
OPEN_BROWSER="${CAMERA_RENDER_OPEN_BROWSER:-1}"

CONSOLE_URL="http://${CONSOLE_HOST}:${CONSOLE_PORT}/"
BRIDGE_URL="http://${BRIDGE_HOST}:${BRIDGE_PORT}"
PRINTER_URL="${OPENCLAW_PRINTER_BRIDGE_URL:-http://${PRINTER_HOST}:${PRINTER_PORT}}"

expand_path() {
  python3 - "$1" <<'PY'
import os
import sys

print(os.path.abspath(os.path.expandvars(os.path.expanduser(sys.argv[1]))))
PY
}

CAMERA_RENDER_DATA_DIR="${CAMERA_RENDER_DATA_DIR:-$HOME/Documents/Chrome-Camera-Anime}"
CAMERA_RENDER_STATE_DIR="${CAMERA_RENDER_STATE_DIR:-$CAMERA_RENDER_DATA_DIR/state}"
CAMERA_RENDER_OUTPUT_DIR="${CAMERA_RENDER_OUTPUT_DIR:-$CAMERA_RENDER_DATA_DIR/outputs}"
CAMERA_RENDER_LOGS_DIR="${CAMERA_RENDER_LOGS_DIR:-$CAMERA_RENDER_DATA_DIR/logs}"
CAMERA_RENDER_CAMERA_CACHE_DIR="${CAMERA_RENDER_CAMERA_CACHE_DIR:-$CAMERA_RENDER_DATA_DIR/localmac-camera}"

CAMERA_RENDER_DATA_DIR="$(expand_path "$CAMERA_RENDER_DATA_DIR")"
CAMERA_RENDER_STATE_DIR="$(expand_path "$CAMERA_RENDER_STATE_DIR")"
CAMERA_RENDER_OUTPUT_DIR="$(expand_path "$CAMERA_RENDER_OUTPUT_DIR")"
CAMERA_RENDER_LOGS_DIR="$(expand_path "$CAMERA_RENDER_LOGS_DIR")"
CAMERA_RENDER_CAMERA_CACHE_DIR="$(expand_path "$CAMERA_RENDER_CAMERA_CACHE_DIR")"

export OPENCLAW_PRINTER_BRIDGE_URL="$PRINTER_URL"
export CAMERA_RENDER_START_WATCH="${CAMERA_RENDER_START_WATCH:-1}"
export CAMERA_RENDER_DATA_DIR
export CAMERA_RENDER_STATE_DIR
export CAMERA_RENDER_OUTPUT_DIR
export CAMERA_RENDER_LOGS_DIR
export CAMERA_RENDER_CAMERA_CACHE_DIR

CONSOLE_PID=""
BRIDGE_PID=""
PRINTER_PID=""

echo "== Chrome Camera Anime Console =="
echo "Repo:    $ROOT_DIR"
echo "Console: $CONSOLE_URL"
echo "Bridge:  $BRIDGE_URL"
echo "Printer: $PRINTER_URL"
echo "Camera:  ${CAMERA_RENDER_CAMERA_NAME:-MacBook Air相机}"
echo "Data:    $CAMERA_RENDER_DATA_DIR"
echo "Output:  $CAMERA_RENDER_OUTPUT_DIR"
echo

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
  stop_pid "$CONSOLE_PID" "camera render console"
  stop_pid "$BRIDGE_PID" "camera render bridge"
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

require_file "$RUNTIME_DIR/manual_insta_capture.py"
require_file "$RUNTIME_DIR/pipeline.py"
require_file "$ROOT_DIR/tools/camera_render_bridge/bridge_server.py"
require_file "$CONSOLE_DIR/scripts/console_server.py"
require_file "$ROOT_DIR/tools/printer_bridge/start_bridge.sh"

mkdir -p "$CAMERA_RENDER_STATE_DIR" "$CAMERA_RENDER_OUTPUT_DIR" "$CAMERA_RENDER_LOGS_DIR" "$CAMERA_RENDER_CAMERA_CACHE_DIR"

if probe_url "$PRINTER_URL/health"; then
  echo "Printer Bridge: already running at $PRINTER_URL"
else
  if port_in_use "$PRINTER_PORT"; then
    echo "ERROR: printer bridge port $PRINTER_PORT is in use, but $PRINTER_URL/health is not reachable."
    read -r -p "Press Enter to close this window..."
    exit 1
  fi
  export OPENCLAW_PRINTER_BRIDGE_ENV="${OPENCLAW_PRINTER_BRIDGE_ENV:-$CAMERA_RENDER_DATA_DIR/printer-bridge.env}"
  export OPENCLAW_PRINTER_BRIDGE_PROFILE="${OPENCLAW_PRINTER_BRIDGE_PROFILE:-$CAMERA_RENDER_DATA_DIR/printer-profile.json}"
  echo "Starting Printer Bridge at $PRINTER_URL..."
  "$ROOT_DIR/tools/printer_bridge/start_bridge.sh" &
  PRINTER_PID=$!
  wait_for_url "$PRINTER_URL/health" "Printer Bridge" "$PRINTER_PID"
  source_env_file "$OPENCLAW_PRINTER_BRIDGE_ENV"
fi

echo
if probe_url "$BRIDGE_URL/health"; then
  echo "Camera Render Bridge: already running at $BRIDGE_URL"
else
  if port_in_use "$BRIDGE_PORT"; then
    echo "ERROR: camera bridge port $BRIDGE_PORT is in use, but $BRIDGE_URL/health is not reachable."
    read -r -p "Press Enter to close this window..."
    exit 1
  fi
  echo "Starting Camera Render Bridge..."
  python3 "$ROOT_DIR/tools/camera_render_bridge/bridge_server.py" \
    --host "$BRIDGE_HOST" \
    --port "$BRIDGE_PORT" \
    --runtime-dir "$RUNTIME_DIR" \
    --printer-url "$PRINTER_URL" &
  BRIDGE_PID=$!
  wait_for_url "$BRIDGE_URL/health" "Camera Render Bridge" "$BRIDGE_PID"
fi

echo
if probe_url "$CONSOLE_URL"; then
  echo "Browser console: already running at $CONSOLE_URL"
  open_console_url
  read -r -p "Press Enter to close this window..."
  exit 0
fi

if port_in_use "$CONSOLE_PORT"; then
  echo "ERROR: console port $CONSOLE_PORT is in use, but $CONSOLE_URL is not reachable."
  read -r -p "Press Enter to close this window..."
  exit 1
fi

echo "Starting browser console server..."
python3 "$CONSOLE_DIR/scripts/console_server.py" \
  --host "$CONSOLE_HOST" \
  --port "$CONSOLE_PORT" \
  --bridge-base-url "$BRIDGE_URL" &
CONSOLE_PID=$!
wait_for_url "$CONSOLE_URL" "Browser console" "$CONSOLE_PID"

open_console_url
echo
echo "Leave this Terminal window open while using the console."
echo "Press Ctrl-C here to stop the camera console and bridge."
echo
wait "$CONSOLE_PID"
