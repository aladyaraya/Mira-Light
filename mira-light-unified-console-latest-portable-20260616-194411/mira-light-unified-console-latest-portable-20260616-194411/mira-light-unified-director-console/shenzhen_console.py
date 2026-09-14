#!/usr/bin/env python3
"""Unified local web console for Shenzhen demo, board camera, and touch controls."""

from __future__ import annotations

import argparse
import base64
import hashlib
import copy
import errno
import json
import mimetypes
import os
from pathlib import Path
try:
    import pty
except Exception:  # pragma: no cover - Windows has no termios-backed pty.
    pty = None
import re
import select
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib import error as url_error
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


CONSOLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CONSOLE_DIR.parent
SOURCE_DEMO_ROOT = Path("/Users/thomasjwang/Documents/GitHub/Mira-Light/Motions_Shenzhen/demo_fixed_protocol_v2")
REPO_LOCAL_DEMO_ROOT = REPO_ROOT / "Motions_Shenzhen" / "demo_fixed_protocol_v2"
SOURCE_SCRIPTS_DIR = SOURCE_DEMO_ROOT / "scripts"
REPO_LOCAL_SCRIPTS_DIR = REPO_LOCAL_DEMO_ROOT / "scripts"
SCRIPTS_DIR = Path(
    os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR")
    or (REPO_LOCAL_SCRIPTS_DIR if REPO_LOCAL_SCRIPTS_DIR.is_dir() else SOURCE_SCRIPTS_DIR)
).expanduser().resolve()
DEMO_ROOT = SCRIPTS_DIR.parent
WEB_ROOT = Path(os.environ.get("MIRA_UNIFIED_WEB_ROOT", CONSOLE_DIR / "web")).expanduser().resolve()
REGISTRY_PATH = CONSOLE_DIR / "scene_registry.json"
CELEBRATION_CONSOLE_DIR = REPO_ROOT / "mira-light-shenzhen-console"
CELEBRATION_CONSOLE_SCRIPT = CELEBRATION_CONSOLE_DIR / "shenzhen_console.py"
CELEBRATION_CONSOLE_LOG = REPO_ROOT / "tmp" / "shenzhen-console-8777.log"
CELEBRATION_CONSOLE_PID = REPO_ROOT / "tmp" / "shenzhen-console-8777.pid"
CELEBRATION_CONSOLE_HOST = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
CELEBRATION_CONSOLE_PORT = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
CELEBRATION_LOCAL_PAGE_URL = f"http://127.0.0.1:{CELEBRATION_CONSOLE_PORT}/08_celebrate/index.html"
CAMERA_CONSOLE_DIR = REPO_ROOT / "mira-light-camera-console"
if str(CAMERA_CONSOLE_DIR) not in sys.path:
    sys.path.insert(0, str(CAMERA_CONSOLE_DIR))

import camera_console as camera_console_module  # noqa: E402
from show_orchestrator import BOOK_PROFILES, SHOW_STATES_BY_STEP, ResourceConflict, ResourceManager, write_json_atomic  # noqa: E402

CameraSampler = camera_console_module.CameraSampler
digua_remote_render_pipeline = camera_console_module.digua_remote_render_pipeline

LOCAL_CAPTURE_DIR = Path(
    os.environ.get("MIRA_SHENZHEN_CAPTURE_DIR", REPO_ROOT / "tmp" / "mira-light-board-camera")
).expanduser().resolve()
REPO_DIGUA_RENDER_SCRIPT = REPO_ROOT / "Chrome-Camera-Anime" / "digua_remote_render_pipeline.py"
SOURCE_DIGUA_RENDER_SCRIPT = (
    Path("/Users/thomasjwang/Documents/GitHub/Javis-Hackathon")
    / "exports"
    / "macbook-camera-print-deploy-pack-20260329"
    / "source"
    / "current"
    / "openclaw-chrome-camera-anime"
    / "runtime"
    / "digua_remote_render_pipeline.py"
)
JAVIS_DIGUA_RENDER_SCRIPT = Path(
    os.environ.get("MIRA_SHENZHEN_DIGUA_RENDER_SCRIPT")
    or (REPO_DIGUA_RENDER_SCRIPT if REPO_DIGUA_RENDER_SCRIPT.is_file() else SOURCE_DIGUA_RENDER_SCRIPT)
).expanduser().resolve()
DIGUA_OUTPUT_DIR = Path(
    os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR", CONSOLE_DIR / "runtime" / "digua-console-output")
).expanduser().resolve()
SHOW_RUNTIME_DIR = Path(os.environ.get("MIRA_SHOW_RUNTIME_DIR", REPO_ROOT / "runtime" / "show")).expanduser().resolve()
SHOW_PHOTO_DIR = SHOW_RUNTIME_DIR / "photos"
SHOW_RENDER_DIR = SHOW_RUNTIME_DIR / "renders"
ROKID_RENDER_SCRIPT = REPO_ROOT / "Chrome-Camera-Anime" / "rokid_render_pipeline.py"
PRINTER_BRIDGE_URL = os.environ.get("OPENCLAW_PRINTER_BRIDGE_URL", "http://127.0.0.1:9771").rstrip("/")
SHOW_PRINT_MEDIA = os.environ.get("MIRA_SHOW_PRINT_MEDIA", "4x6.Fullbleed")
SHOW_LATEST_FRAME_PRINT_PROMPT = os.environ.get(
    "MIRA_SHOW_LATEST_FRAME_PRINT_PROMPT",
    (
        "温暖明亮的手绘动画电影场景，保留真实路演现场和产品展示的核心内容；"
        "场景内容是：我们正在路演，并在展示产品；画面中面前的人要保持微笑，"
        "展现出自然开心的笑脸，并且笑出牙齿。画面适合6寸照片打印。"
    ),
)
DEFAULT_HOST = "192.168.0.183"
DEFAULT_PORT = 22
DEFAULT_USER = "lckfb"
DEFAULT_TIMEOUT_SECONDS = 180.0
PASSWORD_ENV = "MIRA_SHENZHEN_BOARD_PASSWORD"
CAMERA_PASSWORD_ENV = "MIRA_CAMERA_BOARD_PASSWORD"
DEFAULT_UNIFIED_PORT = 8790
DEFAULT_REMOTE_DESKTOP_DIR = "/home/sunrise/Desktop"
REMOTE_DESKTOP_DIR = os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR", DEFAULT_REMOTE_DESKTOP_DIR).rstrip("/")
LEGACY_REMOTE_DESKTOP_DIRS = ["/home/lckfb/Desktop", "/home/sunrise/Desktop"]
LEGACY_REMOTE_DESKTOP_DIR = "/home/sunrise/Desktop"  # kept for backward compat
REMOTE_DESKTOP_ENV_VAR = "MIRA_REMOTE_DESKTOP_DIR"
REMOTE_LED_ENABLED = os.environ.get("MIRA_SHENZHEN_REMOTE_LED_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
REMOTE_TOUCH_ENABLED = os.environ.get("MIRA_SHENZHEN_REMOTE_TOUCH_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
DEFAULT_CAMERA_INTERVAL_SECONDS = 10.0
DEFAULT_CAMERA_DATA_DIR = Path.home() / "Documents" / "Mira-Light-Camera-Console"
BOOK_FOLLOW_DEFAULT_RUNTIME_DIR = REPO_ROOT / "runtime" / "book-follow-console"
BOOK_FOLLOW_DEFAULT_BASE_URL = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL") or os.environ.get("MIRA_LIGHT_BASE_URL", "tcp://192.168.0.183:9527")
BOOK_FOLLOW_DEFAULT_RECEIVER_PORT = int(os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT", "18000"))
BOOK_FOLLOW_DEFAULT_RECEIVER_HOST = os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_HOST", "0.0.0.0")
NARRATION_AUDIO_PATH = Path(
    os.environ.get(
        "MIRA_NARRATION_AUDIO_PATH",
        REPO_ROOT
        / "Mira-Light-Voice-Cloud-Ready"
        / "docs"
        / "0525"
        / "MiniMax_2026-05-25_13_21_00_Comedian_no-watermark.mp3",
    )
).expanduser().resolve()
ANSWER_AUDIO_PATH = Path(os.environ.get("MIRA_ANSWER_AUDIO_PATH", str(NARRATION_AUDIO_PATH))).expanduser().resolve()
ANSWER_AUDIO_DELAY_SECONDS = 0.40
BOOK_FOLLOW_SCRIPT = REPO_ROOT / "scripts" / "run_mira_light_vision_stack.sh"
TEACH_BOARD_SCRIPT_PATH = REPO_ROOT / "scripts" / "teach_motion_board.py"
TEACH_REMOTE_SCRIPT = f"{REMOTE_DESKTOP_DIR}/teach_motion_board.py"
TEACH_REMOTE_DIR = f"{REMOTE_DESKTOP_DIR}/teach_motions"
TEACH_REMOTE_PID = f"{TEACH_REMOTE_DIR}/unified_teach.pid"
TEACH_REMOTE_RAW = f"{TEACH_REMOTE_DIR}/unified_latest_raw.json"
TEACH_REMOTE_LOG = f"{TEACH_REMOTE_DIR}/unified_teach.log"
TEACH_RECORD_DURATION_SECONDS = 300
TEACH_RECORD_SAMPLE_MS = 40
TEACH_RECORD_TORQUE_MODE = "off"
TEACH_PLAY_SPEED_SCALE = 0.5
BOOK_FOLLOW_DEFAULTS = {
    "runtimeDir": str(BOOK_FOLLOW_DEFAULT_RUNTIME_DIR),
    "receiverHost": BOOK_FOLLOW_DEFAULT_RECEIVER_HOST,
    "receiverPort": BOOK_FOLLOW_DEFAULT_RECEIVER_PORT,
    "baseUrl": BOOK_FOLLOW_DEFAULT_BASE_URL,
    "pollInterval": "0.12",
    "trackingUpdateMs": "220",
    "tabletopTrackingUpdateMs": "160",
    "sceneAllowedDetectors": "book_cover_color",
    "trackingAllowedDetectors": "book_cover_color",
    "touchHandArmMinConfidence": "2.0",
    "handAvoidMinConfidence": "2.0",
    "roiTop": "0.16",
    "roiBottom": "0.96",
    "roiLeft": "0.08",
    "roiRight": "0.92",
    "maxAreaRatio": "0.65",
    "hueMin": "14",
    "hueMax": "43",
    "minSaturation": "70",
    "minValue": "80",
    "minColorRatio": "0.22",
    "minAspectRatio": "0.35",
    "maxAspectRatio": "4.2",
    "minRectangularity": "0.46",
    "minSolidity": "0.72",
    "minEdgeRatio": "0.012",
    "maxEdgeRatio": "0.24",
    "minInnerEdgeRatio": "0.012",
    "maxCornerCount": "6",
}
TOUCH_SERVICE_NAME = "mira-touch.service"
TOUCH_MAPPING_PATH = f"{REMOTE_DESKTOP_DIR}/touch_mapping.json"
TOUCH_AUDIO_PORTABLE_BRIDGE_DIR = REPO_ROOT / "portable" / "support" / "touch-audio-bridge"
TOUCH_AUDIO_LEGACY_BRIDGE_DIR = REPO_ROOT / "tmp" / "mira-touch-audio-bridge-20260524" / "audio-bridge"
TOUCH_AUDIO_BRIDGE_DIR = (
    TOUCH_AUDIO_PORTABLE_BRIDGE_DIR
    if TOUCH_AUDIO_PORTABLE_BRIDGE_DIR.is_dir()
    else TOUCH_AUDIO_LEGACY_BRIDGE_DIR
).resolve()
TOUCH_AUDIO_BRIDGE_PORT = int(os.environ.get("MIRA_TOUCH_AUDIO_BRIDGE_PORT", "9783"))
TOUCH_AUDIO_HEALTH_URL = f"http://127.0.0.1:{TOUCH_AUDIO_BRIDGE_PORT}/health"
TOUCH_AUDIO_TRIGGER_URL = f"http://127.0.0.1:{TOUCH_AUDIO_BRIDGE_PORT}/v1/mira-light/trigger"
TOUCH_AUDIO_SELF_TEST_ASSET = os.environ.get(
    "MIRA_TOUCH_AUDIO_SELF_TEST_ASSET",
    "speech/cute_robot_comfort.aiff",
)
TOUCH_SENSITIVITY_PRESETS = {
    "stable": {
        "label": "稳定",
        "description": "最低误触，适合桌面光线和电容噪声不稳定时使用。",
        "values": {
            "lamp_thr": 245,
            "thr_hysteresis": 12,
            "release_debounce_ms": 650,
            "post_release_cooldown_ms": 3000,
        },
    },
    "balanced": {
        "label": "均衡",
        "description": "推荐日常档，比稳定档更容易触发，仍保留防抖。",
        "values": {
            "lamp_thr": 250,
            "thr_hysteresis": 12,
            "release_debounce_ms": 560,
            "post_release_cooldown_ms": 2500,
        },
    },
    "sensitive": {
        "label": "高灵敏",
        "description": "当前现场验证档，轻触更容易触发；如果出现误触请退回均衡。",
        "values": {
            "lamp_thr": 255,
            "thr_hysteresis": 10,
            "release_debounce_ms": 420,
            "post_release_cooldown_ms": 900,
        },
    },
}
SSH_CONTROL_DIR = Path(os.environ.get("MIRA_SHENZHEN_SSH_CONTROL_DIR", "/tmp/mira-ssh"))
SSH_CONTROL_PERSIST_SECONDS = int(os.environ.get("MIRA_SHENZHEN_SSH_CONTROL_PERSIST_SECONDS", "600"))
SSH_CONNECT_RETRIES = int(os.environ.get("MIRA_SHENZHEN_SSH_CONNECT_RETRIES", "2"))
SSH_RETRY_DELAY_SECONDS = float(os.environ.get("MIRA_SHENZHEN_SSH_RETRY_DELAY_SECONDS", "0.15"))
BOARD_KEEPALIVE_INTERVAL_SECONDS = float(os.environ.get("MIRA_UNIFIED_BOARD_KEEPALIVE_SECONDS", "20"))
BOARD_KEEPALIVE_TIMEOUT_SECONDS = float(os.environ.get("MIRA_UNIFIED_BOARD_KEEPALIVE_TIMEOUT_SECONDS", "8"))
KEYCHAIN_SECRET_SERVICES = {
    "ARK_API_KEY": "mira-light-ark-api-key",
}
SSH_LOCK = Lock()
PROCESS_LOCK = Lock()
TOUCH_AUDIO_LOCK = Lock()
ACTIVE_PROCESSES: set[subprocess.Popen] = set()
PLINK_HOSTKEY_CACHE: dict[tuple[str, int, str], str] = {}
SERVO_MIN = 0
SERVO_MAX = 4095
MANUAL_SERVO_SPEEDS = (440, 320, 320, 440)
SERVO_SPEED_PRESETS = {
    "slow": {"label": "慢", "step": 12, "speeds": (180, 140, 140, 180)},
    "medium": {"label": "中", "step": 24, "speeds": (320, 240, 240, 320)},
    "fast": {"label": "快", "step": 48, "speeds": (520, 420, 420, 520)},
}
SERVO_HOLD_INTERVAL_SECONDS = {
    "slow": 0.10,
    "medium": 0.075,
    "fast": 0.055,
}
DEFAULT_SERVO_RECORD_DIR = Path(
    os.environ.get("MIRA_UNIFIED_SERVO_RECORD_DIR", REPO_ROOT / "runtime" / "servo-records")
).expanduser().resolve()
SERVO_POSITION_SCRIPT = f"""set -euo pipefail
echo '== read all servo positions =='
python3 {REMOTE_DESKTOP_DIR}/four_servo_control.py read-pos-all
"""
TOUCH_STATUS_SCRIPT = f"""set +e
export TERM=dumb
echo 'TOUCH_ACTIVE='$(systemctl is-active {TOUCH_SERVICE_NAME} 2>/dev/null || true)
echo 'TOUCH_ENABLED='$(systemctl is-enabled {TOUCH_SERVICE_NAME} 2>/dev/null || true)
echo 'TOUCH_PROCESS_BEGIN'
main_pid=$(systemctl show -p MainPID --value {TOUCH_SERVICE_NAME} 2>/dev/null || true)
if [ -n "$main_pid" ] && [ "$main_pid" != "0" ] && [ -r "/proc/$main_pid/cmdline" ]; then
  printf '%s ' "$main_pid"
  tr '\\0' ' ' < "/proc/$main_pid/cmdline"
  printf '\\n'
fi
echo 'TOUCH_PROCESS_END'
echo 'TOUCH_CONFIG_BEGIN'
python3 - <<'PY' 2>/dev/null || true
import json
from pathlib import Path
p = Path("{TOUCH_MAPPING_PATH}")
data = json.loads(p.read_text())
keys = [
    "version",
    "lamp_thr",
    "thr_hysteresis",
    "thr_min_clamp",
    "release_debounce_ms",
    "release_absence_ms",
    "post_release_cooldown_ms",
    "max_touch_duration_ms",
    "debug_raw",
    "_ui_sensitivity_preset",
    "_ui_sensitivity_label",
]
print(json.dumps({{key: data.get(key) for key in keys}}, ensure_ascii=False))
PY
echo 'TOUCH_CONFIG_END'
echo 'TOUCH_STATUS_BEGIN'
systemctl --no-pager --full status {TOUCH_SERVICE_NAME} 2>&1 | sed -n '1,18p'
echo 'TOUCH_STATUS_END'
echo 'TOUCH_LOG_BEGIN'
if [ -f /var/log/mira-touch.log ]; then
  tail -30 /var/log/mira-touch.log
else
  journalctl -u {TOUCH_SERVICE_NAME} --no-pager -n 25 2>&1
fi
echo 'TOUCH_LOG_END'
exit 0
"""
TOUCH_ACTION_COMMANDS = {
    "start": f"systemctl start {TOUCH_SERVICE_NAME}",
    "stop": f"systemctl stop {TOUCH_SERVICE_NAME}",
    "disable-autostart": f"systemctl disable {TOUCH_SERVICE_NAME}",
    "enable-autostart": f"systemctl enable {TOUCH_SERVICE_NAME}",
}
EMERGENCY_STOP_COMMANDS = [
    {
        "label": "stop known Mira motion scripts",
        "command": "\n".join(
            [
                "pkill -f '[s]ervo_.*\\.py' || true",
                "pkill -f '[f]our_servo_control.py' || true",
                "sleep 0.15",
            ]
        ),
    },
    {
        "label": "force return neutral pose",
        "command": f"python3 {REMOTE_DESKTOP_DIR}/four_servo_control.py pose 2048 2150 2048 2130 --speeds 280 180 180 280",
    },
    {
        "label": "warm neutral light",
        "command": f"python3 {REMOTE_DESKTOP_DIR}/send_uart3_led_cmd.py all 255 220 180 100",
    },
    {
        "label": "read all servo positions",
        "command": f"python3 {REMOTE_DESKTOP_DIR}/four_servo_control.py read-pos-all || true",
    },
]


def parse_servo_positions(stdout: str) -> dict[str, int]:
    positions: dict[str, int] = {}
    pattern = re.compile(r"Read ID\s*:\s*(\d+).*?Position\s*:\s*(\d+)", re.DOTALL)
    for servo_id, position in pattern.findall(stdout.replace("\r", "")):
        positions[servo_id] = int(position)
    return positions


def compact_remote_warning(result: dict) -> str | None:
    return_code = result.get("returnCode")
    if return_code == 0:
        return None
    text = str(result.get("stderr") or result.get("stdout") or f"Remote command exited {return_code}")
    for needle in (
        "timed out waiting for servo response header",
        "Timed out waiting for SSH response",
        "Timed out after",
    ):
        if needle in text:
            return needle
    first_line = next((line.strip() for line in text.replace("\r", "").splitlines() if line.strip()), "")
    if not first_line:
        return f"Remote command exited {return_code}"
    return first_line[:180]


def marker_value(stdout: str, name: str) -> str:
    prefix = f"{name}="
    for line in stdout.replace("\r", "").splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return "unknown"


def marker_block(stdout: str, name: str) -> str:
    begin = f"{name}_BEGIN"
    end = f"{name}_END"
    collecting = False
    lines: list[str] = []
    for line in stdout.replace("\r", "").splitlines():
        stripped = line.strip()
        if stripped == begin:
            collecting = True
            lines = []
            continue
        if stripped == end and collecting:
            return "\n".join(lines).strip()
        if collecting:
            lines.append(line)
    return ""


def render_touch_action_script(action: str) -> str:
    command = TOUCH_ACTION_COMMANDS.get(action)
    if command is None:
        raise ValueError(f"Unknown touch action: {action}")
    if not REMOTE_TOUCH_ENABLED:
        return f"set -euo pipefail\necho 'TOUCH_DISABLED=1'\necho 'Touch/capacitive control is disabled in this UART3 joint-only package.'\n"
    return f"set -euo pipefail\n{command}\n"


def touch_preset_payload(preset_id: str) -> dict:
    preset = TOUCH_SENSITIVITY_PRESETS.get(preset_id)
    if preset is None:
        raise ValueError(f"Unknown touch sensitivity preset: {preset_id}")
    return {
        "id": preset_id,
        "label": preset["label"],
        "description": preset["description"],
        "values": dict(preset["values"]),
    }


def identify_touch_sensitivity_preset(config: dict) -> str | None:
    for preset_id, preset in TOUCH_SENSITIVITY_PRESETS.items():
        values = preset["values"]
        if all(config.get(key) == value for key, value in values.items()):
            return preset_id
    return None


def render_touch_sensitivity_script(preset_id: str) -> str:
    preset = touch_preset_payload(preset_id)
    values_json = json.dumps(preset["values"], ensure_ascii=False, sort_keys=True)
    label = str(preset["label"])
    status_keys_json = json.dumps(
        [
            "version",
            "lamp_thr",
            "thr_hysteresis",
            "thr_min_clamp",
            "release_debounce_ms",
            "release_absence_ms",
            "post_release_cooldown_ms",
            "max_touch_duration_ms",
            "debug_raw",
            "_ui_sensitivity_preset",
            "_ui_sensitivity_label",
        ],
        sort_keys=True,
    )
    return f"""set -euo pipefail
mapping={shlex.quote(TOUCH_MAPPING_PATH)}
backup="$mapping.bak-sensitivity-$(date +%Y%m%d-%H%M%S)"
cp "$mapping" "$backup"
python3 - <<'PY'
import json
from pathlib import Path

p = Path({TOUCH_MAPPING_PATH!r})
updates = json.loads({values_json!r})
data = json.loads(p.read_text())
data.update(updates)
data["_ui_sensitivity_preset"] = {preset_id!r}
data["_ui_sensitivity_label"] = {label!r}
data["_ui_sensitivity_updated_at"] = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n")
print(json.dumps({{"updated": updates, "lamp_thr": data.get("lamp_thr")}}, ensure_ascii=False))
PY
systemctl restart {TOUCH_SERVICE_NAME}
echo "TOUCH_ACTIVE=$(systemctl is-active {TOUCH_SERVICE_NAME} 2>/dev/null || true)"
echo "TOUCH_ENABLED=$(systemctl is-enabled {TOUCH_SERVICE_NAME} 2>/dev/null || true)"
echo "TOUCH_BACKUP=$backup"
echo 'TOUCH_CONFIG_BEGIN'
python3 - <<'PY' 2>/dev/null || true
import json
from pathlib import Path
p = Path({TOUCH_MAPPING_PATH!r})
keys = json.loads({status_keys_json!r})
data = json.loads(p.read_text())
print(json.dumps({{key: data.get(key) for key in keys}}, ensure_ascii=False))
PY
echo 'TOUCH_CONFIG_END'
"""


def read_touch_status(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
) -> dict:
    started = time.monotonic()
    if not REMOTE_TOUCH_ENABLED:
        return {
            "ok": True,
            "service": TOUCH_SERVICE_NAME,
            "active": "disabled",
            "enabled": "disabled",
            "running": False,
            "autostart": False,
            "process": "",
            "config": {},
            "sensitivityPreset": "disabled",
            "firmware": {
                "mappingPath": TOUCH_MAPPING_PATH,
                "mappingVersion": None,
                "thresholdCommand": "",
            },
            "sensitivityPresets": {
                preset_id: touch_preset_payload(preset_id)
                for preset_id in TOUCH_SENSITIVITY_PRESETS
            },
            "statusSummary": "Touch/capacitive control is disabled in this UART3 joint-only package.",
            "logTail": "",
            "updatedAt": timestamp(),
            "durationSeconds": round(time.monotonic() - started, 3),
            "host": host,
            "port": port,
            "user": user,
            "returnCode": 0,
            "stderr": "",
        }
    try:
        result = run_remote_script(
            script=TOUCH_STATUS_SCRIPT,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 20.0),
        )
    except Exception as exc:  # noqa: BLE001 - status should stay visible even when SSH fails.
        result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}

    stdout = str(result.get("stdout") or "")
    active = marker_value(stdout, "TOUCH_ACTIVE")
    enabled = marker_value(stdout, "TOUCH_ENABLED")
    status_block = marker_block(stdout, "TOUCH_STATUS")
    process_block = marker_block(stdout, "TOUCH_PROCESS")
    config_block = marker_block(stdout, "TOUCH_CONFIG")
    log_block = marker_block(stdout, "TOUCH_LOG")
    config: dict = {}
    if config_block:
        try:
            parsed_config = json.loads(config_block)
            if isinstance(parsed_config, dict):
                config = parsed_config
        except json.JSONDecodeError:
            config = {"parseError": config_block}
    preset_id = identify_touch_sensitivity_preset(config) if config else None
    return {
        "ok": result.get("returnCode") == 0,
        "service": TOUCH_SERVICE_NAME,
        "active": active or "unknown",
        "enabled": enabled or "unknown",
        "running": active == "active",
        "autostart": enabled == "enabled",
        "process": process_block,
        "config": config,
        "sensitivityPreset": preset_id or config.get("_ui_sensitivity_preset") or "custom",
        "firmware": {
            "mappingPath": TOUCH_MAPPING_PATH,
            "mappingVersion": config.get("version"),
            "thresholdCommand": f"THR,{config.get('lamp_thr')}" if config.get("lamp_thr") is not None else "",
        },
        "sensitivityPresets": {
            preset_id: touch_preset_payload(preset_id)
            for preset_id in TOUCH_SENSITIVITY_PRESETS
        },
        "statusSummary": status_block,
        "logTail": log_block,
        "updatedAt": timestamp(),
        "durationSeconds": round(time.monotonic() - started, 3),
        "host": host,
        "port": port,
        "user": user,
        "returnCode": result.get("returnCode"),
        "stderr": result.get("stderr") or "",
    }


def run_touch_action(
    *,
    action: str,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
) -> dict:
    script = render_touch_action_script(action)
    started = time.monotonic()
    try:
        result = run_remote_script(
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 30.0),
        )
    except Exception as exc:  # noqa: BLE001 - return an actionable JSON error to the console.
        result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}
    result["durationSeconds"] = round(time.monotonic() - started, 3)
    result["script"] = script
    result["host"] = host
    result["port"] = port
    result["user"] = user
    status = read_touch_status(host=host, port=port, user=user, password=password, timeout_seconds=timeout_seconds)
    return {"action": action, "result": result, "status": status}


