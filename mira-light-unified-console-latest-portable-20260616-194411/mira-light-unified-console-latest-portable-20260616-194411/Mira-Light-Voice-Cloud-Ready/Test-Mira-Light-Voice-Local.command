#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  /bin/bash "$ROOT_DIR/Setup-Mira-Light-Voice.command"
fi

export MIRA_LIGHT_CLAW_MODE=local
export MIRA_LIGHT_OPENCLAW_DIRECT_FIRST=1

.venv/bin/python - <<'PY'
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from mira_realtime_voice_interaction import send_reply

args = argparse.Namespace(
    reply_backend="openclaw-agent",
    reply_agent="mira-voice-spark",
    reply_thinking="off",
    timeout=45,
    lingzhu_base_url="",
    lingzhu_auth_ak="",
    lingzhu_agent_id="main",
    lingzhu_user_id="",
)
start = time.perf_counter()
text, meta, backend = send_reply(
    [{"role": "user", "content": "连通性测试：请只回复“本地可用”。"}],
    session=None,
    args=args,
    additional_user_ids=[],
)
print("ok=true")
print("backend=" + backend)
print("provider=" + str(meta.get("provider")))
print("model=" + str(meta.get("model")))
print("elapsed=%.2f" % (time.perf_counter() - start))
print("text=" + text)
PY
