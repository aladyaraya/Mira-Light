#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw was not found in PATH."
  echo "Cloud mode can still work. Install OpenClaw first if you want local mode."
  exit 1
fi

/bin/bash "$ROOT_DIR/setup/register_mira_voice_spark.sh" "$ROOT_DIR"

mkdir -p "$HOME/.openclaw/agents/main/agent" "$HOME/.openclaw/agents/mira-voice-spark/agent"
if [ -f "$ROOT_DIR/config/private/openclaw-agent-models.json" ]; then
  cp "$ROOT_DIR/config/private/openclaw-agent-models.json" "$HOME/.openclaw/agents/main/agent/models.json"
  cp "$ROOT_DIR/config/private/openclaw-agent-models.json" "$HOME/.openclaw/agents/mira-voice-spark/agent/models.json"
  chmod 600 "$HOME/.openclaw/agents/main/agent/models.json" "$HOME/.openclaw/agents/mira-voice-spark/agent/models.json"
fi

echo "mira-voice-spark local agent installed."
openclaw agents list | grep mira-voice-spark || true
