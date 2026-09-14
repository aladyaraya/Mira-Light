#!/usr/bin/env python3
"""Realtime voice interaction runtime for Mira Light booth demos."""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import json
import math
import os
from pathlib import Path
import queue
import re
import socket
import sys
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from mira_lingzhu_client import send_via_lingzhu_messages
from mira_light_audio import AudioCuePlayer
from mira_name_aliases import normalize_transcript_aliases
from mira_voice_intents import action_for_intent, bridge_payload_for_intent, classify_intent, comfort_like_intent, is_brief_greeting, should_skip_short_reply
import numpy as np
import sounddevice as sd

from openclaw_voice_to_claw import (
    DEFAULT_INITIAL_PROMPT,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL_PROFILE,
    DEFAULT_MODEL_PROFILES,
    VoiceToClawError,
    ensure_mono_float32,
    load_audio_file,
    print_input_devices,
    parse_openclaw_agent_response,
    record_fixed_duration,
    record_push_to_talk,
    resolve_input_device,
    save_wav,
    send_to_openclaw,
    transcribe_local,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / "runtime" / "realtime-voice-interaction"
DEFAULT_CAPTURE_SAMPLE_RATE = 48000
DEFAULT_CHANNELS = 1
DEFAULT_VOICE_MODE = "warm_gentleman"
DEFAULT_TIMEOUT = 45
DEFAULT_MODE = "continuous"
DEFAULT_HISTORY_TURNS = 4
DEFAULT_LATENCY_PRESET = "standard"
DEFAULT_REPLY_AGENT = "mira-voice-spark"
DEFAULT_REPLY_BACKEND = "openclaw-agent"
DEFAULT_REPLY_THINKING = "off"
DEFAULT_IDLE_TIMEOUT_SECONDS = 30.0
DEFAULT_TRIGGER_COOLDOWN_SECONDS = 8.0
DEFAULT_BRIDGE_URL = "http://127.0.0.1:9783"
DEFAULT_SHENZHEN_CONSOLE_URL = "http://127.0.0.1:8777"
DEFAULT_VAD_START_MS = 150
DEFAULT_VAD_END_MS = 650
DEFAULT_MIN_UTTERANCE_MS = 400
DEFAULT_MAX_UTTERANCE_SECONDS = 6.0
DEFAULT_CHUNK_MS = 50
DEFAULT_VAD_MIN_RMS = 0.003
DEFAULT_VAD_SPEECH_RATIO = 1.5
DEFAULT_SKIP_LOW_RMS = 0.0045
DEFAULT_SKIP_LOW_PEAK = 0.04
DEFAULT_REPEAT_MIN_CHARS = 12
DEFAULT_REPEAT_DOMINANT_RATIO = 0.85
DEFAULT_REPEAT_MAX_UNIQUE_CHARS = 3
DEFAULT_REPEAT_MAX_COMPRESSION_RATIO = 8.0
DEFAULT_REPEAT_MAX_CHARS_PER_SECOND = 35.0
DEFAULT_REPEAT_MIN_TOKEN_RUN = 8
DEFAULT_REPEAT_MIN_SUBSTRING_RUN = 6
DEFAULT_REPEAT_MIN_SUBSTRING_UNIT = 2
DEFAULT_REPEAT_MAX_SUBSTRING_UNIT = 8
DEFAULT_KEEP_WARM_SECONDS = 0.0
DEFAULT_POST_TTS_COOLDOWN_SECONDS = 0.9
LOW_LATENCY_KEEP_WARM_SECONDS = 90.0
DEFAULT_API_SYSTEM_PROMPT = (
    "你是 Mira。"
    "你是一个温柔、简短、自然的中文陪伴角色。"
    "你正在展位现场通过灯光和动作陪伴用户。"
    "请优先延续最近几轮上下文。"
    "如果用户表达疲惫、难受或低落，优先给出温和安慰。"
    "如果用户在告别，请自然收尾。"
    "请用简体中文自然回复。"
    "尽量只用 1 到 2 句。"
    "不要使用 emoji 或表情符号。"
    "不要长篇解释。"
)
LOW_LATENCY_PROMPT_HINT = (
    "当前优先采用低延迟回复策略。"
    "优先只用一句完整、自然的短句。"
    "最好控制在 12 到 20 个汉字之间。"
    "不要省略主语或把句子说断。"
    "除非用户明确追问，否则不要展开解释。"
)
EXIT_PHRASES = {
    "退出对话",
    "结束对话",
    "停止监听",
    "退出",
    "结束",
    "stop listening",
    "exit chat",
    "quit chat",
}
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)
MARKDOWN_DECORATION_PATTERN = re.compile(r"[*_`#>]+")
INSTRUCTIONAL_REPLY_PREFIX_PATTERN = re.compile(
    r"^\s*(?:你(?:现在)?(?:可以|就)?|可以|请|建议你)?\s*"
    r"(?:直接)?\s*(?:回|回复|说|这样回|这样说|回答)\s*[:：]\s*",
    flags=re.UNICODE,
)
WRAPPING_QUOTES_PATTERN = re.compile(r'^[“"\'`]+|[”"\'`]+$')
VISIBLE_TEXT_PATTERN = re.compile(r"[^\s，。！？!?,、；：:…~—\-]+", flags=re.UNICODE)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", flags=re.UNICODE)

@dataclass
class UtteranceResult:
    samples: np.ndarray
    sample_rate: int
    source_meta: dict[str, Any]


@dataclass
class ConversationSession:
    max_history_turns: int
    conversation_id: str = field(default_factory=lambda: f"mira-light-live-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
    mode: str = "chat"
    last_intent: str = "none"
    last_scene: str | None = None
    last_user_text: str = ""
    last_reply_text: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active_at: str = field(default_factory=lambda: datetime.now().isoformat())
    history: deque[dict[str, str]] = field(default_factory=deque)
    last_trigger_monotonic: float = 0.0

    def append_turn(self, user_text: str, reply_text: str) -> None:
        if user_text:
            self.history.append({"role": "user", "content": user_text})
        if reply_text:
            self.history.append({"role": "assistant", "content": reply_text})
        while len(self.history) > self.max_history_turns * 2:
            self.history.popleft()

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "lastIntent": self.last_intent,
            "lastScene": self.last_scene,
            "lastUserText": self.last_user_text,
            "lastReplyText": self.last_reply_text,
            "startedAt": self.started_at,
            "lastActiveAt": self.last_active_at,
            "history": list(self.history),
        }


@dataclass
class WarmState:
    last_keep_warm_monotonic: float = 0.0


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")


def build_session_dir(base_dir: Path) -> Path:
    session_dir = base_dir / timestamp_slug()
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_turn_transcript(raw_text: str) -> tuple[str, bool]:
    cleaned = raw_text.strip()
    normalized = normalize_transcript_aliases(cleaned)
    return normalized, normalized != cleaned


def strip_emoji(text: str) -> str:
    cleaned = EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def normalize_reply_text(text: str) -> tuple[str, dict[str, bool]]:
    raw = str(text or "").strip()
    if not raw:
        return "", {"emojiStripped": False, "markdownStripped": False, "instructionalPrefixStripped": False}

    emoji_cleaned = strip_emoji(raw)
    markdown_cleaned = MARKDOWN_DECORATION_PATTERN.sub("", emoji_cleaned)
    markdown_cleaned = re.sub(r"\s{2,}", " ", markdown_cleaned).strip()

    instructional_stripped = False
    extracted = markdown_cleaned
    prefix_match = INSTRUCTIONAL_REPLY_PREFIX_PATTERN.match(markdown_cleaned)
    if prefix_match:
        instructional_stripped = True
        remainder = markdown_cleaned[prefix_match.end():].strip()
        quoted_match = re.search(r'[“"](.+?)[”"]', remainder)
        if quoted_match:
            extracted = quoted_match.group(1).strip()
        else:
            extracted = remainder

    normalized = WRAPPING_QUOTES_PATTERN.sub("", extracted).strip()
    normalized = re.sub(r"\s{2,}", " ", normalized).strip()
    if not normalized:
        normalized = markdown_cleaned

    return normalized, {
        "emojiStripped": emoji_cleaned != raw,
        "markdownStripped": markdown_cleaned != emoji_cleaned,
        "instructionalPrefixStripped": instructional_stripped,
    }


