#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"
export MIRA_LIGHT_CLAW_MODE=cloud
if [[ "${MIRA_LIGHT_FORCE_BUILTIN_MIC:-1}" == "1" ]]; then
  export MIRA_LIGHT_MIC_DEVICE="MacBook Air麦克风"
else
  export MIRA_LIGHT_MIC_DEVICE="${MIRA_LIGHT_MIC_DEVICE:-MacBook Air麦克风}"
fi
export MIRA_LIGHT_STT_PROFILE="${MIRA_LIGHT_STT_PROFILE:-fast}"
export MIRA_LIGHT_LATENCY_PRESET="${MIRA_LIGHT_LATENCY_PRESET:-low}"
export MIRA_LIGHT_TTS_MODE="${MIRA_LIGHT_TTS_MODE:-warm_gentleman}"
export MIRA_LIGHT_POST_TTS_COOLDOWN_SECONDS="${MIRA_LIGHT_POST_TTS_COOLDOWN_SECONDS:-0.25}"
export MIRA_LIGHT_CAPTURE_MODE="${MIRA_LIGHT_CAPTURE_MODE:-enter-vad}"

echo "== Mira Light Voice Chat =="
echo "Folder: $ROOT_DIR"
echo "Mic:    $MIRA_LIGHT_MIC_DEVICE"
echo "Listen: $MIRA_LIGHT_CAPTURE_MODE"
echo "Mode:   cloud chat + TTS, actions disabled"
echo

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Missing .venv. Running setup first..."
  /bin/bash "$ROOT_DIR/commands/Setup.command"
fi

exec "$ROOT_DIR/scripts/run_mira_realtime_voice_interaction.sh" \
  "$MIRA_LIGHT_CAPTURE_MODE" \
  --device "$MIRA_LIGHT_MIC_DEVICE" \
  --profile "$MIRA_LIGHT_STT_PROFILE" \
  --latency-preset "$MIRA_LIGHT_LATENCY_PRESET" \
  --vad-start-ms 80 \
  --vad-end-ms 1200 \
  --vad-min-rms 0.002 \
  --vad-speech-ratio 1.4 \
  --no-startup-warmup \
  --no-trigger
