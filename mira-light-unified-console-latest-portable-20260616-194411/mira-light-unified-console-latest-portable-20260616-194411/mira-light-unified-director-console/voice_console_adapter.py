#!/usr/bin/env python3
"""Voice Console Adapter for Mira Light Unified Director Console.

This adapter bridges the Mira Light voice system (StepFun ASR + LLM planner)
with the Unified Director Console (port 8790), enabling voice control of
console scenes, quick actions, camera, printer, and other console features.

Architecture:
    Microphone -> StepFun Realtime ASR -> Intent Classification / LLM Planning
        -> Console API Adapter -> POST /api/run/{scene_id}
                              -> POST /api/quick-action/{action_id}
                              -> POST /api/camera/start, /api/camera/capture
                              -> POST /api/printer/health
                              -> POST /api/teach/start, /api/teach/play
                              -> POST /api/book-follow/start
                              -> POST /api/emergency-stop

The adapter reuses existing voice components:
    - mira_voice_intents.py   (local keyword classification, zero latency)
    - stepfun_llm_planner.py  (LLM semantic planning with whitelist safety)
    - stepfun_realtime_voice.py (WebSocket realtime voice session)
    - mira_realtime_action_orchestrator.py (event routing state machine)

New components added by this adapter:
    - ConsoleActionDispatcher: routes voice intents to console 8790 APIs
    - CONSOLE_COMMAND_ALIASES: extended intent mappings for console features
    - ConsoleVoiceOrchestrator: extends RealtimeActionOrchestrator for console
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable
import urllib.request
import urllib.error

# ── Add voice system scripts to path ──
VOICE_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "Mira-Light-Voice-Full-Ready" / "scripts"
if str(VOICE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(VOICE_SCRIPTS_DIR))

# Reuse existing voice components
from mira_voice_intents import (
    INTENT_ACTIONS,
    SCENE_COMMAND_ALIASES,
    SIGH_KEYWORDS,
    classify_intent,
    action_for_intent,
)
from mira_realtime_action_orchestrator import (
    RealtimeActionConfig,
    RealtimeActionOrchestrator,
    extract_final_transcript,
    phase_for_realtime_event,
    _join_url,
    post_json_request,
    build_local_fallback_plan,
    validate_plan,
    _unwrap_plan,
)
from stepfun_llm_planner import plan_from_text, build_llm_action_manifest, validate_plan as planner_validate_plan

# ── Constants ──
DEFAULT_CONSOLE_URL = "http://127.0.0.1:8790"
DEFAULT_BRIDGE_URL = "http://127.0.0.1:19783"
DEFAULT_SOURCE = "voice-console"
DEFAULT_ACTION_TIMEOUT_SECONDS = 15
DEFAULT_SEMANTIC_COOLDOWN_SECONDS = 3.0
DEFAULT_SUPPRESS_DUPLICATE_SECONDS = 8.0

# ── Console-specific command aliases ──
# These extend SCENE_COMMAND_ALIASES with console-specific features
CONSOLE_COMMAND_ALIASES: dict[str, tuple[str, ...]] = {
    # New scene commands (11-18)
    "happy_dance": ("开心跳舞", "跳个舞", "好开心", "高兴一下", "跳舞", "happy dance", "celebrate dance"),
    "sad_comfort": ("难过安慰", "安慰我", "我好难过", "叹气安慰", "别难过", "comfort me"),
    "curious_peek": ("好奇探头", "那是什么", "看看那个", "好奇看看", "探头看看", "curious peek"),
    "shy_blush": ("害羞", "害羞脸红", "不好意思", "害羞了", "shy blush", "embarrassed"),
    "stretch_yawn": ("伸懒腰", "打哈欠", "好困", "伸个懒腰", "stretch", "yawn"),
    "alert_startle": ("吓一跳", "受惊", "惊吓", "吓到了", "startled", "scared"),
    "greeting_wave": ("打招呼", "你好", "哈喽", "挥手", "hi", "hello", "wave hello"),
    "thinking_ponder": ("想一想", "思考一下", "让我想想", "嗯让我想想", "thinking", "ponder", "hmm"),
    "angry_pout": ("生气", "愤怒", "好气", "气死了", "angry", "mad", "furious"),
    "proud_chest": ("骄傲", "自豪", "得意", "我很厉害", "proud", "confident"),
    "sleepy_drowse": ("困了", "打盹", "好困啊", "想睡觉", "犯困", "sleepy", "drowsy"),
    "laugh_giggle": ("大笑", "好笑", "哈哈哈", "笑一个", "逗我笑", "laugh", "giggle", "haha"),
    "love_heart": ("爱心", "我爱你", "喜欢你", "表达爱意", "love", "heart", "affection"),
    "confused_lost": ("困惑", "不明白", "听不懂", "什么意思", "迷茫", "confused", "puzzled"),
    "bow_thanks": ("鞠躬", "谢谢", "感谢", "致谢", "多谢", "bow", "thank you", "thanks"),
    "excited_bounce": ("兴奋", "太激动了", "好激动", "太棒了", "excited", "thrilled"),

    # Camera commands
    "camera_start": ("打开摄像头", "启动相机", "看看周围", "打开相机", "开始录像", "camera on", "start camera"),
    "camera_stop": ("关闭摄像头", "停止相机", "关掉相机", "camera off", "stop camera"),
    "camera_capture": ("拍照", "拍一张", "截图", "capture", "take photo", "snapshot"),
    "camera_print": ("打印照片", "打印图片", "打印", "print photo", "print image"),

    # Printer commands
    "printer_status": ("打印机状态", "检查打印", "printer status", "check printer"),

    # Teach (motion recording) commands
    "teach_start": ("开始示教", "记录动作", "示教模式", "teach start", "record motion"),
    "teach_stop": ("停止示教", "结束记录", "teach stop", "stop recording"),
    "teach_play": ("播放动作", "回放", "play motion", "replay"),

    # Book follow commands
    "book_follow_start": ("开始追书", "追书模式", "book follow", "follow book"),
    "book_follow_stop": ("停止追书", "结束追书", "stop book follow"),

    # Touch commands
    "touch_start": ("启动触摸", "打开触摸", "touch on", "enable touch"),
    "touch_stop": ("关闭触摸", "停止触摸", "touch off", "disable touch"),

    # Emergency
    "emergency_stop": ("紧急停止", "停下", "停止", "stop", "halt", "emergency"),

    # Narration
    "narration_play": ("播放旁白", "开始旁白", "narration", "play narration"),

    # Show control
    "show_start": ("开始表演", "启动表演", "show start", "start show"),
    "show_stop": ("停止表演", "结束表演", "show stop", "stop show"),
}

# Merge with existing scene aliases for unified classification
ALL_COMMAND_ALIASES = {**SCENE_COMMAND_ALIASES, **CONSOLE_COMMAND_ALIASES}

# Map console command names to console API endpoints
# These match the actual scene IDs in the Unified Director Console
CONSOLE_API_ENDPOINTS: dict[str, dict[str, Any]] = {
    # Scenes (from console /api/scenes registry)
    # 起床 -> 01_presence_wake
    "wake_up": {"type": "scene", "endpoint": "/api/run/01_presence_wake"},
    # 好奇你是谁 -> 02_cautious_intro
    "curious_observe": {"type": "scene", "endpoint": "/api/run/02_cautious_intro"},
    # 摸一摸 -> 03_hand_nuzzle
    "touch_affection": {"type": "scene", "endpoint": "/api/run/03_hand_nuzzle"},
    # Offer 庆祝 -> 04_offer_celebrate
    "offer": {"type": "scene", "endpoint": "/api/run/04_offer_celebrate"},
    "celebrate": {"type": "scene", "endpoint": "/api/run/04_offer_celebrate"},
    # 送别 -> 05_farewell
    "farewell": {"type": "scene", "endpoint": "/api/run/05_farewell"},
    # 睡觉 -> 06_sleep
    "sleep": {"type": "scene", "endpoint": "/api/run/06_sleep"},
    # 00 摆动测试 -> 07_tabletop_follow
    "swing_test": {"type": "scene", "endpoint": "/api/run/07_tabletop_follow"},
    # 拍照 -> 08_photo_pose
    "take_photo": {"type": "scene", "endpoint": "/api/run/08_photo_pose"},
    # 醒来拍照再睡 -> 09_wake_photo_sleep
    "wake_photo_sleep": {"type": "scene", "endpoint": "/api/run/09_wake_photo_sleep"},

    # Legacy voice module scene names mapped to console scenes
    "hand_avoid": {"type": "scene", "endpoint": "/api/run/03_hand_nuzzle"},
    "cute_probe": {"type": "scene", "endpoint": "/api/run/02_cautious_intro"},
    "daydream": {"type": "scene", "endpoint": "/api/run/06_sleep"},
    "standup_reminder": {"type": "scene", "endpoint": "/api/run/01_presence_wake"},
    "track_target": {"type": "scene", "endpoint": "/api/run/02_cautious_intro"},
    "sigh_demo": {"type": "scene", "endpoint": "/api/run/06_sleep"},
    "multi_person_demo": {"type": "scene", "endpoint": "/api/run/02_cautious_intro"},
    "voice_demo_tired": {"type": "scene", "endpoint": "/api/run/06_sleep"},
    "startle_sound": {"type": "scene", "endpoint": "/api/run/16_alert_startle"},
    "praise_demo": {"type": "scene", "endpoint": "/api/run/14_shy_blush"},
    "criticism_demo": {"type": "scene", "endpoint": "/api/run/12_sad_comfort"},

    # New scenes (11-18)
    "happy_dance": {"type": "scene", "endpoint": "/api/run/11_happy_dance"},
    "sad_comfort": {"type": "scene", "endpoint": "/api/run/12_sad_comfort"},
    "curious_peek": {"type": "scene", "endpoint": "/api/run/13_curious_peek"},
    "shy_blush": {"type": "scene", "endpoint": "/api/run/14_shy_blush"},
    "stretch_yawn": {"type": "scene", "endpoint": "/api/run/15_stretch_yawn"},
    "alert_startle": {"type": "scene", "endpoint": "/api/run/16_alert_startle"},
    "greeting_wave": {"type": "scene", "endpoint": "/api/run/17_greeting_wave"},
    "thinking_ponder": {"type": "scene", "endpoint": "/api/run/18_thinking_ponder"},
    "angry_pout": {"type": "scene", "endpoint": "/api/run/19_angry_pout"},
    "proud_chest": {"type": "scene", "endpoint": "/api/run/20_proud_chest"},
    "sleepy_drowse": {"type": "scene", "endpoint": "/api/run/21_sleepy_drowse"},
    "laugh_giggle": {"type": "scene", "endpoint": "/api/run/22_laugh_giggle"},
    "love_heart": {"type": "scene", "endpoint": "/api/run/23_love_heart"},
    "confused_lost": {"type": "scene", "endpoint": "/api/run/24_confused_lost"},
    "bow_thanks": {"type": "scene", "endpoint": "/api/run/25_bow_thanks"},
    "excited_bounce": {"type": "scene", "endpoint": "/api/run/26_excited_bounce"},

    # Camera (endpoints match shenzhen_console.py)
    "camera_start": {"type": "camera", "endpoint": "/api/camera/watch/start", "method": "POST"},
    "camera_stop": {"type": "camera", "endpoint": "/api/camera/watch/stop", "method": "POST"},
    "camera_capture": {"type": "camera", "endpoint": "/api/camera/capture", "method": "POST"},
    "camera_print": {"type": "camera", "endpoint": "/api/camera/render-print-latest", "method": "POST"},

    # Printer
    "printer_status": {"type": "printer", "endpoint": "/api/printer/health", "method": "GET"},

    # Teach
    "teach_start": {"type": "teach", "endpoint": "/api/teach/start", "method": "POST"},
    "teach_stop": {"type": "teach", "endpoint": "/api/teach/stop", "method": "POST"},
    "teach_play": {"type": "teach", "endpoint": "/api/teach/play", "method": "POST"},

    # Book follow
    "book_follow_start": {"type": "book-follow", "endpoint": "/api/book-follow/start", "method": "POST"},
    "book_follow_stop": {"type": "book-follow", "endpoint": "/api/book-follow/stop", "method": "POST"},

    # Touch
    "touch_start": {"type": "touch", "endpoint": "/api/touch/start", "method": "POST"},
    "touch_stop": {"type": "touch", "endpoint": "/api/touch/stop", "method": "POST"},

    # Emergency
    "emergency_stop": {"type": "emergency", "endpoint": "/api/emergency-stop", "method": "POST"},

    # Narration
    "narration_play": {"type": "narration", "endpoint": "/api/narration/play", "method": "POST"},

    # Show
    "show_start": {"type": "show", "endpoint": "/api/show/start", "method": "POST"},
    "show_stop": {"type": "show", "endpoint": "/api/show/stop", "method": "POST"},
}

# ── TTS Feedback messages ──
TTS_FEEDBACK: dict[str, str] = {
    "wake_up": "起床啦",
    "curious_observe": "让我看看",
    "touch_affection": "好温暖呀",
    "hand_avoid": "别碰我",
    "cute_probe": "我很可爱吧",
    "daydream": "发呆中",
    "standup_reminder": "该站起来活动一下啦",
    "track_target": "我看到你啦",
    "celebrate": "好开心",
    "farewell": "再见啦",
    "sleep": "晚安",
    "sigh_demo": "别叹气啦",
    "multi_person_demo": "好多人呀",
    "voice_demo_tired": "累了就休息一下吧",
    "startle_sound": "吓我一跳",
    "praise_demo": "谢谢夸奖",
    "criticism_demo": "我会努力的",
    "camera_start": "摄像头已打开",
    "camera_stop": "摄像头已关闭",
    "camera_capture": "拍照完成",
    "camera_print": "正在打印照片",
    "printer_status": "打印机状态已检查",
    "teach_start": "开始记录动作",
    "teach_stop": "动作记录完成",
    "teach_play": "播放动作中",
    "book_follow_start": "开始追书",
    "book_follow_stop": "停止追书",
    "touch_start": "触摸感应已开启",
    "touch_stop": "触摸感应已关闭",
    "emergency_stop": "紧急停止",
    "narration_play": "开始旁白",
    "show_start": "表演开始",
    "show_stop": "表演结束",
    "unknown": "我不太明白",
    "error": "执行出错了",
}


# ── Console Action Dispatcher ──

@dataclass
class ConsoleActionConfig:
    """Configuration for console voice adapter."""
    console_url: str = DEFAULT_CONSOLE_URL
    bridge_url: str = DEFAULT_BRIDGE_URL
    source: str = DEFAULT_SOURCE
    request_timeout_seconds: int = DEFAULT_ACTION_TIMEOUT_SECONDS
    semantic_cooldown_seconds: float = DEFAULT_SEMANTIC_COOLDOWN_SECONDS
    suppress_duplicate_seconds: float = DEFAULT_SUPPRESS_DUPLICATE_SECONDS
    tts_feedback_enabled: bool = True
    tts_bridge_url: str = ""
    voice_state_enabled: bool = True
    semantic_actions_enabled: bool = True


class ConsoleActionDispatcher:
    """Dispatches voice commands to the Unified Director Console API.

    This is the core adapter that translates voice intents into console HTTP API calls.
    It handles:
      - Scene execution via POST /api/run/{scene_id}
      - Quick actions via POST /api/quick-action/{action_id}
      - Camera control via /api/camera/*
      - Printer status via /api/printer/health
      - Teach mode via /api/teach/*
      - Book follow via /api/book-follow/*
      - Emergency stop via /api/emergency-stop
      - TTS feedback after action execution
    """

    def __init__(
        self,
        config: ConsoleActionConfig | None = None,
        *,
        post_json: Callable = post_json_request,
    ) -> None:
        self.config = config or ConsoleActionConfig()
        self.post_json = post_json
        self._action_count = 0
        self.last_action_time = 0.0
        self.last_action_name = ""

    def _console_url(self, path: str) -> str:
        return _join_url(self.config.console_url, path)

    def _check_cooldown(self, action_name: str) -> str | None:
        """Return cooldown reason or None if action is allowed."""
        now = time.monotonic()
        elapsed = now - self.last_action_time

        if elapsed < self.config.semantic_cooldown_seconds:
            return f"cooldown ({elapsed:.1f}s < {self.config.semantic_cooldown_seconds}s)"

        if (
            action_name
            and action_name == self.last_action_name
            and elapsed < self.config.suppress_duplicate_seconds
        ):
            return f"duplicate '{action_name}' ({elapsed:.1f}s < {self.config.suppress_duplicate_seconds}s)"

        return None

    def _record_action(self, action_name: str) -> None:
        self.last_action_time = time.monotonic()
        self.last_action_name = action_name
        self._action_count += 1

    def _speak_feedback(self, action_name: str, extra_text: str = "") -> dict[str, Any] | None:
        """Send TTS feedback via bridge if enabled."""
        if not self.config.tts_feedback_enabled or not self.config.tts_bridge_url:
            return None

        text = TTS_FEEDBACK.get(action_name, TTS_FEEDBACK["unknown"])
        if extra_text:
            text = f"{text}，{extra_text}"

        try:
            return self.post_json(
                _join_url(self.config.tts_bridge_url, "/v1/mira-light/speak"),
                {"text": text, "voice": "tts", "wait": False},
                timeout_seconds=3,
            )
        except Exception:
            return None

    def dispatch_console_command(self, command_name: str, transcript: str = "") -> dict[str, Any]:
        """Dispatch a console command by name.

        Args:
            command_name: The command name from CONSOLE_API_ENDPOINTS
            transcript: Original voice transcript for context

        Returns:
            Action result dict with kind, response, error, etc.
        """
        endpoint_info = CONSOLE_API_ENDPOINTS.get(command_name)
        if not endpoint_info:
            return {
                "kind": "console-error",
                "error": f"Unknown console command: {command_name}",
                "transcript": transcript,
            }

        # Cooldown check
        cooldown = self._check_cooldown(command_name)
        if cooldown:
            return {
                "kind": "console-skip",
                "reason": cooldown,
                "command": command_name,
                "transcript": transcript,
            }

        method = endpoint_info.get("method", "POST")
        endpoint = endpoint_info["endpoint"]
        url = self._console_url(endpoint)

        # Build payload based on command type
        payload: dict[str, Any] = {
            "source": self.config.source,
            "transcript": transcript,
        }

        # Scene commands use the scene name in the URL path, no extra payload needed
        if endpoint_info["type"] == "scene":
            payload["async"] = True
            payload["cueMode"] = "voice"
        elif endpoint_info["type"] == "emergency":
            payload = {}  # Emergency stop has no payload
        elif endpoint_info["type"] == "printer":
            method = "GET"
            payload = {}

        # Execute the request
        try:
            if method == "GET":
                response = self._get_json(url, timeout_seconds=self.config.request_timeout_seconds)
            else:
                response = self.post_json(
                    url,
                    payload,
                    timeout_seconds=self.config.request_timeout_seconds,
                )
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}

        self._record_action(command_name)

        # TTS feedback
        tts_result = None
        if self.config.tts_feedback_enabled:
            ok = isinstance(response, dict) and response.get("ok") is not False
            extra = "" if ok else str(response.get("error", ""))[:30]
            tts_result = self._speak_feedback(command_name, extra)

        result: dict[str, Any] = {
            "kind": "console-action",
            "command": command_name,
            "type": endpoint_info["type"],
            "transcript": transcript,
            "request": {"method": method, "url": url, "payload": payload},
            "response": response,
        }
        if tts_result:
            result["tts"] = tts_result
        return result

    def _get_json(self, url: str, timeout_seconds: int = 5) -> dict[str, Any]:
        """Perform a GET request and return JSON."""
        request = urllib.request.Request(url, method="GET")
        no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with no_proxy_opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8").strip()
            return json.loads(raw) if raw else {"ok": True}

    def classify_console_intent(self, transcript: str) -> str:
        """Classify transcript into a console command intent.

        First tries the extended console aliases, then falls back to standard
        scene classification.
        """
        text = transcript.strip().lower()

        # Check console-specific aliases first
        for command_name, aliases in CONSOLE_COMMAND_ALIASES.items():
            for alias in aliases:
                if alias.lower() in text:
                    return command_name

        # Fall back to standard scene classification
        standard_intent = classify_intent(transcript)
        standard_action = action_for_intent(standard_intent)
        if standard_action and standard_action.get("type") != "none":
            return str(standard_action.get("name", ""))

        return "unknown"

    def dispatch_transcript(self, transcript: str) -> dict[str, Any] | None:
        """Main entry point: convert a voice transcript into console action.

        Args:
            transcript: The ASR transcript text.

        Returns:
            Action result dict, or None if no action matched.
        """
        text = transcript.strip()
        if not text:
            return None

        intent = self.classify_console_intent(text)
        if intent == "unknown":
            return {
                "kind": "console-skip",
                "reason": "unknown-intent",
                "transcript": text,
            }

        return self.dispatch_console_command(intent, transcript=text)


# ── Console Voice Orchestrator ──

class ConsoleVoiceOrchestrator(RealtimeActionOrchestrator):
    """Extended orchestrator that routes voice events to the console API.

    This extends the base RealtimeActionOrchestrator with console-specific
    action dispatching while preserving all existing voice state and semantic
    action behavior.
    """

    def __init__(
        self,
        config: ConsoleActionConfig | None = None,
        *,
        planner: Callable | None = None,
        post_json: Callable = post_json_request,
    ) -> None:
        # Initialize base orchestrator with bridge config (for voice states)
        base_config = RealtimeActionConfig(
            bridge_url=config.bridge_url if config else DEFAULT_BRIDGE_URL,
            director_url=config.console_url if config else DEFAULT_CONSOLE_URL,
            voice_state_enabled=config.voice_state_enabled if config else True,
            semantic_actions_enabled=False,  # We handle semantic actions ourselves
            request_timeout_seconds=config.request_timeout_seconds if config else DEFAULT_ACTION_TIMEOUT_SECONDS,
            source=config.source if config else DEFAULT_SOURCE,
        )
        super().__init__(base_config, planner=planner, post_json=post_json)

        self.console_config = config or ConsoleActionConfig()
        self.console_dispatcher = ConsoleActionDispatcher(
            config=self.console_config,
            post_json=post_json,
        )

    def dispatch_transcript(self, transcript: str) -> dict[str, Any] | None:
        """Override to route transcripts to console instead of bridge."""
        text = transcript.strip()
        if not text:
            return None
        if text == self.last_transcript:
            return {"kind": "semantic-skip", "reason": "duplicate-transcript", "transcript": text}
        self.last_transcript = text

        if not self.console_config.semantic_actions_enabled:
            return {"kind": "semantic-skip", "reason": "semantic-actions-disabled", "transcript": text}

        # Use console dispatcher for all actions
        result = self.console_dispatcher.dispatch_transcript(text)
        if result and result.get("kind") == "console-action":
            # Update cooldown tracking in base orchestrator
            action_name = result.get("command", "")
            self._record_action(action_name)
        return result


# ── Standalone transcript-to-console loop ──

def dispatch_transcript_to_console(
    transcript: str,
    *,
    console_url: str = DEFAULT_CONSOLE_URL,
    bridge_url: str = DEFAULT_BRIDGE_URL,
    action_timeout_seconds: int = DEFAULT_ACTION_TIMEOUT_SECONDS,
    tts_feedback_enabled: bool = True,
    tts_bridge_url: str = "",
) -> dict[str, Any]:
    """One-shot dispatch: transcript -> console action.

    This is the minimal entry point for testing and integration.
    """
    config = ConsoleActionConfig(
        console_url=console_url,
        bridge_url=bridge_url,
        request_timeout_seconds=action_timeout_seconds,
        tts_feedback_enabled=tts_feedback_enabled,
        tts_bridge_url=tts_bridge_url,
    )
    dispatcher = ConsoleActionDispatcher(config=config)
    return dispatcher.dispatch_transcript(transcript) or {
        "kind": "console-skip",
        "reason": "no-action",
        "transcript": transcript,
    }


# ── Realtime voice integration ──

def build_console_action_orchestrator(
    console_url: str = DEFAULT_CONSOLE_URL,
    bridge_url: str = DEFAULT_BRIDGE_URL,
    voice_state_enabled: bool = True,
    semantic_actions_enabled: bool = True,
    tts_feedback_enabled: bool = True,
    action_timeout_seconds: int = DEFAULT_ACTION_TIMEOUT_SECONDS,
) -> ConsoleVoiceOrchestrator:
    """Build a ConsoleVoiceOrchestrator ready for realtime voice session."""
    config = ConsoleActionConfig(
        console_url=console_url,
        bridge_url=bridge_url,
        voice_state_enabled=voice_state_enabled,
        semantic_actions_enabled=semantic_actions_enabled,
        tts_feedback_enabled=tts_feedback_enabled,
        tts_bridge_url=bridge_url,
        request_timeout_seconds=action_timeout_seconds,
    )
    return ConsoleVoiceOrchestrator(config=config)


# ── CLI ──

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Voice Console Adapter for Mira Light Unified Director Console"
    )
    parser.add_argument("--transcript", help="Single transcript to dispatch (test mode)")
    parser.add_argument("--console-url", default=DEFAULT_CONSOLE_URL, help="Console URL")
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL, help="Bridge URL for TTS")
    parser.add_argument("--action-timeout-seconds", type=int, default=DEFAULT_ACTION_TIMEOUT_SECONDS)
    parser.add_argument("--no-tts-feedback", action="store_true", help="Disable TTS feedback")
    parser.add_argument("--list-commands", action="store_true", help="List all available voice commands")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_commands:
        print("=== Available Voice Commands ===\n")
        print("--- Scenes ---")
        for name, aliases in SCENE_COMMAND_ALIASES.items():
            print(f"  {name}: {', '.join(aliases)}")
        print("\n--- Console Features ---")
        for name, aliases in CONSOLE_COMMAND_ALIASES.items():
            print(f"  {name}: {', '.join(aliases)}")
        return 0

    if args.transcript:
        result = dispatch_transcript_to_console(
            args.transcript,
            console_url=args.console_url,
            bridge_url=args.bridge_url,
            action_timeout_seconds=args.action_timeout_seconds,
            tts_feedback_enabled=not args.no_tts_feedback,
            tts_bridge_url=args.bridge_url if not args.no_tts_feedback else "",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("kind") == "console-action" else 1

    print("Usage: voice_console_adapter.py --transcript '<text>'")
    print("       voice_console_adapter.py --list-commands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
