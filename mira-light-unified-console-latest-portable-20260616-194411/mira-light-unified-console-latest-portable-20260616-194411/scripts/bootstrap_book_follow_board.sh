#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

BOARD_HOST="${MIRA_SHENZHEN_BOARD_HOST:-192.168.0.183}"
BOARD_PORT="${MIRA_SHENZHEN_BOARD_PORT:-22}"
BOARD_USER="${MIRA_SHENZHEN_BOARD_USER:-root}"
BOARD_PASSWORD="${MIRA_SHENZHEN_BOARD_PASSWORD:-}"
BOARD_DIR="${MIRA_BOOK_FOLLOW_BOARD_DIR:-/home/sunrise/Desktop/mira-book-follow-camera}"
RECEIVER_PORT="${MIRA_BOOK_FOLLOW_RECEIVER_PORT:-18000}"
CAMERA_INDEX="${MIRA_BOOK_FOLLOW_CAMERA_INDEX:-0}"
SERVO_PORT="${MIRA_BOOK_FOLLOW_SERVO_PORT:-9527}"
SERVO_DEVICE="${MIRA_BOOK_FOLLOW_SERVO_DEVICE:-/dev/ttyS3}"
MAC_HOST="${MIRA_BOOK_FOLLOW_MAC_HOST:-}"
BOARD_WAIT_SECONDS="${MIRA_BOOK_FOLLOW_BOARD_WAIT_SECONDS:-45}"
RESTART_SERVO_BRIDGE="${MIRA_BOOK_FOLLOW_RESTART_SERVO_BRIDGE:-1}"
RESTART_CAMERA_SENDER="${MIRA_BOOK_FOLLOW_RESTART_CAMERA_SENDER:-1}"
STOP_CAMERA_SENDER="${MIRA_BOOK_FOLLOW_STOP_CAMERA_SENDER:-0}"
VERIFY_SECONDS="${MIRA_BOOK_FOLLOW_VERIFY_SECONDS:-3}"

CAM_SENDER_SRC="$ROOT_DIR/board-camera-streaming/cam_sender.py"
SERVO_BRIDGE_SRC="$ROOT_DIR/scripts/rdk_bus_servo_tcp_bridge.py"

detect_mac_host() {
  if [ -n "$MAC_HOST" ]; then
    printf '%s\n' "$MAC_HOST"
    return 0
  fi
  ipconfig getifaddr en0 2>/dev/null && return 0
  ipconfig getifaddr en1 2>/dev/null && return 0
  route -n get "$BOARD_HOST" 2>/dev/null | awk '/interface:/{print $2; exit}' | while read -r iface; do
    ipconfig getifaddr "$iface" 2>/dev/null || true
  done | awk 'NF{print; exit}'
}

require_file() {
  if [ ! -f "$1" ]; then
    echo "ERROR: required file not found: $1" >&2
    exit 1
  fi
}

ssh_base() {
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/mira-book-follow-known-hosts -o ConnectTimeout=6 -p "$BOARD_PORT" "$BOARD_USER@$BOARD_HOST" "$@"
}

scp_base() {
  scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/mira-book-follow-known-hosts -o ConnectTimeout=6 -P "$BOARD_PORT" "$@"
}

ssh_board() {
  if [ -n "$BOARD_PASSWORD" ] && command -v sshpass >/dev/null 2>&1; then
    SSHPASS="$BOARD_PASSWORD" sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/mira-book-follow-known-hosts -o ConnectTimeout=6 -p "$BOARD_PORT" "$BOARD_USER@$BOARD_HOST" "$@"
  else
    ssh_base "$@"
  fi
}

scp_board() {
  if [ -n "$BOARD_PASSWORD" ] && command -v sshpass >/dev/null 2>&1; then
    SSHPASS="$BOARD_PASSWORD" sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/mira-book-follow-known-hosts -o ConnectTimeout=6 -P "$BOARD_PORT" "$@"
  else
    scp_base "$@"
  fi
}

require_file "$CAM_SENDER_SRC"
require_file "$SERVO_BRIDGE_SRC"

MAC_HOST="$(detect_mac_host)"
if [ -z "$MAC_HOST" ]; then
  echo "ERROR: could not detect this Mac's LAN IP. Set MIRA_BOOK_FOLLOW_MAC_HOST." >&2
  exit 1
fi

echo "== Mira book-follow board bootstrap =="
echo "Board:    ${BOARD_USER}@${BOARD_HOST}:${BOARD_PORT}"
echo "Mac:      ${MAC_HOST}:${RECEIVER_PORT}"
echo "Servo:    ${BOARD_HOST}:${SERVO_PORT} -> ${SERVO_DEVICE}"
echo "Camera:   /dev/video${CAMERA_INDEX}"
echo "BoardDir: ${BOARD_DIR}"

