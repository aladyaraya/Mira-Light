#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
exec "$ROOT_DIR/Start-Mira-Light-Latest-Console.command"
