#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  /bin/bash "$ROOT_DIR/commands/Setup.command"
fi

echo "== Test Mira Light Bridge =="
/bin/bash "$ROOT_DIR/scripts/ensure_mira_light_bridge.sh"

"$ROOT_DIR/.venv/bin/python" - <<'PY'
import json
import os
import urllib.request

host = os.environ.get("MIRA_LIGHT_BRIDGE_HOST", "127.0.0.1")
port = os.environ.get("MIRA_LIGHT_BRIDGE_PORT", "9783")
base = os.environ.get("MIRA_LIGHT_BRIDGE_URL", f"http://{host}:{port}").rstrip("/")
token = os.environ.get("MIRA_LIGHT_BRIDGE_TOKEN", "")
headers = {"Authorization": f"Bearer {token}"} if token else {}

req = urllib.request.Request(f"{base}/health", headers=headers, method="GET")
with urllib.request.urlopen(req, timeout=3) as response:
    body = response.read().decode("utf-8", errors="replace")

print(f"GET {base}/health -> {response.status}")
try:
    print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
except json.JSONDecodeError:
    print(body)
PY
