#!/usr/bin/env python3
"""Shared voice-intent helpers for Mira Light speech pipelines."""

from __future__ import annotations

from typing import Any


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "comfort": ("好累", "累死", "很累", "今天好累", "辛苦", "难受", "不舒服", "烦", "委屈", "低落", "沮丧"),
    "farewell": ("拜拜", "再见", "我走了", "先走了", "下次见", "回头见"),
    "praise": ("好可爱", "可爱", "喜欢你", "真好看", "好漂亮", "真漂亮"),
    "criticism": ("不好看", "不可爱", "不喜欢你", "你表现不好", "你今天不太行", "你今天有点不太行", "一般般", "有点失望"),
    "celebrate_mood": ("开心", "高兴", "兴奋", "快乐", "太好了", "好耶", "庆祝"),
    "sleep_mood": ("困了", "想睡", "想休息", "休息一下", "安静一点"),
    "daydream_mood": ("发呆", "走神", "放空", "白日梦"),
    "startle_mood": ("害怕", "吓到", "吓一跳", "受惊", "紧张"),
}

COMMAND_PREFIXES = (
    "启动",
    "开始",
    "执行",
    "运行",
    "播放",
    "触发",
    "切到",
    "切换到",
    "进入",
    "来个",
    "来一个",
    "打开",
    "开一下",
    "演示",
)

EMOTION_FIRST_ALIASES = {
    "唉",
    "哎",
    "拜拜",
    "再见",
    "你好可爱",
    "真可爱",
    "我今天好累",
    "累了",
    "疲惫",
    "表现不好",
    "不太行",
    "真漂亮",
    "好漂亮",
}

SCENE_COMMAND_ALIASES: dict[str, tuple[str, ...]] = {
    "wake_up": ("起床", "醒来", "唤醒", "开场", "苏醒", "伸懒腰", "醒一醒", "醒一下", "开机"),
    "curious_observe": ("好奇", "观察", "看一下", "看看我", "好奇你是谁", "歪头看", "试探"),
    "touch_affection": ("摸一摸", "摸摸", "亲近", "撒娇", "靠过来", "蹭一下", "摸它", "互动"),
    "hand_avoid": ("躲开", "躲一下", "手靠近", "别碰", "避开", "后退", "缩一下"),
    "cute_probe": ("卖萌", "可爱动作", "歪头", "探头", "萌一下", "装可爱"),
    "daydream": ("发呆", "走神", "做梦", "白日梦", "放空", "呆一下"),
    "standup_reminder": ("久坐", "站起来", "起身", "提醒我站起来", "蹭蹭", "活动一下"),
    "track_target": ("追踪", "跟踪", "跟着看", "看这边", "目标追踪", "追踪目标", "跟随"),
    "celebrate": ("庆祝", "跳舞", "跳舞模式", "开心跳", "彩虹", "高兴一下", "庆祝一下"),
    "farewell": ("拜拜", "再见", "挥手", "送别", "下次见", "告别"),
    "sleep": ("睡觉", "休息", "睡眠", "关灯休息", "安静下来", "收起来", "回去睡觉"),
    "sigh_demo": ("叹气", "叹气检测", "安慰", "唉", "哎", "听我叹气"),
    "multi_person_demo": ("多人", "两个人", "多人反应", "纠结一下", "不知道看谁"),
    "voice_demo_tired": ("我今天好累", "语音理解", "听懂我累", "累了", "疲惫", "安慰我"),
    "startle_sound": ("吓一跳", "受惊", "惊吓", "突然声音", "被吓到"),
    "praise_demo": ("夸奖", "被夸奖", "开心一下", "你好可爱", "真可爱", "表扬"),
    "criticism_demo": ("批评", "被批评", "委屈", "表现不好", "不太行", "难过一下"),
}

SIGH_KEYWORDS = {
    "唉",
    "哎",
    "唉呀",
    "哎呀",
    "唉...",
    "哎...",
    "唉……",
    "哎……",
}

