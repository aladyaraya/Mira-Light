#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${OPENCLAW_PRINTER_BRIDGE_ENV:-$HOME/.openclaw-printer-bridge.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  umask 077
  cat > "$ENV_FILE" <<EOF
export OPENCLAW_PRINTER_BRIDGE_TOKEN="$TOKEN"
EOF
fi

source "$ENV_FILE"

exec python3 "$SCRIPT_DIR/bridge_server.py"
