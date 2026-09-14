#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

MIC_DEVICE="${MIRA_LIGHT_MIC_DEVICE:-MacBook Air麦克风}"
STT_PROFILE="${MIRA_LIGHT_STT_PROFILE:-fast}"
LATENCY_PRESET="${MIRA_LIGHT_LATENCY_PRESET:-low}"
CLAW_MODE="${MIRA_LIGHT_CLAW_MODE:-local}"
export MIRA_LIGHT_SAY_VOICE="${MIRA_LIGHT_SAY_VOICE:-Tingting}"
export MIRA_LIGHT_SAY_RATE="${MIRA_LIGHT_SAY_RATE:-175}"
BRIDGE_HOST="${MIRA_LIGHT_BRIDGE_HOST:-127.0.0.1}"
BRIDGE_PORT="${MIRA_LIGHT_BRIDGE_PORT:-9783}"
LOCAL_BRIDGE_URL="http://${BRIDGE_HOST}:${BRIDGE_PORT}"
BRIDGE_URL="${MIRA_LIGHT_BRIDGE_URL:-$LOCAL_BRIDGE_URL}"

MOCK_HOST="${MIRA_LIGHT_MOCK_LAMP_HOST:-127.0.0.1}"
MOCK_PORT="${MIRA_LIGHT_MOCK_LAMP_PORT:-9791}"
MOCK_URL="http://${MOCK_HOST}:${MOCK_PORT}"
USE_MOCK_LAMP="${MIRA_LIGHT_USE_MOCK_LAMP:-0}"
LAMP_BASE_URL="${MIRA_LIGHT_LAMP_BASE_URL:-}"

MOCK_PID=""
BRIDGE_PID=""

echo "== Mira Light Voice =="
echo "Repo:   $ROOT_DIR"
echo "Mic:    $MIC_DEVICE"
echo "STT:    $STT_PROFILE"
echo "Latency: $LATENCY_PRESET"
echo "Voice:  $MIRA_LIGHT_SAY_VOICE @ $MIRA_LIGHT_SAY_RATE"
echo "Claw:   $CLAW_MODE"
echo "Bridge: $BRIDGE_URL"
echo "Mode:   full voice + action triggers"
echo

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "ERROR: missing $ROOT_DIR/.venv/bin/python"
  echo "Create the voice runtime environment first:"
  echo "  python3.11 -m venv .venv"
  echo "  .venv/bin/python -m pip install -r mira-light-voice-runtime-pack-2026-05-19/source/requirements.txt"
  echo
  read -r -p "Press Enter to close this window..."
  exit 1
fi

probe_url() {
  "$ROOT_DIR/.venv/bin/python" - "$1" <<'PY'
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

require_file "$ROOT_DIR/tools/mira_light_bridge/bridge_server.py"
require_file "$ROOT_DIR/tools/mira_light_bridge/bridge_config.json"

if probe_url "$BRIDGE_URL/health"; then
  echo "Mira Light bridge: OK"
else
  if [ "$BRIDGE_URL" != "$LOCAL_BRIDGE_URL" ]; then
    echo "WARNING: external bridge is not reachable at $BRIDGE_URL/health"
    echo "Voice will start, but action triggers may fail until that bridge is running."
    echo
  else
    if [ "$USE_MOCK_LAMP" = "1" ]; then
      require_file "$ROOT_DIR/scripts/mock_lamp_server.py"
      if probe_url "$MOCK_URL/health"; then
        echo "Mock lamp: already running at $MOCK_URL"
      else
        if port_in_use "$MOCK_PORT"; then
          echo "ERROR: mock lamp port $MOCK_PORT is already in use, but $MOCK_URL/health is not reachable."
          echo
          read -r -p "Press Enter to close this window..."
          exit 1
        fi
        echo "Starting mock Mira Light lamp at $MOCK_URL..."
        "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/mock_lamp_server.py" --host "$MOCK_HOST" --port "$MOCK_PORT" &
        MOCK_PID=$!
        wait_for_url "$MOCK_URL/health" "Mock lamp" "$MOCK_PID"
      fi
      LAMP_BASE_URL="$MOCK_URL"
    fi

    if port_in_use "$BRIDGE_PORT"; then
      echo "ERROR: bridge port $BRIDGE_PORT is already in use, but $BRIDGE_URL/health is not reachable."
      echo
      read -r -p "Press Enter to close this window..."
      exit 1
    fi

    echo "Starting Mira Light bridge at $BRIDGE_URL..."
    BRIDGE_CMD=(
      "$ROOT_DIR/.venv/bin/python"
      "$ROOT_DIR/tools/mira_light_bridge/bridge_server.py"
      --config "$ROOT_DIR/tools/mira_light_bridge/bridge_config.json"
      --host "$BRIDGE_HOST"
      --port "$BRIDGE_PORT"
    )
    if [ -n "$LAMP_BASE_URL" ]; then
      BRIDGE_CMD+=(--base-url "$LAMP_BASE_URL")
    fi
    "${BRIDGE_CMD[@]}" &
    BRIDGE_PID=$!
    wait_for_url "$BRIDGE_URL/health" "Mira Light bridge" "$BRIDGE_PID"
  fi
fi

echo "Starting Mira Light voice runtime..."
echo "Say '退出对话' to stop listening."
echo

"$ROOT_DIR/scripts/mira-talk-open.sh" \
  --device "$MIC_DEVICE" \
  --profile "$STT_PROFILE" \
  --latency-preset "$LATENCY_PRESET"
