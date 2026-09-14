#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT}/.venv/bin/python"
LOCAL_ENV_FILE="${HOME}/.openclaw/mira-light-realtime.env"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing ${PYTHON_BIN}. Create the repo venv first." >&2
  exit 1
fi

if [[ -f "${LOCAL_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${LOCAL_ENV_FILE}"
fi

# Keep Homebrew's modern Node ahead of HarmonyOS command-line tools after any
# local env file is sourced. OpenClaw needs Node flags older bundled Node builds
# do not understand.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:${PATH}"

CLAW_MODE="${MIRA_LIGHT_CLAW_MODE:-local}"
case "${CLAW_MODE}" in
  local)
    export MIRA_LIGHT_REPLY_BACKEND="openclaw-agent"
    export MIRA_LIGHT_REPLY_AGENT="${MIRA_LIGHT_REPLY_AGENT:-mira-voice-spark}"
    export MIRA_LIGHT_REPLY_THINKING="${MIRA_LIGHT_REPLY_THINKING:-off}"
    export MIRA_LIGHT_OPENCLAW_DIRECT_FIRST="${MIRA_LIGHT_OPENCLAW_DIRECT_FIRST:-1}"
    export MIRA_LIGHT_LINGZHU_AUTO_TUNNEL=0
    ;;
  cloud)
    export MIRA_LIGHT_REPLY_BACKEND="lingzhu"
    export MIRA_LIGHT_REPLY_AGENT="${MIRA_LIGHT_REPLY_AGENT:-mira-voice-spark}"
    export MIRA_LIGHT_REPLY_THINKING="${MIRA_LIGHT_REPLY_THINKING:-off}"
    export MIRA_LIGHT_OPENCLAW_DIRECT_FIRST=0
    export MIRA_LIGHT_LINGZHU_AUTO_TUNNEL="${MIRA_LIGHT_LINGZHU_AUTO_TUNNEL:-1}"
    export MIRA_LIGHT_LINGZHU_BASE_URL="${MIRA_LIGHT_LINGZHU_BASE_URL:-http://127.0.0.1:31879}"
    export MIRA_LIGHT_LINGZHU_AGENT_ID="${MIRA_LIGHT_LINGZHU_AGENT_ID:-main}"
    ;;
  auto)
    export MIRA_LIGHT_REPLY_AGENT="${MIRA_LIGHT_REPLY_AGENT:-mira-voice-spark}"
    if [[ -n "${MIRA_LIGHT_LINGZHU_BASE_URL:-}" ]]; then
      export MIRA_LIGHT_REPLY_BACKEND="lingzhu"
      export MIRA_LIGHT_OPENCLAW_DIRECT_FIRST=0
      export MIRA_LIGHT_LINGZHU_AUTO_TUNNEL="${MIRA_LIGHT_LINGZHU_AUTO_TUNNEL:-1}"
    else
      export MIRA_LIGHT_REPLY_BACKEND="openclaw-agent"
      export MIRA_LIGHT_OPENCLAW_DIRECT_FIRST="${MIRA_LIGHT_OPENCLAW_DIRECT_FIRST:-1}"
      export MIRA_LIGHT_LINGZHU_AUTO_TUNNEL=0
    fi
    ;;
  *)
    echo "Invalid MIRA_LIGHT_CLAW_MODE=${CLAW_MODE}; expected local, cloud, or auto." >&2
    exit 2
    ;;
esac
export MIRA_LIGHT_CLAW_MODE="${CLAW_MODE}"

if [[ "${MIRA_LIGHT_LINGZHU_AUTO_TUNNEL:-0}" == "1" ]]; then
  /bin/bash "${ROOT}/scripts/ensure_mira_lingzhu_tunnel.sh"
fi

if [[ $# -gt 0 ]]; then
  case "$1" in
    continuous|enter-vad|ptt|fixed)
      set -- --mode "$1" "${@:2}"
      ;;
  esac
fi

exec "${PYTHON_BIN}" "${ROOT}/scripts/mira_realtime_voice_interaction.py" "$@"