wait_for_board() {
  local deadline=$((SECONDS + BOARD_WAIT_SECONDS))
  while [ "$SECONDS" -le "$deadline" ]; do
    if ssh_board "true" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

if ! wait_for_board; then
  echo "ERROR: board is not reachable by SSH after ${BOARD_WAIT_SECONDS}s: ${BOARD_HOST}" >&2
  echo "Check board power/network/IP, then rerun this script; it is safe to rerun." >&2
  exit 1
fi

ssh_board "mkdir -p '$BOARD_DIR'"
scp_board "$CAM_SENDER_SRC" "$BOARD_USER@$BOARD_HOST:$BOARD_DIR/cam_sender.py"
scp_board "$SERVO_BRIDGE_SRC" "$BOARD_USER@$BOARD_HOST:$BOARD_DIR/rdk_bus_servo_tcp_bridge.py"

ssh_board "MAC_HOST='$MAC_HOST' RECEIVER_PORT='$RECEIVER_PORT' CAMERA_INDEX='$CAMERA_INDEX' SERVO_PORT='$SERVO_PORT' SERVO_DEVICE='$SERVO_DEVICE' BOARD_DIR='$BOARD_DIR' RESTART_SERVO_BRIDGE='$RESTART_SERVO_BRIDGE' RESTART_CAMERA_SENDER='$RESTART_CAMERA_SENDER' STOP_CAMERA_SENDER='$STOP_CAMERA_SENDER' VERIFY_SECONDS='$VERIFY_SECONDS' bash -s" <<'REMOTE'
set -euo pipefail

cd "$BOARD_DIR"

camera_device="/dev/video${CAMERA_INDEX}"
if [ ! -e "$camera_device" ]; then
  echo "ERROR: camera device is missing on board: $camera_device" >&2
  exit 1
fi

python3 - <<'PY'
try:
    import cv2  # noqa: F401
except Exception as exc:
    raise SystemExit(f"ERROR: python3 cv2 is not available on board: {exc}")
PY

is_truthy() {
  case "$(printf '%s' "${1:-0}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

if is_truthy "$RESTART_SERVO_BRIDGE" || ! ss -lntp 2>/dev/null | grep -q ":${SERVO_PORT} "; then
  old_bridge="$(cat rdk_bus_servo_tcp_bridge.pid 2>/dev/null || true)"
  if [ -n "$old_bridge" ]; then kill "$old_bridge" 2>/dev/null || true; fi
  pkill -f "rdk_bus_servo_tcp_bridge.py .*--port ${SERVO_PORT}" 2>/dev/null || true
  nohup python3 "$BOARD_DIR/rdk_bus_servo_tcp_bridge.py" \
    --host 0.0.0.0 \
    --port "$SERVO_PORT" \
    --device "$SERVO_DEVICE" \
    > "$BOARD_DIR/rdk_bus_servo_tcp_bridge.log" 2>&1 < /dev/null &
  echo $! > rdk_bus_servo_tcp_bridge.pid
  sleep 1
fi

if is_truthy "$RESTART_CAMERA_SENDER" || is_truthy "$STOP_CAMERA_SENDER"; then
  old_sender="$(cat cam_sender.pid 2>/dev/null || true)"
  if [ -n "$old_sender" ]; then kill "$old_sender" 2>/dev/null || true; fi
  pkill -f "cam_sender.py .* ${RECEIVER_PORT} ${CAMERA_INDEX}" 2>/dev/null || true
fi

if ! is_truthy "$STOP_CAMERA_SENDER" && { is_truthy "$RESTART_CAMERA_SENDER" || ! pgrep -f "cam_sender.py .* ${RECEIVER_PORT} ${CAMERA_INDEX}" >/dev/null 2>&1; }; then
  nohup python3 "$BOARD_DIR/cam_sender.py" "$MAC_HOST" "$RECEIVER_PORT" "$CAMERA_INDEX" \
    > "$BOARD_DIR/cam_sender.log" 2>&1 < /dev/null &
  echo $! > cam_sender.pid
fi
sleep "$VERIFY_SECONDS"

if ! is_truthy "$STOP_CAMERA_SENDER" && ! kill -0 "$(cat cam_sender.pid)" 2>/dev/null; then
  echo "ERROR: cam_sender exited early." >&2
  tail -40 "$BOARD_DIR/cam_sender.log" >&2 || true
  exit 1
fi

if ! ss -lntp 2>/dev/null | grep -q ":${SERVO_PORT} "; then
  echo "ERROR: servo bridge is not listening on ${SERVO_PORT}." >&2
  tail -40 "$BOARD_DIR/rdk_bus_servo_tcp_bridge.log" >&2 || true
  exit 1
fi

echo "-- processes --"
ps -ef | grep -E "[c]am_sender.py|[r]dk_bus_servo_tcp_bridge.py" || true
echo "-- servo port --"
ss -lntp 2>/dev/null | grep ":${SERVO_PORT} " || true
echo "-- sender log --"
tail -8 "$BOARD_DIR/cam_sender.log" 2>/dev/null || true
echo "-- servo bridge log --"
tail -8 "$BOARD_DIR/rdk_bus_servo_tcp_bridge.log" 2>/dev/null || true
REMOTE

if command -v nc >/dev/null 2>&1; then
  nc -vz -w 2 "$BOARD_HOST" "$SERVO_PORT"
fi

echo "Book-follow board bootstrap: OK"
