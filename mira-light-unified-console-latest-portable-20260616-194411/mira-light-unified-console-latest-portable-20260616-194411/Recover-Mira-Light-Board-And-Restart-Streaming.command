#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONSOLE_DIR="$ROOT_DIR/mira-light-unified-director-console"
BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/bootstrap_book_follow_board.sh"

CONSOLE_HOST="${MIRA_UNIFIED_CONSOLE_HOST:-127.0.0.1}"
CONSOLE_PORT="${MIRA_UNIFIED_CONSOLE_PORT:-8789}"
CONSOLE_URL="http://${CONSOLE_HOST}:${CONSOLE_PORT}"
BOARD_HOST="${MIRA_SHENZHEN_BOARD_HOST:-192.168.0.183}"
BOARD_PORT="${MIRA_SHENZHEN_BOARD_PORT:-22}"
BOARD_USER="${MIRA_SHENZHEN_BOARD_USER:-root}"
RECEIVER_PORT="${MIRA_BOOK_FOLLOW_RECEIVER_PORT:-18000}"

if [ -z "${MIRA_SHENZHEN_BOARD_PASSWORD+x}" ]; then
  export MIRA_SHENZHEN_BOARD_PASSWORD=""
fi

export MIRA_BOOK_FOLLOW_RECEIVER_PORT="$RECEIVER_PORT"
export MIRA_BOOK_FOLLOW_BOOTSTRAP_BOARD="${MIRA_BOOK_FOLLOW_BOOTSTRAP_BOARD:-1}"
export MIRA_BOOK_FOLLOW_AUTO_START="${MIRA_BOOK_FOLLOW_AUTO_START:-1}"
export MIRA_BOOK_FOLLOW_RESTART_ON_START="${MIRA_BOOK_FOLLOW_RESTART_ON_START:-1}"
export MIRA_BOOK_FOLLOW_RESTART_SERVO_BRIDGE="${MIRA_BOOK_FOLLOW_RESTART_SERVO_BRIDGE:-1}"
export MIRA_BOOK_FOLLOW_RESTART_CAMERA_SENDER="${MIRA_BOOK_FOLLOW_RESTART_CAMERA_SENDER:-1}"
export MIRA_UNIFIED_CAMERA_START_WATCH="${MIRA_UNIFIED_CAMERA_START_WATCH:-1}"

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

wait_for_url() {
  local url="$1"
  local label="$2"
  for _ in {1..80}; do
    if probe_url "$url"; then
      echo "$label: OK"
      return 0
    fi
    sleep 0.25
  done
  echo "ERROR: $label did not become ready at $url" >&2
  return 1
}

post_json() {
  local path="$1"
  local payload="$2"
  python3 - "$CONSOLE_URL" "$path" "$payload" <<'PY'
import json
import sys
import urllib.request

console_url, path, raw_payload = sys.argv[1], sys.argv[2], sys.argv[3]
request = urllib.request.Request(
    f"{console_url.rstrip('/')}{path}",
    data=raw_payload.encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=8) as response:
    body = response.read().decode("utf-8") or "{}"
    try:
        print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(body)
PY
}

summarize_status() {
  python3 - "$CONSOLE_URL" <<'PY'
import json
import sys
import urllib.request

console_url = sys.argv[1].rstrip("/")

def read(path):
    with urllib.request.urlopen(f"{console_url}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8") or "{}")

camera = read("/api/camera/latest")
book = read("/api/book-follow/status")
touch = read("/api/touch/status")

latest = camera.get("latestFrame") or {}
tracking = (book.get("latestEvent") or {}).get("tracking") or {}
touch_status = touch.get("status") or {}

print("== Recovery summary ==")
print(f"Console:      {console_url}/")
print(f"Camera watch: {camera.get('running')} frame={latest.get('filename') or '-'} size={latest.get('sizeBytes') or '-'} error={(camera.get('lastError') or {}).get('message') or '-'}")
print(f"Book-follow:  running={book.get('running')} pid={book.get('pid')} target={tracking.get('target_class') or '-'} confidence={tracking.get('confidence') or '-'}")
print(f"Touch:        active={touch_status.get('active')} autostart={touch_status.get('enabled')}")
PY
}

echo "== Mira recovery: board reachability + streaming =="
echo "Console: ${CONSOLE_URL}/"
echo "Board:   ${BOARD_USER}@${BOARD_HOST}:${BOARD_PORT}"
echo "Receiver port: ${RECEIVER_PORT}"
echo

if ! probe_url "$CONSOLE_URL/"; then
  echo "Starting unified console in background..."
  mkdir -p "$ROOT_DIR/runtime"
  MIRA_SHENZHEN_BOARD_PASSWORD="${MIRA_SHENZHEN_BOARD_PASSWORD:-}" \
  nohup python3 "$CONSOLE_DIR/shenzhen_console.py" \
    --host "$CONSOLE_HOST" \
    --port "$CONSOLE_PORT" \
    --board-host "$BOARD_HOST" \
    --board-port "$BOARD_PORT" \
    --board-user "$BOARD_USER" \
    > "$ROOT_DIR/runtime/unified-console-${CONSOLE_PORT}.log" 2>&1 &
fi

wait_for_url "$CONSOLE_URL/" "Unified console"

echo
echo "Restarting Mac-side book-follow receiver..."
post_json "/api/book-follow/stop" "{}" >/dev/null || true
post_json "/api/book-follow/start" "{\"baseUrl\":\"tcp://${BOARD_HOST}:9527\",\"receiverHost\":\"0.0.0.0\",\"receiverPort\":${RECEIVER_PORT}}" >/dev/null
echo "Book-follow receiver: OK"

echo
echo "Recovering board services and restarting push stream..."
bash "$BOOTSTRAP_SCRIPT"

echo
echo "Starting camera watch..."
post_json "/api/camera/watch/start" "{\"intervalSeconds\":10}" >/dev/null || true

echo
summarize_status

echo
echo "Recovery command finished. It is safe to run this again whenever the board or stream is flaky."
