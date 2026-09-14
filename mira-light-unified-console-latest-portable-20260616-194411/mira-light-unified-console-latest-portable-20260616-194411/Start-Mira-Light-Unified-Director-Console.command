#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

PORTABLE_ENV_FILE="${MIRA_UNIFIED_ENV_FILE:-$ROOT_DIR/portable/unified-console.env}"
if [ -f "$PORTABLE_ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$PORTABLE_ENV_FILE"
  set +a
fi

if [ -x "$ROOT_DIR/.venv/bin/python3" ]; then
  PYTHON_BIN="${MIRA_UNIFIED_PYTHON:-$ROOT_DIR/.venv/bin/python3}"
else
  PYTHON_BIN="${MIRA_UNIFIED_PYTHON:-python3}"
fi

CONSOLE_DIR="$ROOT_DIR/mira-light-unified-director-console"
SHENZHEN_CONSOLE_DIR="$ROOT_DIR/mira-light-shenzhen-console"
CAMERA_CONSOLE_DIR="$ROOT_DIR/mira-light-camera-console"
BOOK_FOLLOW_BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/bootstrap_book_follow_board.sh"
PORTABLE_AUDIO_BRIDGE_DIR="$ROOT_DIR/portable/support/touch-audio-bridge"
LEGACY_AUDIO_BRIDGE_DIR="$ROOT_DIR/tmp/mira-touch-audio-bridge-20260524/audio-bridge"
if [ -d "$PORTABLE_AUDIO_BRIDGE_DIR" ]; then
  AUDIO_BRIDGE_DIR="$PORTABLE_AUDIO_BRIDGE_DIR"
else
  AUDIO_BRIDGE_DIR="$LEGACY_AUDIO_BRIDGE_DIR"
fi
AUDIO_BRIDGE_PORT="${MIRA_TOUCH_AUDIO_BRIDGE_PORT:-9783}"
DEFAULT_ANSWER_AUDIO_PATH="$ROOT_DIR/Mira-Light-Voice-Cloud-Ready/docs/0525/MiniMax_2026-05-25_13_21_00_Comedian_no-watermark.mp3"
SOURCE_SCRIPTS_DIR="/Users/thomasjwang/Documents/GitHub/Mira-Light/Motions_Shenzhen/demo_fixed_protocol_v2/scripts"
REPO_LOCAL_SCRIPTS_DIR="$ROOT_DIR/Motions_Shenzhen/demo_fixed_protocol_v2/scripts"

DETECTED_LAN_HOST="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [ -z "$DETECTED_LAN_HOST" ]; then
  DETECTED_LAN_HOST="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi
LAN_HOST="${MIRA_LAN_HOST:-${DETECTED_LAN_HOST:-127.0.0.1}}"
CONSOLE_HOST="${MIRA_UNIFIED_CONSOLE_HOST:-0.0.0.0}"
CONSOLE_PORT="${MIRA_UNIFIED_CONSOLE_PORT:-8790}"
CONSOLE_PUBLIC_HOST="${MIRA_UNIFIED_CONSOLE_PUBLIC_HOST:-$LAN_HOST}"
CONSOLE_URL="http://${CONSOLE_PUBLIC_HOST}:${CONSOLE_PORT}/"
CONSOLE_LOCAL_URL="http://127.0.0.1:${CONSOLE_PORT}/"
CELEBRATION_HOST="${MIRA_CELEBRATION_CONSOLE_HOST:-0.0.0.0}"
CELEBRATION_PORT="${MIRA_CELEBRATION_CONSOLE_PORT:-8777}"
CELEBRATION_PUBLIC_HOST="${MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST:-$LAN_HOST}"
CELEBRATION_URL="http://${CELEBRATION_PUBLIC_HOST}:${CELEBRATION_PORT}/08_celebrate/index.html"
CELEBRATION_LOCAL_URL="http://127.0.0.1:${CELEBRATION_PORT}/08_celebrate/index.html"
BOARD_HOST="${MIRA_SHENZHEN_BOARD_HOST:-192.168.0.183}"
BOARD_PORT="${MIRA_SHENZHEN_BOARD_PORT:-22}"
BOARD_USER="${MIRA_SHENZHEN_BOARD_USER:-root}"
BOOK_FOLLOW_BASE_URL="${MIRA_BOOK_FOLLOW_BASE_URL:-tcp://${BOARD_HOST}:9527}"
OPEN_BROWSER="${MIRA_UNIFIED_OPEN_BROWSER:-1}"
BOOTSTRAP_BOOK_FOLLOW="${MIRA_BOOK_FOLLOW_BOOTSTRAP_BOARD:-0}"
AUTO_START_BOOK_FOLLOW="${MIRA_BOOK_FOLLOW_AUTO_START:-0}"
RESTART_BOOK_FOLLOW="${MIRA_BOOK_FOLLOW_RESTART_ON_START:-1}"
STOP_LEGACY_CAMERA_CONSOLE="${MIRA_UNIFIED_STOP_LEGACY_CAMERA_CONSOLE:-1}"
LEGACY_CAMERA_PORT="${MIRA_CAMERA_CONSOLE_PORT:-8788}"
PRINTER_BRIDGE_QUEUE="${OPENCLAW_PRINTER_BRIDGE_QUEUE:-Mi_Wireless_Photo_Printer_9135_IP}"
PRINTER_BRIDGE_PORT="${OPENCLAW_PRINTER_BRIDGE_PORT:-9771}"
PRINTER_BRIDGE_CONFIG="${OPENCLAW_PRINTER_BRIDGE_CONFIG:-$HOME/.openclaw-printer-bridge/runtime/bridge_config.json}"
PRINTER_BRIDGE_PROFILE="${OPENCLAW_PRINTER_BRIDGE_PROFILE:-$HOME/.openclaw-printer-bridge/profile.json}"
PRINTER_BRIDGE_START_SCRIPT="${OPENCLAW_PRINTER_BRIDGE_START_SCRIPT:-$HOME/.openclaw-printer-bridge/runtime/start_bridge.sh}"
PRINTER_BRIDGE_4X6_MEDIA="${OPENCLAW_PRINTER_BRIDGE_4X6_MEDIA:-na_index-4x6_4x6in}"

export MIRA_SHENZHEN_BOARD_HOST="$BOARD_HOST"
export MIRA_CAMERA_BOARD_HOST="${MIRA_CAMERA_BOARD_HOST:-$BOARD_HOST}"
export MIRA_BOOK_FOLLOW_BASE_URL="$BOOK_FOLLOW_BASE_URL"
export MIRA_LIGHT_BASE_URL="$BOOK_FOLLOW_BASE_URL"

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
export MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS="${MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS:-10}"
export MIRA_UNIFIED_CAMERA_START_WATCH="${MIRA_UNIFIED_CAMERA_START_WATCH:-1}"
export MIRA_BOOK_FOLLOW_RECEIVER_PORT="${MIRA_BOOK_FOLLOW_RECEIVER_PORT:-18000}"
export MIRA_BOOK_FOLLOW_RESTART_CAMERA_SENDER="${MIRA_BOOK_FOLLOW_RESTART_CAMERA_SENDER:-0}"
export MIRA_BOOK_FOLLOW_STOP_CAMERA_SENDER="${MIRA_BOOK_FOLLOW_STOP_CAMERA_SENDER:-1}"
export MIRA_ANSWER_AUDIO_PATH="${MIRA_ANSWER_AUDIO_PATH:-$DEFAULT_ANSWER_AUDIO_PATH}"

CONSOLE_PID=""
CELEBRATION_PID=""

echo "== Mira Light Unified Director Console =="
echo "Repo:      $ROOT_DIR"
echo "Console:   $CONSOLE_URL"
echo "Celebrate: $CELEBRATION_URL"
echo "Bind:      unified ${CONSOLE_HOST}:${CONSOLE_PORT}, celebrate ${CELEBRATION_HOST}:${CELEBRATION_PORT}"
echo "Local:     $CONSOLE_LOCAL_URL"
echo "Board:     ${BOARD_USER}@${BOARD_HOST}:${BOARD_PORT}"
echo "Python:    $PYTHON_BIN"
echo "Scripts:   $MIRA_SHENZHEN_SCRIPTS_DIR"
echo "Camera:    ${MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS}s refresh"
echo "Book:      receiver port ${MIRA_BOOK_FOLLOW_RECEIVER_PORT}"
echo "Book URL:  $BOOK_FOLLOW_BASE_URL"
echo "Answer:    $MIRA_ANSWER_AUDIO_PATH"
echo "Printer:   $PRINTER_BRIDGE_QUEUE"
echo "Password:  $([ -n "${MIRA_SHENZHEN_BOARD_PASSWORD:-}" ] && echo configured || echo empty)"
echo

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python3 was not found in PATH, and .venv/bin/python3 is not available."
  read -r -p "Press Enter to close this window..."
  exit 1
fi

probe_url() {
  "$PYTHON_BIN" - "$1" <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=1.2) as response:
        raise SystemExit(0 if 200 <= response.status < 500 else 1)
except Exception:
    raise SystemExit(1)
PY
}

