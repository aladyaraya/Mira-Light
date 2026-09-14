#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/config/mira-light-realtime.env"
mkdir -p "$ROOT_DIR/config"

if [ ! -f "$ENV_FILE" ]; then
  cp "$ROOT_DIR/config/mira-light-realtime.env.example" "$ENV_FILE"
fi

echo "== Configure Mira Light Cloud Claw =="
echo "Config: $ENV_FILE"
echo
read -r -p "Lingzhu AUTH AK: " AUTH_AK
read -r -p "Remote SSH password, optional: " REMOTE_PASSWORD

python3 - "$ENV_FILE" "$AUTH_AK" "$REMOTE_PASSWORD" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
updates = {
    "MIRA_LIGHT_CLAW_MODE": "cloud",
    "MIRA_LIGHT_REPLY_BACKEND": "lingzhu",
    "MIRA_LIGHT_LINGZHU_AUTO_TUNNEL": "1",
    "MIRA_LIGHT_LINGZHU_BASE_URL": "http://127.0.0.1:31879",
    "MIRA_LIGHT_LINGZHU_AGENT_ID": "main",
    "MIRA_LIGHT_LINGZHU_AUTH_AK": sys.argv[2],
}
if sys.argv[3]:
    updates["MIRA_LIGHT_LINGZHU_REMOTE_PASSWORD"] = sys.argv[3]

lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
seen = set()
out = []
for line in lines:
    stripped = line.strip()
    replaced = False
    for key, value in updates.items():
        if stripped.startswith(f"export {key}="):
            out.append(f'export {key}="{value}"')
            seen.add(key)
            replaced = True
            break
    if not replaced:
        out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f'export {key}="{value}"')
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

chmod 600 "$ENV_FILE"
echo "Cloud config saved."
