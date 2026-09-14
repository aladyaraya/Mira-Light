#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT}/.venv/bin/python"
PACK_ENV_FILE="${ROOT}/config/mira-light-realtime.env"
LOCAL_ENV_FILE="${HOME}/.openclaw/mira-light-realtime.env"

if [[ -f "${PACK_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${PACK_ENV_FILE}"
elif [[ -f "${LOCAL_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${LOCAL_ENV_FILE}"
fi

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:${PATH}"

BRIDGE_HOST="${MIRA_LIGHT_BRIDGE_HOST:-127.0.0.1}"
BRIDGE_PORT="${MIRA_LIGHT_BRIDGE_PORT:-9783}"
LOCAL_BRIDGE_URL="http://${BRIDGE_HOST}:${BRIDGE_PORT}"
BRIDGE_URL="${MIRA_LIGHT_BRIDGE_URL:-${LOCAL_BRIDGE_URL}}"
LAMP_BASE_URL="${MIRA_LIGHT_LAMP_BASE_URL:-}"
BRIDGE_CONFIG="${MIRA_LIGHT_BRIDGE_CONFIG:-${ROOT}/tools/mira_light_bridge/bridge_config.json}"
BRIDGE_LOG_DIR="${MIRA_LIGHT_BRIDGE_LOG_DIR:-${ROOT}/runtime/logs}"
BRIDGE_PID_FILE="${MIRA_LIGHT_BRIDGE_PID_FILE:-${ROOT}/runtime/mira-light-bridge.pid}"

mkdir -p "${BRIDGE_LOG_DIR}" "$(dirname "${BRIDGE_PID_FILE}")"

probe_url() {
  "${PYTHON_BIN}" - "$1" "${MIRA_LIGHT_BRIDGE_TOKEN:-}" <<'PY'
import sys
import urllib.request

url = sys.argv[1]
token = sys.argv[2]
headers = {"Authorization": f"Bearer {token}"} if token else {}
try:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=1.0) as response:
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
      echo "${label}: OK"
      return 0
    fi
    if [[ -n "${pid}" ]] && ! kill -0 "${pid}" >/dev/null 2>&1; then
      echo "ERROR: ${label} exited before it became ready." >&2
      tail -80 "${BRIDGE_LOG_DIR}/mira-light-bridge.log" 2>/dev/null || true
      return 1
    fi
    sleep 0.25
  done

  echo "ERROR: ${label} did not become ready at ${url}" >&2
  tail -80 "${BRIDGE_LOG_DIR}/mira-light-bridge.log" 2>/dev/null || true
  return 1
}

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing ${PYTHON_BIN}. Run ./commands/Setup.command first." >&2
  exit 1
fi

if [[ ! -f "${ROOT}/tools/mira_light_bridge/bridge_server.py" ]]; then
  echo "Missing bridge server: ${ROOT}/tools/mira_light_bridge/bridge_server.py" >&2
  exit 1
fi

if [[ "${BRIDGE_URL}" != "${LOCAL_BRIDGE_URL}" ]]; then
  if probe_url "${BRIDGE_URL}/health"; then
    echo "[bridge] external bridge healthy at ${BRIDGE_URL}"
    exit 0
  fi
  echo "[bridge] external bridge not reachable at ${BRIDGE_URL}/health" >&2
  echo "[bridge] set MIRA_LIGHT_BRIDGE_URL empty/default to auto-start local bridge." >&2
  exit 1
fi

if probe_url "${BRIDGE_URL}/health"; then
  echo "[bridge] already healthy at ${BRIDGE_URL}"
  exit 0
fi

if [[ -f "${BRIDGE_PID_FILE}" ]]; then
  old_pid="$(cat "${BRIDGE_PID_FILE}" 2>/dev/null || true)"
  if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" >/dev/null 2>&1; then
    echo "[bridge] stale/unhealthy process found pid=${old_pid}; stopping it..."
    kill "${old_pid}" >/dev/null 2>&1 || true
    sleep 0.5
  fi
fi

if port_in_use "${BRIDGE_PORT}"; then
  echo "ERROR: bridge port ${BRIDGE_PORT} is in use, but ${BRIDGE_URL}/health is not reachable." >&2
  echo "Close the process on that port or set MIRA_LIGHT_BRIDGE_PORT to another port." >&2
  exit 1
fi

cmd=(
  "${PYTHON_BIN}"
  "${ROOT}/tools/mira_light_bridge/bridge_server.py"
  --config "${BRIDGE_CONFIG}"
  --host "${BRIDGE_HOST}"
  --port "${BRIDGE_PORT}"
)
if [[ -n "${LAMP_BASE_URL}" ]]; then
  cmd+=(--base-url "${LAMP_BASE_URL}")
fi
if [[ "${MIRA_LIGHT_BRIDGE_DRY_RUN:-0}" == "1" ]]; then
  cmd+=(--dry-run)
fi

echo "[bridge] starting at ${BRIDGE_URL}"
echo "[bridge] log ${BRIDGE_LOG_DIR}/mira-light-bridge.log"
nohup "${cmd[@]}" >"${BRIDGE_LOG_DIR}/mira-light-bridge.log" 2>&1 &
bridge_pid=$!
echo "${bridge_pid}" >"${BRIDGE_PID_FILE}"

wait_for_url "${BRIDGE_URL}/health" "Mira Light bridge" "${bridge_pid}"
