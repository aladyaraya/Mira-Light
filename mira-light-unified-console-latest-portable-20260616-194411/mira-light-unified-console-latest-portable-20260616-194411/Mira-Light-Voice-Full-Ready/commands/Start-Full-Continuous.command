#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export MIRA_LIGHT_CAPTURE_MODE=continuous
exec "$ROOT_DIR/Start-Full.command"
