#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Missing .venv. Running setup first..."
  /bin/bash "$ROOT_DIR/Setup-Mira-Light-Voice.command"
fi

echo "== Test Mira Light Bridge =="
echo "Folder: $ROOT_DIR"
echo

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

