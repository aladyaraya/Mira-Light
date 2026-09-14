#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

openclaw_bin="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
imagesnap_bin="${IMAGESNAP_BIN:-$(command -v imagesnap || true)}"

if [[ -n "$openclaw_bin" && -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]]; then
  openclaw_config_path="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"
  if [[ -f "$openclaw_config_path" ]]; then
    gateway_token="$(
      node - "$openclaw_config_path" <<'NODE'
const fs = require("node:fs");

const configPath = process.argv[2];
const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
const token = config.gateway?.remote?.token ?? config.gateway?.auth?.token ?? "";
if (token) {
  process.stdout.write(String(token));
}
NODE
    )"
    if [[ -n "$gateway_token" ]]; then
      export OPENCLAW_GATEWAY_TOKEN="$gateway_token"
    fi
  fi
fi

run_openclaw() {
  if [[ -z "$openclaw_bin" ]]; then
    return 127
  fi
  if [[ -n "${OPENCLAW_GATEWAY_TOKEN:-}" ]]; then
    env OPENCLAW_GATEWAY_TOKEN="$OPENCLAW_GATEWAY_TOKEN" "$openclaw_bin" "$@"
    return
  fi
  "$openclaw_bin" "$@"
}

default_node_id="__OPENCLAW_MAC_NODE_ID__"
mac_camera_node_id="${OPENCLAW_MAC_NODE_ID:-${MAC_CAMERA_NODE_ID:-$default_node_id}}"
mac_camera_cache_dir="${OPENCLAW_MAC_CAMERA_CACHE_DIR:-$HOME/.openclaw/workspace/.cache/localmac-camera}"
mac_camera_backend="${MAC_CAMERA_BACKEND:-imagesnap}"
mac_camera_interval_sec="${MAC_CAMERA_INTERVAL_SEC:-3}"
mac_camera_change_threshold="${MAC_CAMERA_CHANGE_THRESHOLD:-0.18}"
mac_camera_heartbeat_sec="${MAC_CAMERA_HEARTBEAT_SEC:-60}"
mac_camera_delay_ms="${MAC_CAMERA_DELAY_MS:-350}"
mac_camera_retry_attempts="${MAC_CAMERA_RETRY_ATTEMPTS:-4}"
mac_camera_retry_sleep_sec="${MAC_CAMERA_RETRY_SLEEP_SEC:-5}"
ambient_bridge_url="${AMBIENT_BRIDGE_URL:-http://127.0.0.1:3301/v1/ambient/observe}"

latest_image_path="$mac_camera_cache_dir/latest.jpg"
latest_json_path="$mac_camera_cache_dir/latest.json"
state_json_path="$mac_camera_cache_dir/state.json"
loop_pid_path="$mac_camera_cache_dir/loop.pid"
loop_log_path="$mac_camera_cache_dir/loop.log"

ensure_cache_dir() {
  mkdir -p "$mac_camera_cache_dir"
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "missing file: $path" >&2
    exit 1
  fi
}

copy_media_output() {
  local command_output="$1"
  local media_path
  media_path="$(
    printf '%s\n' "$command_output" \
      | perl -pe 's/\e\[[0-9;?]*[[:alpha:]]//g; s/\r//g' \
      | sed -n 's/^MEDIA://p' \
      | tail -n1
  )"
  if [[ -z "$media_path" ]]; then
    echo "camera command did not return a MEDIA path" >&2
    printf '%s\n' "$command_output" >&2
    exit 1
  fi
  require_file "$media_path"
  cp "$media_path" "$latest_image_path"
}

read_state_field() {
  local field="$1"
  if [[ ! -f "$state_json_path" ]]; then
    return 0
  fi

  node - "$state_json_path" "$field" <<'NODE'
const fs = require("node:fs");
const [statePath, field] = process.argv.slice(2);
const state = JSON.parse(fs.readFileSync(statePath, "utf8"));
const value = state[field];
if (value === undefined || value === null) {
  process.exit(0);
}
process.stdout.write(String(value));
NODE
}

write_json_file() {
  local path="$1"
  local content="$2"
  printf '%s\n' "$content" > "$path"
}

is_transient_camera_snap_error() {
  local output="${1:-}"
  [[ "$output" == *"gateway closed"* ]] && return 0
  [[ "$output" == *"unknown node:"* ]] && return 0
  [[ "$output" == *"TIMEOUT"* ]] && return 0
  return 1
}

capture_with_imagesnap_json() {
  if [[ -z "$imagesnap_bin" ]]; then
    echo "imagesnap not found in PATH; set IMAGESNAP_BIN." >&2
    return 127
  fi

  local staged_path="$mac_camera_cache_dir/imagesnap-$(date -u +%Y%m%d-%H%M%S).jpg"
  local warmup_seconds
  warmup_seconds="$(awk "BEGIN { printf \"%.3f\", ${mac_camera_delay_ms} / 1000 }")"
  "$imagesnap_bin" -q -w "$warmup_seconds" "$staged_path" >/dev/null
  require_file "$staged_path"

  node - "$staged_path" <<'NODE'
const path = require("node:path");
const stagedPath = process.argv[2];
process.stdout.write(JSON.stringify({
  files: [
    {
      path: path.resolve(stagedPath),
    },
  ],
}));
NODE
}

refresh_mac_camera_node() {
  run_openclaw nodes camera list --node "$mac_camera_node_id" >/dev/null 2>&1 || true
}

capture_mac_camera_snap_json() {
  local attempt=1
  local output=""
  local rc=1

  if [[ "$mac_camera_backend" == "imagesnap" ]]; then
    capture_with_imagesnap_json
    return $?
  fi

  if [[ "$mac_camera_backend" != "auto" && "$mac_camera_backend" != "openclaw" ]]; then
    echo "unsupported MAC_CAMERA_BACKEND: $mac_camera_backend" >&2
    return 2
  fi

  if [[ -z "$openclaw_bin" ]]; then
    capture_with_imagesnap_json
    return $?
  fi

  while (( attempt <= mac_camera_retry_attempts )); do
    if output="$(run_openclaw nodes camera snap --node "$mac_camera_node_id" --facing front --delay-ms "$mac_camera_delay_ms" --json 2>&1)"; then
      printf '%s\n' "$output"
      return 0
    fi

    rc=$?
    if ! is_transient_camera_snap_error "$output" || (( attempt == mac_camera_retry_attempts )); then
      if [[ -n "$imagesnap_bin" ]]; then
        printf '%s\n' "$output" >&2
        capture_with_imagesnap_json
        return $?
      fi
      printf '%s\n' "$output" >&2
      return "$rc"
    fi

    printf 'transient camera snap failure on attempt %s/%s; retrying\n' "$attempt" "$mac_camera_retry_attempts" >&2
    refresh_mac_camera_node
    if [[ "$mac_camera_retry_sleep_sec" != "0" ]]; then
      sleep "$mac_camera_retry_sleep_sec"
    fi
    attempt=$((attempt + 1))
  done

  printf '%s\n' "$output" >&2
  return "$rc"
}
