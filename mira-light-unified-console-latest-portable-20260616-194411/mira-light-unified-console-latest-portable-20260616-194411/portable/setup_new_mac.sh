#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Mira Light latest portable setup =="
echo "Root: $ROOT_DIR"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required. Install Python 3 first."
  exit 1
fi

if command -v brew >/dev/null 2>&1; then
  echo "Checking Homebrew tools..."
  missing=()
  for tool in sshpass expect ffmpeg tmux portaudio; do
    if ! brew list "$tool" >/dev/null 2>&1; then
      missing+=("$tool")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "Installing: ${missing[*]}"
    brew install "${missing[@]}"
  else
    echo "Homebrew tools: OK"
  fi
else
  echo "WARNING: Homebrew was not found. Install sshpass, expect, ffmpeg, tmux, and portaudio manually if checks fail."
fi

if [ ! -d ".venv" ]; then
  echo "Creating .venv..."
  python3 -m venv .venv
fi

echo "Installing Python requirements..."
".venv/bin/python3" -m pip install --upgrade pip
".venv/bin/python3" -m pip install -r requirements.txt

if [ ! -f "portable/unified-console.env" ]; then
  echo "Creating portable/unified-console.env from example..."
  cp "portable/unified-console.env.example" "portable/unified-console.env"
  chmod 600 "portable/unified-console.env"
fi

if command -v swiftc >/dev/null 2>&1 && [ -f "mira-light-shenzhen-console/scripts/mac_audio_helper.swift" ]; then
  mkdir -p "mira-light-shenzhen-console/runtime/mac-audio"
  echo "Compiling Mac celebration audio helper..."
  swiftc "mira-light-shenzhen-console/scripts/mac_audio_helper.swift" \
    -o "mira-light-shenzhen-console/runtime/mac-audio/mac_audio_helper" || true
fi

chmod +x \
  Start-Mira-Light-Latest-Console.command \
  Start-Mira-Light-Unified-Director-Console.command \
  Start-Mira-Light-Unified-Director-Console-Keyboard.command \
  Build-Mira-Light-8790-Portable-Package.command \
  Build-Mira-Light-Latest-Portable-Package.command \
  portable/check_new_mac_prereqs.sh \
  scripts/package_unified_console_portable.sh

echo
"portable/check_new_mac_prereqs.sh" || true
echo
echo "Setup finished."
echo "Recommended: double-click Start-Mira-Light-Latest-Console.command to launch the latest keyboard-enabled unified console (8791)."
echo "Compatibility: Start-Mira-Light-Unified-Director-Console.command still launches the classic 8790 console."