def run_touch_sensitivity_action(
    *,
    preset_id: str,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
) -> dict:
    script = render_touch_sensitivity_script(preset_id)
    started = time.monotonic()
    if not REMOTE_TOUCH_ENABLED:
        status = read_touch_status(host=host, port=port, user=user, password=password, timeout_seconds=timeout_seconds)
        result = {
            "returnCode": 0,
            "stdout": "Touch/capacitive sensitivity is disabled in this UART3 joint-only package.\n",
            "stderr": "",
            "durationSeconds": round(time.monotonic() - started, 3),
            "script": "echo touch sensitivity disabled",
            "host": host,
            "port": port,
            "user": user,
        }
        return {"action": "sensitivity", "preset": touch_preset_payload(preset_id), "result": result, "status": status}
    try:
        result = run_remote_script(
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 35.0),
        )
    except Exception as exc:  # noqa: BLE001
        result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}
    result["durationSeconds"] = round(time.monotonic() - started, 3)
    result["script"] = script
    result["host"] = host
    result["port"] = port
    result["user"] = user
    stdout = str(result.get("stdout") or "")
    config: dict = {}
    config_block = marker_block(stdout, "TOUCH_CONFIG")
    if config_block:
        try:
            parsed_config = json.loads(config_block)
            if isinstance(parsed_config, dict):
                config = parsed_config
        except json.JSONDecodeError:
            config = {"parseError": config_block}
    active = marker_value(stdout, "TOUCH_ACTIVE")
    enabled = marker_value(stdout, "TOUCH_ENABLED")
    preset = touch_preset_payload(preset_id)
    if not config:
        config = {
            **preset["values"],
            "_ui_sensitivity_preset": preset_id,
            "_ui_sensitivity_label": preset["label"],
        }
    status = {
        "ok": result.get("returnCode") == 0,
        "service": TOUCH_SERVICE_NAME,
        "active": active or "unknown",
        "enabled": enabled or "unknown",
        "running": active == "active",
        "autostart": enabled == "enabled",
        "process": "",
        "config": config,
        "sensitivityPreset": preset_id,
        "firmware": {
            "mappingPath": TOUCH_MAPPING_PATH,
            "mappingVersion": config.get("version"),
            "thresholdCommand": f"THR,{config.get('lamp_thr')}" if config.get("lamp_thr") is not None else "",
        },
        "sensitivityPresets": {
            preset_id: touch_preset_payload(preset_id)
            for preset_id in TOUCH_SENSITIVITY_PRESETS
        },
        "statusSummary": "lightweight sensitivity update; use refresh for full service log",
        "logTail": "",
        "updatedAt": timestamp(),
        "durationSeconds": round(time.monotonic() - started, 3),
        "host": host,
        "port": port,
        "user": user,
        "returnCode": result.get("returnCode"),
        "stderr": result.get("stderr") or "",
    }
    return {"action": "sensitivity", "preset": touch_preset_payload(preset_id), "result": result, "status": status}


def _http_json(url: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 1.2) -> tuple[bool, dict]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    try:
        request = Request(url, data=data, headers=headers, method=method)
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            body = json.loads(raw or "{}")
            if not isinstance(body, dict):
                body = {"raw": body}
            return 200 <= response.status < 300 and body.get("ok", True) is not False, {
                "status": response.status,
                "body": body,
            }
    except Exception as exc:  # noqa: BLE001 - health checks should be reported as JSON.
        return False, {"error": str(exc)}


def _touch_audio_port_processes() -> list[dict]:
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{TOUCH_AUDIO_BRIDGE_PORT}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]
    processes: list[dict] = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            pid = parts[1]
            command = " ".join(parts)
            try:
                ps = subprocess.run(
                    ["ps", "-p", pid, "-o", "command="],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                    check=False,
                )
                command = ps.stdout.strip() or command
            except Exception:
                pass
            processes.append({"pid": pid, "command": command})
    return processes


def touch_audio_local_status() -> dict:
    ok, payload = _http_json(TOUCH_AUDIO_HEALTH_URL, timeout=1.2)
    processes = _touch_audio_port_processes()
    return {
        "ok": ok,
        "running": ok,
        "healthUrl": TOUCH_AUDIO_HEALTH_URL,
        "triggerUrl": TOUCH_AUDIO_TRIGGER_URL,
        "port": TOUCH_AUDIO_BRIDGE_PORT,
        "bridgeDir": str(TOUCH_AUDIO_BRIDGE_DIR),
        "health": payload,
        "processes": processes,
        "updatedAt": timestamp(),
    }