GREETING_PHRASES = {
    "你好",
    "你好啊",
    "你好呀",
    "哈喽",
    "嗨",
    "hello",
    "hi",
}
LOW_INFORMATION_UTTERANCES = {
    "嗯",
    "嗯嗯",
    "啊",
    "啊啊",
    "哦",
    "哦哦",
    "喔",
    "喔喔",
    "额",
    "呃",
    "诶",
    "欸",
    "哈",
    "哼",
}

INTENT_ACTIONS: dict[str, dict[str, str]] = {
    "sigh": {"type": "trigger", "name": "sigh_detected"},
    "comfort": {"type": "trigger", "name": "voice_tired"},
    "farewell": {"type": "trigger", "name": "farewell_detected"},
    "praise": {"type": "trigger", "name": "praise_detected"},
    "criticism": {"type": "trigger", "name": "criticism_detected"},
    "celebrate_mood": {"type": "scene", "name": "celebrate"},
    "sleep_mood": {"type": "scene", "name": "sleep"},
    "daydream_mood": {"type": "scene", "name": "daydream"},
    "startle_mood": {"type": "scene", "name": "startle_sound"},
}


def _clean_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _compact_text(text: str) -> str:
    cleaned = _clean_text(text)
    for mark in ("，", "。", "！", "？", ",", ".", "!", "?", "：", ":", "、", " "):
        cleaned = cleaned.replace(mark, "")
    return cleaned


def scene_for_command(transcript: str) -> str | None:
    compact = _compact_text(transcript)
    if not compact:
        return None
    has_command_prefix = any(prefix in compact for prefix in COMMAND_PREFIXES)

    for scene_name, aliases in SCENE_COMMAND_ALIASES.items():
        if compact == scene_name.replace("_", ""):
            return scene_name
        for alias in aliases:
            alias_compact = _compact_text(alias)
            if not alias_compact:
                continue
            if compact == alias_compact:
                if alias_compact in EMOTION_FIRST_ALIASES and not has_command_prefix:
                    return None
                return scene_name
            if alias_compact in compact and (
                has_command_prefix
                or compact.startswith(alias_compact)
                or compact.endswith(alias_compact)
            ):
                if alias_compact in EMOTION_FIRST_ALIASES and not has_command_prefix:
                    return None
                return scene_name
    return None


def is_sigh_text(transcript: str) -> bool:
    cleaned = _clean_text(transcript)
    if not cleaned:
        return False
    if cleaned in SIGH_KEYWORDS:
        return True
    return cleaned.rstrip("!！?？。,.，") in {"唉", "哎", "唉呀", "哎呀"}


def classify_intent(transcript: str) -> str:
    cleaned = _clean_text(transcript)
    if not cleaned:
        return "chat"
    scene_name = scene_for_command(cleaned)
    if scene_name:
        return f"scene:{scene_name}"
    if is_sigh_text(cleaned):
        return "sigh"
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in cleaned for keyword in keywords):
            return intent
    return "chat"


def is_brief_greeting(transcript: str) -> bool:
    cleaned = _clean_text(transcript).rstrip("!！?？。,.，~～")
    if not cleaned:
        return False
    return cleaned in GREETING_PHRASES


def should_skip_short_reply(transcript: str, *, intent: str) -> bool:
    cleaned = _clean_text(transcript).rstrip("!！?？。,.，~～")
    if not cleaned:
        return True
    visible = "".join(ch for ch in cleaned if not ch.isspace())
    if len(visible) <= 1:
        return True
    if intent != "chat":
        return False
    if cleaned in GREETING_PHRASES:
        return False
    if cleaned in LOW_INFORMATION_UTTERANCES:
        return True
    return False


def action_for_intent(intent: str) -> dict[str, str] | None:
    if intent.startswith("scene:"):
        scene_name = intent.split(":", 1)[1].strip()
        if scene_name:
            return {"type": "scene", "name": scene_name}
    return INTENT_ACTIONS.get(intent)


def comfort_like_intent(intent: str) -> bool:
    return intent in {"sigh", "comfort"}


def bridge_payload_for_intent(intent: str, transcript: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": "voice-realtime",
        "transcript": transcript,
        "cueMode": "scene",
    }
    if intent == "farewell":
        payload["direction"] = "center"
    return payload
