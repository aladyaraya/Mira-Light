#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
STABLE_ENTRY="$ROOT_DIR/Start-Mira-Light-Unified-Director-Console.command"

if [ ! -x "$STABLE_ENTRY" ]; then
  echo "ERROR: stable unified console entry was not found or is not executable."
  echo "Expected: $STABLE_ENTRY"
  read -r -p "Press Enter to close this window..."
  exit 1
fi

export MIRA_UNIFIED_CONSOLE_PORT="${MIRA_UNIFIED_CONSOLE_PORT:-8789}"
export MIRA_UNIFIED_CAMERA_START_WATCH="${MIRA_UNIFIED_CAMERA_START_WATCH:-0}"
export MIRA_BOOK_FOLLOW_AUTO_START="${MIRA_BOOK_FOLLOW_AUTO_START:-0}"
export MIRA_BOOK_FOLLOW_BOOTSTRAP_BOARD="${MIRA_BOOK_FOLLOW_BOOTSTRAP_BOARD:-0}"
export MIRA_BOOK_FOLLOW_RESTART_ON_START="${MIRA_BOOK_FOLLOW_RESTART_ON_START:-0}"
export MIRA_UNIFIED_STOP_LEGACY_CAMERA_CONSOLE="${MIRA_UNIFIED_STOP_LEGACY_CAMERA_CONSOLE:-0}"
export MIRA_BOOK_FOLLOW_RECEIVER_PORT="${MIRA_BOOK_FOLLOW_RECEIVER_PORT:-18089}"

echo "== Mira Light Unified Director Console: 8789 Debug =="
echo "This launcher keeps the 8790 stable console untouched."
echo "Console:      http://127.0.0.1:${MIRA_UNIFIED_CONSOLE_PORT}/"
echo "Camera watch: ${MIRA_UNIFIED_CAMERA_START_WATCH} (0 avoids /dev/video0 conflicts)"
echo "Book auto:    ${MIRA_BOOK_FOLLOW_AUTO_START}"
echo "Book port:    ${MIRA_BOOK_FOLLOW_RECEIVER_PORT}"
echo

exec "$STABLE_ENTRY"
