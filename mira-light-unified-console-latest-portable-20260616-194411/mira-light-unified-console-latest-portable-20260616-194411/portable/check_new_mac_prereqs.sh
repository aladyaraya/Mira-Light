#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${MIRA_UNIFIED_ENV_FILE:-$ROOT_DIR/portable/unified-console.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

PYTHON_BIN="${MIRA_UNIFIED_PYTHON:-$ROOT_DIR/.venv/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="${MIRA_UNIFIED_PYTHON:-python3}"
fi

BOARD_HOST="${MIRA_SHENZHEN_BOARD_HOST:-192.168.0.183}"
BOARD_PORT="${MIRA_SHENZHEN_BOARD_PORT:-22}"
BOARD_USER="${MIRA_SHENZHEN_BOARD_USER:-root}"
BOARD_PASSWORD="${MIRA_SHENZHEN_BOARD_PASSWORD:-}"
CONSOLE_PORT="${MIRA_UNIFIED_CONSOLE_PORT:-8790}"
CELEBRATION_PORT="${MIRA_CELEBRATION_CONSOLE_PORT:-8777}"
AUDIO_PORT="${MIRA_TOUCH_AUDIO_BRIDGE_PORT:-9783}"

status=0

pass() { printf 'OK      %s\n' "$1"; }
warn() { printf 'WARN    %s\n' "$1"; }
fail() { printf 'MISSING %s\n' "$1"; status=1; }

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "$1"
  else
    fail "$1"
  fi
}

check_file() {
  if [ -e "$1" ]; then
    pass "$1"
  else
    fail "$1"
  fi
}

echo "== Mira Light portable prerequisites =="
echo "Root: $ROOT_DIR"
echo "Env:  ${ENV_FILE#$ROOT_DIR/}"
echo

check_command "$PYTHON_BIN"
check_command ssh
check_command sshpass
check_command expect
check_command ffmpeg
check_command tmux
check_command lsof
check_command curl

echo
check_file "Start-Mira-Light-Latest-Console.command"
check_file "Start-Mira-Light-Unified-Director-Console.command"
check_file "Start-Mira-Light-Unified-Director-Console-Keyboard.command"
check_file "mira-light-unified-director-console/shenzhen_console.py"
check_file "mira-light-unified-director-console/web/index.html"
check_file "mira-light-unified-director-console-keyboard/web/index.html"
check_file "mira-light-shenzhen-console/web/08_celebrate/index.html"
check_file "mira-light-camera-console/camera_console.py"
check_file "Chrome-Camera-Anime/digua_remote_render_pipeline.py"
check_file "Motions_Shenzhen/demo_fixed_protocol_v2/scripts/common.py"
check_file "portable/support/touch-audio-bridge/audio_bridge_server.py"
check_file "portable/support/touch-audio-bridge/assets/speech/cute_robot_comfort.aiff"

echo
if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  "$PYTHON_BIN" - <<'PY' || status=1
mods = ["numpy", "cv2", "sounddevice", "soundfile"]
for name in mods:
    try:
        __import__(name)
        print(f"OK      python import {name}")
    except Exception as exc:
        print(f"MISSING python import {name}: {exc}")
        raise SystemExit(1)
PY
fi

echo
if [ -n "$BOARD_PASSWORD" ] && command -v sshpass >/dev/null 2>&1; then
  if sshpass -p "$BOARD_PASSWORD" ssh \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=3 \
    -p "$BOARD_PORT" \
    "$BOARD_USER@$BOARD_HOST" true >/dev/null 2>&1; then
    pass "board SSH ${BOARD_USER}@${BOARD_HOST}:${BOARD_PORT}"
  else
    warn "board SSH failed; check Wi-Fi, board power, IP, and password"
  fi
else
  warn "board SSH skipped; password or sshpass missing"
fi

if command -v nc >/dev/null 2>&1; then
  if nc -G 2 -z "$BOARD_HOST" 9527 >/dev/null 2>&1; then
    pass "servo bridge ${BOARD_HOST}:9527"
  else
    warn "servo bridge ${BOARD_HOST}:9527 is not reachable yet"
  fi
fi

LAN_HOST="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 127.0.0.1)"
echo
echo "Latest URL:       http://127.0.0.1:8791/"
echo "Console URL:      http://127.0.0.1:${CONSOLE_PORT}/"
echo "LAN latest URL:   http://${LAN_HOST}:8791/"
echo "LAN console URL:  http://${LAN_HOST}:${CONSOLE_PORT}/"
echo "Celebration URL:  http://${LAN_HOST}:${CELEBRATION_PORT}/08_celebrate/index.html"
echo "Touch audio URL:  http://127.0.0.1:${AUDIO_PORT}/health"

exit "$status"
