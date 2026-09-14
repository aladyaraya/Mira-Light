#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  /bin/bash "$ROOT_DIR/commands/Setup.command"
fi

if [ -f "$ROOT_DIR/config/mira-light-realtime.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/config/mira-light-realtime.env"
  set +a
fi

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"
export MIRA_LIGHT_CLAW_MODE=cloud

echo "== Test Cloud Tunnel =="
/bin/bash "$ROOT_DIR/scripts/ensure_mira_lingzhu_tunnel.sh"

echo
echo "== Test Cloud Chat =="
.venv/bin/python - <<'PY'
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from mira_lingzhu_client import send_via_lingzhu_messages

start = time.perf_counter()
text, meta = send_via_lingzhu_messages(
    [{"role": "user", "content": "连通性测试：请只回复“云端可用”。"}],
    base_url=os.environ.get("MIRA_LIGHT_LINGZHU_BASE_URL", "http://127.0.0.1:31879"),
    auth_ak=os.environ.get("MIRA_LIGHT_LINGZHU_AUTH_AK", ""),
    agent_id=os.environ.get("MIRA_LIGHT_LINGZHU_AGENT_ID", "main"),
    user_id="mira-light-full-ready-test",
    session_id="mira-light-full-ready-test",
    additional_user_ids="",
    timeout_seconds=45,
)
print("ok=true")
print("provider=" + str(meta.get("provider")))
print("model=" + str(meta.get("model")))
print("elapsed=%.2f" % (time.perf_counter() - start))
print("text=" + text)
PY
