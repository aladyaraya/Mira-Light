#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  /bin/bash "$ROOT_DIR/commands/Setup.command"
fi

export MIRA_LIGHT_CLAW_MODE=local
export MIRA_LIGHT_MIC_DEVICE="${MIRA_LIGHT_MIC_DEVICE:-MacBook Air麦克风}"
export MIRA_LIGHT_STT_PROFILE="${MIRA_LIGHT_STT_PROFILE:-fast}"
export MIRA_LIGHT_LATENCY_PRESET="${MIRA_LIGHT_LATENCY_PRESET:-low}"
export MIRA_LIGHT_TTS_MODE="${MIRA_LIGHT_TTS_MODE:-warm_gentleman}"

exec "$ROOT_DIR/scripts/run_mira_realtime_voice_interaction.sh" \
  enter-vad \
  --device "$MIRA_LIGHT_MIC_DEVICE" \
  --profile "$MIRA_LIGHT_STT_PROFILE" \
  --latency-preset "$MIRA_LIGHT_LATENCY_PRESET" \
  --no-startup-warmup \
  --no-trigger