def should_exit(transcript: str) -> bool:
    lowered = " ".join(transcript.strip().lower().split())
    return lowered in EXIT_PHRASES

def update_session_mode(session: ConversationSession, intent: str) -> None:
    if comfort_like_intent(intent) or intent == "farewell":
        session.mode = intent
    else:
        session.mode = "chat"
    session.last_intent = intent
    session.last_active_at = datetime.now().isoformat()


def build_system_prompt(session: ConversationSession, *, base_prompt: str) -> str:
    mode_hint = {
        "chat": "当前会话模式是普通陪伴聊天。",
        "comfort": "当前会话模式是安慰陪伴，请优先温和接住用户情绪。",
        "sigh": "当前会话模式是安静安慰，请像听见一声叹气那样温和接住用户。",
        "farewell": "当前会话模式是告别收尾，请自然简短结束。",
    }.get(session.mode, "当前会话模式是普通陪伴聊天。")
    state_hint = (
        f"最近一次识别到的意图是 {session.last_intent}。"
        f"最近一次触发的场景是 {session.last_scene or 'none'}。"
    )
    return f"{base_prompt}\n{mode_hint}\n{state_hint}"


def build_messages(session: ConversationSession, transcript: str, *, base_prompt: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": build_system_prompt(session, base_prompt=base_prompt)}]
    messages.extend(list(session.history))
    messages.append({"role": "user", "content": transcript})
    return messages


def build_low_latency_system_prompt(base_prompt: str) -> str:
    if LOW_LATENCY_PROMPT_HINT in base_prompt:
        return base_prompt
    return f"{base_prompt}\n{LOW_LATENCY_PROMPT_HINT}"


def apply_latency_preset(args: argparse.Namespace) -> dict[str, Any]:
    applied: dict[str, Any] = {"preset": args.latency_preset}
    if args.latency_preset != "low":
        if args.startup_warmup is None:
            args.startup_warmup = False
        return applied

    if args.vad_start_ms == DEFAULT_VAD_START_MS:
        args.vad_start_ms = 100
        applied["vadStartMs"] = args.vad_start_ms
    if args.vad_end_ms == DEFAULT_VAD_END_MS:
        args.vad_end_ms = 400
        applied["vadEndMs"] = args.vad_end_ms
    if args.history_turns == DEFAULT_HISTORY_TURNS:
        args.history_turns = 2
        applied["historyTurns"] = args.history_turns
    if args.api_system_prompt == DEFAULT_API_SYSTEM_PROMPT:
        args.api_system_prompt = build_low_latency_system_prompt(args.api_system_prompt)
        applied["shortReplyHint"] = True
    if args.startup_warmup is None:
        args.startup_warmup = True
        applied["startupWarmup"] = True
    if args.keep_warm_seconds <= 0:
        args.keep_warm_seconds = LOW_LATENCY_KEEP_WARM_SECONDS
        applied["keepWarmSeconds"] = args.keep_warm_seconds
    return applied


def build_openclaw_reply_prompt(messages: list[dict[str, str]]) -> str:
    lines = [
        "你现在只负责为展位里的 Mira 生成直接说给用户听的简短中文回复。",
        "只输出 Mira 最终要说的话。",
        "不要解释任务，不要复述规则，不要输出分析、标签、引号或多余前缀。",
        "尽量只用 1 到 2 句。",
        "",
        "以下是当前会话上下文：",
    ]
    for message in messages:
        role = str(message.get("role") or "").strip().lower()
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            lines.append(f"[系统设定]\n{content}")
        elif role == "assistant":
            lines.append(f"[Mira]\n{content}")
        else:
            lines.append(f"[用户]\n{content}")
    lines.append("")
    lines.append("请直接继续这段对话，只输出 Mira 会说的最终正文。")
    return "\n".join(lines).strip()


def send_via_openclaw_messages(
    messages: list[dict[str, str]],
    *,
    agent: str,
    thinking: str,
    timeout_seconds: int,
) -> tuple[str, dict[str, Any]]:
    reply_prompt = build_openclaw_reply_prompt(messages)
    code, stdout, stderr = send_to_openclaw(
        reply_prompt,
        agent=agent,
        session_id=None,
        thinking=thinking,
        timeout_seconds=timeout_seconds,
        json_output=True,
    )
    if code != 0:
        raise VoiceToClawError(stderr.strip() or stdout.strip() or "openclaw agent reply failed")
    if "Connection error." in stdout:
        raise VoiceToClawError("openclaw agent returned connection error")
    parsed = parse_openclaw_agent_response(stdout)
    if str(parsed.get("text") or "").strip().lower() == "connection error.":
        raise VoiceToClawError("openclaw agent returned connection error")
    meta = parsed.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    agent_meta = meta.get("agentMeta") if isinstance(meta, dict) else {}
    if not isinstance(agent_meta, dict):
        agent_meta = {}
    return str(parsed["text"]).strip(), {
        "provider": str(agent_meta.get("provider") or "openclaw-agent"),
        "model": str(agent_meta.get("model") or ""),
        "agent": agent,
        "thinking": thinking,
        "payload": parsed.get("payload"),
    }


def _load_direct_newapi_config(agent: str) -> dict[str, str]:
    candidates = [
        Path.home() / ".openclaw" / "agents" / agent / "agent" / "models.json",
        Path.home() / ".openclaw" / "agents" / "main" / "agent" / "models.json",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        provider = (payload.get("providers") or {}).get("newapi")
        if not isinstance(provider, dict):
            continue
        base_url = str(provider.get("baseUrl") or "").strip()
        api_key = str(provider.get("apiKey") or "").strip()
        if base_url and api_key:
            return {"baseUrl": base_url, "apiKey": api_key, "configPath": str(path)}
    raise VoiceToClawError("newapi config not found in OpenClaw models.json")


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()
    text = first.get("text")
    return str(text).strip() if text else ""


def send_via_newapi_direct_messages(
    messages: list[dict[str, str]],
    *,
    agent: str,
    timeout_seconds: int,
) -> tuple[str, dict[str, Any]]:
    config = _load_direct_newapi_config(agent)
    request = urllib.request.Request(
        f"{config['baseUrl'].rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": "gpt-5.4",
                "messages": messages,
                "max_tokens": 96,
                "temperature": 0.7,
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['apiKey']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise VoiceToClawError(f"NewAPI HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise VoiceToClawError(f"NewAPI request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise VoiceToClawError("NewAPI returned invalid JSON") from exc

    text = _extract_chat_completion_text(payload)
    if not text:
        raise VoiceToClawError("NewAPI returned no reply text")
    return text, {
        "provider": "newapi-direct",
        "model": "gpt-5.4",
        "agent": agent,
        "payload": payload,
        "configPath": config["configPath"],
    }


def send_reply(
    messages: list[dict[str, str]],
    *,
    session: ConversationSession,
    args: argparse.Namespace,
    additional_user_ids: str | list[str] | tuple[str, ...] | None,
) -> tuple[str, dict[str, Any], str]:
    if args.reply_backend == "lingzhu":
        text, meta = send_via_lingzhu_messages(
            messages,
            base_url=args.lingzhu_base_url,
            auth_ak=args.lingzhu_auth_ak,
            agent_id=args.lingzhu_agent_id,
            user_id=args.lingzhu_user_id or session.conversation_id,
            session_id=session.conversation_id,
            additional_user_ids=additional_user_ids,
            timeout_seconds=args.timeout,
        )
        return text, meta, "lingzhu-live-adapter"

    if os.environ.get("MIRA_LIGHT_OPENCLAW_DIRECT_FIRST", "").strip().lower() in {"1", "true", "yes", "on"}:
        text, meta = send_via_newapi_direct_messages(
            messages,
            agent=args.reply_agent,
            timeout_seconds=args.timeout,
        )
        return text, meta, "newapi-direct"

    try:
        text, meta = send_via_openclaw_messages(
            messages,
            agent=args.reply_agent,
            thinking=args.reply_thinking,
            timeout_seconds=args.timeout,
        )
        return text, meta, "openclaw-agent"
    except VoiceToClawError as exc:
        text, meta = send_via_newapi_direct_messages(
            messages,
            agent=args.reply_agent,
            timeout_seconds=args.timeout,
        )
        meta["openclawError"] = str(exc)
        return text, meta, "newapi-direct"



def fallback_reply_for_intent(intent: str) -> str:
    if intent.startswith("scene:"):
        scene_name = intent.split(":", 1)[1].strip()
        return local_scene_reply(scene_name)
    if intent == "sigh":
        return "我在呢，先慢一点也没关系。"
    if intent == "comfort":
        return "辛苦了，先慢一点也没关系，我陪你缓一缓。"
    if intent == "farewell":
        return "好呀，那我们下次见。"
    if intent == "praise":
        return "谢谢你，我会把这句夸奖记在心里。"
    if intent == "criticism":
        return "我听见了，我会再努力一点。"
    return "我听见你了，我们继续。"


def local_scene_reply(scene_name: str) -> str:
    replies = {
        "celebrate": "好，我跳一下。",
        "sleep": "好，我安静下来。",
        "wake_up": "好，我醒一下。",
        "curious_observe": "好，我看一下。",
        "touch_affection": "好，我靠近一点。",
        "hand_avoid": "好，我躲一下。",
        "cute_probe": "好，我卖个萌。",
        "daydream": "好，我发会儿呆。",
        "standup_reminder": "好，我提醒你动一动。",
        "track_target": "好，我开始看这边。",
        "farewell": "好呀，那我们下次见。",
        "sigh_demo": "我听见了，慢慢来。",
        "multi_person_demo": "好，我试着看看大家。",
        "voice_demo_tired": "辛苦了，我陪你缓一缓。",
        "startle_sound": "哎呀，我被吓了一下。",
        "praise_demo": "谢谢你，我开心了。",
        "criticism_demo": "我听见了，我会再努力一点。",
    }
    return replies.get(scene_name, "好，我来动一下。")


def local_action_reply(intent: str, trigger_result: dict[str, Any]) -> str | None:
    action = trigger_result.get("action")
    if not isinstance(action, dict):
        action = action_for_intent(intent)
    if not isinstance(action, dict):
        return None
    if trigger_result.get("skipped"):
        reason = str(trigger_result.get("reason") or "")
        if reason == "trigger-disabled":
            return "现在是聊天安全模式，我先不触发身体动作。"
        if reason == "cooldown-active":
            return "我刚刚动过了，先缓一下。"
        return None
    if not trigger_result.get("ok"):
        return "我想动一下，但本地灯控 bridge 还没连上。"

    action_type = str(action.get("type") or "")
    action_name = str(action.get("name") or "")
    if action_type == "scene":
        return local_scene_reply(action_name)
    if action_type == "trigger":
        if intent == "comfort":
            return "辛苦了，我陪你缓一缓。"
        if intent == "sigh":
            return "我听见了，先慢一点。"
        if intent == "praise":
            return "谢谢你，我收到这句夸奖了。"
        if intent == "criticism":
            return "我听见了，我会再努力一点。"
        if intent == "farewell":
            return "好呀，那我们下次见。"
        return "好，我已经收到这个信号。"
    return None


def bridge_headers(token: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def post_bridge_json(base_url: str, path: str, payload: dict[str, Any], *, token: str, timeout_seconds: int) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=bridge_headers(token),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise VoiceToClawError(f"Bridge HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise VoiceToClawError(f"Bridge request failed: {exc}") from exc


def post_json(base_url: str, path: str, payload: dict[str, Any], *, timeout_seconds: int = 8) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8").strip()
            return json.loads(raw) if raw else {"ok": True}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise VoiceToClawError(f"HTTP {exc.code} calling {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise VoiceToClawError(f"Request failed calling {path}: {exc}") from exc


def fetch_json(url: str, *, token: str = "", timeout_seconds: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=bridge_headers(token), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8").strip()
            return json.loads(raw) if raw else {"ok": True}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise VoiceToClawError(f"HTTP {exc.code} calling {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise VoiceToClawError(f"Request failed calling {url}: {exc}") from exc


def bridge_lamp_endpoint_error(base_url: str, *, token: str, timeout_seconds: float = 0.8) -> str | None:
    url = f"{base_url.rstrip('/')}/health"
    try:
        health = fetch_json(url, token=token, timeout_seconds=2)
    except Exception as exc:  # noqa: BLE001
        return f"local bridge not reachable: {exc}"
    runtime = health.get("runtime") if isinstance(health, dict) else {}
    lamp_base_url = str(runtime.get("baseUrl") or "") if isinstance(runtime, dict) else ""
    parsed = urllib.parse.urlparse(lamp_base_url)
    if parsed.scheme != "tcp":
        return None
    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return f"invalid lamp endpoint: {lamp_base_url}"
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return None
    except OSError as exc:
        return f"lamp endpoint {host}:{port} not reachable: {exc}"


SHENZHEN_SCENE_IDS: dict[str, str] = {
    "wake_up": "01_presence_wake",
    "curious_observe": "02_cautious_intro",
    "cute_probe": "02_cautious_intro",
    "touch_affection": "03_hand_nuzzle",
    "celebrate": "04_offer_celebrate",
    "farewell": "05_farewell",
    "sleep": "06_sleep",
    "track_target": "07_tabletop_follow",
}


def shenzhen_scene_id_for_action(action: dict[str, Any]) -> str | None:
    if action.get("type") != "scene":
        return None
    return SHENZHEN_SCENE_IDS.get(str(action.get("name") or ""))


def shenzhen_console_available(console_url: str) -> bool:
    if not console_url:
        return False
    try:
        state = fetch_json(f"{console_url.rstrip('/')}/api/state", timeout_seconds=1)
    except Exception:  # noqa: BLE001
        return False
    return bool(state.get("ok")) if isinstance(state, dict) else False


def post_shenzhen_scene(console_url: str, scene_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {
        "context": payload,
        "source": "mira-light-voice",
    }
    return post_json(console_url, f"/api/run/{urllib.parse.quote(scene_id)}", body, timeout_seconds=8)


def maybe_trigger_mira_action(
    session: ConversationSession,
    *,
    intent: str,
    transcript: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if args.no_trigger:
        return {"ok": True, "skipped": True, "reason": "trigger-disabled"}

    action = action_for_intent(intent)
    if not action:
        return {"ok": True, "skipped": True, "reason": "no-mapped-action"}

    now = time.monotonic()
    if session.last_scene == action["name"] and (now - session.last_trigger_monotonic) < args.trigger_cooldown_seconds:
        return {"ok": True, "skipped": True, "reason": "cooldown-active", "name": action["name"]}

    payload = bridge_payload_for_intent(intent, transcript)
    shenzhen_scene_id = shenzhen_scene_id_for_action(action)
    if shenzhen_scene_id and shenzhen_console_available(args.shenzhen_console_url):
        response = post_shenzhen_scene(args.shenzhen_console_url, shenzhen_scene_id, payload)
        session.last_scene = action["name"]
        session.last_trigger_monotonic = now
        return {
            "ok": True,
            "action": action,
            "route": "shenzhen-console",
            "shenzhenSceneId": shenzhen_scene_id,
            "response": response,
        }

    endpoint_error = bridge_lamp_endpoint_error(args.bridge_url, token=args.bridge_token)
    if endpoint_error:
        return {"ok": False, "error": endpoint_error, "action": action}

    if action["type"] == "trigger":
        body = {"event": action["name"], "payload": payload}
        response = post_bridge_json(args.bridge_url, "/v1/mira-light/trigger", body, token=args.bridge_token, timeout_seconds=8)
    else:
        body = {"scene": action["name"], "async": True, "cueMode": "scene", "context": payload}
        response = post_bridge_json(args.bridge_url, "/v1/mira-light/run-scene", body, token=args.bridge_token, timeout_seconds=8)

    session.last_scene = action["name"]
    session.last_trigger_monotonic = now
    return {"ok": True, "action": action, "response": response}


def rms_level(samples: np.ndarray) -> float:
    mono = ensure_mono_float32(samples)
    if mono.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(mono), dtype=np.float64)))


def peak_level(samples: np.ndarray) -> float:
    mono = ensure_mono_float32(samples)
    if mono.size == 0:
        return 0.0
    return float(np.max(np.abs(mono)))


def build_audio_metrics(samples: np.ndarray, *, sample_rate: int) -> dict[str, float]:
    mono = ensure_mono_float32(samples)
    duration_ms = (len(mono) / sample_rate * 1000.0) if sample_rate > 0 else 0.0
    return {
        "durationMs": round(duration_ms, 3),
        "rms": round(rms_level(mono), 6),
        "peak": round(peak_level(mono), 6),
    }


def low_energy_skip_reason(source_meta: dict[str, Any], audio_metrics: dict[str, float]) -> str | None:
    if source_meta.get("captureMode") not in {"continuous", "enter-vad"}:
        return None
    if audio_metrics["durationMs"] > 1500:
        return None
    if audio_metrics["rms"] >= DEFAULT_SKIP_LOW_RMS:
        return None
    if audio_metrics["peak"] >= DEFAULT_SKIP_LOW_PEAK:
        return None
    return "low-energy-utterance"


def visible_transcript_text(text: str) -> str:
    return "".join(VISIBLE_TEXT_PATTERN.findall(text or ""))


def repeated_substring_details(visible_text: str) -> dict[str, int | str] | None:
    for unit_length in range(DEFAULT_REPEAT_MIN_SUBSTRING_UNIT, DEFAULT_REPEAT_MAX_SUBSTRING_UNIT + 1):
        best_unit = ""
        best_run = 0
        index = 0
        while index + unit_length <= len(visible_text):
            unit = visible_text[index : index + unit_length]
            if not unit.strip():
                index += 1
                continue
            run = 1
            cursor = index + unit_length
            while visible_text[cursor : cursor + unit_length] == unit:
                run += 1
                cursor += unit_length
            if run > best_run:
                best_run = run
                best_unit = unit
            index += max(1, unit_length * run)
        if best_run >= DEFAULT_REPEAT_MIN_SUBSTRING_RUN:
            return {
                "reason": "repetitive-transcript",
                "mode": "substring-run",
                "unit": best_unit,
                "unitLength": unit_length,
                "runLength": best_run,
            }
    return None


def repetitive_transcript_details(
    transcript_payload: dict[str, Any],
    *,
    audio_metrics: dict[str, float],
) -> dict[str, float | int | str] | None:
    visible_text = visible_transcript_text(str(transcript_payload.get("text") or ""))
    if len(visible_text) < DEFAULT_REPEAT_MIN_CHARS:
        return None

    counts: dict[str, int] = {}
    for ch in visible_text:
        counts[ch] = counts.get(ch, 0) + 1
    dominant_char, dominant_count = max(counts.items(), key=lambda item: item[1])
    dominant_ratio = dominant_count / len(visible_text)
    unique_chars = len(counts)

    segments = transcript_payload.get("segments")
    compression_ratio = 0.0
    segment_duration_seconds = 0.0
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            compression_ratio = max(compression_ratio, float(segment.get("compression_ratio") or 0.0))
            start = float(segment.get("start") or 0.0)
            end = float(segment.get("end") or 0.0)
            segment_duration_seconds += max(0.0, end - start)

    duration_seconds = max(audio_metrics["durationMs"] / 1000.0, segment_duration_seconds, 1e-6)
    chars_per_second = len(visible_text) / duration_seconds
    tokens = TOKEN_PATTERN.findall(str(transcript_payload.get("text") or ""))

    substring_result = repeated_substring_details(visible_text)
    if substring_result is not None:
        substring_result["compressionRatio"] = round(compression_ratio, 4)
        substring_result["charsPerSecond"] = round(chars_per_second, 3)
        substring_result["visibleChars"] = len(visible_text)
        substring_result["dominantChar"] = dominant_char
        substring_result["dominantRatio"] = round(dominant_ratio, 4)
        return substring_result

    if dominant_ratio < DEFAULT_REPEAT_DOMINANT_RATIO:
        dominant_char_result = None
    elif unique_chars > DEFAULT_REPEAT_MAX_UNIQUE_CHARS:
        dominant_char_result = None
    elif compression_ratio < DEFAULT_REPEAT_MAX_COMPRESSION_RATIO and chars_per_second < DEFAULT_REPEAT_MAX_CHARS_PER_SECOND:
        dominant_char_result = None
    else:
        dominant_char_result = {
            "reason": "repetitive-transcript",
            "mode": "character",
            "dominantChar": dominant_char,
            "dominantRatio": round(dominant_ratio, 4),
            "uniqueChars": unique_chars,
            "compressionRatio": round(compression_ratio, 4),
            "charsPerSecond": round(chars_per_second, 3),
            "visibleChars": len(visible_text),
        }

    if dominant_char_result:
        return dominant_char_result

    if len(tokens) < 6:
        return None
    token_counts: dict[str, int] = {}
    for token in tokens:
        token_counts[token] = token_counts.get(token, 0) + 1
    dominant_token, dominant_token_count = max(token_counts.items(), key=lambda item: item[1])
    dominant_token_ratio = dominant_token_count / len(tokens)
    if (
        dominant_token_ratio >= 0.75
        and len(token_counts) <= DEFAULT_REPEAT_MAX_UNIQUE_CHARS
        and (
            compression_ratio >= DEFAULT_REPEAT_MAX_COMPRESSION_RATIO
            or chars_per_second >= DEFAULT_REPEAT_MAX_CHARS_PER_SECOND
        )
    ):
        return {
            "reason": "repetitive-transcript",
            "mode": "token",
            "dominantToken": dominant_token,
            "dominantRatio": round(dominant_token_ratio, 4),
            "uniqueTokens": len(token_counts),
            "compressionRatio": round(compression_ratio, 4),
            "charsPerSecond": round(chars_per_second, 3),
            "tokenCount": len(tokens),
        }

    longest_run_token = ""
    longest_run = 0
    current_token = ""
    current_run = 0
    for token in tokens:
        normalized_token = token.lower()
        if normalized_token == current_token:
            current_run += 1
        else:
            current_token = normalized_token
            current_run = 1
        if current_run > longest_run:
            longest_run = current_run
            longest_run_token = normalized_token
    if longest_run >= DEFAULT_REPEAT_MIN_TOKEN_RUN:
        return {
            "reason": "repetitive-transcript",
            "mode": "consecutive-token-run",
            "dominantToken": longest_run_token,
            "runLength": longest_run,
            "tokenCount": len(tokens),
            "compressionRatio": round(compression_ratio, 4),
            "charsPerSecond": round(chars_per_second, 3),
        }
    return None


def capture_continuous_utterance(args: argparse.Namespace, *, require_manual_start: bool = False) -> UtteranceResult | None:
    device = resolve_input_device(args.device)
    sample_rate = int(args.sample_rate)
    channels = int(args.channels)
    chunk_frames = max(1, int(sample_rate * (args.chunk_ms / 1000.0)))
    chunk_seconds = chunk_frames / sample_rate
    start_chunks = max(1, math.ceil(args.vad_start_ms / args.chunk_ms))
    end_chunks = max(1, math.ceil(args.vad_end_ms / args.chunk_ms))
    min_chunks = max(1, math.ceil(args.min_utterance_ms / args.chunk_ms))
    max_chunks = max(min_chunks, math.ceil(args.max_utterance_seconds / chunk_seconds))
    preroll_chunks = start_chunks
    timeout_seconds = max(0.2, min(1.0, args.chunk_ms / 1000.0 * 2))

    q: queue.Queue[np.ndarray] = queue.Queue()
    errors: list[str] = []

    def callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        del frames, time_info
        if status:
            errors.append(str(status))
        q.put(indata.copy())

    pre_roll: deque[np.ndarray] = deque(maxlen=preroll_chunks)
    utterance_chunks: list[np.ndarray] = []
    idle_started = time.monotonic()
    noise_floor = max(1e-4, args.vad_min_rms * 0.5)
    speech_run = 0
    silence_run = 0
    active = False

    if require_manual_start:
        print("Press Enter to start listening. Recording will stop automatically after silence.")
        input()

    with sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        callback=callback,
        device=int(device["index"]),
    ):
        while True:
            try:
                chunk = q.get(timeout=timeout_seconds)
            except queue.Empty:
                if require_manual_start and not active:
                    continue
                if not active and (time.monotonic() - idle_started) >= args.idle_timeout_seconds:
                    return None
                continue

            mono = ensure_mono_float32(chunk)
            chunk_rms = rms_level(mono)
            threshold = max(args.vad_min_rms, noise_floor * args.vad_speech_ratio)
            is_speech = chunk_rms >= threshold

            if not active:
                pre_roll.append(chunk)
                if is_speech:
                    speech_run += 1
                else:
                    speech_run = 0
                    noise_floor = 0.9 * noise_floor + 0.1 * chunk_rms
                if speech_run >= start_chunks:
                    active = True
                    utterance_chunks = list(pre_roll)
                    silence_run = 0
                    if args.verbose_vad:
                        print(f"[vad] speech-start rms={chunk_rms:.4f} threshold={threshold:.4f}")
                continue

            utterance_chunks.append(chunk)
            if is_speech:
                silence_run = 0
            else:
                silence_run += 1

            if silence_run < end_chunks and len(utterance_chunks) < max_chunks:
                continue

            samples = np.concatenate(utterance_chunks, axis=0)
            duration_ms = len(samples) / sample_rate * 1000.0
            if duration_ms < args.min_utterance_ms:
                if args.verbose_vad:
                    print(f"[vad] dropped short utterance duration_ms={duration_ms:.0f}")
                pre_roll.clear()
                utterance_chunks = []
                active = False
                speech_run = 0
                silence_run = 0
                idle_started = time.monotonic()
                continue

            if errors and args.verbose_vad:
                print(f"[audio-status] {errors[-1]}", file=sys.stderr)
            return UtteranceResult(
                samples=samples,
                sample_rate=sample_rate,
                source_meta={
                    "inputDevice": device,
                    "captureMode": "enter-vad" if require_manual_start else "continuous",
                    "vad": {
                        "startMs": args.vad_start_ms,
                        "endMs": args.vad_end_ms,
                        "minUtteranceMs": args.min_utterance_ms,
                        "maxUtteranceSeconds": args.max_utterance_seconds,
                        "chunkMs": args.chunk_ms,
                    },
                },
            )


def capture_next_utterance(args: argparse.Namespace) -> UtteranceResult | None:
    if args.file:
        source_path = Path(args.file).expanduser().resolve()
        if not source_path.is_file():
            raise VoiceToClawError(f"Audio file not found: {source_path}")
        samples, sample_rate = load_audio_file(source_path)
        return UtteranceResult(samples=samples, sample_rate=sample_rate, source_meta={"sourceFile": str(source_path)})

    if args.mode == "ptt":
        device = resolve_input_device(args.device)
        samples = record_push_to_talk(
            device_index=int(device["index"]),
            sample_rate=args.sample_rate,
            channels=args.channels,
        )
        return UtteranceResult(samples=samples, sample_rate=args.sample_rate, source_meta={"inputDevice": device, "captureMode": "ptt"})

    if args.mode == "fixed":
        device = resolve_input_device(args.device)
        samples = record_fixed_duration(
            device_index=int(device["index"]),
            sample_rate=args.sample_rate,
            channels=args.channels,
            seconds=args.seconds,
        )
        return UtteranceResult(samples=samples, sample_rate=args.sample_rate, source_meta={"inputDevice": device, "captureMode": "fixed"})

    if args.mode == "enter-vad":
        return capture_continuous_utterance(args, require_manual_start=True)

    return capture_continuous_utterance(args)


def transcribe_utterance(utterance: UtteranceResult, *, args: argparse.Namespace) -> dict[str, Any]:
    model_repo = args.model_repo or DEFAULT_MODEL_PROFILES[args.profile]
    initial_prompt = args.initial_prompt or DEFAULT_INITIAL_PROMPT
    transcript_payload = transcribe_local(
        utterance.samples,
        sample_rate=int(utterance.sample_rate),
        language=args.language,
        model_repo=model_repo,
        initial_prompt=initial_prompt,
    )
    raw_transcript = str(transcript_payload.get("text") or "").strip()
    transcript, normalization_applied = normalize_turn_transcript(raw_transcript)
    transcript_payload["rawText"] = raw_transcript
    transcript_payload["text"] = transcript
    transcript_payload["normalizationApplied"] = normalization_applied
    transcript_payload["captureMode"] = utterance.source_meta.get("captureMode")
    transcript_payload["modelRepo"] = model_repo
    transcript_payload["initialPrompt"] = initial_prompt
    return transcript_payload


def warm_stt_model(args: argparse.Namespace) -> dict[str, Any]:
    model_repo = args.model_repo or DEFAULT_MODEL_PROFILES[args.profile]
    sample_rate = 16000
    warm_samples = np.zeros(int(sample_rate * 0.25), dtype=np.float32)
    started = time.perf_counter()
    try:
        transcribe_local(
            warm_samples,
            sample_rate=sample_rate,
            language=args.language,
            model_repo=model_repo,
            initial_prompt=args.initial_prompt or DEFAULT_INITIAL_PROMPT,
        )
        return {"ok": True, "modelRepo": model_repo, "seconds": round(time.perf_counter() - started, 3)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "modelRepo": model_repo, "error": str(exc), "seconds": round(time.perf_counter() - started, 3)}


def ping_runtime_interfaces(args: argparse.Namespace) -> dict[str, Any]:
    results: dict[str, Any] = {}
    if args.reply_backend == "lingzhu" and args.lingzhu_base_url:
        base_url = args.lingzhu_base_url.rstrip("/")
        health_errors: list[str] = []
        for path in ("/v1/health", "/metis/agent/api/health"):
            url = f"{base_url}{path}"
            try:
                results["lingzhu"] = fetch_json(url, timeout_seconds=3)
                results["lingzhu"]["healthPath"] = path
                break
            except Exception as exc:  # noqa: BLE001
                health_errors.append(f"{path}: {exc}")
        else:
            results["lingzhu"] = {"ok": False, "error": " | ".join(health_errors)}
    if args.bridge_url:
        url = f"{args.bridge_url.rstrip('/')}/health"
        try:
            results["bridge"] = fetch_json(url, token=args.bridge_token, timeout_seconds=3)
        except Exception as exc:  # noqa: BLE001
            results["bridge"] = {"ok": False, "error": str(exc)}
    return results


def maybe_keep_warm(
    *,
    args: argparse.Namespace,
    audio_player: AudioCuePlayer,
    warm_state: WarmState,
    force: bool = False,
    include_stt: bool = False,
) -> dict[str, Any] | None:
    if not force and args.keep_warm_seconds <= 0:
        return None
    now = time.monotonic()
    if not force and (now - warm_state.last_keep_warm_monotonic) < args.keep_warm_seconds:
        return None

    payload: dict[str, Any] = {
        "at": datetime.now().isoformat(),
        "audio": audio_player.prepare_output(),
        "http": ping_runtime_interfaces(args),
    }
    if include_stt:
        payload["stt"] = warm_stt_model(args)
    warm_state.last_keep_warm_monotonic = now
    return payload


def run_turn(
    *,
    turn_dir: Path,
    session: ConversationSession,
    audio_player: AudioCuePlayer,
    args: argparse.Namespace,
) -> dict[str, Any]:
    turn_started = time.perf_counter()
    utterance = capture_next_utterance(args)
    if utterance is None:
        return {"idleTimeoutReached": True}
    captured_at = time.perf_counter()

    audio_path = save_wav(utterance.samples, sample_rate=int(utterance.sample_rate), path=turn_dir / "input.wav")
    audio_metrics = build_audio_metrics(utterance.samples, sample_rate=int(utterance.sample_rate))

    result: dict[str, Any] = {
        "audioPath": str(audio_path),
        "inputMeta": utterance.source_meta,
        "audioMetrics": audio_metrics,
        "latencyPolicy": {
            "preset": args.latency_preset,
            "vadStartMs": args.vad_start_ms,
            "vadEndMs": args.vad_end_ms,
            "historyTurns": args.history_turns,
            "profile": args.profile,
            "startupWarmup": bool(args.startup_warmup),
            "keepWarmSeconds": args.keep_warm_seconds,
        },
    }

    low_energy_reason = low_energy_skip_reason(utterance.source_meta, audio_metrics)
    if low_energy_reason:
        result["skipped"] = True
        result["skipReason"] = low_energy_reason
        return result

    try:
        stt_started = time.perf_counter()
        transcript_payload = transcribe_utterance(utterance, args=args)
        stt_finished = time.perf_counter()
    except VoiceToClawError as exc:
        if "empty text" not in str(exc).lower():
            raise
        result["skipped"] = True
        result["skipReason"] = "empty-transcript"
        result["transcriptionError"] = str(exc)
        return result

    transcript = str(transcript_payload["text"]).strip()
    raw_transcript = str(transcript_payload.get("rawText") or "").strip()

    (turn_dir / "transcript.txt").write_text(transcript + "\n", encoding="utf-8")
    write_json(turn_dir / "transcript.json", transcript_payload)

    result.update(
        {
            "transcript": transcript,
            "rawTranscript": raw_transcript,
            "normalizationApplied": bool(transcript_payload.get("normalizationApplied")),
            "modelRepo": transcript_payload.get("modelRepo"),
            "initialPrompt": transcript_payload.get("initialPrompt"),
        }
    )
    result["timings"] = {
        "captureSeconds": round(captured_at - turn_started, 3),
        "sttSeconds": round(stt_finished - stt_started, 3),
    }

    repetitive_details = repetitive_transcript_details(transcript_payload, audio_metrics=audio_metrics)
    if repetitive_details:
        result["skipped"] = True
        result["skipReason"] = str(repetitive_details["reason"])
        result["skipDetails"] = repetitive_details
        return result

    if should_exit(transcript):
        result["exitRequested"] = True
        return result

    intent = classify_intent(transcript)
    update_session_mode(session, intent)
    result["intent"] = intent
    result["sessionMode"] = session.mode
    if should_skip_short_reply(transcript, intent=intent):
        result["skipped"] = True
        result["skipReason"] = "short-low-information-transcript"
        return result
    is_greeting_turn = intent == "chat" and is_brief_greeting(transcript)
    lingzhu_additional_user_ids: str | list[str] | tuple[str, ...] | None = args.lingzhu_additional_user_ids
    if args.reply_backend == "lingzhu" and is_greeting_turn:
        lingzhu_additional_user_ids = []
    result["memoryPolicy"] = {
        "briefGreeting": is_greeting_turn,
        "additionalUserIdsRequested": args.lingzhu_additional_user_ids,
        "additionalUserIdsUsed": lingzhu_additional_user_ids,
    }

    try:
        trigger_started = time.perf_counter()
        trigger_result = maybe_trigger_mira_action(session, intent=intent, transcript=transcript, args=args)
        trigger_finished = time.perf_counter()
    except Exception as exc:  # noqa: BLE001
        trigger_finished = time.perf_counter()
        trigger_result = {"ok": False, "error": str(exc)}
    result["triggerResult"] = trigger_result
    result["timings"]["triggerSeconds"] = round(trigger_finished - trigger_started, 3)

    messages = build_messages(session, transcript, base_prompt=args.api_system_prompt)
    result["messages"] = messages

    action_reply = local_action_reply(intent, trigger_result)
    if action_reply:
        reply_started = reply_finished = time.perf_counter()
        raw_reply_text = action_reply
        api_meta = {
            "provider": "local-action-ack",
            "intent": intent,
            "payload": {"localActionAck": True, "intent": intent, "triggerResult": trigger_result},
        }
        reply_backend = "local-action-ack"
    else:
        try:
            reply_started = time.perf_counter()
            raw_reply_text, api_meta, reply_backend = send_reply(
                messages,
                session=session,
                args=args,
                additional_user_ids=lingzhu_additional_user_ids,
            )
            reply_finished = time.perf_counter()
        except Exception as exc:  # noqa: BLE001
            reply_finished = time.perf_counter()
            error_text = str(exc)
            raw_reply_text = "" if args.reply_backend == "lingzhu" and "401" in error_text else fallback_reply_for_intent(intent)
            api_meta = {"provider": "fallback", "error": str(exc), "payload": {"fallback": True, "intent": intent}}
            reply_backend = "fallback"
    result["timings"]["replySeconds"] = round(reply_finished - reply_started, 3)

    reply_text, reply_normalization = normalize_reply_text(raw_reply_text)
    (turn_dir / "reply.txt").write_text(reply_text + "\n", encoding="utf-8")
    write_json(turn_dir / "reply.api.json", api_meta.get("payload", api_meta))

    result["replyBackend"] = reply_backend
    result["replyText"] = reply_text
    result["rawReplyText"] = raw_reply_text
    result.update(reply_normalization)
    result["apiMeta"] = {k: v for k, v in api_meta.items() if k != "payload"}

    if reply_text:
        tts_started = time.perf_counter()
        audio_result = audio_player.speak_text(reply_text, voice=args.voice_mode, wait=True)
        tts_finished = time.perf_counter()
        write_json(turn_dir / "reply.audio.json", audio_result)
        result["audioResult"] = audio_result
        result["timings"]["ttsAndPlaybackSeconds"] = round(tts_finished - tts_started, 3)
        elapsed = audio_result.get("elapsedSeconds") if isinstance(audio_result, dict) else None
        if isinstance(elapsed, (int, float)):
            result["timings"]["audioCommandSeconds"] = float(elapsed)
        if args.post_tts_cooldown_seconds > 0:
            cooldown_started = time.perf_counter()
            time.sleep(args.post_tts_cooldown_seconds)
            cooldown_finished = time.perf_counter()
            result["postTtsCooldownSeconds"] = args.post_tts_cooldown_seconds
            result["timings"]["postTtsCooldownSeconds"] = round(cooldown_finished - cooldown_started, 3)
    else:
        result["timings"]["ttsAndPlaybackSeconds"] = 0.0

    session.last_user_text = transcript
    session.last_reply_text = reply_text
    session.append_turn(transcript, reply_text)
    result["sessionState"] = session.snapshot()
    result["timings"]["totalTurnSeconds"] = round(time.perf_counter() - turn_started, 3)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Realtime voice interaction runtime for Mira Light booth demos.")
    parser.add_argument("--list-inputs", action="store_true", help="List audio input devices and exit.")
    parser.add_argument("--mode", choices=["continuous", "enter-vad", "ptt", "fixed"], default=DEFAULT_MODE, help="Audio capture mode.")
    parser.add_argument("--device", default="DJI MIC MINI", help="Input device name or index.")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_CAPTURE_SAMPLE_RATE, help="Microphone capture sample rate.")
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS, help="Microphone capture channels.")
    parser.add_argument("--seconds", type=float, default=6.0, help="Fixed recording length for fixed mode.")
    parser.add_argument("--file", help="Run a single turn from an existing audio file.")
    parser.add_argument("--once", action="store_true", help="Run a single turn and exit.")
    parser.add_argument(
        "--profile",
        choices=sorted(DEFAULT_MODEL_PROFILES),
        default=os.environ.get("MIRA_LIGHT_STT_PROFILE", DEFAULT_MODEL_PROFILE),
        help="Local MLX Whisper profile.",
    )
    parser.add_argument("--model-repo", help="Override the MLX Whisper model repo.")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="Language hint for STT.")
    parser.add_argument(
        "--initial-prompt",
        default=os.environ.get("MIRA_LIGHT_STT_INITIAL_PROMPT"),
        help="Optional STT terminology prompt.",
    )
    parser.add_argument("--api-system-prompt", default=DEFAULT_API_SYSTEM_PROMPT, help="System prompt for reply generation.")
    parser.add_argument(
        "--latency-preset",
        choices=["standard", "low"],
        default=os.environ.get("MIRA_LIGHT_LATENCY_PRESET", DEFAULT_LATENCY_PRESET),
        help="Preset for booth latency tuning.",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="OpenClaw reply timeout in seconds.")
    parser.add_argument(
        "--reply-backend",
        choices=["openclaw-agent", "lingzhu"],
        default=os.environ.get("MIRA_LIGHT_REPLY_BACKEND", DEFAULT_REPLY_BACKEND),
        help="Reply backend for Mira dialogue.",
    )
    parser.add_argument("--reply-agent", default=os.environ.get("MIRA_LIGHT_REPLY_AGENT", DEFAULT_REPLY_AGENT), help="OpenClaw agent id for reply generation.")
    parser.add_argument("--reply-thinking", default=os.environ.get("MIRA_LIGHT_REPLY_THINKING", DEFAULT_REPLY_THINKING), help="Thinking level for OpenClaw reply generation.")
    parser.add_argument("--lingzhu-base-url", default=os.environ.get("MIRA_LIGHT_LINGZHU_BASE_URL", ""), help="Lingzhu live adapter base URL.")
    parser.add_argument("--lingzhu-auth-ak", default=os.environ.get("MIRA_LIGHT_LINGZHU_AUTH_AK", ""), help="Lingzhu live adapter auth AK.")
    parser.add_argument("--lingzhu-agent-id", default=os.environ.get("MIRA_LIGHT_LINGZHU_AGENT_ID", "main"), help="Lingzhu agent id.")
    parser.add_argument("--lingzhu-user-id", default=os.environ.get("MIRA_LIGHT_LINGZHU_USER_ID", ""), help="Override Lingzhu user id for the whole session.")
    parser.add_argument(
        "--lingzhu-additional-user-ids",
        default=os.environ.get("MIRA_LIGHT_LINGZHU_ADDITIONAL_USER_IDS", "mira-light-bridge"),
        help="Comma-separated additional user ids for Lingzhu prompt-pack memory.",
    )
    parser.add_argument(
        "--voice-mode",
        dest="voice_mode",
        default=os.environ.get("MIRA_LIGHT_TTS_MODE", DEFAULT_VOICE_MODE),
        choices=["gentle_sister", "warm_gentleman", "female", "male"],
        help="Audio voice mode for speaker playback.",
    )
    parser.add_argument("--voice", dest="voice_mode", choices=["gentle_sister", "warm_gentleman", "female", "male"], help=argparse.SUPPRESS)
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR), help="Directory for saved session artifacts.")
    parser.add_argument("--history-turns", type=int, default=DEFAULT_HISTORY_TURNS, help="How many recent turns to keep in context.")
    parser.add_argument("--idle-timeout-seconds", type=float, default=DEFAULT_IDLE_TIMEOUT_SECONDS, help="How long continuous mode waits without speech before ending the session.")
    parser.add_argument("--trigger-cooldown-seconds", type=float, default=DEFAULT_TRIGGER_COOLDOWN_SECONDS, help="Minimum seconds before repeating the same scene trigger.")
    parser.add_argument("--bridge-url", default=os.environ.get("MIRA_LIGHT_BRIDGE_URL", DEFAULT_BRIDGE_URL), help="Base URL for the local Mira Light bridge.")
    parser.add_argument("--bridge-token", default=os.environ.get("MIRA_LIGHT_BRIDGE_TOKEN", ""), help="Bridge bearer token, if required.")
    parser.add_argument(
        "--shenzhen-console-url",
        default=os.environ.get("MIRA_LIGHT_SHENZHEN_CONSOLE_URL", DEFAULT_SHENZHEN_CONSOLE_URL),
        help="Shenzhen demo console URL. Scene triggers use this first when available.",
    )
    parser.add_argument("--no-trigger", action="store_true", help="Disable runtime scene/trigger calls and only do conversation + TTS.")
    parser.add_argument("--dry-run-audio", action="store_true", help="Do not actually play speaker audio.")
    parser.add_argument(
        "--startup-warmup",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Warm STT, speaker output, and health endpoints before listening.",
    )
    parser.add_argument(
        "--keep-warm-seconds",
        type=float,
        default=float(os.environ.get("MIRA_LIGHT_KEEP_WARM_SECONDS", DEFAULT_KEEP_WARM_SECONDS)),
        help="Ping hot interfaces every N seconds between turns. 0 disables keep-warm.",
    )
    parser.add_argument(
        "--post-tts-cooldown-seconds",
        type=float,
        default=float(os.environ.get("MIRA_LIGHT_POST_TTS_COOLDOWN_SECONDS", DEFAULT_POST_TTS_COOLDOWN_SECONDS)),
        help="Pause briefly after speaking so the mic does not capture speaker tail audio.",
    )
    parser.add_argument("--vad-start-ms", type=int, default=DEFAULT_VAD_START_MS, help="Speech onset duration in ms for continuous mode.")
    parser.add_argument("--vad-end-ms", type=int, default=DEFAULT_VAD_END_MS, help="Silence duration in ms to end an utterance.")
    parser.add_argument("--min-utterance-ms", type=int, default=DEFAULT_MIN_UTTERANCE_MS, help="Minimum utterance duration in ms.")
    parser.add_argument("--max-utterance-seconds", type=float, default=DEFAULT_MAX_UTTERANCE_SECONDS, help="Maximum utterance duration in seconds.")
    parser.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS, help="Audio chunk size in ms for continuous mode.")
    parser.add_argument("--vad-min-rms", type=float, default=DEFAULT_VAD_MIN_RMS, help="Base RMS threshold for speech detection.")
    parser.add_argument("--vad-speech-ratio", type=float, default=DEFAULT_VAD_SPEECH_RATIO, help="Multiplier above noise floor to consider a chunk speech.")
    parser.add_argument("--verbose-vad", action="store_true", help="Print VAD debug messages.")
    return parser.parse_args()


def save_session_snapshot(session_dir: Path, session: ConversationSession, args: argparse.Namespace) -> None:
    write_json(
        session_dir / "session.json",
        {
            "savedAt": datetime.now().isoformat(),
            "args": {
                "mode": args.mode,
                "device": args.device,
                "sampleRate": args.sample_rate,
                "channels": args.channels,
                "profile": args.profile,
                "bridgeUrl": args.bridge_url,
                "triggerDisabled": args.no_trigger,
                "historyTurns": args.history_turns,
                "replyBackend": args.reply_backend,
                "replyAgent": args.reply_agent,
                "replyThinking": args.reply_thinking,
                "latencyPreset": args.latency_preset,
                "startupWarmup": bool(args.startup_warmup),
                "keepWarmSeconds": args.keep_warm_seconds,
                "vadStartMs": args.vad_start_ms,
                "vadEndMs": args.vad_end_ms,
            },
            "session": session.snapshot(),
        },
    )


def main() -> int:
    args = parse_args()
    latency_changes = apply_latency_preset(args)

    if args.list_inputs:
        return print_input_devices()

    session_dir = build_session_dir(Path(args.runtime_dir).expanduser())
    session = ConversationSession(max_history_turns=max(1, args.history_turns))
    audio_player = AudioCuePlayer(dry_run=args.dry_run_audio)
    warm_state = WarmState()

    print("Mira realtime voice interaction is ready.")
    print(f"Capture mode: {args.mode}")
    print(f"Input device: {args.device}")
    print(f"STT profile: {args.profile} @ {args.sample_rate} Hz")
    print(f"Latency preset: {args.latency_preset}")
    if args.reply_backend == "lingzhu":
        print(f"Reply backend: lingzhu ({args.lingzhu_base_url or '-'})")
    else:
        print(f"Reply backend: openclaw-agent ({args.reply_agent})")
    print(f"Bridge: {args.bridge_url} (trigger enabled={not args.no_trigger})")
    if args.mode == "ptt":
        print("Press Enter to start recording, then Enter again to stop. Say '退出对话' to exit.")
    elif args.mode == "enter-vad":
        print(
            f"Enter-VAD mode with VAD start={args.vad_start_ms}ms end={args.vad_end_ms}ms. "
            "Press Enter to start each turn; silence will end it automatically."
        )
    elif args.mode == "fixed":
        print(f"Recording fixed {args.seconds:.1f}s turns. Say '退出对话' to exit.")
    else:
        print(
            f"Continuous mode with VAD start={args.vad_start_ms}ms end={args.vad_end_ms}ms "
            f"idle-timeout={args.idle_timeout_seconds:.0f}s."
        )
    if latency_changes:
        print(f"Latency tuning: {json.dumps(latency_changes, ensure_ascii=False)}")

    if args.startup_warmup:
        print("Running startup warmup...")
        warmup_payload = maybe_keep_warm(
            args=args,
            audio_player=audio_player,
            warm_state=warm_state,
            force=True,
            include_stt=True,
        ) or {}
        write_json(session_dir / "warmup.json", warmup_payload)
        http_hint = warmup_payload.get("http") if isinstance(warmup_payload, dict) else {}
        print(f"Warmup ready: {json.dumps(http_hint, ensure_ascii=False)}")

    turn_index = 0
    try:
        while True:
            turn_index += 1
            turn_dir = session_dir / f"turn-{turn_index:03d}"
            turn_dir.mkdir(parents=True, exist_ok=True)

            keep_warm_payload = maybe_keep_warm(
                args=args,
                audio_player=audio_player,
                warm_state=warm_state,
                force=False,
                include_stt=False,
            )
            if keep_warm_payload:
                write_json(turn_dir / "keep-warm.json", keep_warm_payload)

            print(f"\n[turn {turn_index:03d}] listening...")
            turn_result = run_turn(turn_dir=turn_dir, session=session, audio_player=audio_player, args=args)
            write_json(turn_dir / "turn.json", turn_result)
            save_session_snapshot(session_dir, session, args)

            if turn_result.get("idleTimeoutReached"):
                print(f"[turn {turn_index:03d}] idle timeout reached. Ending session.")
                break

            if turn_result.get("skipped"):
                reason = str(turn_result.get("skipReason") or "skipped")
                metrics = turn_result.get("audioMetrics") or {}
                metrics_hint = ""
                if isinstance(metrics, dict) and metrics:
                    metrics_hint = (
                        f" duration={metrics.get('durationMs')}ms"
                        f" rms={metrics.get('rms')}"
                        f" peak={metrics.get('peak')}"
                    )
                print(f"[turn {turn_index:03d}] skipped: {reason}{metrics_hint}")
                if args.file or args.once:
                    break
                continue

            transcript = str(turn_result.get("transcript") or "").strip()
            if transcript:
                print(f"[turn {turn_index:03d}] transcript: {transcript}")

            if turn_result.get("intent"):
                print(f"[turn {turn_index:03d}] intent: {turn_result['intent']} mode={turn_result.get('sessionMode')}")

            reply_text = str(turn_result.get("replyText") or "").strip()
            if reply_text:
                print(f"[turn {turn_index:03d}] mira: {reply_text}")
            timings = turn_result.get("timings") or {}
            if isinstance(timings, dict) and timings:
                timing_parts = []
                timing_labels = [
                    ("captureSeconds", "capture"),
                    ("sttSeconds", "stt"),
                    ("triggerSeconds", "trigger"),
                    ("replySeconds", "reply"),
                    ("ttsAndPlaybackSeconds", "tts+play"),
                    ("audioCommandSeconds", "audio-cmd"),
                    ("postTtsCooldownSeconds", "cooldown"),
                    ("totalTurnSeconds", "total"),
                ]
                for key, label in timing_labels:
                    value = timings.get(key)
                    if isinstance(value, (int, float)):
                        timing_parts.append(f"{label}={value:.3f}s")
                if timing_parts:
                    print(f"[turn {turn_index:03d}] timing: " + " ".join(timing_parts))
            if turn_result.get("replyBackend") == "fallback":
                api_meta = turn_result.get("apiMeta") or {}
                if isinstance(api_meta, dict) and api_meta.get("error"):
                    print(f"[turn {turn_index:03d}] reply fallback error: {api_meta['error']}")

            if turn_result.get("exitRequested"):
                print(f"[turn {turn_index:03d}] exit requested by user speech.")
                break

            if args.file or args.once:
                break
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")

    save_session_snapshot(session_dir, session, args)
    print(f"Saved session under: {session_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VoiceToClawError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
