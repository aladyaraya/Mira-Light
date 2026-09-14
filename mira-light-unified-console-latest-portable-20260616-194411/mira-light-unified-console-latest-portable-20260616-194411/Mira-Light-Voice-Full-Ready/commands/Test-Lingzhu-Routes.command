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

/bin/bash "$ROOT_DIR/scripts/ensure_mira_lingzhu_tunnel.sh"

.venv/bin/python - <<'PY'
import json
import os
import urllib.error
import urllib.request

base = os.environ.get("MIRA_LIGHT_LINGZHU_BASE_URL", "http://127.0.0.1:31879").rstrip("/")
ak = os.environ.get("MIRA_LIGHT_LINGZHU_AUTH_AK", "")
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ak}",
}

def request(method, path, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"{method} {path} -> {resp.status}")
            print(body[:600])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"{method} {path} -> {exc.code}")
        print(body[:600])

print(f"base={base}")
print(f"ak_present={bool(ak)} ak_length={len(ak)}")
request("GET", "/v1/health")
request("GET", "/metis/agent/api/health")
request("POST", "/v1/chat", {"agent_id": "main", "user_id": "probe", "message_id": "probe-001", "message": [{"role": "user", "type": "text", "text": "ping"}]})
request("POST", "/metis/agent/api/sse", {"agent_id": "main", "user_id": "probe", "message_id": "probe-001", "message": [{"role": "user", "type": "text", "text": "ping"}]})
PY
