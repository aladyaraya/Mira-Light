#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$(pwd)}"
workspace="$repo_root/tools/openclaw_agents/mira_voice_spark_workspace"
agent_dir="${OPENCLAW_MIRA_VOICE_SPARK_AGENT_DIR:-$HOME/.openclaw/agents/mira-voice-spark/agent}"
model="${OPENCLAW_MIRA_VOICE_SPARK_MODEL:-newapi/gpt-5.4}"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw command not found. Install/configure OpenClaw first." >&2
  exit 1
fi

if [ ! -d "$workspace" ]; then
  echo "Missing Mira voice spark workspace: $workspace" >&2
  exit 1
fi

mkdir -p "$agent_dir"

openclaw agents add mira-voice-spark \
  --workspace "$workspace" \
  --agent-dir "$agent_dir" \
  --model "$model" \
  --non-interactive

echo "Registered mira-voice-spark"
echo "Workspace: $workspace"
echo "Agent dir: $agent_dir"
echo "Model: $model"