def start_touch_audio_bridge() -> dict:
    before = touch_audio_local_status()
    if before.get("running"):
        return {"ok": True, "started": False, "reason": "already-running", "status": before}
    launcher = TOUCH_AUDIO_BRIDGE_DIR / "Start-Audio-Bridge.command"
    if not launcher.is_file():
        return {
            "ok": False,
            "started": False,
            "reason": "missing-launcher",
            "launcher": str(launcher),
            "status": before,
        }
    with TOUCH_AUDIO_LOCK:
        if touch_audio_local_status().get("running"):
            return {"ok": True, "started": False, "reason": "already-running", "status": touch_audio_local_status()}
        if shutil.which("tmux"):
            subprocess.run(["tmux", "kill-session", "-t", "mira-touch-audio"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            command = f"cd {shlex.quote(str(TOUCH_AUDIO_BRIDGE_DIR))} && ./Start-Audio-Bridge.command --port {TOUCH_AUDIO_BRIDGE_PORT}"
            launch = subprocess.run(
                ["tmux", "new-session", "-d", "-s", "mira-touch-audio", command],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
        else:
            log_path = TOUCH_AUDIO_BRIDGE_DIR / "audio-bridge-console.log"
            log_file = log_path.open("ab")
            proc = subprocess.Popen(
                [str(launcher), "--port", str(TOUCH_AUDIO_BRIDGE_PORT)],
                cwd=str(TOUCH_AUDIO_BRIDGE_DIR),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            launch = subprocess.CompletedProcess(args=[str(launcher)], returncode=0, stdout=f"pid={proc.pid}", stderr="")
        for _ in range(20):
            status = touch_audio_local_status()
            if status.get("running"):
                return {
                    "ok": True,
                    "started": True,
                    "reason": "started",
                    "launcher": str(launcher),
                    "launch": {"returnCode": launch.returncode, "stdout": launch.stdout, "stderr": launch.stderr},
                    "status": status,
                }
            time.sleep(0.2)
        status = touch_audio_local_status()
        return {
            "ok": False,
            "started": False,
            "reason": "start-timeout",
            "launcher": str(launcher),
            "launch": {"returnCode": launch.returncode, "stdout": launch.stdout, "stderr": launch.stderr},
            "status": status,
        }


def board_touch_audio_probe(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
    test_audio: bool,
) -> dict:
    script = f"""set +e
python3 - <<'PY'
import json
import urllib.request
from pathlib import Path

p = Path({TOUCH_MAPPING_PATH!r})
data = json.loads(p.read_text())
comfort = data.get("comfort_sound") or {{}}
url = str(comfort.get("bridge_url") or "")
base = url.rsplit("/v1/", 1)[0] if "/v1/" in url else url.rstrip("/")
payload = {{"event": str(comfort.get("event_name") or "long_touch_comfort"), "payload": {{"asset_name": str(comfort.get("asset_name") or {TOUCH_AUDIO_SELF_TEST_ASSET!r}), "self_test": True}}}}
result = {{"bridge_url": url, "health_url": base + "/health" if base else "", "comfort_sound": comfort}}
try:
    with urllib.request.urlopen(result["health_url"], timeout=2.0) as response:
        result["health"] = {{"ok": 200 <= response.status < 300, "status": response.status, "body": response.read(400).decode(errors="replace")}}
except Exception as exc:
    result["health"] = {{"ok": False, "error": repr(exc)}}
if {str(test_audio)}:
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={{"Content-Type": "application/json"}}, method="POST")
        with urllib.request.urlopen(req, timeout=2.5) as response:
            result["trigger"] = {{"ok": 200 <= response.status < 300, "status": response.status, "body": response.read(400).decode(errors="replace")}}
    except Exception as exc:
        result["trigger"] = {{"ok": False, "error": repr(exc)}}
print(json.dumps(result, ensure_ascii=False))
PY
"""
    started = time.monotonic()
    try:
        result = run_remote_script(
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 12.0),
        )
    except Exception as exc:  # noqa: BLE001
        result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}
    stdout = str(result.get("stdout") or "").strip()
    parsed: dict = {}
    if stdout:
        try:
            parsed = json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError:
            parsed = {"parseError": stdout}
    health_ok = bool(parsed.get("health", {}).get("ok"))
    trigger = parsed.get("trigger")
    trigger_ok = trigger is None or bool(trigger.get("ok"))
    return {
        "ok": result.get("returnCode") == 0 and health_ok and trigger_ok,
        "returnCode": result.get("returnCode"),
        "durationSeconds": round(time.monotonic() - started, 3),
        "host": host,
        "port": port,
        "user": user,
        "probe": parsed,
        "stderr": result.get("stderr") or "",
    }


def check_touch_audio(
    *,
    auto_start: bool,
    board_check: bool,
    test_audio: bool,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
) -> dict:
    started = time.monotonic()
    local = touch_audio_local_status()
    repair: dict | None = None
    if auto_start and not local.get("running"):
        repair = start_touch_audio_bridge()
        local = touch_audio_local_status()
    board = None
    if board_check:
        board = board_touch_audio_probe(
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=timeout_seconds,
            test_audio=test_audio,
        )
    ok = bool(local.get("running")) and (board is None or bool(board.get("ok")))
    return {
        "ok": ok,
        "running": bool(local.get("running")),
        "local": local,
        "repair": repair,
        "board": board,
        "autoStart": auto_start,
        "boardCheck": board_check,
        "testAudio": test_audio,
        "updatedAt": timestamp(),
        "durationSeconds": round(time.monotonic() - started, 3),
    }


def save_embedded_photo(stdout: str) -> tuple[str, str | None]:
    match = re.search(r"PHOTO_B64_BEGIN\s*(.*?)\s*PHOTO_B64_END", stdout, re.DOTALL)
    if not match:
        return stdout, None

    encoded = "".join(match.group(1).split())
    image_bytes = base64.b64decode(encoded, validate=True)
    LOCAL_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    target = LOCAL_CAPTURE_DIR / f"wake-photo-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.jpg"
    target.write_bytes(image_bytes)

    cleaned = re.sub(
        r"PHOTO_B64_BEGIN\s*.*?\s*PHOTO_B64_END",
        f"PHOTO_SAVED_LOCAL={target}",
        stdout,
        count=1,
        flags=re.DOTALL,
    )
    return cleaned, str(target)


def validate_servo_positions(raw_positions: object) -> dict[str, int]:
    if not isinstance(raw_positions, dict):
        raise ValueError("positions must be an object with keys 0, 1, 2, and 3")
    positions: dict[str, int] = {}
    for servo_id in ("0", "1", "2", "3"):
        if servo_id not in raw_positions:
            raise ValueError(f"missing servo position: {servo_id}")
        value = int(raw_positions[servo_id])
        if value < SERVO_MIN or value > SERVO_MAX:
            raise ValueError(f"servo {servo_id} position out of range: {value}")
        positions[servo_id] = value
    return positions


def render_servo_pose_script(positions: dict[str, int], speeds: tuple[int, int, int, int] = MANUAL_SERVO_SPEEDS) -> str:
    p0, p1, p2, p3 = (positions[str(index)] for index in range(4))
    s0, s1, s2, s3 = speeds
    return (
        "set -euo pipefail\n"
        f'export {REMOTE_DESKTOP_ENV_VAR}="${{{REMOTE_DESKTOP_ENV_VAR}:-{REMOTE_DESKTOP_DIR}}}"\n'
        "echo '== manual servo pose =='\n"
        f'python3 "${{{REMOTE_DESKTOP_ENV_VAR}}}/four_servo_control.py" pose {p0} {p1} {p2} {p3} '
        f"--speeds {s0} {s1} {s2} {s3}\n"
    )


def servo_speed_preset_name(raw_preset: object) -> str:
    preset = str(raw_preset or "medium").strip().lower()
    if preset not in SERVO_SPEED_PRESETS:
        raise ValueError(f"Unknown servo speed preset: {preset}")
    return preset


def servo_speed_preset_config(raw_preset: object) -> dict:
    preset = servo_speed_preset_name(raw_preset)
    config = SERVO_SPEED_PRESETS[preset]
    return {
        "id": preset,
        "label": str(config["label"]),
        "step": int(config["step"]),
        "speeds": list(config["speeds"]),
    }


def servo_speed_preset_speeds(raw_preset: object) -> tuple[int, int, int, int]:
    preset = servo_speed_preset_name(raw_preset)
    return tuple(int(value) for value in SERVO_SPEED_PRESETS[preset]["speeds"])


def servo_hold_interval_seconds(raw_preset: object) -> float:
    preset = servo_speed_preset_name(raw_preset)
    return float(SERVO_HOLD_INTERVAL_SECONDS[preset])


def validate_servo_id(raw_servo_id: object) -> str:
    servo_id = str(raw_servo_id).strip()
    if servo_id not in {"0", "1", "2", "3"}:
        raise ValueError(f"invalid servo id: {raw_servo_id}")
    return servo_id


def validate_servo_direction(raw_direction: object) -> int:
    direction = int(raw_direction)
    if direction not in {-1, 1}:
        raise ValueError(f"invalid servo direction: {raw_direction}")
    return direction


def clamp_servo_position(value: int) -> int:
    return max(SERVO_MIN, min(SERVO_MAX, int(value)))


def render_servo_hold_loop_script(
    *,
    positions: dict[str, int],
    servo_id: str,
    direction: int,
    step: int,
    speeds: tuple[int, int, int, int],
    interval_seconds: float,
) -> str:
    p0, p1, p2, p3 = (int(positions[str(index)]) for index in range(4))
    s0, s1, s2, s3 = (int(value) for value in speeds)
    servo_index = int(servo_id)
    delta = int(direction) * int(step)
    interval = max(0.03, float(interval_seconds))
    return f"""set -euo pipefail
python3 - <<'PY'
import signal
import subprocess
import time

positions = [{p0}, {p1}, {p2}, {p3}]
servo_index = {servo_index}
delta = {delta}
minimum = {SERVO_MIN}
maximum = {SERVO_MAX}
speeds = [{s0}, {s1}, {s2}, {s3}]
interval = {interval!r}
command_prefix = ["python3", "{REMOTE_DESKTOP_DIR}/four_servo_control.py", "pose"]

def _stop(_signum, _frame):
    raise SystemExit(0)

for _sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    signal.signal(_sig, _stop)

while True:
    next_value = positions[servo_index] + delta
    if next_value < minimum:
        next_value = minimum
    elif next_value > maximum:
        next_value = maximum
    positions[servo_index] = next_value
    subprocess.run(
        command_prefix + [str(value) for value in positions] + ["--speeds"] + [str(value) for value in speeds],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    time.sleep(interval)
PY
"""


def run_text_command(command: list[str], timeout_seconds: float = 3.0) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "returnCode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics should always surface an error payload.
        return {"returnCode": -1, "stdout": "", "stderr": str(exc)}


def local_ips() -> list[str]:
    ips: list[str] = []
    for interface in ("en0", "en1", "en2", "bridge100"):
        result = run_text_command(["ipconfig", "getifaddr", interface], timeout_seconds=1.0)
        value = str(result.get("stdout") or "").strip()
        if value:
            ips.append(f"{interface}: {value}")
    return ips


def route_to_host(host: str) -> dict:
    result = run_text_command(["route", "-n", "get", host], timeout_seconds=2.0)
    text = f"{result.get('stdout') or ''}\n{result.get('stderr') or ''}"
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()
    interface = parsed.get("interface", "")
    gateway = parsed.get("gateway", "")
    warnings = []
    if interface.startswith("utun") or gateway.startswith("198.18."):
        warnings.append("当前到板子 IP 的路由走 utun/VPN/代理，不像本地局域网直连。")
    return {
        "ok": result.get("returnCode") == 0,
        "parsed": parsed,
        "stdout": result.get("stdout") or "",
        "stderr": result.get("stderr") or "",
        "warnings": warnings,
    }


def tcp_probe(host: str, port: int, timeout_seconds: float = 2.0) -> dict:
    started = datetime.now()
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            ok = True
            error = None
    except Exception as exc:  # noqa: BLE001
        ok = False
        error = str(exc)
    elapsed = (datetime.now() - started).total_seconds()
    return {"ok": ok, "host": host, "port": port, "error": error, "durationSeconds": round(elapsed, 3)}


def connection_diagnostics(host: str, port: int) -> dict:
    route = route_to_host(host)
    tcp = tcp_probe(host, port)
    warnings = [*route.get("warnings", [])]
    if tcp.get("ok") and warnings:
        warnings.append("22 端口可连但路由异常时，常见现象是 SSH 随后 Connection closed。")
    if not tcp.get("ok"):
        warnings.append("22 端口不可连；请确认板子 IP、同一局域网和 SSH 服务。")
    return {
        "ok": bool(tcp.get("ok")) and not warnings,
        "host": host,
        "port": port,
        "localIps": local_ips(),
        "route": route,
        "tcp": tcp,
        "warnings": warnings,
        "updatedAt": timestamp(),
    }


def connection_diagnostics(
    host: str,
    port: int,
    *,
    user: str = DEFAULT_USER,
    password: str = "",
    timeout_seconds: float = 8.0,
) -> dict:
    route = route_to_host(host)
    tcp = tcp_probe(host, port)
    warnings = [*route.get("warnings", [])]
    if tcp.get("ok") and warnings:
        warnings.append("22 绔彛鍙繛浣嗚矾鐢卞紓甯告椂锛屽父瑙佺幇璞℃槸 SSH 闅忓悗 Connection closed銆?")
    if not tcp.get("ok"):
        warnings.append("22 绔彛涓嶅彲杩烇紱璇风‘璁ゆ澘瀛?IP銆佸悓涓€灞€鍩熺綉鍜?SSH 鏈嶅姟銆?")

    ssh = None
    if tcp.get("ok"):
        ssh_result = run_remote_script(
            script="echo SSH_OK",
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 15.0),
        )
        ssh_ok = ssh_result.get("returnCode") == 0 and "SSH_OK" in str(ssh_result.get("stdout", ""))
        ssh = {
            "ok": ssh_ok,
            "returnCode": ssh_result.get("returnCode"),
            "stdout": compact_console_output(ssh_result.get("stdout", ""), limit=200),
            "stderr": compact_console_output(ssh_result.get("stderr", ""), limit=400),
        }
        if not ssh_ok:
            warning = ssh["stderr"] or ssh["stdout"] or "SSH auth probe failed"
            warnings.append(str(warning).strip()[:220])

    return {
        "ok": bool(tcp.get("ok")) and bool(ssh and ssh.get("ok")) and not warnings,
        "host": host,
        "port": port,
        "localIps": local_ips(),
        "route": route,
        "tcp": tcp,
        "ssh": ssh,
        "warnings": warnings,
        "updatedAt": timestamp(),
    }


def render_teach_install_script() -> str:
    if not TEACH_BOARD_SCRIPT_PATH.is_file():
        raise FileNotFoundError(f"Teach board script not found: {TEACH_BOARD_SCRIPT_PATH}")
    encoded = base64.b64encode(TEACH_BOARD_SCRIPT_PATH.read_bytes()).decode("ascii")
    return f"""set -euo pipefail
mkdir -p {shlex.quote(TEACH_REMOTE_DIR)}
python3 - <<'PY'
import base64
from pathlib import Path
target = Path({TEACH_REMOTE_SCRIPT!r})
target.write_bytes(base64.b64decode({encoded!r}))
target.chmod(0o755)
PY
"""


def render_teach_status_script() -> str:
    return f"""set +e
export TERM=dumb
mkdir -p {shlex.quote(TEACH_REMOTE_DIR)}
pid="$(cat {shlex.quote(TEACH_REMOTE_PID)} 2>/dev/null || true)"
running=0
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then running=1; fi
echo "TEACH_RUNNING=$running"
echo "TEACH_PID=$pid"
echo "TEACH_RAW={TEACH_REMOTE_RAW}"
echo "TEACH_RAW_EXISTS=$([ -s {shlex.quote(TEACH_REMOTE_RAW)} ] && echo 1 || echo 0)"
if [ -s {shlex.quote(TEACH_REMOTE_RAW)} ]; then
  python3 - <<'PY' 2>/dev/null || true
import json
from pathlib import Path
p = Path({TEACH_REMOTE_RAW!r})
data = json.loads(p.read_text())
print("TEACH_FRAME_COUNT=" + str(data.get("frameCount", len(data.get("frames", [])))))
print("TEACH_DURATION_MS=" + str(data.get("durationMs", 0)))
print("TEACH_STOPPED_BY=" + str(data.get("stoppedBy", "-")))
PY
fi
echo "TEACH_LOG_BEGIN"
tail -30 {shlex.quote(TEACH_REMOTE_LOG)} 2>/dev/null || true
echo "TEACH_LOG_END"
exit 0
"""


def parse_teach_status(result: dict) -> dict:
    stdout = result.get("stdout", "")
    raw_exists = marker_value(stdout, "TEACH_RAW_EXISTS") == "1"
    frame_count = marker_value(stdout, "TEACH_FRAME_COUNT")
    duration_ms = marker_value(stdout, "TEACH_DURATION_MS")
    return {
        "running": marker_value(stdout, "TEACH_RUNNING") == "1",
        "pid": marker_value(stdout, "TEACH_PID"),
        "rawPath": marker_value(stdout, "TEACH_RAW") or TEACH_REMOTE_RAW,
        "rawExists": raw_exists,
        "frameCount": int(frame_count) if frame_count.isdigit() else None,
        "durationMs": int(duration_ms) if duration_ms.isdigit() else None,
        "stoppedBy": marker_value(stdout, "TEACH_STOPPED_BY"),
        "log": marker_block(stdout, "TEACH_LOG"),
        "returnCode": result.get("returnCode"),
        "updatedAt": timestamp(),
    }


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def remote_desktop_export_line() -> str:
    return f'export {REMOTE_DESKTOP_ENV_VAR}="${{{REMOTE_DESKTOP_ENV_VAR}:-{REMOTE_DESKTOP_DIR}}}"'


def normalize_command_for_distribution(command: str) -> str:
    normalized = str(command)
    prefixes = sorted(set(LEGACY_REMOTE_DESKTOP_DIRS + [DEFAULT_REMOTE_DESKTOP_DIR, REMOTE_DESKTOP_DIR]), key=len, reverse=True)
    pattern = re.compile(rf"({'|'.join(re.escape(prefix) for prefix in prefixes)})/([^\s\"']+)")
    normalized = pattern.sub(lambda match: f'"${{{REMOTE_DESKTOP_ENV_VAR}}}/{match.group(2)}"', normalized)
    return normalized


def adapt_board_script(script: str) -> str:
    """Adapt legacy board commands for the current UART3 joint-only setup."""
    adapted = str(script)
    for legacy_dir in LEGACY_REMOTE_DESKTOP_DIRS:
        adapted = adapted.replace(legacy_dir, REMOTE_DESKTOP_DIR)
    adapted = adapted.replace(DEFAULT_REMOTE_DESKTOP_DIR, REMOTE_DESKTOP_DIR)
    if REMOTE_LED_ENABLED:
        return adapted

    lines: list[str] = []
    for line in adapted.splitlines():
        if "send_uart3_led_cmd.py" in line:
            message = f"[skip] LED/head command disabled: {line.strip()}"
            lines.append(f"echo {shlex.quote(message)}")
        else:
            lines.append(line)
    return "\n".join(lines) + ("\n" if adapted.endswith("\n") else "")


def render_remote_script(steps: list[dict]) -> str:
    lines = ["set -euo pipefail", remote_desktop_export_line()]
    for step in steps:
        label = str(step["label"])
        command = normalize_command_for_distribution(str(step["command"]))
        lines.append(f"echo '== {label} =='")
        lines.append(command)
    return adapt_board_script("\n".join(lines) + "\n")


EMERGENCY_STOP_SCRIPT = render_remote_script(EMERGENCY_STOP_COMMANDS)


def parse_extra_args(raw: object) -> list[str]:
    if raw in (None, "", False):
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    if isinstance(raw, str):
        return shlex.split(raw)
    raise ValueError("extraArgs must be a string or list")


def expand_registry_args(raw_args: object) -> list[str]:
    if raw_args in (None, "", False):
        return []
    if not isinstance(raw_args, list):
        raise ValueError("defaultArgs must be a list")
    values: list[str] = []
    for item in raw_args:
        value = str(item)
        if value == "$MIRA_SHENZHEN_DIGUA_OUTPUT_DIR":
            value = str(DIGUA_OUTPUT_DIR)
        values.append(os.path.expandvars(value))
    return values


def redact_password(text: str, password: str) -> str:
    if not password:
        return text
    return text.replace(password, "***")


def compact_console_output(text: str, *, limit: int) -> str:
    cleaned = "\n".join(line.strip() for line in str(text or "").replace("\r", "").splitlines() if line.strip())
    return cleaned[:limit]


def timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def coerce_book_follow_config(raw: dict | None = None) -> dict:
    raw = raw or {}
    config = dict(BOOK_FOLLOW_DEFAULTS)
    aliases = {
        "runtimeDir": "runtimeDir",
        "receiverHost": "receiverHost",
        "receiverPort": "receiverPort",
        "baseUrl": "baseUrl",
        "pollInterval": "pollInterval",
        "trackingUpdateMs": "trackingUpdateMs",
        "tabletopTrackingUpdateMs": "tabletopTrackingUpdateMs",
        "sceneAllowedDetectors": "sceneAllowedDetectors",
        "trackingAllowedDetectors": "trackingAllowedDetectors",
        "touchHandArmMinConfidence": "touchHandArmMinConfidence",
        "handAvoidMinConfidence": "handAvoidMinConfidence",
        "roiTop": "roiTop",
        "roiBottom": "roiBottom",
        "roiLeft": "roiLeft",
        "roiRight": "roiRight",
        "maxAreaRatio": "maxAreaRatio",
        "hueMin": "hueMin",
        "hueMax": "hueMax",
        "minSaturation": "minSaturation",
        "minValue": "minValue",
        "minColorRatio": "minColorRatio",
        "minAspectRatio": "minAspectRatio",
        "maxAspectRatio": "maxAspectRatio",
        "minRectangularity": "minRectangularity",
        "minSolidity": "minSolidity",
        "minEdgeRatio": "minEdgeRatio",
        "maxEdgeRatio": "maxEdgeRatio",
        "minInnerEdgeRatio": "minInnerEdgeRatio",
        "maxCornerCount": "maxCornerCount",
    }
    for source_key, target_key in aliases.items():
        value = raw.get(source_key)
        if value not in (None, ""):
            config[target_key] = str(value).strip()
    config["receiverPort"] = int(config["receiverPort"])
    config["runtimeDir"] = str(Path(config["runtimeDir"]).expanduser().resolve())
    return config


def build_book_follow_env(config: dict) -> dict[str, str]:
    runtime_dir = Path(config["runtimeDir"]).expanduser().resolve()
    return {
        "MIRA_LIGHT_SERVICE_ROOT": str(REPO_ROOT),
        "MIRA_LIGHT_WORKSPACE_RUNTIME_DIR": str(runtime_dir),
        "MIRA_LIGHT_DEFAULT_TARGET_MODE": "tabletop_follow",
        "MIRA_LIGHT_VISION_HOST": str(config["receiverHost"]),
        "MIRA_LIGHT_VISION_PORT": str(config["receiverPort"]),
        "MIRA_LIGHT_BASE_URL": str(config["baseUrl"]),
        "MIRA_LIGHT_VISION_POLL_INTERVAL": str(config["pollInterval"]),
        "MIRA_LIGHT_TRACKING_UPDATE_MS": str(config["trackingUpdateMs"]),
        "MIRA_LIGHT_TABLETOP_TRACKING_UPDATE_MS": str(config["tabletopTrackingUpdateMs"]),
        "MIRA_LIGHT_SCENE_ALLOWED_DETECTORS": str(config["sceneAllowedDetectors"]),
        "MIRA_LIGHT_TRACKING_ALLOWED_DETECTORS": str(config["trackingAllowedDetectors"]),
        "MIRA_LIGHT_TOUCH_HAND_ARM_MIN_CONFIDENCE": str(config["touchHandArmMinConfidence"]),
        "MIRA_LIGHT_HAND_AVOID_MIN_CONFIDENCE": str(config["handAvoidMinConfidence"]),
        "MIRA_LIGHT_TABLETOP_ROI_TOP": str(config["roiTop"]),
        "MIRA_LIGHT_TABLETOP_ROI_BOTTOM": str(config["roiBottom"]),
        "MIRA_LIGHT_TABLETOP_ROI_LEFT": str(config["roiLeft"]),
        "MIRA_LIGHT_TABLETOP_ROI_RIGHT": str(config["roiRight"]),
        "MIRA_LIGHT_TABLETOP_MAX_AREA_RATIO": str(config["maxAreaRatio"]),
        "MIRA_LIGHT_TABLETOP_BOOK_COLOR_ENABLED": "1",
        "MIRA_LIGHT_TABLETOP_BOOK_HUE_MIN": str(config["hueMin"]),
        "MIRA_LIGHT_TABLETOP_BOOK_HUE_MAX": str(config["hueMax"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_SATURATION": str(config["minSaturation"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_VALUE": str(config["minValue"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_COLOR_RATIO": str(config["minColorRatio"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_ASPECT_RATIO": str(config["minAspectRatio"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MAX_ASPECT_RATIO": str(config["maxAspectRatio"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_RECTANGULARITY": str(config["minRectangularity"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_SOLIDITY": str(config["minSolidity"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_EDGE_RATIO": str(config["minEdgeRatio"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MAX_EDGE_RATIO": str(config["maxEdgeRatio"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MIN_INNER_EDGE_RATIO": str(config["minInnerEdgeRatio"]),
        "MIRA_LIGHT_TABLETOP_BOOK_MAX_CORNER_COUNT": str(config["maxCornerCount"]),
        "MIRA_LIGHT_TABLETOP_BOOK_SELECTION_BONUS": "0.42",
    }


def play_local_audio(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    try:
        process = subprocess.Popen(
            ["afplay", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("afplay not found; this action requires macOS audio playback") from exc
    return {
        "ok": True,
        "path": str(path),
        "pid": process.pid,
        "startedAt": timestamp(),
    }


def play_local_audio_after_delay(path: Path, delay_seconds: float) -> dict:
    result: dict = {"ok": None, "path": str(path), "delaySeconds": delay_seconds, "startedAt": None, "error": None}

    def worker() -> None:
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        try:
            result.update(play_local_audio(path))
        except Exception as exc:  # noqa: BLE001 - surface via result dict captured by caller.
            result.update({"ok": False, "error": str(exc), "startedAt": timestamp()})

    thread = Thread(target=worker, name="mira-answer-audio", daemon=True)
    thread.start()
    return {"ok": True, "path": str(path), "delaySeconds": delay_seconds, "thread": thread.name}


def read_printer_bridge_token() -> str:
    if os.environ.get("OPENCLAW_PRINTER_BRIDGE_TOKEN"):
        return str(os.environ["OPENCLAW_PRINTER_BRIDGE_TOKEN"])
    for env_path in (
        Path(os.environ.get("OPENCLAW_PRINTER_BRIDGE_ENV", "")) if os.environ.get("OPENCLAW_PRINTER_BRIDGE_ENV") else None,
        Path.home() / ".openclaw-printer-bridge.env",
        REPO_ROOT / "Chrome-Camera-Anime" / ".runtime" / "printer-bridge.env",
    ):
        if env_path is None or not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("export OPENCLAW_PRINTER_BRIDGE_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    token: str = "",
    timeout: float = 5.0,
) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, method=method, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        parsed = json.loads(raw or "{}")
        if isinstance(parsed, dict):
            parsed.setdefault("httpStatus", response.status)
            return parsed
        return {"ok": True, "value": parsed, "httpStatus": response.status}


def read_json_file(path: Path) -> dict | None:
    try:
        if not path.is_file():
            return None
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def tail_text(path: Path, max_lines: int = 60) -> str:
    try:
        if not path.is_file():
            return ""
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:])
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def summarize_book_follow_event(event: dict | None, bridge_state: dict | None) -> dict:
    tracking = (event or {}).get("tracking") if isinstance(event, dict) else {}
    tracking = tracking if isinstance(tracking, dict) else {}
    control_hint = (event or {}).get("control_hint") if isinstance(event, dict) else {}
    control_hint = control_hint if isinstance(control_hint, dict) else {}
    last_decision = (bridge_state or {}).get("lastDecision") if isinstance(bridge_state, dict) else {}
    last_decision = last_decision if isinstance(last_decision, dict) else {}
    runtime_state = (bridge_state or {}).get("runtimeState") if isinstance(bridge_state, dict) else {}
    runtime_state = runtime_state if isinstance(runtime_state, dict) else {}
    return {
        "targetPresent": bool(tracking.get("target_present")),
        "detector": tracking.get("detector") or "-",
        "targetClass": tracking.get("target_class") or "-",
        "targetSubclass": tracking.get("target_subclass") or "-",
        "targetMode": tracking.get("target_mode") or "-",
        "confidence": tracking.get("confidence"),
        "centerNorm": tracking.get("center_norm") or {},
        "feedbackProfile": control_hint.get("feedback_profile") or "-",
        "recommendedUpdateMs": control_hint.get("recommended_update_ms"),
        "bridgeAction": last_decision.get("action") or "-",
        "bridgeReason": last_decision.get("actionReason") or last_decision.get("trackingGateReason") or "",
        "trackingActive": runtime_state.get("trackingActive"),
        "trackingTarget": runtime_state.get("trackingTarget") or {},
    }


def register_process(process: subprocess.Popen) -> None:
    with PROCESS_LOCK:
        ACTIVE_PROCESSES.add(process)


def unregister_process(process: subprocess.Popen) -> None:
    with PROCESS_LOCK:
        ACTIVE_PROCESSES.discard(process)


def terminate_active_processes(grace_seconds: float = 0.4) -> int:
    with PROCESS_LOCK:
        processes = [process for process in ACTIVE_PROCESSES if process.poll() is None]

    for process in processes:
        try:
            process.terminate()
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + grace_seconds
    for process in processes:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                pass

    return len(processes)


def ssh_control_path(*, host: str, port: int, user: str) -> Path:
    digest = hashlib.sha256(f"{user}@{host}:{port}".encode("utf-8")).hexdigest()[:16]
    return SSH_CONTROL_DIR / f"cm-{digest}"


def ssh_control_options(*, host: str, port: int, user: str) -> list[str]:
    # Windows OpenSSH does not support ControlMaster/ControlPath unix socket
    # multiplexing; using it produces "getsockname failed: Not a socket".
    if os.name == "nt":
        return []
    SSH_CONTROL_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    control_path = ssh_control_path(host=host, port=port, user=user)
    return [
        "-o",
        "ControlMaster=auto",
        "-o",
        f"ControlPersist={SSH_CONTROL_PERSIST_SECONDS}s",
        "-o",
        f"ControlPath={control_path}",
    ]


def is_transient_ssh_failure(result: dict) -> bool:
    if result.get("returnCode") != 255:
        return False
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    if "Permission denied" in text or "Authentication failed" in text:
        return False
    transient_markers = (
        "Connection reset",
        "Connection closed",
        "kex_exchange_identification",
        "mux_client_request_session",
    )
    return not text.strip() or any(marker in text for marker in transient_markers)


def plink_cache_key(*, host: str, port: int, user: str) -> tuple[str, int, str]:
    return (host, port, user)


DEFAULT_PLINK_HOSTKEYS = {
    ("192.168.0.183", 22): "SHA256:K8oyEoddaZ4keNu39exAqMJLDEcncgoQGcRPQ898Bb4",
}


def extract_plink_hostkey(text: str) -> str | None:
    match = re.search(r"(ssh-[\w-]+\s+\d+\s+SHA256:[A-Za-z0-9+/=:-]+)", text or "")
    if not match:
        return None
    return match.group(1).strip()


def resolve_plink_hostkey(*, host: str, port: int, user: str) -> str:
    configured = os.environ.get("MIRA_SHENZHEN_PLINK_HOSTKEY", "").strip()
    if configured:
        return configured
    default_hostkey = DEFAULT_PLINK_HOSTKEYS.get((host, port), "")
    if default_hostkey:
        return default_hostkey
    return PLINK_HOSTKEY_CACHE.get(plink_cache_key(host=host, port=port, user=user), "")


def build_plink_command(
    *,
    plink_bin: str,
    host: str,
    port: int,
    user: str,
    password: str,
    remote: str,
    hostkey: str = "",
) -> list[str]:
    command = [
        plink_bin,
        "-batch",
        "-ssh",
        "-P",
        str(port),
    ]
    if hostkey:
        command.extend(["-hostkey", hostkey])
    command.extend(["-pw", password, f"{user}@{host}", remote])
    return command


def run_local_command(command: list[str], timeout_seconds: float, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    register_process(process)
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(command, timeout_seconds, output=stdout, stderr=stderr) from exc
    finally:
        unregister_process(process)
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def command_preview(command: list[str], env_keys: list[str] | None = None) -> str:
    prefix = ""
    if env_keys:
        prefix = " ".join(f"{key}=<from environment or console>" for key in env_keys) + " "
    return prefix + " ".join(shlex.quote(str(part)) for part in command)


def read_keychain_secret(service: str) -> str:
    command = ["security", "find-generic-password", "-s", service, "-w"]
    account = os.environ.get("USER") or os.environ.get("LOGNAME")
    if account:
        command[2:2] = ["-a", account]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def hydrate_env_from_keychain(env: dict[str, str], keys: list[str]) -> None:
    for key in keys:
        if env.get(key):
            continue
        service = KEYCHAIN_SECRET_SERVICES.get(key)
        if not service:
            continue
        value = read_keychain_secret(service)
        if value:
            env[key] = value


def run_local_action_command(
    *,
    command: list[str],
    env: dict[str, str],
    timeout_seconds: float,
    redact_values: list[str] | None = None,
) -> dict:
    redact_values = [value for value in (redact_values or []) if value]
    try:
        result = run_local_command(command, timeout_seconds=timeout_seconds, env=env)
    except subprocess.TimeoutExpired:
        return {"returnCode": -1, "stdout": "", "stderr": f"Timed out after {timeout_seconds:.1f}s"}
    stdout = result.stdout
    stderr = result.stderr
    for value in redact_values:
        stdout = stdout.replace(value, "[redacted]")
        stderr = stderr.replace(value, "[redacted]")
    return {"returnCode": result.returncode, "stdout": stdout, "stderr": stderr}


def run_ssh_with_pty(command: list[str], password: str, timeout_seconds: float) -> dict:
    if pty is None:
        return {"returnCode": 255, "stdout": "", "stderr": "pty is unavailable on this platform"}
    master_fd, slave_fd = pty.openpty()
    started = time.monotonic()
    output_chunks: list[str] = []
    process = subprocess.Popen(
        command,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        text=False,
        close_fds=True,
    )
    register_process(process)
    os.close(slave_fd)
    password_sent = False
    try:
        while True:
            if time.monotonic() - started > timeout_seconds:
                process.kill()
                return {
                    "returnCode": -1,
                    "stdout": redact_password("".join(output_chunks), password),
                    "stderr": f"Timed out after {timeout_seconds:.1f}s",
                }

            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    chunk = b""
                if chunk:
                    text = chunk.decode("utf-8", errors="replace")
                    output_chunks.append(text)
                    if not password_sent and "password:" in text.lower():
                        os.write(master_fd, (password + "\n").encode("utf-8"))
                        password_sent = True
                elif process.poll() is not None:
                    break

            if process.poll() is not None and not ready:
                break
    finally:
        unregister_process(process)
        os.close(master_fd)

    stdout = redact_password("".join(output_chunks), password)
    return {"returnCode": process.returncode, "stdout": stdout, "stderr": ""}


def run_ssh_with_expect(command: list[str], password: str, timeout_seconds: float) -> dict:
    expect_bin = shutil.which("expect")
    if not expect_bin:
        return run_ssh_with_pty(command, password=password, timeout_seconds=timeout_seconds)

    expect_program = r"""
set timeout $env(MIRA_EXPECT_TIMEOUT)
spawn {*}$argv
expect {
  -re "(?i)are you sure you want to continue connecting" {
    send "yes\r"
    exp_continue
  }
  -re "(?i)password:" {
    send "$env(MIRA_EXPECT_PASSWORD)\r"
    exp_continue
  }
  timeout {
    puts "\nTimed out waiting for SSH response"
    exit 124
  }
  eof
}
catch wait result
exit [lindex $result 3]
"""
    env = {
        **os.environ,
        "MIRA_EXPECT_PASSWORD": password,
        "MIRA_EXPECT_TIMEOUT": str(max(1, int(timeout_seconds))),
    }
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".expect", delete=False) as handle:
            handle.write(expect_program)
            expect_script = handle.name
        try:
            process = subprocess.Popen(
                [expect_bin, expect_script, *command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            register_process(process)
            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds + 5.0)
            except subprocess.TimeoutExpired as exc:
                process.kill()
                stdout, stderr = process.communicate()
                raise subprocess.TimeoutExpired(command, timeout_seconds + 5.0, output=stdout, stderr=stderr) from exc
            finally:
                unregister_process(process)
        finally:
            Path(expect_script).unlink(missing_ok=True)
    except subprocess.TimeoutExpired:
        return {"returnCode": -1, "stdout": "", "stderr": f"Timed out after {timeout_seconds:.1f}s"}

    return {
        "returnCode": process.returncode,
        "stdout": redact_password(stdout, password),
        "stderr": redact_password(stderr, password),
    }


def run_remote_script(
    *,
    script: str,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
) -> dict:
    with SSH_LOCK:
        return _run_remote_script_unlocked(
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=timeout_seconds,
        )


def try_run_remote_script(
    *,
    script: str,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
) -> dict:
    if not SSH_LOCK.acquire(blocking=False):
        return {"returnCode": None, "stdout": "", "stderr": "ssh busy; keepalive skipped"}
    try:
        return _run_remote_script_unlocked(
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=timeout_seconds,
        )
    finally:
        SSH_LOCK.release()


def _run_remote_script_unlocked(
    *,
    script: str,
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_seconds: float,
) -> dict:
    script = adapt_board_script(script)
    remote = f"bash -lc {shlex.quote(script)}"
    plink_bin = shutil.which("plink") or shutil.which("plink.exe")
    if password and os.name == "nt" and plink_bin:
        plink_hostkey = resolve_plink_hostkey(host=host, port=port, user=user)
        command = build_plink_command(
            plink_bin=plink_bin,
            host=host,
            port=port,
            user=user,
            password=password,
            remote=remote,
            hostkey=plink_hostkey,
        )
        try:
            result = run_local_command(command, timeout_seconds=timeout_seconds)
        except subprocess.TimeoutExpired:
            return {"returnCode": -1, "stdout": "", "stderr": f"Timed out after {timeout_seconds:.1f}s"}
        if result.returncode != 0 and not plink_hostkey:
            learned_hostkey = extract_plink_hostkey(result.stderr)
            if learned_hostkey:
                PLINK_HOSTKEY_CACHE[plink_cache_key(host=host, port=port, user=user)] = learned_hostkey
                retry_command = build_plink_command(
                    plink_bin=plink_bin,
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    remote=remote,
                    hostkey=learned_hostkey,
                )
                try:
                    result = run_local_command(retry_command, timeout_seconds=timeout_seconds)
                except subprocess.TimeoutExpired:
                    return {"returnCode": -1, "stdout": "", "stderr": f"Timed out after {timeout_seconds:.1f}s"}
        return {
            "returnCode": result.returncode,
            "stdout": redact_password(result.stdout, password),
            "stderr": redact_password(result.stderr, password),
        }
    control_options = ssh_control_options(host=host, port=port, user=user)
    base = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "NumberOfPasswordPrompts=1",
        *control_options,
        "-p",
        str(port),
        f"{user}@{host}",
        remote,
    ]
    if password:
        if ssh_control_path(host=host, port=port, user=user).exists():
            warm_command = [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=8",
                "-o",
                "NumberOfPasswordPrompts=0",
                *control_options,
                "-p",
                str(port),
                f"{user}@{host}",
                remote,
            ]
            try:
                result = run_local_command(warm_command, timeout_seconds=timeout_seconds)
            except subprocess.TimeoutExpired:
                return {"returnCode": -1, "stdout": "", "stderr": f"Timed out after {timeout_seconds:.1f}s"}
            if result.returncode != 255:
                return {
                    "returnCode": result.returncode,
                    "stdout": redact_password(result.stdout, password),
                    "stderr": redact_password(result.stderr, password),
                }
        for attempt in range(max(0, SSH_CONNECT_RETRIES) + 1):
            result = run_ssh_with_expect(base, password=password, timeout_seconds=timeout_seconds)
            if not is_transient_ssh_failure(result) or attempt >= SSH_CONNECT_RETRIES:
                return result
            time.sleep(SSH_RETRY_DELAY_SECONDS)

    command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        *control_options,
        "-p",
        str(port),
        f"{user}@{host}",
        remote,
    ]
    try:
        result = run_local_command(command, timeout_seconds=timeout_seconds)
    except subprocess.TimeoutExpired:
        return {"returnCode": -1, "stdout": "", "stderr": f"Timed out after {timeout_seconds:.1f}s"}
    return {"returnCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


class ShenzhenConsoleServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address,
        handler_class,
        *,
        registry: dict,
        host: str,
        board_port: int,
        user: str,
        timeout_seconds: float,
        password: str,
        camera_sampler: CameraSampler,
    ):
        super().__init__(server_address, handler_class)
        self.registry = registry
        self.board_host = host
        self.board_port = board_port
        self.board_user = user
        self.timeout_seconds = timeout_seconds
        self.password = password
        self.camera_sampler = camera_sampler
        self.lock = Lock()
        self.queue: list[dict] = []
        self.current_job: dict | None = None
        self.celebration_process: subprocess.Popen | None = None
        self.celebration_started_at: str | None = None
        self.celebration_last_return_code: int | None = None
        self.book_follow_process: subprocess.Popen | None = None
        self.book_follow_config = coerce_book_follow_config()
        self.book_follow_started_at: str | None = None
        self.book_follow_last_return_code: int | None = None
        self.book_follow_last_forward: dict | None = None
        self.resource_manager = ResourceManager(default_ttl_seconds=240.0)
        self.show_state = {
            "status": "idle",
            "activeStep": None,
            "lastStep": None,
            "lastError": None,
            "updatedAt": timestamp(),
            "book": copy.deepcopy(BOOK_PROFILES["yellow_book"]),
            "photo": {
                "lastSnapshot": None,
                "lastMode": None,
                "renderJobs": [],
                "reprintJobs": [],
            },
        }
        self.worker_active = False
        self.position_refresh_running = False
        self.servo_control_running = False
        self.servo_hold_process: subprocess.Popen[str] | None = None
        self.state = {
            "running": False,
            "current": None,
            "lastResult": None,
            "servoControl": {
                "running": False,
                "error": None,
                "updatedAt": None,
            },
            "servoPositions": {
                "values": {},
                "updatedAt": None,
                "running": False,
                "error": None,
                "host": None,
                "port": None,
                "user": None,
            },
            "servoRecord": {
                **servo_speed_preset_config("medium"),
                "records": [],
                "lastSavedPath": None,
            },
            "servoHold": {
                "running": False,
                "servoId": None,
                "direction": None,
                "speedPreset": "medium",
                "speedLabel": servo_speed_preset_config("medium")["label"],
                "step": servo_speed_preset_config("medium")["step"],
                "intervalMs": int(round(servo_hold_interval_seconds("medium") * 1000)),
                "sessionId": None,
                "startedAt": None,
                "updatedAt": None,
                "error": None,
            },
            "teachMotion": {
                "running": False,
                "status": "idle",
                "error": None,
                "rawPath": TEACH_REMOTE_RAW,
                "rawExists": False,
                "frameCount": None,
                "durationMs": None,
                "updatedAt": None,
                "lastAction": None,
            },
            "queue": [],
            "history": [],
        }

    def camera_snapshot(self) -> dict:
        snapshot = copy.deepcopy(self.camera_sampler.snapshot())
        latest = snapshot.get("latestFrame")
        if latest:
            filename = latest.get("filename")
            if filename:
                image_url = str(latest.get("imageUrl") or "")
                suffix = ""
                if "?" in image_url:
                    suffix = "?" + image_url.split("?", 1)[1]
                latest["imageUrl"] = f"/api/camera/image/{filename}{suffix}"
        return snapshot

    def _persist_show_files(self) -> None:
        status = self.show_status()
        write_json_atomic(SHOW_RUNTIME_DIR / "locks.json", status["lockDetails"])
        write_json_atomic(SHOW_RUNTIME_DIR / "current_feedback.json", status)

    def scene_by_id(self, scene_id: str) -> dict | None:
        return next((scene for scene in self.registry["scenes"] if scene["id"] == scene_id), None)

    def update_show_state(self, *, step: str | None = None, status: str | None = None, error: str | None = None) -> None:
        with self.lock:
            if step is not None:
                self.show_state["activeStep"] = step
                self.show_state["lastStep"] = step
            if status is not None:
                self.show_state["status"] = status
            self.show_state["lastError"] = error
            self.show_state["updatedAt"] = timestamp()
        self._persist_show_files()

    def show_status(self) -> dict:
        book_follow = self.book_follow_snapshot()
        summary = book_follow.get("summary") or {}
        target_subclass = summary.get("targetSubclass")
        book_locked = bool(book_follow.get("running")) and bool(summary.get("targetPresent")) and target_subclass == "yellow_book"
        with self.lock:
            show_state = copy.deepcopy(self.show_state)
        book_profile = copy.deepcopy(BOOK_PROFILES["yellow_book"])
        photo_state = copy.deepcopy(show_state.get("photo") or {})
        photo_state.setdefault("lastSnapshot", None)
        photo_state.setdefault("lastMode", None)
        photo_state.setdefault("renderJobs", [])
        photo_state.setdefault("reprintJobs", [])
        return {
            "ok": True,
            "activeStep": show_state.get("activeStep"),
            "lastStep": show_state.get("lastStep"),
            "status": show_state.get("status"),
            "lastError": show_state.get("lastError"),
            "updatedAt": show_state.get("updatedAt"),
            "locks": self.resource_manager.owner_map(),
            "lockDetails": self.resource_manager.snapshot(),
            "book": {
                **book_profile,
                "locked": book_locked,
                "detector": summary.get("detector") or "-",
                "targetSubclass": target_subclass or "-",
                "summaryText": book_profile["summary"],
            },
            "photo": photo_state,
            "bookFollow": book_follow,
        }

    def printer_health(self) -> dict:
        token = read_printer_bridge_token()
        bridge_health: dict
        printer_status: dict
        try:
            bridge_health = request_json(f"{PRINTER_BRIDGE_URL}/health", timeout=3.0)
            bridge_ok = bool(bridge_health.get("ok"))
        except Exception as exc:  # noqa: BLE001
            bridge_health = {"ok": False, "error": str(exc)}
            bridge_ok = False

        if not token:
            printer_status = {"ok": False, "error": "missing OPENCLAW_PRINTER_BRIDGE_TOKEN"}
        else:
            try:
                printer_status = request_json(
                    f"{PRINTER_BRIDGE_URL}/v1/printers/default",
                    token=token,
                    timeout=5.0,
                )
            except Exception as exc:  # noqa: BLE001
                printer_status = {"ok": False, "error": str(exc)}

        return {
            "ok": bool(bridge_ok and printer_status.get("ok")),
            "bridgeUrl": PRINTER_BRIDGE_URL,
            "tokenConfigured": bool(token),
            "bridge": bridge_health,
            "printer": printer_status,
            "updatedAt": timestamp(),
        }

    def _url_healthy(self, url: str, timeout: float = 1.2) -> tuple[bool, str | None]:
        try:
            with urlopen(url, timeout=timeout) as response:
                return 200 <= response.status < 500, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _celebration_page_healthy(self, timeout: float = 1.2) -> tuple[bool, str | None]:
        return self._url_healthy(CELEBRATION_LOCAL_PAGE_URL, timeout=timeout)

    def _fallback_lan_host(self) -> str:
        configured = os.environ.get("MIRA_LAN_HOST") or os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST")
        if configured:
            return configured.strip()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                host = sock.getsockname()[0]
                if host:
                    return host
        except OSError:
            pass
        return "127.0.0.1"

    def celebration_page_url(self, request_host: str | None = None) -> str:
        host = (request_host or "").split(",", 1)[0].strip()
        if host.startswith("["):
            host = host.split("]", 1)[0].lstrip("[")
        else:
            host = host.split(":", 1)[0]
        if not host or host in {"0.0.0.0", "127.0.0.1", "localhost", "::1"}:
            host = self._fallback_lan_host()
        return f"http://{host}:{CELEBRATION_CONSOLE_PORT}/08_celebrate/index.html"

    def _celebration_port_pids(self) -> list[int]:
        try:
            result = subprocess.run(
                ["lsof", "-tiTCP:%d" % CELEBRATION_CONSOLE_PORT, "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                timeout=1.5,
                check=False,
            )
        except Exception:  # noqa: BLE001
            return []
        pids: list[int] = []
        for line in result.stdout.splitlines():
            try:
                pids.append(int(line.strip()))
            except ValueError:
                pass
        return pids

    def _is_our_celebration_pid(self, pid: int) -> bool:
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True,
                text=True,
                timeout=1.5,
                check=False,
            )
        except Exception:  # noqa: BLE001
            return False
        command = result.stdout.strip()
        return (
            "mira-light-shenzhen-console/shenzhen_console.py" in command
            or str(CELEBRATION_CONSOLE_SCRIPT) in command
            or (
                "shenzhen_console.py" in command
                and f"--port {CELEBRATION_CONSOLE_PORT}" in command
            )
        )

    def _stop_stale_celebration_processes(self) -> list[int]:
        stopped: list[int] = []
        for pid in self._celebration_port_pids():
            if not self._is_our_celebration_pid(pid):
                continue
            try:
                os.kill(pid, 15)
                stopped.append(pid)
            except ProcessLookupError:
                pass
        if stopped:
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if not self._celebration_port_pids():
                    break
                time.sleep(0.15)
        return stopped

    def ensure_celebration_page(self, request_host: str | None = None) -> tuple[dict, int]:
        page_url = self.celebration_page_url(request_host)
        healthy, error = self._celebration_page_healthy()
        if healthy:
            public_healthy, public_error = self._url_healthy(page_url, timeout=0.8)
            if not public_healthy:
                error = public_error
                self._stop_stale_celebration_processes()
                healthy = False

        if healthy:
            return {
                "ok": True,
                "running": True,
                "url": page_url,
                "localUrl": CELEBRATION_LOCAL_PAGE_URL,
                "reason": "already-running",
                "startedAt": self.celebration_started_at,
                "lastReturnCode": self.celebration_last_return_code,
                "updatedAt": timestamp(),
            }, 200

        if self.celebration_process is not None and self.celebration_process.poll() is not None:
            self.celebration_last_return_code = self.celebration_process.returncode
            unregister_process(self.celebration_process)
            self.celebration_process = None

        stopped = self._stop_stale_celebration_processes()
        pids = self._celebration_port_pids()
        if pids:
            return {
                "ok": False,
                "running": False,
                "url": page_url,
                "localUrl": CELEBRATION_LOCAL_PAGE_URL,
                "error": "Celebration port is occupied by another process",
                "port": CELEBRATION_CONSOLE_PORT,
                "pids": pids,
                "lastHealthError": error,
                "updatedAt": timestamp(),
            }, 409

        if not CELEBRATION_CONSOLE_SCRIPT.is_file():
            return {
                "ok": False,
                "running": False,
                "url": page_url,
                "localUrl": CELEBRATION_LOCAL_PAGE_URL,
                "error": f"Missing celebration console script: {CELEBRATION_CONSOLE_SCRIPT}",
                "updatedAt": timestamp(),
            }, 502

        CELEBRATION_CONSOLE_LOG.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("MIRA_SHENZHEN_BOARD_PASSWORD", self.password or "")
        env.setdefault("MIRA_SHENZHEN_SCRIPTS_DIR", str(SCRIPTS_DIR))
        env.setdefault(
            "MIRA_SHENZHEN_DIGUA_OUTPUT_DIR",
            str(CELEBRATION_CONSOLE_DIR / "runtime" / "digua-console-output"),
        )
        command = [
            sys.executable,
            "-u",
            str(CELEBRATION_CONSOLE_SCRIPT),
            "--host",
            CELEBRATION_CONSOLE_HOST,
            "--port",
            str(CELEBRATION_CONSOLE_PORT),
            "--board-host",
            self.board_host,
            "--board-port",
            str(self.board_port),
            "--board-user",
            self.board_user,
        ]
        log_file = CELEBRATION_CONSOLE_LOG.open("a", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=str(REPO_ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
        )
        log_file.close()
        register_process(process)
        self.celebration_process = process
        self.celebration_started_at = timestamp()
        self.celebration_last_return_code = None
        CELEBRATION_CONSOLE_PID.write_text(f"{process.pid}\n", encoding="utf-8")

        deadline = time.monotonic() + 5.0
        last_error = error
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.celebration_last_return_code = process.returncode
                unregister_process(process)
                self.celebration_process = None
                return {
                    "ok": False,
                    "running": False,
                    "url": page_url,
                    "localUrl": CELEBRATION_LOCAL_PAGE_URL,
                    "error": "Celebration console exited before becoming healthy",
                    "returnCode": process.returncode,
                    "logTail": tail_text(CELEBRATION_CONSOLE_LOG),
                    "updatedAt": timestamp(),
                }, 502
            healthy, last_error = self._celebration_page_healthy(timeout=0.6)
            if healthy:
                return {
                    "ok": True,
                    "running": True,
                    "url": page_url,
                    "localUrl": CELEBRATION_LOCAL_PAGE_URL,
                    "reason": "started",
                    "pid": process.pid,
                    "stoppedStalePids": stopped,
                    "startedAt": self.celebration_started_at,
                    "updatedAt": timestamp(),
                }, 200
            time.sleep(0.2)

        return {
            "ok": False,
            "running": process.poll() is None,
            "url": page_url,
            "localUrl": CELEBRATION_LOCAL_PAGE_URL,
            "error": f"Celebration page did not become healthy: {last_error}",
            "pid": process.pid if process.poll() is None else None,
            "logTail": tail_text(CELEBRATION_CONSOLE_LOG),
            "updatedAt": timestamp(),
        }, 502

    def reset_show(self) -> dict:
        self.resource_manager.clear()
        with self.lock:
            self.show_state = {
                "status": "idle",
                "activeStep": None,
                "lastStep": None,
                "lastError": None,
                "updatedAt": timestamp(),
                "book": copy.deepcopy(BOOK_PROFILES["yellow_book"]),
                "photo": {
                    "lastSnapshot": None,
                    "lastMode": None,
                    "renderJobs": [],
                    "reprintJobs": [],
                },
            }
        self._persist_show_files()
        return self.show_status()

    def _teach_busy_reason_locked(self) -> str | None:
        teach = self.state.get("teachMotion") or {}
        if teach.get("running"):
            return "teach recording is already running"
        if self.current_job is not None or self.queue or self.worker_active:
            return "action queue is busy"
        if self.position_refresh_running:
            return "servo position refresh is running"
        if self.servo_control_running:
            return "manual servo control is running"
        return None

    def _set_teach_state(self, payload: dict) -> dict:
        with self.lock:
            current = dict(self.state.get("teachMotion") or {})
            current.update(payload)
            current["updatedAt"] = timestamp()
            self.state["teachMotion"] = current
            return copy.deepcopy(current)

    def teach_status(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> dict:
        result = run_remote_script(
            script=render_teach_status_script(),
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 12.0),
        )
        status = parse_teach_status(result)
        status["status"] = "recording" if status["running"] else ("ready" if status["rawExists"] else "idle")
        status["error"] = None if result.get("returnCode") == 0 else (result.get("stderr") or result.get("stdout") or "teach status failed")
        return self._set_teach_state(status)

    def start_teach_recording(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> tuple[dict, dict]:
        with self.lock:
            reason = self._teach_busy_reason_locked()
            if reason:
                raise RuntimeError(reason)
            self.state["teachMotion"] = {
                **self.state["teachMotion"],
                "running": True,
                "status": "starting",
                "error": None,
                "lastAction": "start",
                "updatedAt": timestamp(),
            }

        install_script = render_teach_install_script()
        start_script = f"""{install_script}
set -euo pipefail
old_pid="$(cat {shlex.quote(TEACH_REMOTE_PID)} 2>/dev/null || true)"
if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
  echo "recording already running: $old_pid"
  exit 2
fi
rm -f {shlex.quote(TEACH_REMOTE_PID)}
nohup python3 {shlex.quote(TEACH_REMOTE_SCRIPT)} record \
  --name unified_teach \
  --duration {TEACH_RECORD_DURATION_SECONDS} \
  --sample-ms {TEACH_RECORD_SAMPLE_MS} \
  --torque-mode {shlex.quote(TEACH_RECORD_TORQUE_MODE)} \
  --output {shlex.quote(TEACH_REMOTE_RAW)} \
  > {shlex.quote(TEACH_REMOTE_LOG)} 2>&1 < /dev/null &
echo $! > {shlex.quote(TEACH_REMOTE_PID)}
sleep 1.2
{render_teach_status_script()}
"""
        result = run_remote_script(
            script=start_script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 20.0),
        )
        status = parse_teach_status(result)
        ok = result.get("returnCode") == 0 and status.get("running")
        payload = {
            **status,
            "status": "recording" if ok else "error",
            "error": None if ok else (result.get("stderr") or result.get("stdout") or "failed to start teach recording"),
            "lastAction": "start",
        }
        return self._set_teach_state(payload), result

    def stop_teach_recording(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> tuple[dict, dict]:
        stop_script = f"""set +e
mkdir -p {shlex.quote(TEACH_REMOTE_DIR)}
pid="$(cat {shlex.quote(TEACH_REMOTE_PID)} 2>/dev/null || true)"
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
  kill -TERM "$pid" 2>/dev/null || true
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 0.2
  done
fi
python3 {REMOTE_DESKTOP_DIR}/four_servo_control.py torque on >> {shlex.quote(TEACH_REMOTE_LOG)} 2>&1 || true
{render_teach_status_script()}
"""
        result = run_remote_script(
            script=stop_script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 20.0),
        )
        status = parse_teach_status(result)
        ok = result.get("returnCode") == 0 and not status.get("running")
        payload = {
            **status,
            "running": False,
            "status": "ready" if status.get("rawExists") else "idle",
            "error": None if ok else (result.get("stderr") or result.get("stdout") or "failed to stop teach recording"),
            "lastAction": "stop",
        }
        return self._set_teach_state(payload), result

    def play_teach_motion(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> tuple[dict, dict]:
        with self.lock:
            reason = self._teach_busy_reason_locked()
            if reason:
                raise RuntimeError(reason)
            self.state["teachMotion"] = {
                **self.state["teachMotion"],
                "status": "playing",
                "error": None,
                "lastAction": "play",
                "updatedAt": timestamp(),
            }
        play_script = f"""{render_teach_install_script()}
set -euo pipefail
test -s {shlex.quote(TEACH_REMOTE_RAW)}
python3 {shlex.quote(TEACH_REMOTE_SCRIPT)} play {shlex.quote(TEACH_REMOTE_RAW)} --speed-scale {TEACH_PLAY_SPEED_SCALE}
{render_teach_status_script()}
"""
        result = run_remote_script(
            script=play_script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=max(60.0, min(timeout_seconds, 360.0)),
        )
        status = parse_teach_status(result)
        ok = result.get("returnCode") == 0
        payload = {
            **status,
            "running": False,
            "status": "ready" if status.get("rawExists") else "idle",
            "error": None if ok else (result.get("stderr") or result.get("stdout") or "teach playback failed"),
            "lastAction": "play",
        }
        return self._set_teach_state(payload), result

    def play_answer_demo(self, body: dict) -> tuple[dict, int]:
        import answer_demo  # Local module with the tunable TIMELINE.

        audio_path = Path(body.get("audioPath") or ANSWER_AUDIO_PATH).expanduser().resolve()
        script = answer_demo.render_board_script()
        if body.get("dryRun"):
            return {
                "ok": True,
                "dryRun": True,
                "audio": {
                    "path": str(audio_path),
                    "exists": audio_path.is_file(),
                    "delaySeconds": answer_demo.AUDIO_DELAY_SECONDS,
                },
                "timelineMarkers": len(answer_demo.TIMELINE),
                "timeline": answer_demo.normalized_timeline(),
                "script": script,
            }, 200

        owner = "answer_demo"
        resources = [
            {"resource": "servo_motion", "mode": "exclusive"},
            {"resource": "audio_output", "mode": "exclusive"},
        ]
        self.resource_manager.acquire(owner, resources, ttl_seconds=45.0, metadata={"step": "answer_demo"})
        host = port = user = None
        started = time.monotonic()
        try:
            host = str(body.get("host") or self.board_host)
            port = int(body.get("port") or self.board_port)
            user = str(body.get("user") or self.board_user)
            password = str(body.get("password") or self.password or "")
            timeout = float(body.get("timeoutSeconds") or max(self.timeout_seconds, 30.0))
            with self.lock:
                self.state["running"] = True
                self.state["current"] = {"kind": "answer-demo", "id": "answer_demo", "title": "演示答", "host": host, "port": port}
            audio = play_local_audio_after_delay(audio_path, answer_demo.AUDIO_DELAY_SECONDS)
            result = run_remote_script(
                script=script,
                host=host,
                port=port,
                user=user,
                password=password,
                timeout_seconds=timeout,
            )
            result["durationSeconds"] = round(time.monotonic() - started, 3)
            result["script"] = script
            result["host"] = host
            result["port"] = port
            result["user"] = user
            result["audio"] = audio
            result["timelineMarkers"] = len(answer_demo.TIMELINE)
            ok = result.get("returnCode") == 0
            entry = {
                "at": timestamp(),
                "kind": "answer-demo",
                "id": "answer_demo",
                "title": "演示答",
                "returnCode": result.get("returnCode"),
            }
            with self.lock:
                self.state["running"] = False
                self.state["current"] = None
                self.state["lastResult"] = {**entry, **result}
                self.state["history"] = [entry, *self.state["history"][:19]]
            self.update_show_state(
                step="answer_demo",
                status="book_explained" if ok else "error",
                error=None if ok else (result.get("stderr") or "Answer demo failed"),
            )
            return {"ok": ok, "result": result, "status": self.show_status()}, 200 if ok else 502
        finally:
            with self.lock:
                current = self.state.get("current") or {}
                if current.get("id") == "answer_demo":
                    self.state["running"] = False
                    self.state["current"] = None
            self.resource_manager.release_owner(owner)
            self._persist_show_files()

    def play_voice_motion_demo(self, body: dict) -> tuple[dict, int]:
        import voice_motion_demos

        demo_id = str(body.get("demo") or body.get("id") or "")
        demo = voice_motion_demos.get_demo(demo_id)
        audio_path = Path(body.get("audioPath") or ANSWER_AUDIO_PATH).expanduser().resolve()
        script = voice_motion_demos.render_board_script(demo)
        if body.get("dryRun"):
            payload = voice_motion_demos.demo_payload(demo, include_script=False)
            payload["audio"] = {
                "path": str(audio_path),
                "exists": audio_path.is_file(),
                "delaySeconds": demo.audio_delay_seconds,
                "enabled": bool(demo.uses_answer_audio and body.get("playAudio", demo.uses_answer_audio)),
            }
            payload["script"] = script
            return {"ok": True, "dryRun": True, "demo": payload}, 200

        owner = f"voice_motion:{demo.id}"
        play_audio = bool(demo.uses_answer_audio and body.get("playAudio", True))
        resources = [{"resource": "servo_motion", "mode": "exclusive"}]
        if play_audio:
            resources.append({"resource": "audio_output", "mode": "exclusive"})
        self.resource_manager.acquire(owner, resources, ttl_seconds=60.0, metadata={"demo": demo.id})
        started = time.monotonic()
        try:
            host, port, user, password, timeout = self._handler_connection(body)
            with self.lock:
                self.state["running"] = True
                self.state["current"] = {
                    "kind": "voice-motion-demo",
                    "id": demo.id,
                    "title": f"{demo.title}动作调试",
                    "host": host,
                    "port": port,
                }
            audio = None
            if play_audio:
                audio = play_local_audio_after_delay(audio_path, demo.audio_delay_seconds)
            result = run_remote_script(
                script=script,
                host=host,
                port=port,
                user=user,
                password=password,
                timeout_seconds=max(float(timeout), 30.0),
            )
            result["durationSeconds"] = round(time.monotonic() - started, 3)
            result["script"] = script
            result["host"] = host
            result["port"] = port
            result["user"] = user
            result["demo"] = voice_motion_demos.demo_payload(demo, include_script=False)
            result["audio"] = audio
            ok = result.get("returnCode") == 0
            entry = {
                "at": timestamp(),
                "kind": "voice-motion-demo",
                "id": demo.id,
                "title": f"{demo.title}动作调试",
                "returnCode": result.get("returnCode"),
            }
            with self.lock:
                self.state["running"] = False
                self.state["current"] = None
                self.state["lastResult"] = {**entry, **result}
                self.state["history"] = [entry, *self.state["history"][:19]]
            self.update_show_state(
                step=f"voice_motion:{demo.id}",
                status="book_explained" if demo.id == "answer" and ok else ("idle" if ok else "error"),
                error=None if ok else (result.get("stderr") or f"{demo.title} motion demo failed"),
            )
            return {"ok": ok, "result": result, "status": self.show_status()}, 200 if ok else 502
        finally:
            with self.lock:
                current = self.state.get("current") or {}
                if current.get("kind") == "voice-motion-demo" and current.get("id") == demo.id:
                    self.state["running"] = False
                    self.state["current"] = None
            self.resource_manager.release_owner(owner)
            self._persist_show_files()

    def _handler_connection(self, body: dict) -> tuple[str, int, str, str, float]:
        host = str(body.get("host") or self.board_host)
        port = int(body.get("port") or self.board_port)
        user = str(body.get("user") or self.board_user)
        password = str(body.get("password") or self.password or "")
        timeout = float(body.get("timeoutSeconds") or self.timeout_seconds)
        return host, port, user, password, timeout

    def book_follow_paths(self, config: dict | None = None) -> dict[str, Path]:
        selected = config or self.book_follow_config
        runtime_dir = Path(selected["runtimeDir"]).expanduser().resolve()
        return {
            "runtimeDir": runtime_dir,
            "latestEvent": runtime_dir / "vision.latest.json",
            "bridgeState": runtime_dir / "vision.bridge.state.json",
            "eventsJsonl": runtime_dir / "vision.events.jsonl",
            "log": runtime_dir / "vision-stack.log",
        }

    def book_follow_receiver_url(self, config: dict | None = None, *, local: bool = False) -> str:
        del local
        selected = config or self.book_follow_config
        receiver_host = str(selected.get("receiverHost") or "0.0.0.0")
        if receiver_host in {"0.0.0.0", "::"}:
            receiver_host = "127.0.0.1"
        return f"http://{receiver_host}:{selected['receiverPort']}/upload"

    def forward_camera_frame_to_book_follow(self, image_path: Path, frame: dict) -> dict:
        del frame
        process = self.book_follow_process
        running = bool(process and process.poll() is None)
        if not running:
            result = {
                "ok": False,
                "skipped": True,
                "reason": "book-follow not running",
                "filename": image_path.name,
                "updatedAt": timestamp(),
            }
            self.book_follow_last_forward = result
            return result

        upload_url = self.book_follow_receiver_url(local=True)
        payload = image_path.read_bytes()
        if len(payload) < 512 or not payload.startswith(b"\xff\xd8"):
            result = {
                "ok": False,
                "skipped": True,
                "reason": "invalid JPEG frame",
                "url": upload_url,
                "filename": image_path.name,
                "sizeBytes": len(payload),
                "updatedAt": timestamp(),
            }
            self.book_follow_last_forward = result
            return result

        req = Request(
            upload_url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "image/jpeg",
                "Content-Length": str(len(payload)),
                "X-Seq": image_path.stem,
                "X-Timestamp": str(time.time()),
            },
        )
        try:
            with urlopen(req, timeout=3) as response:
                response.read()
                result = {
                    "ok": 200 <= response.status < 300,
                    "status": response.status,
                    "url": upload_url,
                    "filename": image_path.name,
                    "sizeBytes": len(payload),
                    "updatedAt": timestamp(),
                }
        except (OSError, TimeoutError, url_error.URLError) as exc:
            result = {
                "ok": False,
                "status": None,
                "url": upload_url,
                "filename": image_path.name,
                "sizeBytes": len(payload),
                "error": str(exc),
                "updatedAt": timestamp(),
            }
        self.book_follow_last_forward = result
        return result

    def book_follow_snapshot(self) -> dict:
        process = self.book_follow_process
        running = bool(process and process.poll() is None)
        if process is not None and not running:
            self.book_follow_last_return_code = process.poll()
            unregister_process(process)
            self.book_follow_process = None
        paths = self.book_follow_paths()
        latest_event = read_json_file(paths["latestEvent"])
        bridge_state = read_json_file(paths["bridgeState"])
        summary = summarize_book_follow_event(latest_event, bridge_state)
        return {
            "ok": True,
            "running": running,
            "pid": process.pid if running and process is not None else None,
            "startedAt": self.book_follow_started_at,
            "lastReturnCode": self.book_follow_last_return_code,
            "config": copy.deepcopy(self.book_follow_config),
            "receiverUrl": self.book_follow_receiver_url(local=False),
            "lastForward": copy.deepcopy(self.book_follow_last_forward),
            "paths": {key: str(value) for key, value in paths.items()},
            "latestEvent": latest_event,
            "bridgeState": bridge_state,
            "summary": summary,
            "logTail": tail_text(paths["log"]),
            "updatedAt": timestamp(),
        }

    def start_book_follow(self, raw_config: dict | None = None) -> tuple[dict, str | None]:
        if not BOOK_FOLLOW_SCRIPT.is_file():
            return self.book_follow_snapshot(), f"Missing book-follow script: {BOOK_FOLLOW_SCRIPT}"
        process = self.book_follow_process
        if process is not None and process.poll() is None:
            return self.book_follow_snapshot(), "already-running"
        try:
            self.resource_manager.acquire(
                "book_follow",
                [
                    {"resource": "servo_motion", "mode": "exclusive"},
                    {"resource": "camera_stream", "mode": "read"},
                ],
                ttl_seconds=3600.0,
                metadata={"step": "book_follow"},
            )
        except ResourceConflict as exc:
            return self.book_follow_snapshot(), f"resource-conflict:{exc.resource}"
        config = coerce_book_follow_config(raw_config)
        paths = self.book_follow_paths(config)
        paths["runtimeDir"].mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.update(build_book_follow_env(config))
        log_file = paths["log"].open("a", encoding="utf-8")
        command = ["bash", str(BOOK_FOLLOW_SCRIPT)]
        process = subprocess.Popen(
            command,
            cwd=str(REPO_ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        log_file.close()
        register_process(process)
        self.book_follow_process = process
        self.book_follow_config = config
        self.book_follow_started_at = timestamp()
        self.book_follow_last_return_code = None
        time.sleep(0.35)
        if process.poll() is not None:
            self.book_follow_last_return_code = process.returncode
            unregister_process(process)
            self.book_follow_process = None
            self.resource_manager.release_owner("book_follow")
            return self.book_follow_snapshot(), "exited-early"
        self.update_show_state(step="book_follow", status="book_following")
        return self.book_follow_snapshot(), None

    def stop_book_follow(self) -> dict:
        process = self.book_follow_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
            finally:
                unregister_process(process)
        if process is not None:
            self.book_follow_last_return_code = process.poll()
        self.book_follow_process = None
        self.resource_manager.release_owner("book_follow")
        with self.lock:
            if self.show_state.get("activeStep") == "book_follow":
                self.show_state["status"] = "idle"
                self.show_state["activeStep"] = None
                self.show_state["updatedAt"] = timestamp()
        self._persist_show_files()
        return self.book_follow_snapshot()

    def latest_stream_frame_path(self) -> Path | None:
        paths = self.book_follow_paths()
        captures_dir = paths["runtimeDir"] / "captures"
        candidates: list[Path] = []
        if captures_dir.is_dir():
            candidates.extend(captures_dir.rglob("*.jpg"))
        latest = self.camera_sampler.snapshot().get("latestFrame") or {}
        latest_path = latest.get("path")
        if latest_path:
            candidates.append(Path(str(latest_path)).expanduser())
        existing = [path for path in candidates if path.is_file()]
        if not existing:
            return None
        return max(existing, key=lambda path: path.stat().st_mtime_ns)

    def latest_camera_frame_path(self) -> Path | None:
        latest = self.camera_sampler.snapshot().get("latestFrame") or {}
        latest_path = latest.get("path")
        if not latest_path:
            return None
        path = Path(str(latest_path)).expanduser()
        return path if path.is_file() else None

    def _copy_photo_snapshot(self, source_path: Path, *, mode: str) -> Path:
        SHOW_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        suffix = source_path.suffix if source_path.suffix.lower() in {".jpg", ".jpeg", ".png"} else ".jpg"
        output_path = SHOW_PHOTO_DIR / f"mira-show-{mode}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}{suffix}"
        shutil.copy2(source_path, output_path)
        return output_path

    def _record_photo_state(self, *, snapshot_path: Path, mode: str, render_job: dict | None = None) -> None:
        with self.lock:
            photo = self.show_state.setdefault("photo", {})
            photo["lastSnapshot"] = str(snapshot_path)
            photo["lastMode"] = mode
            if render_job is not None:
                jobs = list(photo.get("renderJobs") or [])
                photo["renderJobs"] = [render_job, *jobs[:9]]
            self.show_state["status"] = "photo_done"
            if mode == "stream_snapshot":
                self.show_state["activeStep"] = "photo_snapshot"
            elif mode == "highres_exclusive":
                self.show_state["activeStep"] = "photo_highres"
            else:
                self.show_state["activeStep"] = mode
            self.show_state["lastStep"] = self.show_state["activeStep"]
            self.show_state["lastError"] = None
            self.show_state["updatedAt"] = timestamp()
        self._persist_show_files()

    def _update_render_job(self, job_id: str, updates: dict) -> None:
        with self.lock:
            jobs = list((self.show_state.get("photo") or {}).get("renderJobs") or [])
            for job in jobs:
                if job.get("id") == job_id:
                    job.update(updates)
                    job["updatedAt"] = timestamp()
                    break
            self.show_state.setdefault("photo", {})["renderJobs"] = jobs
        self._persist_show_files()

    def _append_render_job(self, job: dict) -> None:
        with self.lock:
            photo = self.show_state.setdefault("photo", {})
            jobs = list(photo.get("renderJobs") or [])
            photo["renderJobs"] = [job, *jobs[:9]]
            self.show_state["status"] = "photo_print_retry"
            self.show_state["activeStep"] = "reprint_latest_render"
            self.show_state["lastStep"] = "reprint_latest_render"
            self.show_state["lastError"] = None
            self.show_state["updatedAt"] = timestamp()
        self._persist_show_files()

    def _append_reprint_job(self, job: dict) -> None:
        with self.lock:
            photo = self.show_state.setdefault("photo", {})
            jobs = list(photo.get("reprintJobs") or [])
            photo["reprintJobs"] = [job, *jobs[:19]]
            self.show_state["status"] = "photo_print_retry"
            self.show_state["activeStep"] = "reprint_latest_render"
            self.show_state["lastStep"] = "reprint_latest_render"
            self.show_state["lastError"] = None
            self.show_state["updatedAt"] = timestamp()
        self._persist_show_files()

    def _update_reprint_job(self, job_id: str, updates: dict) -> None:
        with self.lock:
            photo = self.show_state.setdefault("photo", {})
            jobs = list(photo.get("reprintJobs") or [])
            for job in jobs:
                if job.get("id") == job_id:
                    job.update(updates)
                    job["updatedAt"] = timestamp()
                    break
            photo["reprintJobs"] = jobs
            self.show_state["updatedAt"] = timestamp()
        self._persist_show_files()

    def reprint_jobs_snapshot(self) -> dict:
        with self.lock:
            jobs = list((self.show_state.get("photo") or {}).get("reprintJobs") or [])
        return {"ok": True, "reprintJobs": copy.deepcopy(jobs), "updatedAt": timestamp()}

    def _submit_render_output_to_printer(self, output_path: Path) -> dict:
        token = read_printer_bridge_token()
        if not token:
            raise RuntimeError("missing OPENCLAW_PRINTER_BRIDGE_TOKEN")
        return request_json(
            f"{PRINTER_BRIDGE_URL}/v1/printers/default/print-image",
            method="POST",
            token=token,
            timeout=40.0,
            payload={
                "content_base64": base64.b64encode(output_path.read_bytes()).decode("ascii"),
                "filename": output_path.name,
                "media": SHOW_PRINT_MEDIA,
                "copies": 1,
                "fit_to_page": True,
            },
        )

    def latest_render_output_path(self) -> Path | None:
        with self.lock:
            jobs = list((self.show_state.get("photo") or {}).get("renderJobs") or [])
        for job in jobs:
            raw_path = job.get("renderOutput") or (job.get("renderResult") or {}).get("output_path")
            if not raw_path:
                continue
            path = Path(str(raw_path)).expanduser()
            if path.is_file():
                return path
        return None

    def _render_print_worker(
        self,
        *,
        owner: str,
        job_id: str,
        snapshot_path: Path,
        render: bool,
        print_requested: bool,
        style_prompt: str | None = None,
    ) -> None:
        output_path = snapshot_path
        try:
            self._update_render_job(job_id, {"status": "running"})
            if render:
                if not ROKID_RENDER_SCRIPT.is_file():
                    raise FileNotFoundError(f"Missing render script: {ROKID_RENDER_SCRIPT}")
                command = [
                    os.environ.get("PYTHON", "python3"),
                    str(ROKID_RENDER_SCRIPT),
                    "--image-path",
                    str(snapshot_path),
                    "--output-dir",
                    str(SHOW_RENDER_DIR),
                    "--style-slug",
                    "mira-show-anime",
                ]
                if style_prompt:
                    command.extend(["--style-prompt", style_prompt])
                completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=480)
                if completed.returncode != 0:
                    raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "render failed")
                parsed = json.loads(completed.stdout)
                output_path = Path(str(parsed.get("output_path") or snapshot_path))
                self._update_render_job(job_id, {"renderOutput": str(output_path), "renderResult": parsed})
            if print_requested:
                print_result = self._submit_render_output_to_printer(output_path)
                self._update_render_job(job_id, {"printResult": print_result})
            self._update_render_job(job_id, {"status": "done"})
        except Exception as exc:  # noqa: BLE001 - background status should be visible instead of crashing the console.
            self._update_render_job(job_id, {"status": "failed", "error": str(exc)})
        finally:
            self.resource_manager.release_owner(owner)
            self._persist_show_files()

    def _build_render_print_job(
        self,
        *,
        snapshot_path: Path,
        render: bool,
        print_requested: bool,
        style_prompt: str | None = None,
        trigger: str = "show-photo",
    ) -> dict:
        job = {
            "id": uuid4().hex,
            "status": "pending",
            "snapshotPath": str(snapshot_path),
            "render": render,
            "print": print_requested,
            "trigger": trigger,
            "stylePrompt": style_prompt,
            "createdAt": timestamp(),
            "updatedAt": timestamp(),
        }
        return job

    def _start_render_print_job(self, *, owner: str, job: dict, snapshot_path: Path) -> None:
        Thread(
            target=self._render_print_worker,
            kwargs={
                "owner": owner,
                "job_id": job["id"],
                "snapshot_path": snapshot_path,
                "render": bool(job.get("render")),
                "print_requested": bool(job.get("print")),
                "style_prompt": str(job.get("stylePrompt") or "") or None,
            },
            daemon=True,
        ).start()

    def render_print_latest_camera_frame(self, body: dict | None = None) -> tuple[dict, int]:
        body = body or {}
        owner = "camera_latest_render_print"
        style_prompt = str(body.get("stylePrompt") or SHOW_LATEST_FRAME_PRINT_PROMPT)
        if body.get("dryRun"):
            source_path = self.latest_camera_frame_path()
            return {
                "ok": source_path is not None,
                "dryRun": True,
                "sourcePath": str(source_path) if source_path else None,
                "stylePrompt": style_prompt,
                "render": True,
                "print": True,
                "error": None if source_path else "No current camera frame is available yet",
                "status": self.show_status(),
            }, 200 if source_path else 404
        try:
            self.resource_manager.acquire(
                owner,
                [
                    {"resource": "camera_stream", "mode": "read"},
                    {"resource": "render_print", "mode": "exclusive"},
                ],
                ttl_seconds=600.0,
                metadata={"mode": "latest_camera_render_print"},
            )
        except ResourceConflict as exc:
            return {"ok": False, "error": str(exc), "conflict": exc.as_payload(), "status": self.show_status()}, 409

        try:
            source_path = self.latest_camera_frame_path()
            if source_path is None:
                raise FileNotFoundError("No current camera frame is available yet")
            snapshot_path = self._copy_photo_snapshot(source_path, mode="latest_frame_print")
            render_job = self._build_render_print_job(
                snapshot_path=snapshot_path,
                render=True,
                print_requested=True,
                style_prompt=style_prompt,
                trigger="latest-camera-frame",
            )
            self.resource_manager.release_owner(owner, resources=["camera_stream"])
            self._record_photo_state(snapshot_path=snapshot_path, mode="latest_frame_print", render_job=render_job)
            self._start_render_print_job(owner=owner, job=render_job, snapshot_path=snapshot_path)
            return {
                "ok": True,
                "mode": "latest_frame_print",
                "snapshotPath": str(snapshot_path),
                "renderJob": render_job,
                "status": self.show_status(),
            }, 200
        except Exception as exc:  # noqa: BLE001
            self.resource_manager.release_owner(owner)
            self.update_show_state(step=owner, status="error", error=str(exc))
            return {"ok": False, "error": str(exc), "status": self.show_status()}, 502

    def reprint_latest_rendered_image(self) -> tuple[dict, int]:
        owner = "camera_latest_render_reprint"
        try:
            self.resource_manager.acquire(
                owner,
                [{"resource": "render_print", "mode": "exclusive"}],
                ttl_seconds=90.0,
                metadata={"mode": "reprint_latest_render"},
            )
        except ResourceConflict as exc:
            return {"ok": False, "error": str(exc), "conflict": exc.as_payload(), "status": self.show_status()}, 409

        output_path = self.latest_render_output_path()
        if output_path is None:
            self.resource_manager.release_owner(owner)
            return {"ok": False, "error": "No rendered image is available yet", "status": self.show_status()}, 404

        job = self._build_render_print_job(
            snapshot_path=output_path,
            render=False,
            print_requested=True,
            trigger="reprint-latest-render",
        )
        job["renderOutput"] = str(output_path)
        job["sourceRenderOutput"] = str(output_path)
        self._append_reprint_job(job)
        try:
            self._update_reprint_job(job["id"], {"status": "running", "stage": "submitting"})
            print_result = self._submit_render_output_to_printer(output_path)
            self._update_reprint_job(job["id"], {"status": "done", "stage": "sent", "printResult": print_result})
            return {
                "ok": True,
                "mode": "reprint_latest_render",
                "outputPath": str(output_path),
                "renderJob": job,
                "printResult": print_result,
                "status": self.show_status(),
            }, 200
        except Exception as exc:  # noqa: BLE001
            self._update_reprint_job(job["id"], {"status": "failed", "stage": "failed", "error": str(exc)})
            return {
                "ok": False,
                "error": str(exc),
                "outputPath": str(output_path),
                "renderJob": job,
                "status": self.show_status(),
            }, 502
        finally:
            self.resource_manager.release_owner(owner)

    def capture_show_photo(self, body: dict | None = None) -> tuple[dict, int]:
        body = body or {}
        mode = str(body.get("mode") or "stream_snapshot")
        render = bool(body.get("render", False))
        print_requested = bool(body.get("print", False))
        if mode not in {"stream_snapshot", "highres_exclusive"}:
            return {"ok": False, "error": f"Unknown photo mode: {mode}"}, 400

        owner = "photo_snapshot" if mode == "stream_snapshot" else "photo_highres"
        requirements: list[dict[str, str]] = []
        if mode == "stream_snapshot":
            requirements.append({"resource": "camera_stream", "mode": "read"})
        else:
            requirements.append({"resource": "camera_capture", "mode": "exclusive"})
        if render or print_requested:
            requirements.append({"resource": "render_print", "mode": "exclusive"})

        paused_config = copy.deepcopy(self.book_follow_config)
        should_resume_book_follow = False
        if mode == "highres_exclusive" and self.book_follow_snapshot().get("running"):
            should_resume_book_follow = True
            self.stop_book_follow()
        should_resume_camera_watch = False
        if mode == "highres_exclusive" and self.camera_sampler.running:
            should_resume_camera_watch = True
            self.camera_sampler.stop()

        try:
            self.resource_manager.acquire(owner, requirements, ttl_seconds=600.0, metadata={"mode": mode})
        except ResourceConflict as exc:
            if should_resume_book_follow:
                self.start_book_follow(paused_config)
            return {"ok": False, "error": str(exc), "conflict": exc.as_payload(), "status": self.show_status()}, 409

        render_job = None
        snapshot_path: Path | None = None
        try:
            if mode == "stream_snapshot":
                source_path = self.latest_stream_frame_path()
                if source_path is None:
                    raise FileNotFoundError("No latest stream frame is available yet")
                snapshot_path = self._copy_photo_snapshot(source_path, mode=mode)
            else:
                frame = self.camera_sampler.capture_once()
                source_path = Path(str(frame["path"]))
                snapshot_path = self._copy_photo_snapshot(source_path, mode=mode)

            if render or print_requested:
                render_job = self._build_render_print_job(
                    snapshot_path=snapshot_path,
                    render=render,
                    print_requested=print_requested,
                    style_prompt=str(body.get("stylePrompt") or "") or None,
                )
                self.resource_manager.release_owner(owner, resources=["camera_stream", "camera_capture"])
            else:
                self.resource_manager.release_owner(owner)

            self._record_photo_state(snapshot_path=snapshot_path, mode=mode, render_job=render_job)
            if render_job is not None:
                self._start_render_print_job(owner=owner, job=render_job, snapshot_path=snapshot_path)
            if should_resume_book_follow:
                self.start_book_follow(paused_config)
            if should_resume_camera_watch:
                self.camera_sampler.start()
            return {
                "ok": True,
                "mode": mode,
                "snapshotPath": str(snapshot_path),
                "renderJob": render_job,
                "resumedBookFollow": should_resume_book_follow,
                "status": self.show_status(),
            }, 200
        except Exception as exc:  # noqa: BLE001
            self.resource_manager.release_owner(owner)
            if should_resume_book_follow:
                self.start_book_follow(paused_config)
            if should_resume_camera_watch:
                self.camera_sampler.start()
            self.update_show_state(step=owner, status="error", error=str(exc))
            return {"ok": False, "error": str(exc), "status": self.show_status()}, 502

    def _job_view(self, job: dict) -> dict:
        return {
            "queueId": job["queueId"],
            "kind": job["kind"],
            "itemId": job["itemId"],
            "title": job["title"],
            "status": job["status"],
            "queuedAt": job["queuedAt"],
            "startedAt": job.get("startedAt"),
            "runMode": job.get("runMode", "remote"),
            "host": job.get("host"),
            "port": job.get("port"),
            "user": job.get("user"),
        }

    def _current_view(self) -> dict | None:
        if self.current_job is None:
            return None
        job = self.current_job
        return {
            "kind": job["kind"],
            "id": job["itemId"],
            "queueId": job["queueId"],
            "title": job["title"],
            "runMode": job.get("runMode", "remote"),
            "host": job.get("host"),
            "port": job.get("port"),
        }

    def _refresh_queue_state_locked(self) -> None:
        queue = []
        if self.current_job is not None:
            queue.append(self._job_view(self.current_job))
        queue.extend(self._job_view(job) for job in self.queue)
        self.state["running"] = self.current_job is not None
        self.state["current"] = self._current_view()
        self.state["queue"] = queue

    def snapshot_state(self) -> dict:
        with self.lock:
            return copy.deepcopy(self.state)

    def _servo_record_snapshot_locked(self) -> dict:
        current = copy.deepcopy(self.state.get("servoRecord") or {})
        preset = servo_speed_preset_name(current.get("id") or current.get("speedPreset") or "medium")
        config = servo_speed_preset_config(preset)
        records = list(current.get("records") or [])
        return {
            **config,
            "records": records,
            "lastSavedPath": current.get("lastSavedPath"),
        }

    def _servo_hold_snapshot_locked(self) -> dict:
        current = copy.deepcopy(self.state.get("servoHold") or {})
        preset = servo_speed_preset_name(current.get("speedPreset") or "medium")
        config = servo_speed_preset_config(preset)
        return {
            "running": bool(current.get("running")),
            "servoId": current.get("servoId"),
            "direction": current.get("direction"),
            "speedPreset": preset,
            "speedLabel": config["label"],
            "step": config["step"],
            "intervalMs": int(round(servo_hold_interval_seconds(preset) * 1000)),
            "sessionId": current.get("sessionId"),
            "startedAt": current.get("startedAt"),
            "updatedAt": current.get("updatedAt"),
            "error": current.get("error"),
        }

    def set_servo_speed_preset(self, raw_preset: object) -> dict:
        preset = servo_speed_preset_name(raw_preset)
        with self.lock:
            current = self._servo_record_snapshot_locked()
            self.state["servoRecord"] = {
                **servo_speed_preset_config(preset),
                "records": current.get("records") or [],
                "lastSavedPath": current.get("lastSavedPath"),
            }
            return copy.deepcopy(self.state["servoRecord"])

    def record_servo_frame(self, raw_preset: object | None = None) -> tuple[dict | None, str | None]:
        preset = servo_speed_preset_name(raw_preset or self.state.get("servoRecord", {}).get("id") or "medium")
        with self.lock:
            values = dict(self.state.get("servoPositions", {}).get("values") or {})
            if not values:
                return None, "请先读取或微调舵机位置。"
            record_state = self._servo_record_snapshot_locked()
            config = servo_speed_preset_config(preset)
            record = {
                "index": len(record_state.get("records") or []) + 1,
                "at": timestamp(),
                "positions": {str(index): int(values.get(str(index), 0)) for index in range(4)},
                "speedPreset": config["id"],
                "speedLabel": config["label"],
                "step": config["step"],
                "speeds": list(config["speeds"]),
            }
            records = [*(record_state.get("records") or []), record]
            self.state["servoRecord"] = {
                **config,
                "records": records,
                "lastSavedPath": record_state.get("lastSavedPath"),
            }
            return copy.deepcopy(record), None

    def clear_servo_records(self) -> dict:
        with self.lock:
            current = self._servo_record_snapshot_locked()
            self.state["servoRecord"] = {
                **servo_speed_preset_config(current["id"]),
                "records": [],
                "lastSavedPath": None,
            }
            return copy.deepcopy(self.state["servoRecord"])

    def save_servo_records(self) -> tuple[str | None, str | None]:
        with self.lock:
            record_state = self._servo_record_snapshot_locked()
            records = list(record_state.get("records") or [])
        if not records:
            return None, "没有可保存的记录。"

        DEFAULT_SERVO_RECORD_DIR.mkdir(parents=True, exist_ok=True)
        target = DEFAULT_SERVO_RECORD_DIR / f"servo-record-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        payload = {
            "savedAt": timestamp(),
            "format": "mira-light-servo-record-v1",
            "speedPreset": record_state["id"],
            "records": records,
            "count": len(records),
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with self.lock:
            self.state["servoRecord"] = {
                **servo_speed_preset_config(record_state["id"]),
                "records": records,
                "lastSavedPath": str(target),
            }
        return str(target), None

    def _should_start_worker_locked(self) -> bool:
        if self.queue and not self.worker_active and not self.position_refresh_running and not self.servo_control_running:
            self.worker_active = True
            return True
        return False

    def _start_worker(self) -> None:
        Thread(target=self._queue_worker_loop, daemon=True).start()

    def enqueue_job(
        self,
        *,
        kind: str,
        item_id: str,
        title: str,
        script: str,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
        run_mode: str = "remote",
        local_command: list[str] | None = None,
        local_env: dict[str, str] | None = None,
        redact_values: list[str] | None = None,
        lock_owner: str | None = None,
        local_audio_path: str | None = None,
        local_audio_delay_seconds: float = 0.0,
    ) -> dict:
        job = {
            "queueId": uuid4().hex,
            "kind": kind,
            "itemId": item_id,
            "title": title,
            "script": script,
            "runMode": run_mode,
            "localCommand": local_command,
            "localEnv": local_env or {},
            "redactValues": redact_values or [],
            "lockOwner": lock_owner,
            "localAudioPath": local_audio_path,
            "localAudioDelaySeconds": local_audio_delay_seconds,
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "timeoutSeconds": timeout_seconds,
            "status": "pending",
            "queuedAt": timestamp(),
        }
        should_start_worker = False
        with self.lock:
            self.queue.append(job)
            queued = self._job_view(job)
            self._refresh_queue_state_locked()
            should_start_worker = self._should_start_worker_locked()
        if should_start_worker:
            self._start_worker()
        return queued

    def refresh_servo_positions(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> tuple[dict | None, str | None]:
        with self.lock:
            if self.current_job is not None or self.queue or self.worker_active or self.servo_control_running:
                return None, "busy"
            if self.position_refresh_running:
                return None, "refreshing"
            previous_updated_at = self.state["servoPositions"].get("updatedAt")
            self.position_refresh_running = True
            self.state["servoPositions"] = {
                **self.state["servoPositions"],
                "running": True,
                "error": None,
                "host": host,
                "port": port,
                "user": user,
            }

        started = time.monotonic()
        payload = {
            **self.state["servoPositions"],
            "running": False,
            "error": "Servo position refresh did not complete",
            "warning": None,
            "host": host,
            "port": port,
            "user": user,
            "returnCode": -1,
            "durationSeconds": 0.0,
        }
        try:
            try:
                result = run_remote_script(
                    script=SERVO_POSITION_SCRIPT,
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    timeout_seconds=min(timeout_seconds, 20.0),
                )
            except Exception as exc:  # noqa: BLE001 - keep the dashboard alive on read failures.
                result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}
            result["durationSeconds"] = round(time.monotonic() - started, 3)
            result["script"] = SERVO_POSITION_SCRIPT
            result["host"] = host
            result["port"] = port
            result["user"] = user

            values = parse_servo_positions(result.get("stdout", ""))
            warning = compact_remote_warning(result) if values else None
            error = None if values else (result.get("stderr") or result.get("stdout") or "No servo positions returned")
            payload = {
                "values": values,
                "updatedAt": timestamp() if values else previous_updated_at,
                "running": False,
                "error": error,
                "warning": warning,
                "host": host,
                "port": port,
                "user": user,
                "returnCode": result.get("returnCode"),
                "durationSeconds": result.get("durationSeconds"),
            }
        except Exception as exc:  # noqa: BLE001 - the state flag must always be released.
            payload = {
                "values": {},
                "updatedAt": previous_updated_at,
                "running": False,
                "error": str(exc),
                "warning": None,
                "host": host,
                "port": port,
                "user": user,
                "returnCode": -1,
                "durationSeconds": round(time.monotonic() - started, 3),
            }
        finally:
            should_start_worker = False
            with self.lock:
                self.position_refresh_running = False
                self.state["servoPositions"] = payload
                should_start_worker = self._should_start_worker_locked()
        if should_start_worker:
            self._start_worker()
        return payload, None

    def set_manual_servo_pose(
        self,
        *,
        positions: dict[str, int],
        speed_preset: str = "medium",
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> tuple[dict | None, dict | None, str | None]:
        with self.lock:
            if self.current_job is not None or self.queue or self.worker_active:
                return None, None, "busy"
            if self.position_refresh_running:
                return None, None, "refreshing"
            if self.servo_control_running:
                return None, None, "controlling"
            previous_values = dict(self.state["servoPositions"].get("values", {}))
            previous_updated_at = self.state["servoPositions"].get("updatedAt")
            self.servo_control_running = True
            self.state["servoControl"] = {
                "running": True,
                "error": None,
                "updatedAt": self.state["servoControl"].get("updatedAt"),
            }

        preset = servo_speed_preset_name(speed_preset)
        script = render_servo_pose_script(positions, servo_speed_preset_speeds(preset))
        started = time.monotonic()
        try:
            result = run_remote_script(
                script=script,
                host=host,
                port=port,
                user=user,
                password=password,
                timeout_seconds=min(timeout_seconds, 20.0),
            )
        except Exception as exc:  # noqa: BLE001 - keep manual control errors visible.
            result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}
        result["durationSeconds"] = round(time.monotonic() - started, 3)
        result["script"] = script
        result["host"] = host
        result["port"] = port
        result["user"] = user

        ok = result.get("returnCode") == 0
        error = None if ok else (result.get("stderr") or result.get("stdout") or "Manual servo command failed")
        payload = {
            "values": positions if ok else previous_values,
            "updatedAt": timestamp() if ok else previous_updated_at,
            "running": False,
            "error": error,
            "host": host,
            "port": port,
            "user": user,
            "returnCode": result.get("returnCode"),
            "durationSeconds": result.get("durationSeconds"),
        }

        should_start_worker = False
        with self.lock:
            self.servo_control_running = False
            self.state["servoControl"] = {
                "running": False,
                "error": error,
                "updatedAt": timestamp(),
            }
            self.state["servoPositions"] = payload
            current_record_state = self._servo_record_snapshot_locked()
            self.state["servoRecord"] = {
                **servo_speed_preset_config(preset),
                "records": current_record_state.get("records") or [],
                "lastSavedPath": current_record_state.get("lastSavedPath"),
            }
            should_start_worker = self._should_start_worker_locked()
        if should_start_worker:
            self._start_worker()
        return payload, result, None

    def _servo_hold_runner(
        self,
        *,
        process: subprocess.Popen[str],
        session_id: str,
        servo_id: str,
        direction: int,
        step: int,
        interval_seconds: float,
        host: str,
        port: int,
        user: str,
        speed_preset: str,
    ) -> None:
        poll_interval = min(0.02, max(0.01, interval_seconds / 2.0))
        next_tick = time.monotonic() + interval_seconds
        stdout = ""
        stderr = ""
        return_code = None
        try:
            while True:
                if process.poll() is not None:
                    break
                now = time.monotonic()
                if now >= next_tick:
                    with self.lock:
                        hold_state = self._servo_hold_snapshot_locked()
                        if hold_state.get("sessionId") != session_id or not hold_state.get("running"):
                            break
                        current = dict(self.state["servoPositions"].get("values") or {})
                        if servo_id in current:
                            current[servo_id] = clamp_servo_position(int(current[servo_id]) + direction * step)
                            self.state["servoPositions"] = {
                                **self.state["servoPositions"],
                                "values": current,
                                "updatedAt": timestamp(),
                                "running": False,
                                "error": None,
                                "host": host,
                                "port": port,
                                "user": user,
                            }
                            self.state["servoHold"] = {
                                **hold_state,
                                "updatedAt": timestamp(),
                                "error": None,
                            }
                    next_tick += interval_seconds
                time.sleep(poll_interval)
        finally:
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=0.4)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                        process.wait(timeout=0.4)
                    except Exception:
                        pass
                except Exception:
                    pass
            try:
                stdout, stderr = process.communicate(timeout=0.2)
            except Exception:
                stdout = ""
                stderr = ""
            unregister_process(process)
            return_code = process.returncode
            error = None if return_code in (0, -15) else (stderr.strip() or stdout.strip() or "continuous servo hold stopped unexpectedly")
            should_start_worker = False
            with self.lock:
                if self.servo_hold_process is process:
                    self.servo_hold_process = None
                current_hold = self._servo_hold_snapshot_locked()
                if current_hold.get("sessionId") == session_id:
                    self.servo_control_running = False
                    self.state["servoControl"] = {
                        "running": False,
                        "error": error,
                        "updatedAt": timestamp(),
                    }
                    self.state["servoHold"] = {
                        **current_hold,
                        "running": False,
                        "updatedAt": timestamp(),
                        "error": error,
                    }
                    should_start_worker = self._should_start_worker_locked()
            if should_start_worker:
                self._start_worker()

    def start_servo_hold(
        self,
        *,
        servo_id: str,
        direction: int,
        speed_preset: str,
        positions: dict[str, int] | None,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> tuple[dict | None, dict | None, str | None]:
        servo_id = validate_servo_id(servo_id)
        direction = validate_servo_direction(direction)
        preset = servo_speed_preset_name(speed_preset)
        if self.servo_hold_process and self.servo_hold_process.poll() is None:
            return None, None, "holding"
        with self.lock:
            if self.current_job is not None or self.queue or self.worker_active:
                return None, None, "busy"
            if self.position_refresh_running:
                return None, None, "refreshing"
            if self.servo_control_running:
                return None, None, "controlling"
            current_values = dict(self.state["servoPositions"].get("values") or {})
            if positions:
                current_values.update({str(index): int(positions[str(index)]) for index in range(4)})
            if any(str(index) not in current_values for index in range(4)):
                return None, None, "missing_positions"
            current_values = {str(index): clamp_servo_position(current_values[str(index)]) for index in range(4)}
            self.state["servoPositions"] = {
                **self.state["servoPositions"],
                "values": current_values,
                "host": host,
                "port": port,
                "user": user,
            }
            self.servo_control_running = True
            session_id = uuid4().hex
            self.state["servoControl"] = {
                "running": True,
                "error": None,
                "updatedAt": self.state["servoControl"].get("updatedAt"),
            }
            self.state["servoHold"] = {
                "running": True,
                "servoId": servo_id,
                "direction": direction,
                "speedPreset": preset,
                "speedLabel": servo_speed_preset_config(preset)["label"],
                "step": servo_speed_preset_config(preset)["step"],
                "intervalMs": int(round(servo_hold_interval_seconds(preset) * 1000)),
                "sessionId": session_id,
                "startedAt": timestamp(),
                "updatedAt": timestamp(),
                "error": None,
            }

        warmup = run_remote_script(
            script="true\n",
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=min(timeout_seconds, 10.0),
        )
        if warmup.get("returnCode") != 0:
            with self.lock:
                self.servo_control_running = False
                self.state["servoControl"] = {
                    "running": False,
                    "error": warmup.get("stderr") or warmup.get("stdout") or "servo hold warmup failed",
                    "updatedAt": timestamp(),
                }
                self.state["servoHold"] = {
                    **self._servo_hold_snapshot_locked(),
                    "running": False,
                    "updatedAt": timestamp(),
                    "error": self.state["servoControl"]["error"],
                }
            return None, warmup, "start_failed"

        interval_seconds = servo_hold_interval_seconds(preset)
        step = int(servo_speed_preset_config(preset)["step"])
        remote_script = render_servo_hold_loop_script(
            positions=current_values,
            servo_id=servo_id,
            direction=direction,
            step=step,
            speeds=servo_speed_preset_speeds(preset),
            interval_seconds=interval_seconds,
        )
        remote = f"bash -lc {shlex.quote(adapt_board_script(remote_script))}"
        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            *ssh_control_options(host=host, port=port, user=user),
            "-p",
            str(port),
            f"{user}@{host}",
            remote,
        ]
        try:
            process = subprocess.Popen(
                command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                self.servo_control_running = False
                self.state["servoControl"] = {
                    "running": False,
                    "error": str(exc),
                    "updatedAt": timestamp(),
                }
                self.state["servoHold"] = {
                    **self._servo_hold_snapshot_locked(),
                    "running": False,
                    "updatedAt": timestamp(),
                    "error": str(exc),
                }
            return None, {"returnCode": -1, "stdout": "", "stderr": str(exc)}, "start_failed"

        register_process(process)
        with self.lock:
            self.servo_hold_process = process
        Thread(
            target=self._servo_hold_runner,
            kwargs={
                "process": process,
                "session_id": session_id,
                "servo_id": servo_id,
                "direction": direction,
                "step": step,
                "interval_seconds": interval_seconds,
                "host": host,
                "port": port,
                "user": user,
                "speed_preset": preset,
            },
            daemon=True,
        ).start()
        return copy.deepcopy(self.state["servoPositions"]), warmup, None

    def stop_servo_hold(self) -> tuple[dict, dict]:
        process = None
        with self.lock:
            process = self.servo_hold_process
            current_hold = self._servo_hold_snapshot_locked()
            self.state["servoHold"] = {
                **current_hold,
                "running": False,
                "updatedAt": timestamp(),
                "error": current_hold.get("error"),
            }
            self.state["servoControl"] = {
                "running": False,
                "error": self.state["servoControl"].get("error"),
                "updatedAt": timestamp(),
            }
            self.servo_control_running = False
            servo_positions = copy.deepcopy(self.state["servoPositions"])
            hold_state = copy.deepcopy(self.state["servoHold"])
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                    process.wait(timeout=0.5)
                except Exception:
                    pass
            except Exception:
                pass
        return hold_state, servo_positions

    def delete_pending_job(self, queue_id: str) -> tuple[dict | None, str | None]:
        with self.lock:
            if self.current_job is not None and self.current_job["queueId"] == queue_id:
                return None, "running"
            for index, job in enumerate(self.queue):
                if job["queueId"] == queue_id:
                    removed = self.queue.pop(index)
                    removed["status"] = "removed"
                    self._refresh_queue_state_locked()
                    return self._job_view(removed), None
        return None, "not_found"

    def force_stop_to_neutral(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout_seconds: float,
    ) -> dict:
        with self.lock:
            removed_count = len(self.queue)
            for job in self.queue:
                job["status"] = "removed"
            self.queue.clear()
            self.state["running"] = True
            self.state["current"] = {
                "kind": "emergency",
                "id": "force_stop_neutral",
                "title": "强停归位",
                "host": host,
                "port": port,
            }
            self._refresh_queue_state_locked()

        stopped_processes = terminate_active_processes()
        started = time.monotonic()
        try:
            result = run_remote_script(
                script=EMERGENCY_STOP_SCRIPT,
                host=host,
                port=port,
                user=user,
                password=password,
                timeout_seconds=min(timeout_seconds, 30.0),
            )
        except Exception as exc:  # noqa: BLE001 - emergency result must be surfaced to the console.
            result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}

        result["durationSeconds"] = round(time.monotonic() - started, 3)
        result["script"] = EMERGENCY_STOP_SCRIPT
        result["host"] = host
        result["port"] = port
        result["user"] = user
        result["stoppedProcesses"] = stopped_processes
        result["clearedQueueItems"] = removed_count

        entry = {
            "at": timestamp(),
            "kind": "emergency",
            "id": "force_stop_neutral",
            "title": "强停归位",
            "returnCode": result.get("returnCode"),
        }
        values = parse_servo_positions(result.get("stdout", ""))
        with self.lock:
            self.state["lastResult"] = {**entry, **result}
            self.state["history"] = [entry, *self.state["history"][:19]]
            if values:
                self.state["servoPositions"] = {
                    "values": values,
                    "updatedAt": entry["at"],
                    "running": False,
                    "error": None,
                    "host": host,
                    "port": port,
                    "user": user,
                    "returnCode": result.get("returnCode"),
                    "durationSeconds": result.get("durationSeconds"),
                }
            self._refresh_queue_state_locked()
        self.resource_manager.clear()
        self.update_show_state(step="emergency_stop", status="idle", error=None)
        return result

    def _record_result_locked(self, *, job: dict, result: dict) -> None:
        entry = {
            "at": timestamp(),
            "kind": job["kind"],
            "id": job["itemId"],
            "queueId": job["queueId"],
            "title": job["title"],
            "returnCode": result.get("returnCode"),
        }
        self.state["lastResult"] = {**entry, **result}
        self.state["history"] = [entry, *self.state["history"][:19]]
        if job["itemId"] == "read_positions" and result.get("returnCode") == 0:
            values = parse_servo_positions(result.get("stdout", ""))
            if values:
                self.state["servoPositions"] = {
                    "values": values,
                    "updatedAt": entry["at"],
                    "running": False,
                    "error": None,
                    "host": result.get("host"),
                    "port": result.get("port"),
                    "user": result.get("user"),
                    "returnCode": result.get("returnCode"),
                    "durationSeconds": result.get("durationSeconds"),
                }

    def _run_job(self, job: dict) -> dict:
        started = time.monotonic()
        audio = None
        try:
            if job.get("localAudioPath"):
                audio = play_local_audio_after_delay(
                    Path(str(job["localAudioPath"])).expanduser().resolve(),
                    float(job.get("localAudioDelaySeconds") or 0.0),
                )
            if job.get("runMode") == "local":
                result = run_local_action_command(
                    command=job["localCommand"],
                    env=job["localEnv"],
                    timeout_seconds=job["timeoutSeconds"],
                    redact_values=job.get("redactValues", []),
                )
            else:
                result = run_remote_script(
                    script=job["script"],
                    host=job["host"],
                    port=job["port"],
                    user=job["user"],
                    password=job["password"],
                    timeout_seconds=job["timeoutSeconds"],
                )
        except Exception as exc:  # noqa: BLE001 - surface queue failures to the console.
            result = {"returnCode": -1, "stdout": "", "stderr": str(exc)}
        result["durationSeconds"] = round(time.monotonic() - started, 3)
        result["script"] = job["script"]
        result["runMode"] = job.get("runMode", "remote")
        result["host"] = job.get("host")
        result["port"] = job.get("port")
        result["user"] = job.get("user")
        if audio is not None:
            result["audio"] = audio
        return result

    def _queue_error_result(self, job: dict, exc: Exception, started: float) -> dict:
        return {
            "returnCode": -1,
            "stdout": "",
            "stderr": f"Queue worker error: {type(exc).__name__}: {exc}",
            "durationSeconds": round(time.monotonic() - started, 3),
            "script": job.get("script", ""),
            "host": job.get("host"),
            "port": job.get("port"),
            "user": job.get("user"),
        }

    def _queue_worker_loop(self) -> None:
        while True:
            with self.lock:
                if not self.queue:
                    self.current_job = None
                    self.worker_active = False
                    self._refresh_queue_state_locked()
                    return
                job = self.queue.pop(0)
                job["status"] = "running"
                job["startedAt"] = timestamp()
                self.current_job = job
                self._refresh_queue_state_locked()

            started = time.monotonic()
            try:
                result = self._run_job(job)
            except Exception as exc:  # noqa: BLE001 - never leave the queue wedged on worker bugs.
                result = self._queue_error_result(job, exc, started)

            with self.lock:
                job["status"] = "done" if result.get("returnCode") == 0 else "failed"
                job["finishedAt"] = timestamp()
                self._record_result_locked(job=job, result=result)
                self.current_job = None
                self._refresh_queue_state_locked()
            if job.get("lockOwner"):
                self.resource_manager.release_owner(str(job["lockOwner"]))
                ok = result.get("returnCode") == 0
                self.update_show_state(
                    step=job["itemId"],
                    status=SHOW_STATES_BY_STEP.get(job["itemId"], self.show_state.get("status", "idle")) if ok else "error",
                    error=None if ok else (result.get("stderr") or "Show step failed"),
                )


class ShenzhenConsoleHandler(BaseHTTPRequestHandler):
    server: ShenzhenConsoleServer

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print(f"[unified-console] {self.address_string()} - {format % args}")

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "image/jpeg")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def _serve_static(self, raw_path: str) -> None:
        path = raw_path or "/"
        if path == "/":
            path = "/index.html"
        target = (WEB_ROOT / path.lstrip("/")).resolve()
        try:
            target.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self._send_json(403, {"ok": False, "error": "Forbidden"})
            return
        if not target.is_file():
            self._send_json(404, {"ok": False, "error": "Not found"})
            return
        content = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_camera_image(self, raw_filename: str) -> None:
        filename = unquote(raw_filename)
        frame = self.server.camera_sampler.frame_path(filename)
        if frame is None:
            self._send_json(404, {"ok": False, "error": "Camera frame not found"})
            return
        self._send_file(frame)

    def _send_camera_error(self, exc: Exception) -> None:
        status = 409 if "capture already in progress" in str(exc) else 502
        self._send_json(status, {"ok": False, "error": str(exc), "state": self.server.camera_snapshot()})

    def _scene_by_id(self, scene_id: str) -> dict | None:
        return next((scene for scene in self.server.registry["scenes"] if scene["id"] == scene_id), None)

    def _quick_action_by_id(self, action_id: str) -> dict | None:
        return next((action for action in self.server.registry["quickActions"] if action["id"] == action_id), None)

    def _scene_script_path(self, scene: dict) -> Path:
        target = (SCRIPTS_DIR / scene["script"]).resolve()
        target.relative_to(SCRIPTS_DIR.resolve())
        if not target.is_file():
            raise FileNotFoundError(f"Scene script not found: {scene['script']}")
        return target

    def _registry_script_path(self, item: dict) -> Path:
        target = (SCRIPTS_DIR / item["script"]).resolve()
        target.relative_to(SCRIPTS_DIR.resolve())
        if not target.is_file():
            raise FileNotFoundError(f"Script not found: {item['script']}")
        return target

    def _build_scene_script(self, scene: dict, body: dict) -> str:
        if "localScript" in scene:
            command, env_keys, _env, _redact_values = self._build_local_action_command(scene, body)
            return command_preview(command, env_keys=env_keys)
        script_path = self._registry_script_path(scene)
        command = [
            os.environ.get("PYTHON", "python3"),
            str(script_path),
            *expand_registry_args(scene.get("defaultArgs", [])),
            *parse_extra_args(body.get("extraArgs")),
        ]
        try:
            result = run_local_command(command, timeout_seconds=20.0)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Timed out while rendering scene script: {exc}") from exc
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Scene script failed")
        return result.stdout

    def _build_quick_action_script(self, action: dict, body: dict) -> str:
        if "localScript" in action:
            command, env_keys, _env, _redact_values = self._build_local_action_command(action, body)
            return command_preview(command, env_keys=env_keys)
        if "script" not in action:
            return render_remote_script(action["commands"])
        script_path = self._registry_script_path(action)
        command = [
            os.environ.get("PYTHON", "python3"),
            str(script_path),
            *expand_registry_args(action.get("defaultArgs", [])),
            *parse_extra_args(body.get("extraArgs")),
        ]
        try:
            result = run_local_command(command, timeout_seconds=20.0)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Timed out while rendering quick action script: {exc}") from exc
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Quick action script failed")
        return result.stdout

    def _local_script_path(self, action: dict) -> Path:
        script = str(action["localScript"])
        if script == "$JAVIS_DIGUA_RENDER_SCRIPT":
            target = JAVIS_DIGUA_RENDER_SCRIPT
        else:
            target = Path(script).expanduser()
            if not target.is_absolute():
                target = DEMO_ROOT / target
        target = target.resolve()
        if not target.is_file():
            raise FileNotFoundError(f"Local action script not found: {target}")
        return target

    def _build_local_action_command(self, action: dict, body: dict) -> tuple[list[str], list[str], dict[str, str], list[str]]:
        script_path = self._local_script_path(action)
        host, port, user, password, _timeout = self._connection_from_body(body)
        command = [
            os.environ.get("PYTHON", "python3"),
            str(script_path),
            "--host",
            host,
            "--port",
            str(port),
            "--user",
            user,
            *expand_registry_args(action.get("defaultArgs", [])),
            *parse_extra_args(body.get("extraArgs")),
        ]
        env = dict(os.environ)
        env_keys: list[str] = []
        if password:
            env["DIGUA_SSH_PASSWORD"] = password
            env_keys.append("DIGUA_SSH_PASSWORD")
        for key in action.get("requiredEnv", []):
            if key not in env_keys:
                env_keys.append(key)
        hydrate_env_from_keychain(env, env_keys)
        return command, env_keys, env, [password]

    def _connection_from_body(self, body: dict) -> tuple[str, int, str, str, float]:
        host = str(body.get("host") or self.server.board_host)
        port = int(body.get("port") or self.server.board_port)
        user = str(body.get("user") or self.server.board_user)
        password = str(body.get("password") or self.server.password or "")
        timeout = float(body.get("timeoutSeconds") or self.server.timeout_seconds)
        return host, port, user, password, timeout

    def _enqueue_script(
        self,
        *,
        kind: str,
        item_id: str,
        title: str,
        script: str,
        body: dict,
        local_audio_path: str | None = None,
        local_audio_delay_seconds: float = 0.0,
    ) -> dict:
        host, port, user, password, timeout = self._connection_from_body(body)
        return self.server.enqueue_job(
            kind=kind,
            item_id=item_id,
            title=title,
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=timeout,
            local_audio_path=local_audio_path,
            local_audio_delay_seconds=local_audio_delay_seconds,
        )

    def _enqueue_local_item(self, *, kind: str, item: dict, body: dict) -> dict:
        host, port, user, password, timeout = self._connection_from_body(body)
        command, env_keys, env, redact_values = self._build_local_action_command(item, body)
        timeout = float(item.get("timeoutSeconds") or timeout)
        return self.server.enqueue_job(
            kind=kind,
            item_id=item["id"],
            title=item["title"],
            script=command_preview(command, env_keys=env_keys),
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=timeout,
            run_mode="local",
            local_command=command,
            local_env=env,
            redact_values=redact_values,
        )

    def _enqueue_local_action(self, *, action: dict, body: dict) -> dict:
        return self._enqueue_local_item(kind="quick-action", item=action, body=body)

    def _enqueue_show_scene(self, *, step: str, scene_id: str, resources: list[dict[str, str]], body: dict) -> dict:
        owner = f"show:{step}"
        scene = self._scene_by_id(scene_id)
        if scene is None:
            raise FileNotFoundError(f"Unknown scene for show step {step}: {scene_id}")
        self.server.resource_manager.acquire(owner, resources, ttl_seconds=600.0, metadata={"step": step, "scene": scene_id})
        try:
            script = self._build_scene_script(scene, body)
            host, port, user, password, timeout = self._connection_from_body(body)
            queued = self.server.enqueue_job(
                kind="show-step",
                item_id=step,
                title=scene["title"],
                script=script,
                host=host,
                port=port,
                user=user,
                password=password,
                timeout_seconds=float(scene.get("timeoutSeconds") or timeout),
                lock_owner=owner,
            )
            self.server.update_show_state(step=step, status=SHOW_STATES_BY_STEP.get(step, "idle"))
            return queued
        except Exception:
            self.server.resource_manager.release_owner(owner)
            raise

    def _run_show_step(self, step: str, body: dict) -> tuple[dict, int]:
        if step == "book_follow":
            status, reason = self.server.start_book_follow(body)
            ok = reason in {None, "already-running"}
            return {"ok": ok, "reason": reason, "status": self.server.show_status(), "bookFollow": status}, 200 if ok else 409

        if step == "book_summary":
            owner = "show:book_summary"
            try:
                self.server.resource_manager.acquire(
                    owner,
                    [
                        {"resource": "camera_stream", "mode": "read"},
                        {"resource": "audio_output", "mode": "exclusive"},
                    ],
                    ttl_seconds=45.0,
                    metadata={"step": step},
                )
                profile = copy.deepcopy(BOOK_PROFILES["yellow_book"])
                self.server.update_show_state(step=step, status=SHOW_STATES_BY_STEP[step])
                payload = {"ok": True, "step": step, "book": profile}
            finally:
                self.server.resource_manager.release_owner(owner)
                self.server._persist_show_files()
            payload["status"] = self.server.show_status()
            return payload, 200

        if step == "answer_demo":
            return self.server.play_answer_demo(body)

        if step.startswith("voice_motion:"):
            demo_id = step.split(":", 1)[1].strip()
            if not demo_id:
                return {"ok": False, "error": "Missing voice motion demo id"}, 400
            payload = dict(body)
            payload["demo"] = demo_id
            payload["playAudio"] = demo_id == "answer"
            return self.server.play_voice_motion_demo(payload)

        if step == "photo_snapshot":
            return self.server.capture_show_photo({"mode": "stream_snapshot", "render": True, "print": False})

        if step == "photo_highres":
            return self.server.capture_show_photo({"mode": "highres_exclusive", "render": True, "print": True})

        if step in {"offer_celebrate", "photo_pose", "sleep", "wake_up", "touch",
                     "happy_dance", "sad_comfort", "curious_peek", "shy_blush",
                     "stretch_yawn", "alert_startle", "greeting_wave", "thinking_ponder",
                     "angry_pout", "proud_chest", "sleepy_drowse", "laugh_giggle",
                     "love_heart", "confused_lost", "bow_thanks", "excited_bounce"}:
            if step in {"offer_celebrate", "photo_pose", "sleep", "touch"} and self.server.book_follow_snapshot().get("running"):
                self.server.stop_book_follow()
            scene_map = {
                "wake_up": "01_presence_wake",
                "touch": "03_hand_nuzzle",
                "offer_celebrate": "04_offer_celebrate",
                "photo_pose": "08_photo_pose",
                "sleep": "06_sleep",
                "happy_dance": "11_happy_dance",
                "sad_comfort": "12_sad_comfort",
                "curious_peek": "13_curious_peek",
                "shy_blush": "14_shy_blush",
                "stretch_yawn": "15_stretch_yawn",
                "alert_startle": "16_alert_startle",
                "greeting_wave": "17_greeting_wave",
                "thinking_ponder": "18_thinking_ponder",
                "angry_pout": "19_angry_pout",
                "proud_chest": "20_proud_chest",
                "sleepy_drowse": "21_sleepy_drowse",
                "laugh_giggle": "22_laugh_giggle",
                "love_heart": "23_love_heart",
                "confused_lost": "24_confused_lost",
                "bow_thanks": "25_bow_thanks",
                "excited_bounce": "26_excited_bounce",
            }
            resources = [{"resource": "servo_motion", "mode": "exclusive"}]
            if step == "touch":
                resources.append({"resource": "touch_service", "mode": "exclusive"})
            queued = self._enqueue_show_scene(step=step, scene_id=scene_map[step], resources=resources, body=body)
            return {"ok": True, "queued": queued, "status": self.server.show_status()}, 202

        return {"ok": False, "error": f"Unknown show step: {step}"}, 400

    def _record_result(self, *, kind: str, item_id: str, title: str, result: dict) -> None:
        entry = {
            "at": timestamp(),
            "kind": kind,
            "id": item_id,
            "title": title,
            "returnCode": result.get("returnCode"),
        }
        with self.server.lock:
            self.server.state["running"] = False
            self.server.state["current"] = None
            self.server.state["lastResult"] = {**entry, **result}
            self.server.state["history"] = [entry, *self.server.state["history"][:19]]

    def _execute_script(self, *, kind: str, item_id: str, title: str, script: str, body: dict) -> dict:
        host, port, user, password, timeout = self._connection_from_body(body)
        with self.server.lock:
            self.server.state["running"] = True
            self.server.state["current"] = {"kind": kind, "id": item_id, "title": title, "host": host, "port": port}
        started = time.monotonic()
        result = run_remote_script(
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=timeout,
        )
        result["durationSeconds"] = round(time.monotonic() - started, 3)
        result["script"] = script
        result["host"] = host
        result["port"] = port
        result["user"] = user
        self._record_result(kind=kind, item_id=item_id, title=title, result=result)
        return result

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/health", "/api/health"}:
            self._send_json(200, {"ok": True})
            return
        if path == "/api/scenes":
            self._send_json(
                200,
                {
                    "ok": True,
                    "registry": self.server.registry,
                    "defaults": {
                        "host": self.server.board_host,
                        "port": self.server.board_port,
                        "user": self.server.board_user,
                        "scriptsDir": str(SCRIPTS_DIR),
                    },
                    "passwordConfigured": bool(self.server.password),
                },
            )
            return
        if path == "/api/state":
            state = self.server.snapshot_state()
            self._send_json(200, {"ok": True, "state": state})
            return
        if path == "/api/camera/latest":
            self._send_json(200, self.server.camera_snapshot())
            return
        if path.startswith("/api/camera/image/"):
            self._serve_camera_image(path.removeprefix("/api/camera/image/"))
            return
        if path == "/api/book-follow/status":
            self._send_json(200, self.server.book_follow_snapshot())
            return
        if path == "/api/show/status":
            self._send_json(200, self.server.show_status())
            return
        if path == "/api/celebration-page/ensure":
            payload, status = self.server.ensure_celebration_page(self.headers.get("Host"))
            self._send_json(status, payload)
            return
        if path == "/api/show/feedback":
            self._send_json(200, self.server.show_status())
            return
        if path == "/api/teach/status":
            status = self.server.teach_status(
                host=self.server.board_host,
                port=self.server.board_port,
                user=self.server.board_user,
                password=self.server.password,
                timeout_seconds=self.server.timeout_seconds,
            )
            self._send_json(200 if not status.get("error") else 502, {"ok": not bool(status.get("error")), "teachMotion": status})
            return
        if path == "/api/printer/health":
            payload = self.server.printer_health()
            self._send_json(200 if payload.get("ok") else 502, payload)
            return
        if path == "/api/camera/reprint-jobs":
            self._send_json(200, self.server.reprint_jobs_snapshot())
            return
        if path == "/api/locks":
            self._send_json(200, self.server.resource_manager.snapshot())
            return
        if path == "/api/touch/status":
            status = read_touch_status(
                host=self.server.board_host,
                port=self.server.board_port,
                user=self.server.board_user,
                password=self.server.password,
                timeout_seconds=self.server.timeout_seconds,
            )
            self._send_json(200 if status.get("ok") else 502, {"ok": status.get("ok"), "status": status})
            return
        if path == "/api/touch-audio/status":
            status = check_touch_audio(
                auto_start=False,
                board_check=False,
                test_audio=False,
                host=self.server.board_host,
                port=self.server.board_port,
                user=self.server.board_user,
                password=self.server.password,
                timeout_seconds=self.server.timeout_seconds,
            )
            self._send_json(200 if status.get("ok") else 502, {"ok": status.get("ok"), "status": status})
            return
        self._serve_static(path)

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/queue/"):
            queue_id = unquote(path.removeprefix("/api/queue/"))
            removed, reason = self.server.delete_pending_job(queue_id)
            if removed is not None:
                self._send_json(200, {"ok": True, "removed": removed})
                return
            if reason == "running":
                self._send_json(409, {"ok": False, "error": "Running queue item cannot be removed"})
                return
            self._send_json(404, {"ok": False, "error": "Queue item not found"})
            return
        self._send_json(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json()
        except json.JSONDecodeError as exc:
            self._send_json(400, {"ok": False, "error": f"Invalid JSON: {exc}"})
            return

        try:
            if path == "/api/camera/watch/start":
                try:
                    interval = body.get("intervalSeconds")
                    if interval is not None:
                        self.server.camera_sampler.set_interval(float(interval))
                    self.server.camera_sampler.start()
                    self._send_json(200, self.server.camera_snapshot())
                except Exception as exc:  # noqa: BLE001
                    self._send_camera_error(exc)
                return

            if path == "/api/camera/watch/stop":
                self.server.camera_sampler.stop()
                self._send_json(200, self.server.camera_snapshot())
                return

            if path == "/api/camera/capture":
                owner = "manual_camera_capture"
                try:
                    self.server.resource_manager.acquire(owner, [{"resource": "camera_capture", "mode": "exclusive"}], ttl_seconds=90.0)
                    self.server.camera_sampler.capture_once()
                    snapshot = self.server.camera_snapshot()
                    self._send_json(200, {"ok": True, "frame": snapshot.get("latestFrame"), "state": snapshot})
                except RuntimeError as exc:
                    self._send_camera_error(exc)
                except ResourceConflict as exc:
                    self._send_json(409, {"ok": False, "error": str(exc), "conflict": exc.as_payload()})
                except Exception as exc:  # noqa: BLE001
                    self._send_camera_error(exc)
                finally:
                    self.server.resource_manager.release_owner(owner)
                return

            if path == "/api/book-follow/start":
                snapshot, reason = self.server.start_book_follow(body)
                ok = reason in {None, "already-running"}
                status_code = 200 if ok else (409 if str(reason).startswith("resource-conflict") else 502)
                self._send_json(status_code, {"ok": ok, "reason": reason, "status": snapshot})
                return

            if path == "/api/book-follow/stop":
                snapshot = self.server.stop_book_follow()
                self._send_json(200, {"ok": True, "status": snapshot})
                return

            if path == "/api/show/reset":
                self._send_json(200, self.server.reset_show())
                return

            if path.startswith("/api/teach/"):
                action = path.removeprefix("/api/teach/")
                host, port, user, password, timeout = self._connection_from_body(body)
                try:
                    if action == "status":
                        teach_motion = self.server.teach_status(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            timeout_seconds=timeout,
                        )
                        self._send_json(200 if not teach_motion.get("error") else 502, {"ok": not bool(teach_motion.get("error")), "teachMotion": teach_motion})
                        return
                    if action == "start":
                        teach_motion, result = self.server.start_teach_recording(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            timeout_seconds=timeout,
                        )
                        ok = result.get("returnCode") == 0 and teach_motion.get("running")
                        self._send_json(200 if ok else 502, {"ok": ok, "teachMotion": teach_motion, "result": result})
                        return
                    if action == "stop":
                        teach_motion, result = self.server.stop_teach_recording(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            timeout_seconds=timeout,
                        )
                        ok = result.get("returnCode") == 0 and not teach_motion.get("running")
                        self._send_json(200 if ok else 502, {"ok": ok, "teachMotion": teach_motion, "result": result})
                        return
                    if action == "play":
                        teach_motion, result = self.server.play_teach_motion(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            timeout_seconds=timeout,
                        )
                        ok = result.get("returnCode") == 0
                        self._send_json(200 if ok else 502, {"ok": ok, "teachMotion": teach_motion, "result": result})
                        return
                except RuntimeError as exc:
                    self._send_json(409, {"ok": False, "error": str(exc), "teachMotion": self.server.snapshot_state().get("teachMotion")})
                    return

            if path == "/api/show/step":
                step = str(body.get("step") or "")
                try:
                    payload, status_code = self._run_show_step(step, body)
                except ResourceConflict as exc:
                    payload, status_code = (
                        {"ok": False, "error": str(exc), "conflict": exc.as_payload(), "status": self.server.show_status()},
                        409,
                    )
                self._send_json(status_code, payload)
                return

            if path == "/api/photo/snapshot":
                payload, status_code = self.server.capture_show_photo(body)
                self._send_json(status_code, payload)
                return

            if path == "/api/camera/render-print-latest":
                payload, status_code = self.server.render_print_latest_camera_frame(body)
                self._send_json(status_code, payload)
                return

            if path == "/api/camera/reprint-latest-render":
                payload, status_code = self.server.reprint_latest_rendered_image()
                self._send_json(status_code, payload)
                return

            if path == "/api/play-answer-demo":
                try:
                    payload, status_code = self.server.play_answer_demo(body)
                except ResourceConflict as exc:
                    payload, status_code = (
                        {"ok": False, "error": str(exc), "conflict": exc.as_payload(), "status": self.server.show_status()},
                        409,
                    )
                self._send_json(status_code, payload)
                return

            if path == "/api/voice-motion-demo":
                try:
                    payload, status_code = self.server.play_voice_motion_demo(body)
                except ResourceConflict as exc:
                    payload, status_code = (
                        {"ok": False, "error": str(exc), "conflict": exc.as_payload(), "status": self.server.show_status()},
                        409,
                    )
                except ValueError as exc:
                    payload, status_code = ({"ok": False, "error": str(exc)}, 400)
                self._send_json(status_code, payload)
                return

            if path == "/api/audio/narration":
                try:
                    self._send_json(200, {"ok": True, "audio": play_local_audio(NARRATION_AUDIO_PATH)})
                except Exception as exc:  # noqa: BLE001
                    self._send_json(502, {"ok": False, "error": str(exc), "path": str(NARRATION_AUDIO_PATH)})
                return

            if path == "/api/touch-audio/check":
                host, port, user, password, timeout = self._connection_from_body(body)
                status = check_touch_audio(
                    auto_start=bool(body.get("autoStart", True)),
                    board_check=bool(body.get("boardCheck", False)),
                    test_audio=bool(body.get("testAudio", False)),
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    timeout_seconds=timeout,
                )
                self._send_json(200 if status.get("ok") else 502, {"ok": status.get("ok"), "status": status})
                return

            if path == "/api/connection-diagnose":
                host, port, user, password, timeout = self._connection_from_body(body)
                diagnosis = connection_diagnostics(
                    host,
                    port,
                    user=user,
                    password=password,
                    timeout_seconds=timeout,
                )
                self._send_json(200, {"ok": True, "diagnosis": diagnosis})
                return

            if path.startswith("/api/touch/"):
                action = path.removeprefix("/api/touch/")
                if action == "sensitivity":
                    preset_id = str(body.get("preset") or "")
                    if preset_id not in TOUCH_SENSITIVITY_PRESETS:
                        self._send_json(400, {"ok": False, "error": "Unknown touch sensitivity preset"})
                        return
                    host, port, user, password, timeout = self._connection_from_body(body)
                    payload = run_touch_sensitivity_action(
                        preset_id=preset_id,
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        timeout_seconds=timeout,
                    )
                    ok = payload["result"].get("returnCode") == 0 and payload["status"].get("ok")
                    self._send_json(200 if ok else 502, {"ok": ok, **payload})
                    return
                if action in TOUCH_ACTION_COMMANDS:
                    host, port, user, password, timeout = self._connection_from_body(body)
                    payload = run_touch_action(
                        action=action,
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        timeout_seconds=timeout,
                    )
                    ok = payload["result"].get("returnCode") == 0
                    self._send_json(200 if ok else 502, {"ok": ok, **payload})
                    return

            if path == "/api/servo-speed":
                try:
                    servo_record = self.server.set_servo_speed_preset(body.get("preset"))
                except ValueError as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)})
                    return
                self._send_json(200, {"ok": True, "servoRecord": servo_record})
                return

            if path == "/api/servo-record/record":
                record, error = self.server.record_servo_frame(body.get("speedPreset"))
                if record is None:
                    self._send_json(409, {"ok": False, "error": error, "servoRecord": self.server.snapshot_state().get("servoRecord")})
                    return
                self._send_json(200, {"ok": True, "record": record, "servoRecord": self.server.snapshot_state().get("servoRecord")})
                return

            if path == "/api/servo-record/save":
                saved_path, error = self.server.save_servo_records()
                if saved_path is None:
                    self._send_json(409, {"ok": False, "error": error, "servoRecord": self.server.snapshot_state().get("servoRecord")})
                    return
                self._send_json(200, {"ok": True, "path": saved_path, "servoRecord": self.server.snapshot_state().get("servoRecord")})
                return

            if path == "/api/servo-record/clear":
                servo_record = self.server.clear_servo_records()
                self._send_json(200, {"ok": True, "servoRecord": servo_record})
                return

            if path == "/api/servo-hold/start":
                try:
                    servo_id = validate_servo_id(body.get("servoId"))
                    direction = validate_servo_direction(body.get("direction"))
                    speed_preset = servo_speed_preset_name(body.get("speedPreset"))
                    positions = validate_servo_positions(body.get("positions"))
                except (TypeError, ValueError) as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)})
                    return
                host, port, user, password, timeout = self._connection_from_body(body)
                servo_positions, result, reason = self.server.start_servo_hold(
                    servo_id=servo_id,
                    direction=direction,
                    speed_preset=speed_preset,
                    positions=positions,
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    timeout_seconds=timeout,
                )
                if servo_positions is not None:
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "servoPositions": servo_positions,
                            "result": result,
                            "servoHold": self.server.snapshot_state().get("servoHold"),
                        },
                    )
                    return
                if reason == "busy":
                    self._send_json(409, {"ok": False, "error": "Action queue is busy; continuous servo hold paused"})
                    return
                if reason == "refreshing":
                    self._send_json(409, {"ok": False, "error": "Servo position refresh is running; retry shortly"})
                    return
                if reason == "holding":
                    self._send_json(409, {"ok": False, "error": "Continuous servo hold is already running", "servoHold": self.server.snapshot_state().get("servoHold")})
                    return
                if reason == "missing_positions":
                    self._send_json(409, {"ok": False, "error": "Please refresh servo positions before starting continuous hold"})
                    return
                self._send_json(502, {"ok": False, "error": result.get("stderr") or result.get("stdout") or "Failed to start continuous servo hold", "result": result, "servoHold": self.server.snapshot_state().get("servoHold")})
                return

            if path == "/api/servo-hold/stop":
                servo_hold, servo_positions = self.server.stop_servo_hold()
                self._send_json(200, {"ok": True, "servoHold": servo_hold, "servoPositions": servo_positions})
                return

            if path == "/api/servo-control":
                try:
                    positions = validate_servo_positions(body.get("positions"))
                except (TypeError, ValueError) as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)})
                    return
                try:
                    speed_preset = servo_speed_preset_name(body.get("speedPreset"))
                except ValueError as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)})
                    return
                host, port, user, password, timeout = self._connection_from_body(body)
                servo_positions, result, reason = self.server.set_manual_servo_pose(
                    positions=positions,
                    speed_preset=speed_preset,
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    timeout_seconds=timeout,
                )
                if servo_positions is not None:
                    status = 200 if result and result.get("returnCode") == 0 else 502
                    self._send_json(
                        status,
                        {
                            "ok": status == 200,
                            "servoPositions": servo_positions,
                            "result": result,
                            "servoRecord": self.server.snapshot_state().get("servoRecord"),
                        },
                    )
                    return
                if reason == "busy":
                    self._send_json(409, {"ok": False, "error": "Action queue is busy; manual servo control paused"})
                    return
                if reason == "refreshing":
                    self._send_json(409, {"ok": False, "error": "Servo position refresh is running; retry shortly"})
                    return
                self._send_json(409, {"ok": False, "error": "Manual servo control already running"})
                return

            if path == "/api/servo-positions":
                host, port, user, password, timeout = self._connection_from_body(body)
                positions, reason = self.server.refresh_servo_positions(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    timeout_seconds=timeout,
                )
                if positions is not None:
                    status = 200 if positions.get("error") is None else 502
                    self._send_json(status, {"ok": status == 200, "servoPositions": positions})
                    return
                if reason == "busy":
                    self._send_json(409, {"ok": False, "error": "Action queue is busy; servo position refresh paused"})
                    return
                self._send_json(409, {"ok": False, "error": "Servo position refresh already running"})
                return

            if path == "/api/emergency-stop":
                host, port, user, password, timeout = self._connection_from_body(body)
                result = self.server.force_stop_to_neutral(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    timeout_seconds=timeout,
                )
                status = 200 if result.get("returnCode") == 0 else 502
                self._send_json(status, {"ok": status == 200, "result": result})
                return

            if path.startswith("/api/preview/"):
                scene_id = unquote(path.removeprefix("/api/preview/"))
                scene = self._scene_by_id(scene_id)
                if scene is None:
                    self._send_json(404, {"ok": False, "error": "Unknown scene"})
                    return
                script = self._build_scene_script(scene, body)
                self._send_json(200, {"ok": True, "scene": scene, "script": script})
                return

            if path.startswith("/api/run/"):
                scene_id = unquote(path.removeprefix("/api/run/"))
                scene = self._scene_by_id(scene_id)
                if scene is None:
                    self._send_json(404, {"ok": False, "error": "Unknown scene"})
                    return
                script = self._build_scene_script(scene, body)
                if "localScript" in scene:
                    queued = self._enqueue_local_item(kind="scene", item=scene, body=body)
                else:
                    queued = self._enqueue_script(kind="scene", item_id=scene_id, title=scene["title"], script=script, body=body)
                self._send_json(202, {"ok": True, "queued": queued})
                return

            if path.startswith("/api/quick-action/"):
                action_id = unquote(path.removeprefix("/api/quick-action/"))
                action = self._quick_action_by_id(action_id)
                if action is None:
                    self._send_json(404, {"ok": False, "error": "Unknown quick action"})
                    return
                script = self._build_quick_action_script(action, body)
                if body.get("preview", False):
                    self._send_json(200, {"ok": True, "action": action, "script": script})
                    return
                if "localScript" in action:
                    queued = self._enqueue_local_action(action=action, body=body)
                else:
                    local_audio_path = str(ANSWER_AUDIO_PATH) if action.get("playAnswerAudio") else None
                    queued = self._enqueue_script(
                        kind="quick-action",
                        item_id=action_id,
                        title=action["title"],
                        script=script,
                        body=body,
                        local_audio_path=local_audio_path,
                        local_audio_delay_seconds=ANSWER_AUDIO_DELAY_SECONDS if local_audio_path else 0.0,
                    )
                self._send_json(202, {"ok": True, "queued": queued})
                return
        except Exception as exc:
            with self.server.lock:
                self.server.state["running"] = False
                self.server.state["current"] = None
            self._send_json(500, {"ok": False, "error": str(exc)})
            return

        self._send_json(404, {"ok": False, "error": "Unknown endpoint"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the unified Mira Light Shenzhen demo, camera, and touch console.")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument(
        "--port",
        default=int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", DEFAULT_UNIFIED_PORT)),
        type=int,
        help="HTTP bind port",
    )
    parser.add_argument("--board-host", default=os.environ.get("MIRA_SHENZHEN_BOARD_HOST", DEFAULT_HOST))
    parser.add_argument("--board-port", default=int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", DEFAULT_PORT)), type=int)
    parser.add_argument("--board-user", default=os.environ.get("MIRA_SHENZHEN_BOARD_USER", DEFAULT_USER))
    parser.add_argument("--timeout-seconds", default=DEFAULT_TIMEOUT_SECONDS, type=float)
    parser.add_argument("--password-env", default=PASSWORD_ENV)
    parser.add_argument("--camera-password-env", default=os.environ.get("MIRA_CAMERA_PASSWORD_ENV", CAMERA_PASSWORD_ENV))
    parser.add_argument(
        "--camera-interval-seconds",
        type=float,
        default=float(
            os.environ.get(
                "MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS",
                os.environ.get("MIRA_CAMERA_INTERVAL_SECONDS", DEFAULT_CAMERA_INTERVAL_SECONDS),
            )
        ),
    )
    parser.add_argument(
        "--camera-data-dir",
        type=Path,
        default=Path(os.environ.get("MIRA_CAMERA_CONSOLE_DATA_DIR", DEFAULT_CAMERA_DATA_DIR)),
    )
    parser.add_argument("--camera-remote-device", default=os.environ.get("DIGUA_CAMERA_DEVICE", digua_remote_render_pipeline.DEFAULT_DEVICE))
    parser.add_argument("--camera-input-format", default=os.environ.get("DIGUA_CAMERA_INPUT_FORMAT", digua_remote_render_pipeline.DEFAULT_INPUT_FORMAT))
    parser.add_argument("--camera-video-size", default=os.environ.get("DIGUA_CAMERA_VIDEO_SIZE", digua_remote_render_pipeline.DEFAULT_VIDEO_SIZE))
    parser.add_argument("--camera-remote-temp-path", default=os.environ.get("DIGUA_CAMERA_REMOTE_TEMP_PATH", "/tmp/digua-camera-capture.jpg"))
    parser.add_argument("--camera-controls", default=os.environ.get("MIRA_CAMERA_V4L2_CTRLS") or os.environ.get("DIGUA_CAMERA_V4L2_CTRLS", ""))
    parser.add_argument("--camera-bind-address", default=os.environ.get("DIGUA_SSH_BIND_ADDRESS", ""))
    parser.add_argument("--camera-known-hosts-path", type=Path, default=digua_remote_render_pipeline.DEFAULT_KNOWN_HOSTS_PATH)
    parser.add_argument("--camera-connect-timeout", type=int, default=digua_remote_render_pipeline.DEFAULT_CONNECT_TIMEOUT)
    parser.add_argument("--camera-capture-timeout", type=int, default=int(os.environ.get("MIRA_CAMERA_CAPTURE_TIMEOUT", "40")))
    parser.add_argument("--camera-ssh-retries", type=int, default=int(os.environ.get("MIRA_CAMERA_SSH_RETRIES", "1")))
    parser.add_argument("--camera-ssh-retry-delay-seconds", type=float, default=float(os.environ.get("MIRA_CAMERA_SSH_RETRY_DELAY_SECONDS", "1.0")))
    parser.add_argument("--camera-start-watch", dest="camera_start_watch", action="store_true")
    parser.add_argument("--no-camera-start-watch", dest="camera_start_watch", action="store_false")
    parser.set_defaults(
        camera_start_watch=camera_console_module.parse_bool(os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"), True)
    )
    return parser


def warm_ssh_control_master(*, host: str, port: int, user: str, password: str, timeout_seconds: float) -> None:
    if not password:
        return
    result = run_remote_script(
        script=f"""
python3 - <<'PY'
import os
import py_compile

path = "{REMOTE_DESKTOP_DIR}/four_servo_control.py"
if os.path.exists(path):
    py_compile.compile(path, doraise=False)
print("mira_board_python_ready")
PY
true
""",
        host=host,
        port=port,
        user=user,
        password=password,
        timeout_seconds=min(timeout_seconds, 12.0),
    )
    status = "ready" if result.get("returnCode") == 0 else f"failed code={result.get('returnCode')}"
    print(f"[unified-console] ssh control master warmup {status}")


def keep_board_session_warm(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    interval_seconds: float,
    timeout_seconds: float,
) -> None:
    if not password or interval_seconds <= 0:
        return
    script = """
python3 - <<'PY'
print("mira_keepalive_ready")
PY
"""
    while True:
        result = try_run_remote_script(
            script=script,
            host=host,
            port=port,
            user=user,
            password=password,
            timeout_seconds=max(1.0, timeout_seconds),
        )
        code = result.get("returnCode")
        if code not in (0, None):
            print(f"[unified-console] board keepalive failed code={code}: {(result.get('stderr') or '').strip()}")
        time.sleep(interval_seconds)


def warm_voice_motion_assets() -> None:
    try:
        import answer_demo
        import voice_motion_demos

        for demo_id in ("listening", "thinking", "answer"):
            voice_motion_demos.render_board_script(demo_id)
            voice_motion_demos.demo_payload(demo_id, include_script=False)
        answer_demo.normalized_timeline()
        print("[unified-console] voice motion assets warmup ready")
    except Exception as exc:  # noqa: BLE001 - warmup must not stop the console.
        print(f"[unified-console] voice motion assets warmup failed: {exc}")


def main() -> int:
    args = build_parser().parse_args()
    password = os.environ.get(args.password_env, "")
    camera_password = os.environ.get(args.camera_password_env, "") or password
    registry = load_registry()
    defaults = registry.get("boardDefaults", {})
    board_host = args.board_host or defaults.get("host", DEFAULT_HOST)
    board_port = args.board_port or defaults.get("port", DEFAULT_PORT)
    board_user = args.board_user or defaults.get("user", DEFAULT_USER)
    capture_dir = (args.camera_data_dir.expanduser().resolve() / "frames")
    camera_sampler = CameraSampler(
        board_host=board_host,
        board_port=board_port,
        board_user=board_user,
        board_password=camera_password,
        interval_seconds=args.camera_interval_seconds,
        capture_dir=capture_dir,
        remote_device=args.camera_remote_device,
        input_format=args.camera_input_format,
        video_size=args.camera_video_size,
        remote_temp_path=args.camera_remote_temp_path,
        camera_controls=args.camera_controls,
        bind_address=args.camera_bind_address,
        known_hosts_path=args.camera_known_hosts_path,
        connect_timeout=args.camera_connect_timeout,
        capture_timeout=args.camera_capture_timeout,
        ssh_retries=args.camera_ssh_retries,
        ssh_retry_delay_seconds=args.camera_ssh_retry_delay_seconds,
    )
    print(f"[unified-console] open http://{args.host}:{args.port}")
    print(f"[unified-console] board ssh {board_user}@{board_host}:{board_port}")
    print(f"[unified-console] password env {args.password_env} configured={bool(password)}")
    print(f"[unified-console] camera interval {camera_sampler.interval_seconds:g}s capture_dir={capture_dir}")
    print(f"[unified-console] camera controls {camera_sampler.camera_controls or '-'}")
    print(f"[unified-console] camera password env {args.camera_password_env}/{args.password_env} configured={bool(camera_password)}")
    server = ShenzhenConsoleServer(
        (args.host, args.port),
        ShenzhenConsoleHandler,
        registry=registry,
        host=board_host,
        board_port=board_port,
        user=board_user,
        timeout_seconds=args.timeout_seconds,
        password=password,
        camera_sampler=camera_sampler,
    )
    camera_sampler.set_after_capture(server.forward_camera_frame_to_book_follow)
    if args.camera_start_watch:
        camera_sampler.start()
    Thread(target=warm_voice_motion_assets, daemon=True).start()
    if password:
        Thread(
            target=warm_ssh_control_master,
            kwargs={
                "host": board_host,
                "port": board_port,
                "user": board_user,
                "password": password,
                "timeout_seconds": args.timeout_seconds,
            },
            daemon=True,
        ).start()
        Thread(
            target=keep_board_session_warm,
            kwargs={
                "host": board_host,
                "port": board_port,
                "user": board_user,
                "password": password,
                "interval_seconds": BOARD_KEEPALIVE_INTERVAL_SECONDS,
                "timeout_seconds": min(args.timeout_seconds, BOARD_KEEPALIVE_TIMEOUT_SECONDS),
            },
            daemon=True,
        ).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[unified-console] shutdown requested")
    finally:
        server.stop_book_follow()
        camera_sampler.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
