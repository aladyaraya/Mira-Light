#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

export MIRA_UNIFIED_WEB_ROOT="${MIRA_UNIFIED_WEB_ROOT:-$ROOT_DIR/mira-light-unified-director-console-keyboard/web}"
export MIRA_UNIFIED_CONSOLE_PORT="${MIRA_UNIFIED_CONSOLE_PORT:-8791}"

exec bash "$ROOT_DIR/Start-Mira-Light-Unified-Director-Console.command"
