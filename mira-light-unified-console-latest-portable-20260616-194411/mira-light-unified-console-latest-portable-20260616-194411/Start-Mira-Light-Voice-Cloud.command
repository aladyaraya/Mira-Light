#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
export MIRA_LIGHT_CLAW_MODE=cloud
exec "$ROOT_DIR/Start-Mira-Light-Voice.command"
