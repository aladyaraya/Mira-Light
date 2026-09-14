#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

echo "== Setup Mira Light Voice =="
echo "Python: $PYTHON_BIN"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements.txt

if command -v npm >/dev/null 2>&1; then
  if ! command -v node-edge-tts >/dev/null 2>&1; then
    npm install -g node-edge-tts || true
  fi
fi

mkdir -p "$HOME/.local/bin"
cp bin/speaker-preferred-tts-play "$HOME/.local/bin/speaker-preferred-tts-play"
cp bin/speaker-beosound-tts-play "$HOME/.local/bin/speaker-beosound-tts-play"
chmod +x "$HOME/.local/bin/speaker-preferred-tts-play" "$HOME/.local/bin/speaker-beosound-tts-play"

if [ ! -f "config/mira-light-realtime.env" ]; then
  cp config/mira-light-realtime.env.example config/mira-light-realtime.env
fi

if command -v openclaw >/dev/null 2>&1; then
  echo "Registering mira-voice-spark agent for optional local mode..."
  /bin/bash "$ROOT_DIR/setup/register_mira_voice_spark.sh" "$ROOT_DIR" || true

  if [ -f "$ROOT_DIR/config/private/openclaw-agent-models.json" ]; then
    mkdir -p "$HOME/.openclaw/agents/main/agent" "$HOME/.openclaw/agents/mira-voice-spark/agent"
    cp "$ROOT_DIR/config/private/openclaw-agent-models.json" "$HOME/.openclaw/agents/main/agent/models.json"
    cp "$ROOT_DIR/config/private/openclaw-agent-models.json" "$HOME/.openclaw/agents/mira-voice-spark/agent/models.json"
    chmod 600 "$HOME/.openclaw/agents/main/agent/models.json" "$HOME/.openclaw/agents/mira-voice-spark/agent/models.json"
  fi
fi

echo
echo "Setup complete."
echo "Next: run ./Configure-Mira-Light-Voice-Cloud.command to add the cloud AK."
