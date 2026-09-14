#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

if [ -f "$ROOT_DIR/config/mira-light-realtime.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/config/mira-light-realtime.env"
  set +a
fi
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

if [ ! -x ".venv/bin/python" ]; then
  /bin/bash "$ROOT_DIR/Setup-Mira-Light-Voice.command"
fi

/bin/bash "$ROOT_DIR/scripts/ensure_mira_lingzhu_tunnel.sh"

.venv/bin/python - <<'PY'
import json
import os
import urllib.error
import urllib.request

base = os.environ.get("MIRA_LIGHT_LINGZHU_BASE_URL", "http://127.0.0.1:31879").rstrip("/")
ak = os.environ.get("MIRA_LIGHT_LINGZHU_AUTH_AK", "")


def request(method: str, path: str, payload: dict | None = None) -> None:
    headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if ak:
        headers["Authorization"] = f"Bearer {ak}"
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"{method} {path} -> {response.status}")
            print(body[:500])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"{method} {path} -> {exc.code}")
        print(body[:500])
    except Exception as exc:
        print(f"{method} {path} -> ERROR {exc!r}")


message = [{"role": "user", "type": "text", "text": "ping"}]
common = {
    "agent_id": os.environ.get("MIRA_LIGHT_LINGZHU_AGENT_ID", "main"),
    "user_id": "probe",
    "session_id": "probe",
    "message_id": "probe-001",
    "additional_user_ids": [],
    "disable_default_additional_user_ids": True,
    "message": message,
    "query": "user: ping",
}

print(f"base={base}")
print(f"ak_present={bool(ak)} ak_length={len(ak)}")
request("GET", "/v1/health")
request("GET", "/metis/agent/api/health")
request("POST", "/v1/chat", common)
request("POST", "/metis/agent/api/sse", common)
PY