probe_answer_demo_endpoint() {
  "$PYTHON_BIN" - "$CONSOLE_LOCAL_URL" <<'PY'
import json
import sys
import urllib.request

console_url = sys.argv[1].rstrip("/")
request = urllib.request.Request(
    f"{console_url}/api/play-answer-demo",
    data=json.dumps({"dryRun": True}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=2.5) as response:
        body = json.loads(response.read().decode("utf-8") or "{}")
        raise SystemExit(0 if response.status == 200 and body.get("ok") and body.get("dryRun") else 1)
except Exception:
    raise SystemExit(1)
PY
}

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

console_port_pids() {
  lsof -tiTCP:"$CONSOLE_PORT" -sTCP:LISTEN 2>/dev/null || true
}

celebration_port_pids() {
  lsof -tiTCP:"$CELEBRATION_PORT" -sTCP:LISTEN 2>/dev/null || true
}

is_our_console_pid() {
  local pid="$1"
  local command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [ -n "$command" ] || return 1
  case "$command" in
    *"$CONSOLE_DIR/shenzhen_console.py"*|*"mira-light-unified-director-console/shenzhen_console.py"*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_our_celebration_pid() {
  local pid="$1"
  local command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [ -n "$command" ] || return 1
  case "$command" in
    *"$SHENZHEN_CONSOLE_DIR/shenzhen_console.py"*|*"mira-light-shenzhen-console/shenzhen_console.py"*|*"shenzhen_console.py --host "*" --port $CELEBRATION_PORT"*|*"shenzhen_console.py --port $CELEBRATION_PORT"*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

stop_stale_console_on_port() {
  local pids pid stopped=0
  pids="$(console_port_pids)"
  [ -n "$pids" ] || return 1
  for pid in $pids; do
    if is_our_console_pid "$pid"; then
      echo "Stopping stale unified console on port $CONSOLE_PORT (pid $pid)..."
      kill "$pid" >/dev/null 2>&1 || true
      stopped=1
    fi
  done
  if [ "$stopped" = "1" ]; then
    for _ in {1..20}; do
      port_in_use "$CONSOLE_PORT" || return 0
      sleep 0.25
    done
    pids="$(console_port_pids)"
    for pid in $pids; do
      if is_our_console_pid "$pid"; then
        echo "Force stopping stale unified console on port $CONSOLE_PORT (pid $pid)..."
        kill -9 "$pid" >/dev/null 2>&1 || true
      fi
    done
    sleep 0.25
    port_in_use "$CONSOLE_PORT" && return 1
    return 0
  fi
  return 1
}

stop_stale_celebration_on_port() {
  local pids pid stopped=0
  pids="$(celebration_port_pids)"
  [ -n "$pids" ] || return 1
  for pid in $pids; do
    if is_our_celebration_pid "$pid"; then
      echo "Stopping stale celebration console on port $CELEBRATION_PORT (pid $pid)..."
      kill "$pid" >/dev/null 2>&1 || true
      stopped=1
    fi
  done
  if [ "$stopped" = "1" ]; then
    for _ in {1..20}; do
      port_in_use "$CELEBRATION_PORT" || return 0
      sleep 0.25
    done
    pids="$(celebration_port_pids)"
    for pid in $pids; do
      if is_our_celebration_pid "$pid"; then
        echo "Force stopping stale celebration console on port $CELEBRATION_PORT (pid $pid)..."
        kill -9 "$pid" >/dev/null 2>&1 || true
      fi
    done
    sleep 0.25
    port_in_use "$CELEBRATION_PORT" && return 1
    return 0
  fi
  return 1
}

stop_legacy_camera_console() {
  case "$(printf '%s' "$STOP_LEGACY_CAMERA_CONSOLE" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on)
      local pids
      pids="$(lsof -tiTCP:"$LEGACY_CAMERA_PORT" -sTCP:LISTEN 2>/dev/null || true)"
      if [ -n "$pids" ]; then
        echo "Stopping legacy camera console on port $LEGACY_CAMERA_PORT to avoid /dev/video0 conflicts..."
        kill $pids >/dev/null 2>&1 || true
        sleep 0.5
      fi
      ;;
  esac
}

printer_bridge_pids() {
  lsof -tiTCP:"$PRINTER_BRIDGE_PORT" -sTCP:LISTEN 2>/dev/null || true
}

printer_bridge_queue() {
  if [ ! -f "$PRINTER_BRIDGE_CONFIG" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$PRINTER_BRIDGE_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

try:
    print(json.loads(Path(sys.argv[1]).read_text()).get("queue_name", ""))
except Exception:
    raise SystemExit(1)
PY
}

configure_printer_bridge_queue() {
  "$PYTHON_BIN" - "$PRINTER_BRIDGE_CONFIG" "$PRINTER_BRIDGE_PROFILE" "$PRINTER_BRIDGE_QUEUE" "$PRINTER_BRIDGE_4X6_MEDIA" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1]).expanduser()
profile_path = Path(sys.argv[2]).expanduser()
queue_name = sys.argv[3]
four_by_six_media = sys.argv[4]

def update_json(path, updater):
    if not path.exists():
        return False
    payload = json.loads(path.read_text())
    changed = updater(payload)
    if changed:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return changed

def update_config(payload):
    changed = False
    for key in ("queue_name", "display_name"):
        if payload.get(key) != queue_name:
            payload[key] = queue_name
            changed = True
    aliases = payload.setdefault("media_aliases", {})
    for alias in ("4x6", "4x6.Fullbleed"):
        if aliases.get(alias) != four_by_six_media:
            aliases[alias] = four_by_six_media
            changed = True
    supported = payload.setdefault("supported_media", [])
    for media in ("4x6", "4x6.Fullbleed", four_by_six_media):
        if media not in supported:
            supported.append(media)
            changed = True
    return changed

def update_profile(payload):
    printer = payload.setdefault("printer", {})
    changed = False
    for key in ("queue_name", "display_name"):
        if printer.get(key) != queue_name:
            printer[key] = queue_name
            changed = True
    aliases = printer.setdefault("default_media_aliases", {})
    for alias in ("4x6", "4x6.Fullbleed"):
        if aliases.get(alias) != four_by_six_media:
            aliases[alias] = four_by_six_media
            changed = True
    return changed

changed_config = update_json(config_path, update_config)
changed_profile = update_json(profile_path, update_profile)
print("changed" if changed_config or changed_profile else "unchanged")
PY
}

restart_printer_bridge_if_needed() {
  local configured current pids pid
  if [ ! -f "$PRINTER_BRIDGE_CONFIG" ]; then
    echo "Printer bridge: config not found; skipping queue check."
    return 0
  fi

  configured="$(configure_printer_bridge_queue || true)"
  current="$(printer_bridge_queue || true)"
  if [ "$current" != "$PRINTER_BRIDGE_QUEUE" ]; then
    echo "WARNING: printer bridge config queue is $current; expected $PRINTER_BRIDGE_QUEUE."
    return 0
  fi

  pids="$(printer_bridge_pids)"
  if [ -z "$pids" ]; then
    if [ -x "$PRINTER_BRIDGE_START_SCRIPT" ]; then
      echo "Starting printer bridge on port $PRINTER_BRIDGE_PORT..."
      nohup "$PRINTER_BRIDGE_START_SCRIPT" >/tmp/openclaw-printer-bridge.log 2>&1 &
    else
      echo "Printer bridge: not running, launcher missing; print health will show the issue."
    fi
    return 0
  fi

  if [ "$configured" = "changed" ]; then
    echo "Restarting printer bridge so queue $PRINTER_BRIDGE_QUEUE is active..."
    for pid in $pids; do
      kill "$pid" >/dev/null 2>&1 || true
    done
    sleep 0.5
    if [ -x "$PRINTER_BRIDGE_START_SCRIPT" ]; then
      nohup "$PRINTER_BRIDGE_START_SCRIPT" >/tmp/openclaw-printer-bridge.log 2>&1 &
    fi
  else
    echo "Printer bridge: queue $PRINTER_BRIDGE_QUEUE configured."
  fi
}

ensure_touch_audio_bridge() {
  if port_in_use "$AUDIO_BRIDGE_PORT"; then
    echo "Touch audio bridge: already running on port $AUDIO_BRIDGE_PORT."
    return 0
  fi
  if [ ! -x "$AUDIO_BRIDGE_DIR/Start-Audio-Bridge.command" ]; then
    echo "WARNING: touch audio bridge launcher missing: $AUDIO_BRIDGE_DIR/Start-Audio-Bridge.command"
    return 0
  fi
  echo "Starting touch audio bridge on port $AUDIO_BRIDGE_PORT..."
  if command -v tmux >/dev/null 2>&1; then
    tmux kill-session -t mira-touch-audio >/dev/null 2>&1 || true
    tmux new-session -d -s mira-touch-audio "cd '$AUDIO_BRIDGE_DIR' && ./Start-Audio-Bridge.command --port '$AUDIO_BRIDGE_PORT'"
  else
    (cd "$AUDIO_BRIDGE_DIR" && ./Start-Audio-Bridge.command --port "$AUDIO_BRIDGE_PORT" >/dev/null 2>&1 &)
  fi
}

ensure_celebration_console() {
  if probe_url "$CELEBRATION_LOCAL_URL"; then
    if probe_url "$CELEBRATION_URL"; then
      echo "Celebration page: already running at $CELEBRATION_URL"
      return 0
    fi
    echo "Celebration page is local-only; restarting it for LAN access..."
  fi

  if port_in_use "$CELEBRATION_PORT"; then
    if stop_stale_celebration_on_port; then
      echo "Stale celebration console cleared; continuing startup."
    else
      echo "WARNING: celebration port $CELEBRATION_PORT is in use, but $CELEBRATION_LOCAL_URL is not reachable."
      lsof -nP -iTCP:"$CELEBRATION_PORT" -sTCP:LISTEN || true
      return 0
    fi
  fi

  echo "Starting celebration page server on port $CELEBRATION_PORT..."
  "$PYTHON_BIN" "$SHENZHEN_CONSOLE_DIR/shenzhen_console.py" \
    --host "$CELEBRATION_HOST" \
    --port "$CELEBRATION_PORT" \
    --board-host "$BOARD_HOST" \
    --board-port "$BOARD_PORT" \
    --board-user "$BOARD_USER" &
  CELEBRATION_PID=$!
  wait_for_url "$CELEBRATION_LOCAL_URL" "Celebration page" "$CELEBRATION_PID"
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

post_book_follow_start() {
  "$PYTHON_BIN" - "$CONSOLE_LOCAL_URL" "$MIRA_BOOK_FOLLOW_RECEIVER_PORT" "$BOOK_FOLLOW_BASE_URL" <<'PY'
import json
import sys
import urllib.request

console_url = sys.argv[1].rstrip("/")
receiver_port = int(sys.argv[2])
base_url = sys.argv[3]
payload = {
    "baseUrl": base_url,
    "receiverHost": "0.0.0.0",
    "receiverPort": receiver_port,
    "pollInterval": "0.12",
    "trackingUpdateMs": "220",
    "tabletopTrackingUpdateMs": "160",
    "sceneAllowedDetectors": "book_cover_color",
    "trackingAllowedDetectors": "book_cover_color",
    "touchHandArmMinConfidence": "2.0",
    "handAvoidMinConfidence": "2.0",
    "hueMin": "14",
    "hueMax": "43",
    "minSaturation": "70",
    "minColorRatio": "0.22",
}
request = urllib.request.Request(
    f"{console_url}/api/book-follow/start",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=5) as response:
    body = json.loads(response.read().decode("utf-8") or "{}")
    status = body.get("status", {})
    print(
        "Book-follow: "
        f"ok={body.get('ok')} reason={body.get('reason')} "
        f"running={status.get('running')} receiver={status.get('receiverUrl')}"
    )
PY
}

post_book_follow_stop() {
  "$PYTHON_BIN" - "$CONSOLE_LOCAL_URL" <<'PY'
import sys
import urllib.request

console_url = sys.argv[1].rstrip("/")
request = urllib.request.Request(f"{console_url}/api/book-follow/stop", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(request, timeout=5) as response:
    response.read()
PY
}

bootstrap_book_follow_board() {
  case "$(printf '%s' "$BOOTSTRAP_BOOK_FOLLOW" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on)
      if [ -x "$BOOK_FOLLOW_BOOTSTRAP_SCRIPT" ]; then
        echo "Bootstrapping book-follow board services..."
        bash "$BOOK_FOLLOW_BOOTSTRAP_SCRIPT" || echo "WARNING: book-follow board bootstrap failed; console is still running."
      else
        echo "WARNING: book-follow bootstrap script is missing or not executable: $BOOK_FOLLOW_BOOTSTRAP_SCRIPT"
      fi
      ;;
    *)
      echo "Book-follow board bootstrap disabled."
      ;;
  esac
}

start_book_follow_stack() {
  case "$(printf '%s' "$AUTO_START_BOOK_FOLLOW" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on)
      if [ "$(printf '%s' "$RESTART_BOOK_FOLLOW" | tr '[:upper:]' '[:lower:]')" = "1" ] || \
         [ "$(printf '%s' "$RESTART_BOOK_FOLLOW" | tr '[:upper:]' '[:lower:]')" = "true" ] || \
         [ "$(printf '%s' "$RESTART_BOOK_FOLLOW" | tr '[:upper:]' '[:lower:]')" = "yes" ] || \
         [ "$(printf '%s' "$RESTART_BOOK_FOLLOW" | tr '[:upper:]' '[:lower:]')" = "on" ]; then
        echo "Restarting book-follow vision stack with current config..."
        post_book_follow_stop || true
      else
        echo "Starting book-follow vision stack..."
      fi
      post_book_follow_start || echo "WARNING: book-follow auto-start failed; use the console button to retry."
      ;;
    *)
      echo "Book-follow auto-start disabled."
      ;;
  esac
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
  stop_pid "$CELEBRATION_PID" "Mira Light celebration page"
  stop_pid "$CONSOLE_PID" "Mira Light unified director console"
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
require_file "$CONSOLE_DIR/answer_demo.py"
require_file "$CONSOLE_DIR/voice_motion_demos.py"
require_file "$CONSOLE_DIR/scene_registry.json"
require_file "$CONSOLE_DIR/web/index.html"
require_file "$SHENZHEN_CONSOLE_DIR/shenzhen_console.py"
require_file "$SHENZHEN_CONSOLE_DIR/scene_registry.json"
require_file "$SHENZHEN_CONSOLE_DIR/web/08_celebrate/index.html"
require_file "$CAMERA_CONSOLE_DIR/camera_console.py"
require_file "$ROOT_DIR/Chrome-Camera-Anime/digua_remote_render_pipeline.py"

if [ ! -f "$MIRA_ANSWER_AUDIO_PATH" ]; then
  echo "WARNING: answer demo audio was not found: $MIRA_ANSWER_AUDIO_PATH"
  echo "         Set MIRA_ANSWER_AUDIO_PATH to a valid mp3/wav/aiff before using 演示答."
fi

if [ ! -d "$MIRA_SHENZHEN_SCRIPTS_DIR" ]; then
  echo "ERROR: Shenzhen motion scripts directory was not found."
  echo "Expected: $MIRA_SHENZHEN_SCRIPTS_DIR"
  read -r -p "Press Enter to close this window..."
  exit 1
fi

stop_legacy_camera_console
restart_printer_bridge_if_needed
ensure_touch_audio_bridge
ensure_celebration_console

if probe_url "$CONSOLE_LOCAL_URL"; then
  if probe_answer_demo_endpoint; then
    echo "Unified director console: already running at $CONSOLE_URL"
    echo "Answer demo endpoint: OK"
    bootstrap_book_follow_board
    start_book_follow_stack
    open_console_url
    CELEBRATION_PID=""
    read -r -p "Press Enter to close this window..."
    exit 0
  fi
  echo "Unified director console is running, but it does not expose /api/play-answer-demo."
  echo "Restarting it so the latest answer-demo code is loaded..."
  if stop_stale_console_on_port; then
    echo "Old unified console cleared; continuing startup."
  else
    echo "ERROR: could not restart the existing listener on port $CONSOLE_PORT."
    lsof -nP -iTCP:"$CONSOLE_PORT" -sTCP:LISTEN || true
    read -r -p "Press Enter to close this window..."
    exit 1
  fi
fi

if port_in_use "$CONSOLE_PORT"; then
  if stop_stale_console_on_port; then
    echo "Stale unified console cleared; continuing startup."
  else
    echo "ERROR: console port $CONSOLE_PORT is in use, but $CONSOLE_URL is not reachable."
    echo "The listener is not this repo's unified console, so it was not stopped automatically."
    lsof -nP -iTCP:"$CONSOLE_PORT" -sTCP:LISTEN || true
    read -r -p "Press Enter to close this window..."
    exit 1
  fi
fi

echo "Starting unified director console server..."
"$PYTHON_BIN" "$CONSOLE_DIR/shenzhen_console.py" \
  --host "$CONSOLE_HOST" \
  --port "$CONSOLE_PORT" \
  --board-host "$BOARD_HOST" \
  --board-port "$BOARD_PORT" \
  --board-user "$BOARD_USER" &
CONSOLE_PID=$!

wait_for_url "$CONSOLE_LOCAL_URL" "Unified director console" "$CONSOLE_PID"

bootstrap_book_follow_board
start_book_follow_stack

open_console_url

echo
echo "Leave this Terminal window open while using the unified director console."
echo "Preview buttons do not touch the device; run buttons, servo controls, and touch controls send SSH commands to the board."
echo "Press Ctrl-C here to stop the console."
echo
wait "$CONSOLE_PID"
