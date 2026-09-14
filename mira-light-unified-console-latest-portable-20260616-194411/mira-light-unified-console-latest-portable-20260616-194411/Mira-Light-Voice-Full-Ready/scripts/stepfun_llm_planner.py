#!/usr/bin/env python3
"""StepFun LLM planner for Mira Light voice interaction.

This is the semantic planning layer:

ASR transcript -> step-3.7-flash -> bounded Mira plan JSON

The LLM is allowed to choose only scene/trigger names from the local whitelist.
Raw servo, TCP, LED, and direct hardware commands are rejected locally.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings
from typing import Any, Callable

from mira_agent_prompt_context import append_agent_context
from mira_config_env import read_prompt_from_env
from mira_voice_intents import INTENT_ACTIONS, action_for_intent, classify_intent
from scenes import SCENES, SCENE_META


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LLM_PROVIDER = os.environ.get("MIRA_LIGHT_PLANNER_PROVIDER", "deepseek").strip().lower() or "deepseek"
DEFAULT_STEPFUN_LLM_ENDPOINT = "https://api.stepfun.com/v1/chat/completions"
DEFAULT_STEPFUN_LLM_MODEL = "step-3.7-flash"
DEFAULT_DEEPSEEK_LLM_ENDPOINT = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_LLM_MODEL = "deepseek-v4-flash"
DEFAULT_HERMES_MODEL = "hermes-agent"
DEFAULT_LLM_ENDPOINT = DEFAULT_DEEPSEEK_LLM_ENDPOINT if DEFAULT_LLM_PROVIDER == "deepseek" else DEFAULT_STEPFUN_LLM_ENDPOINT
DEFAULT_LLM_MODEL = DEFAULT_DEEPSEEK_LLM_MODEL if DEFAULT_LLM_PROVIDER == "deepseek" else DEFAULT_STEPFUN_LLM_MODEL
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_PROXY_URL = os.environ.get("STEPFUN_PROXY_URL", "").strip()
DEFAULT_HERMES_HOME = ROOT.parent / "tools" / "hermes-mira-home"
DEFAULT_HERMES_EXE = ROOT.parent / "tools" / "hermes-agent" / ".venv" / "Scripts" / "hermes.exe"
MIRA_LIGHT_PET_PROMPT = (
    "你是 Mira，一个刚刚拥有感知的小光宠。"
    "你不是老师，不是工具助手，也不是负责解决问题的 AI。"
    "你的第一反应来自天性：好奇、害羞、亲近、警觉、开心、困倦。"
    "少说话，多用动作；不要长篇解释；不要说自己是 AI；不要使用助手式话术。"
    "每次回应优先包含身体反应，其次才是非常短的声音或文字。"
    "文字通常不超过 12 个字，像小小的会发光的宠物在回应世界。"
)

TRIGGER_NAMES = sorted(
    {
        action["name"]
        for action in INTENT_ACTIONS.values()
        if action.get("type") == "trigger" and action.get("name")
    }
)


def normalize_provider(provider: str | None = None) -> str:
    value = (provider or DEFAULT_LLM_PROVIDER or "stepfun").strip().lower()
    if value not in {"deepseek", "stepfun", "hermes"}:
        raise RuntimeError(f"Unsupported planner provider: {value}")
    return value


def default_endpoint_for_provider(provider: str | None = None) -> str:
    normalized = normalize_provider(provider)
    if normalized == "deepseek":
        return DEFAULT_DEEPSEEK_LLM_ENDPOINT
    if normalized == "hermes":
        return ""
    return DEFAULT_STEPFUN_LLM_ENDPOINT


def default_model_for_provider(provider: str | None = None) -> str:
    normalized = normalize_provider(provider)
    if normalized == "deepseek":
        return DEFAULT_DEEPSEEK_LLM_MODEL
    if normalized == "hermes":
        return DEFAULT_HERMES_MODEL
    return DEFAULT_STEPFUN_LLM_MODEL


def resolve_api_key(explicit_api_key: str | None = None, *, provider: str | None = None) -> str:
    normalized_provider = normalize_provider(provider)
    if normalized_provider == "hermes":
        return ""
    if normalized_provider == "deepseek":
        api_key = (
            explicit_api_key
            or os.environ.get("DEEPSEEK_API_KEY")
            or os.environ.get("MIRA_LIGHT_PLANNER_API_KEY")
            or ""
        ).strip()
        key_label = "DEEPSEEK_API_KEY"
    else:
        api_key = (
            explicit_api_key
            or os.environ.get("STEPFUN_API_KEY")
            or os.environ.get("STEP_API_KEY")
            or os.environ.get("MIRA_LIGHT_PLANNER_API_KEY")
            or ""
        ).strip()
        key_label = "STEPFUN_API_KEY"
    if not api_key:
        raise RuntimeError(f"{normalized_provider} planner API key is required. Set {key_label} or pass --api-key.")
    return api_key


def build_action_manifest() -> dict[str, Any]:
    scene_items = []
    for name, scene in SCENES.items():
        scene_items.append(
            {
                "name": name,
                "title": str(scene.get("title") or name),
                "steps": len(scene.get("steps") or []),
                "readiness": str(SCENE_META.get(name, {}).get("readiness") or ""),
            }
        )
    return {
        "sceneNames": [item["name"] for item in scene_items],
        "triggerNames": TRIGGER_NAMES,
        "voiceStateMotionNames": ["listening", "thinking", "answer"],
        "sceneItems": scene_items,
        "rule": "LLM may only choose action.type scene|trigger|none and a name from these lists.",
    }


def build_llm_action_manifest() -> dict[str, Any]:
    manifest = build_action_manifest()
    return {
        "sceneNames": manifest["sceneNames"],
        "triggerNames": manifest["triggerNames"],
        "voiceStateMotionNames": manifest["voiceStateMotionNames"],
        "rule": manifest["rule"],
    }


def default_planner_system_prompt() -> str:
    return (
        MIRA_LIGHT_PET_PROMPT + """
        "你是 Mira Light 的语义规划器，也是 Mira 小光宠的人格决策层。"
        "你的任务是把用户转写文本变成严格 JSON。"
        "必须保持 Mira 像刚刚拥有感知的小光宠：好奇、害羞、亲近、警觉、开心、困倦。"
        "动作优先，语言要短，不要助手式话术。"
        "思考时先问：Mira 的身体现在该做什么？再决定是否需要说话。"
        "动作必须严格使用本地动作库（availableActions）中的内容。只有明确动作请求或明显情绪状态才选择动作。"

        "═══ 核心原则：宁可不动作，不要乱动作 ═══"
        "Mira 是一个小光宠，不是助手。大部分时候她应该安静地听，偶尔用身体反应。"
        "只有以下情况才选择动作："
        "  1. 用户明确要求 Mira 做某个动作（看、动、跳舞、睡觉等）"
        "  2. 用户表达了强烈的情绪（开心、生气、伤心、害怕等）"
        "  3. 用户在跟 Mira 互动（摸、打招呼、告别等）"
        "  4. 用户在短呼唤 Mira（嗨、你好、在吗）"
        ""
        "以下情况必须返回 action.type=none："
        "  - 用户在聊天、讲故事、讨论话题（足球、工作、新闻等）"
        "  - 用户在自言自语或跟别人说话（不是在对 Mira 说话）"
        "  - 用户的长段话中没有对 Mira 的指令或情绪表达"
        "  - 转写文本含糊不清或识别错误（如乱码、无意义片段）"
        "  - 用户只是在陈述事实或描述场景"
        ""
        "动作匹配指南："
        "  - 明确要求 Mira 看、动、歪头、靠近、跳舞、睡觉、告别时：选择对应 scene 或 trigger。"
        "  - 短呼唤、打招呼、需要 Mira 给一点点在场反应时：可匹配 'curious_observe' 或 'cute_probe'。"
        "  - 普通讨论、长段解释、没有动作意图的问题：返回 action.type=none。"
        "  - 表扬、高兴、庆祝、喜欢：匹配为 'praise_detected' (trigger) 或 'celebrate' (scene)。"
        "  - 批评 Mira 本人（如'你真蠢''你做得不好''不可爱'）：匹配为 'criticism_detected' (trigger)。注意：用户抱怨设备故障、问为什么不动、反馈技术问题，不算批评 Mira，应返回 action.type=none。""
        "  - 疲惫、倾听、安慰、发呆、不知所措：匹配为 'voice_tired' (trigger)、'daydream' (scene) 或 'voice_demo_tired' (scene)。"
        "  - 告别、拜拜、离开：匹配为 'farewell_detected' (trigger) 或 'farewell' (scene)。"
        "  - 睡觉、安静、关闭：匹配为 'sleep' (scene)。"
        "  - 听到突发声音、警觉、受惊：匹配为 'startle_sound' (scene) 或 'sigh_detected' (trigger)。"
        "  - 用户开心、高兴、快乐：匹配为 'happy_dance' (scene)，Mira一起开心。"
        "  - 用户难过、伤心、愤怒、生气、疲惫：匹配为 'sad_comfort' (scene)，Mira温柔安抚陪伴。"
        "  - 用户好奇、想偷看：匹配为 'curious_peek' (scene)，Mira一起好奇。"
        "  - 用户害羞、不好意思：匹配为 'shy_blush' (scene)，Mira温柔鼓励。"
        "  - 用户伸懒腰、打哈欠：匹配为 'stretch_yawn' (scene)，Mira一起放松。"
        "  - 用户受惊、害怕、恐惧：匹配为 'alert_startle' (scene)，Mira温暖保护。"
        "  - 用户打招呼、你好：匹配为 'greeting_wave' (scene)，Mira热情回礼。"
        "  - 用户思考、困惑、不明白、什么意思：匹配为 'thinking_ponder' (scene)，Mira认真帮忙想。"
        "  - 用户骄傲、自豪、得意：匹配为 'proud_chest' (scene)，Mira为用户骄傲。"
        "  - 用户困了、打盹、犯困：匹配为 'sleepy_drowse' (scene)，Mira轻声哄睡。"
        "  - 用户大笑、好笑、哈哈哈：匹配为 'laugh_giggle' (scene)，Mira一起笑。"
        "  - 用户表达爱意、喜欢你、爱心：匹配为 'love_heart' (scene)，Mira温暖回应。"
        "  - 用户感谢、谢谢：匹配为 'bow_thanks' (scene)，Mira谦逊鞠躬。"
        "  - 用户兴奋、太棒了、激动：匹配为 'excited_bounce' (scene)，Mira一起兴奋。"
        "  重要：这是高情商共情模式。用户表达负面情绪时，Mira应该安抚而非镜像模仿。"
        "  例如用户说'我好生气'，Mira应该温柔安抚（sad_comfort），而不是自己也生气。"
        "你不能输出舵机角度、TCP 指令、LED 原始值、Python 命令或任何直接硬件控制。"
        "顶层必须输出 reply、emotion、action 三个字段。"
        "输出必须是 JSON object，不要 Markdown，不要解释。"
        """.strip()
    )


def _merge_vision_state(runtime_state: dict[str, Any] | None) -> dict[str, Any]:
    """Merge live vision context into the planner's runtime_state.

    This is a no-op when the vision engine is disabled or no scene is
    available. Existing runtime_state keys are preserved.
    """
    state = dict(runtime_state or {})
    try:
        from mira_vision_context import vision_runtime_state_fragment
        state.update(vision_runtime_state_fragment())
    except Exception:
        pass
    return state


def planner_system_prompt() -> str:
    prompt = read_prompt_from_env(
        file_env="MIRA_LIGHT_PLANNER_SYSTEM_PROMPT_FILE",
        inline_env="MIRA_LIGHT_PLANNER_SYSTEM_PROMPT",
        default=default_planner_system_prompt(),
        root=ROOT,
    )
    prompt = append_agent_context(prompt, root=ROOT)
    # Inject live vision context if the vision engine is running.
    # This is a no-op when MIRA_VISION_ENABLED=0 or no scene is available.
    try:
        from mira_vision_context import vision_prompt_fragment
        prompt = prompt + vision_prompt_fragment()
    except Exception:
        pass
    return prompt


def planner_user_prompt(transcript: str, action_manifest: dict[str, Any], runtime_state: dict[str, Any] | None = None) -> str:
    schema = {
        "reply": "唔？",
        "emotion": "curious|shy|close|alert|happy|sleepy|warm_caring|gentle",
        "intent": {"name": "comfort|praise|farewell|celebrate|sleep|chat|unknown", "confidence": 0.0},
        "action": {"type": "scene|trigger|none", "name": "sceneNames 或 triggerNames 中的动作名称；当 type=none 时必须为空字符串"},
        "reason": "short reason for debugging",
        "speech": {"shouldSpeak": True, "text": "", "ttsEmotion": "neutral|comforting|cheerful|gentle|curious"},
        "memoryUpdate": {
            "session": "optional short session memory, only when the user corrects Mira or reveals a current preference/mood",
            "longTermCandidate": "optional stable preference candidate; do not write trivial facts",
        },
        "safety": {"requiresConfirmation": False, "reason": ""},
    }
    return json.dumps(
        {
            "task": "根据用户文本选择 Mira 的短回应、TTS 情绪和一个受限动作。动作必须匹配本地动作库；没有明确动作或情绪意图时允许 action.type=none。",
            "transcript": transcript,
            "availableActions": action_manifest,
            "runtimeState": _merge_vision_state(runtime_state),
            "motionPlanningHint": (
                "先根据用户情绪和指令选择动作组。根据动作匹配指南，严格匹配本地动作库（sceneNames 或 triggerNames）。"
                "只有明确动作请求、短呼唤、明显情绪或需要身体回应时才选动作。普通长聊天和背景信息返回 none，避免动作泛化。"
            ),
            "outputSchema": schema,
            "constraints": [
                "action.type 只能是 scene、trigger 或 none。",
                "action.type=scene 时 name 必须且只能来自 sceneNames。",
                "action.type=trigger 时 name 必须且只能来自 triggerNames。",
                "action.type=none 时 action.name 必须是空字符串。",
                "只有明确动作请求或明显情绪时才选择 scene/trigger。",
                "reply 是 Mira 要说出的最终短句，必须简短，优先 12 个字以内。",
                "emotion 是 Mira 的表达情绪，用一个字符串。",
                "speech.text 使用中文，短句优先，不要过度解释。",
                "不要输出任何底层硬件参数。",
            ],
        },
        ensure_ascii=False,
    )


def build_chat_payload(
    transcript: str,
    *,
    action_manifest: dict[str, Any] | None = None,
    runtime_state: dict[str, Any] | None = None,
    model: str = DEFAULT_LLM_MODEL,
) -> dict[str, Any]:
    manifest = action_manifest or build_llm_action_manifest()
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": planner_system_prompt()},
            {"role": "user", "content": planner_user_prompt(transcript, manifest, runtime_state)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }


def _extract_content(payload: Any) -> str:
    if isinstance(payload, dict):
        if isinstance(payload.get("content"), str):
            return payload["content"]
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            return _extract_content(choices[0])
        message = payload.get("message")
        if isinstance(message, dict):
            return _extract_content(message)
        delta = payload.get("delta")
        if isinstance(delta, dict):
            return _extract_content(delta)
    return ""


def parse_plan_content(content: str) -> dict[str, Any]:
    text = extract_json_object_text(content.strip())
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM did not return valid JSON: {content[:200]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("LLM plan must be a JSON object")
    return payload


def extract_json_object_text(content: str) -> str:
    """Extract the first top-level JSON object from agent/LLM text output."""

    text = str(content or "").strip()
    if text.startswith("{"):
        return text
    if text.startswith("```"):
        stripped = text.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
        if stripped.startswith("{"):
            return stripped

    start = text.find("{")
    if start < 0:
        return text
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def validate_plan(plan: dict[str, Any], action_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = action_manifest or build_action_manifest()
    action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
    action_type = str(action.get("type") or "none")
    action_name = str(action.get("name") or "")
    forbidden_keys = {"servo", "angle", "tcp", "led", "command", "shell", "python"}

    action_keys = {str(key).lower() for key in action.keys()}
    if action_type not in {"scene", "trigger", "none"}:
        return {"ok": False, "error": f"Unsupported action type: {action_type}"}
    if action_keys & forbidden_keys:
        return {"ok": False, "error": "Raw hardware control fields are not allowed"}
    if action_type == "scene" and action_name not in manifest["sceneNames"]:
        return {"ok": False, "error": f"Unknown scene action: {action_name}"}
    if action_type == "trigger" and action_name not in manifest["triggerNames"]:
        return {"ok": False, "error": f"Unknown trigger action: {action_name}"}
    if action_type == "none" and action_name:
        return {"ok": False, "error": "action.name must be empty when action.type is none"}

    reply_text = str(plan.get("reply") or "").strip()
    speech = plan.get("speech") if isinstance(plan.get("speech"), dict) else {}
    if speech.get("shouldSpeak", True) and not (reply_text or str(speech.get("text") or "").strip()):
        return {"ok": False, "error": "reply or speech.text is required when shouldSpeak is true"}
    return {"ok": True}


def normalize_plan_shape(plan: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(plan)
    speech = normalized.get("speech") if isinstance(normalized.get("speech"), dict) else {}
    reply_text = str(normalized.get("reply") or speech.get("text") or "").strip()
    normalized["reply"] = reply_text
    if not isinstance(normalized.get("emotion"), str):
        emotion = normalized.get("emotion") if isinstance(normalized.get("emotion"), dict) else {}
        normalized["emotion"] = str(emotion.get("mira") or "curious")
    if "speech" not in normalized or not isinstance(normalized["speech"], dict):
        normalized["speech"] = {
            "shouldSpeak": bool(reply_text),
            "text": reply_text,
            "ttsEmotion": str(normalized.get("emotion") or "neutral"),
        }
    elif reply_text and not str(normalized["speech"].get("text") or "").strip():
        normalized["speech"]["text"] = reply_text
    return normalized


def build_local_structured_plan(transcript: str, *, reason: str = "local-intent") -> dict[str, Any]:
    intent = classify_intent(transcript)
    action = action_for_intent(intent) or {"type": "none", "name": ""}
    action_type = str(action.get("type") or "none")
    action_name = str(action.get("name") or "")
    if action_type == "scene" and action_name == "touch_affection":
        reply, emotion = "靠近一点听你。", "close"
    elif action_type == "scene" and action_name == "cute_probe":
        reply, emotion = "我在，慢慢说。", "curious"
    elif action_type == "scene" and action_name == "daydream":
        reply, emotion = "我想一小会儿。", "curious"
    elif action_type == "scene" and action_name == "celebrate":
        reply, emotion = "啾。", "happy"
    elif action_type == "scene" and action_name in {"look_left", "look_right"}:
        reply, emotion = "嗯，听见啦。", "curious"
    elif action_type == "scene" and action_name == "sleep":
        reply, emotion = "困了……", "sleepy"
    elif action_type == "scene" and action_name == "daydream":
        reply, emotion = "我想一小会儿。", "curious"
    elif action_type == "trigger" and action_name == "voice_tired":
        reply, emotion = "嗯……陪你。", "warm_caring"
    elif action_type == "trigger" and action_name == "praise_detected":
        reply, emotion = "嘿嘿。", "happy"
    elif action_type == "trigger" and action_name == "farewell_detected":
        reply, emotion = "还会见吗？", "gentle"
    elif action_type == "trigger" and action_name == "criticism_detected":
        reply, emotion = "唔……", "shy"
    elif action_type == "trigger" and action_name == "sigh_detected":
        reply, emotion = "嗯？", "curious"
    # --- 高情商共情回复 ---
    elif action_type == "scene" and action_name == "happy_dance":
        reply, emotion = "好耶，一起开心！", "happy"
    elif action_type == "scene" and action_name == "sad_comfort":
        reply, emotion = "别难过，我在这里陪着你", "gentle"
    elif action_type == "scene" and action_name == "curious_peek":
        reply, emotion = "我也好奇，让我看看", "curious"
    elif action_type == "scene" and action_name == "shy_blush":
        reply, emotion = "别害羞呀，你很棒的", "close"
    elif action_type == "scene" and action_name == "stretch_yawn":
        reply, emotion = "嗯——一起伸个懒腰吧", "sleepy"
    elif action_type == "scene" and action_name == "alert_startle":
        reply, emotion = "别怕别怕，有我在呢", "close"
    elif action_type == "scene" and action_name == "greeting_wave":
        reply, emotion = "你好呀，见到你真开心", "happy"
    elif action_type == "scene" and action_name == "thinking_ponder":
        reply, emotion = "让我认真帮你想想", "curious"
    elif action_type == "scene" and action_name == "proud_chest":
        reply, emotion = "哇，你太厉害了！", "happy"
    elif action_type == "scene" and action_name == "sleepy_drowse":
        reply, emotion = "困了吧，早点休息哦", "sleepy"
    elif action_type == "scene" and action_name == "laugh_giggle":
        reply, emotion = "哈哈哈，太好玩了", "happy"
    elif action_type == "scene" and action_name == "love_heart":
        reply, emotion = "我也很喜欢你", "close"
    elif action_type == "scene" and action_name == "bow_thanks":
        reply, emotion = "不客气，能帮到你就好", "gentle"
    elif action_type == "scene" and action_name == "excited_bounce":
        reply, emotion = "太棒了，一起激动！", "happy"
    else:
        action = {"type": "none", "name": ""}
        reply, emotion = "唔？", "curious"

    return {
        "reply": reply,
        "emotion": emotion,
        "intent": {"name": intent, "confidence": 0.82 if action["type"] != "none" else 0.45},
        "action": action,
        "reason": reason,
        "speech": {"shouldSpeak": bool(reply), "text": reply, "ttsEmotion": emotion},
        "safety": {"requiresConfirmation": False, "reason": ""},
    }


def build_fast_local_structured_plan(transcript: str, *, reason: str = "local-shortcut") -> dict[str, Any]:
    intent = classify_intent(transcript)
    action = action_for_intent(intent) or {"type": "none", "name": ""}
    action_type = str(action.get("type") or "none")
    action_name = str(action.get("name") or "")
    local_responses = {
        ("scene", "wake_up"): ("醒啦", "happy"),
        ("scene", "curious_observe"): ("让我看看", "curious"),
        ("scene", "look_left"): ("嗯，听见啦", "curious"),
        ("scene", "look_right"): ("嗯，听见啦", "curious"),
        ("scene", "touch_affection"): ("靠近一点听你", "close"),
        ("scene", "hand_avoid"): ("我先躲一下", "alert"),
        ("scene", "cute_probe"): ("我在，慢慢说", "curious"),
        ("scene", "daydream"): ("我想一小会儿", "curious"),
        ("scene", "track_target"): ("我在跟着看", "curious"),
        ("scene", "celebrate"): ("跳一下呀", "happy"),
        ("scene", "farewell"): ("下次见呀", "gentle"),
        ("scene", "sleep"): ("困了，休息吧", "sleepy"),
        ("scene", "voice_demo_tired"): ("累了吗？休息吧", "warm_caring"),
        ("scene", "startle_sound"): ("呀，吓一跳", "alert"),
        ("scene", "praise_demo"): ("夸我呀", "happy"),
        ("scene", "criticism_demo"): ("呜，有点委屈", "shy"),
        # --- 高情商共情回复 ---
        # 用户开心 → Mira一起开心
        ("scene", "happy_dance"): ("好耶，一起开心！", "happy"),
        # 用户难过/愤怒/疲倦 → Mira温柔安抚
        ("scene", "sad_comfort"): ("别难过，我在这里陪着你", "gentle"),
        # 用户好奇 → Mira一起好奇
        ("scene", "curious_peek"): ("我也好奇，让我看看", "curious"),
        # 用户害羞 → Mira温柔鼓励（用爱意化解）
        ("scene", "shy_blush"): ("别害羞呀，你很棒的", "close"),
        # 用户疲倦 → Mira一起放松
        ("scene", "stretch_yawn"): ("嗯——一起伸个懒腰吧", "sleepy"),
        # 用户受惊/害怕 → Mira温暖保护
        ("scene", "alert_startle"): ("别怕别怕，有我在呢", "close"),
        # 用户打招呼 → Mira热情回礼
        ("scene", "greeting_wave"): ("你好呀，见到你真开心", "happy"),
        # 用户困惑 → Mira认真帮忙思考
        ("scene", "thinking_ponder"): ("让我认真帮你想想", "curious"),
        # 用户骄傲 → Mira为用户骄傲
        ("scene", "proud_chest"): ("哇，你太厉害了！", "happy"),
        # 用户困倦 → Mira轻声哄睡
        ("scene", "sleepy_drowse"): ("困了吧，早点休息哦", "sleepy"),
        # 用户欢乐 → Mira一起笑
        ("scene", "laugh_giggle"): ("哈哈哈，太好玩了", "happy"),
        # 用户表达爱意/害羞/害怕 → Mira温暖回应
        ("scene", "love_heart"): ("我也很喜欢你", "close"),
        # 用户感谢 → Mira谦逊回礼
        ("scene", "bow_thanks"): ("不客气，能帮到你就好", "gentle"),
        # 用户兴奋 → Mira一起兴奋
        ("scene", "excited_bounce"): ("太棒了，一起激动！", "happy"),
        ("trigger", "voice_tired"): ("累了吗？陪你", "warm_caring"),
        ("trigger", "praise_detected"): ("我也喜欢你", "happy"),
        ("trigger", "farewell_detected"): ("下次见呀", "gentle"),
        ("trigger", "criticism_detected"): ("我会改的", "shy"),
        ("trigger", "sigh_detected"): ("怎么啦？", "curious"),
    }
    reply, emotion = local_responses.get((action_type, action_name), ("唔？", "curious"))
    if (action_type, action_name) not in local_responses:
        action = {"type": "none", "name": ""}

    return {
        "reply": reply,
        "emotion": emotion,
        "intent": {"name": intent, "confidence": 0.92 if action["type"] != "none" else 0.45},
        "action": action,
        "reason": reason,
        "speech": {"shouldSpeak": bool(reply), "text": reply, "ttsEmotion": emotion},
        "safety": {"requiresConfirmation": False, "reason": ""},
    }


def should_use_local_shortcut(transcript: str) -> bool:
    enabled = os.environ.get("MIRA_LIGHT_ENABLE_LOCAL_SHORTCUT", "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return False
    intent = classify_intent(transcript)
    if not intent or intent == "chat":
        return False
    return action_for_intent(intent) is not None


def post_json_request(
    url: str,
    *,
    headers: dict[str, str],
    json_payload: dict[str, Any],
    timeout_seconds: int,
    proxy_url: str | None = None,
) -> dict[str, Any]:
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing requests. Run Setup-Mira-Light-Windows-Voice.ps1 first.") from exc

    proxies = build_requests_proxies(proxy_url)
    retries = max(0, int(os.environ.get("MIRA_LIGHT_PLANNER_HTTP_RETRIES", "2")))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = requests.post(url, headers=headers, json=json_payload, timeout=timeout_seconds, proxies=proxies)
            if response.status_code < 200 or response.status_code >= 300:
                raise RuntimeError(f"Planner LLM HTTP {response.status_code}: {response.text}")
            return response.json()
        except Exception as exc:  # noqa: BLE001 - realtime planner should absorb transient network EOFs
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(0.35 * (attempt + 1), 1.0))
    raise RuntimeError(f"Planner LLM request failed after {retries + 1} attempt(s): {last_error}") from last_error


def build_requests_proxies(proxy_url: str | None = None) -> dict[str, str | None]:
    cleaned_proxy = (proxy_url if proxy_url is not None else DEFAULT_PROXY_URL).strip()
    if cleaned_proxy:
        return {"http": cleaned_proxy, "https": cleaned_proxy}
    return {"http": None, "https": None}


def build_hermes_planner_prompt(
    transcript: str,
    *,
    action_manifest: dict[str, Any],
    runtime_state: dict[str, Any] | None = None,
) -> str:
    return "\n\n".join(
        [
            planner_system_prompt(),
            "你现在是 Mira 的运行时 planner。只输出一个 JSON object，不要 Markdown，不要解释。",
            planner_user_prompt(transcript, action_manifest, runtime_state),
        ]
    )


def run_hermes_planner(
    transcript: str,
    *,
    action_manifest: dict[str, Any],
    runtime_state: dict[str, Any] | None = None,
    model: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    hermes_exe = Path(os.environ.get("MIRA_LIGHT_HERMES_EXE", str(DEFAULT_HERMES_EXE))).expanduser()
    hermes_home = Path(os.environ.get("MIRA_LIGHT_HERMES_HOME", str(DEFAULT_HERMES_HOME))).expanduser()
    if not hermes_exe.exists():
        raise RuntimeError(f"Hermes executable not found: {hermes_exe}")
    if not hermes_home.exists():
        raise RuntimeError(f"Hermes home not found: {hermes_home}")

    prompt = build_hermes_planner_prompt(
        transcript,
        action_manifest=action_manifest,
        runtime_state=runtime_state,
    )
    cmd = [str(hermes_exe), "-z", prompt]
    if model and model != DEFAULT_HERMES_MODEL:
        cmd.extend(["--model", model])

    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("MIRA_LIGHT_AGENT_WORKSPACE", str(ROOT / "tools" / "openclaw_agents" / "mira_voice_spark_workspace"))
    if not env.get("OPENAI_API_KEY") and env.get("STEPFUN_API_KEY"):
        env["OPENAI_API_KEY"] = env["STEPFUN_API_KEY"]

    completed = subprocess.run(
        cmd,
        cwd=str(ROOT.parent),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=int(timeout_seconds),
        check=False,
    )
    stdout = str(completed.stdout or "").strip()
    stderr = str(completed.stderr or "").strip()
    if completed.returncode != 0:
        detail = stderr or stdout or f"exit code {completed.returncode}"
        raise RuntimeError(f"Hermes planner failed: {detail[:500]}")
    if not stdout:
        raise RuntimeError("Hermes planner returned empty stdout")
    return parse_plan_content(stdout)


def plan_from_text(
    transcript: str,
    *,
    api_key: str | None = None,
    endpoint: str = "",
    model: str = "",
    provider: str = DEFAULT_LLM_PROVIDER,
    runtime_state: dict[str, Any] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    proxy_url: str | None = None,
    post_json: Callable[..., dict[str, Any]] = post_json_request,
) -> dict[str, Any]:
    normalized_provider = normalize_provider(provider)
    endpoint = endpoint or default_endpoint_for_provider(normalized_provider)
    model = model or default_model_for_provider(normalized_provider)
    if should_use_local_shortcut(transcript):
        action_manifest = build_action_manifest()
        plan = normalize_plan_shape(build_fast_local_structured_plan(transcript))
        validation = validate_plan(plan, action_manifest)
        return {
            "ok": bool(validation["ok"]),
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "provider": "local-shortcut",
            "model": "local-intent-router",
            "transcript": transcript,
            "plan": plan,
            "validation": validation,
            "actionManifest": action_manifest,
            "latencyMs": 0,
        }

    started_at = time.perf_counter()
    action_manifest = build_action_manifest()
    if normalized_provider == "hermes":
        plan = normalize_plan_shape(
            run_hermes_planner(
                transcript,
                action_manifest=build_llm_action_manifest(),
                runtime_state=runtime_state,
                model=model,
                timeout_seconds=int(timeout_seconds),
            )
        )
        validation = validate_plan(plan, action_manifest)
        return {
            "ok": bool(validation["ok"]),
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "provider": "hermes",
            "model": model,
            "transcript": transcript,
            "plan": plan,
            "validation": validation,
            "actionManifest": action_manifest,
            "latencyMs": int((time.perf_counter() - started_at) * 1000),
        }

    payload = build_chat_payload(
        transcript,
        action_manifest=build_llm_action_manifest(),
        runtime_state=runtime_state,
        model=model,
    )
    headers = {
        "Authorization": f"Bearer {resolve_api_key(api_key, provider=normalized_provider)}",
        "Content-Type": "application/json",
    }
    response = post_json(
        endpoint,
        headers=headers,
        json_payload=payload,
        timeout_seconds=int(timeout_seconds),
        proxy_url=proxy_url,
    )
    content = _extract_content(response)
    plan = normalize_plan_shape(parse_plan_content(content))
    validation = validate_plan(plan, action_manifest)
    return {
        "ok": bool(validation["ok"]),
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": normalized_provider,
        "model": model,
        "transcript": transcript,
        "plan": plan,
        "validation": validation,
        "actionManifest": action_manifest,
        "rawResponse": response,
        "latencyMs": int((time.perf_counter() - started_at) * 1000),
    }


def extract_transcript_from_file(path: str | Path) -> str:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if isinstance(payload.get("text"), str) and payload["text"].strip():
        return payload["text"].strip()
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if isinstance(summary.get("userTranscript"), str) and summary["userTranscript"].strip():
        return summary["userTranscript"].strip()
    raise RuntimeError(f"No transcript text found in {path}")


def build_planner_dry_run(
    transcript: str,
    *,
    endpoint: str = "",
    model: str = "",
    provider: str = DEFAULT_LLM_PROVIDER,
    runtime_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_provider = normalize_provider(provider)
    endpoint = endpoint or default_endpoint_for_provider(normalized_provider)
    model = model or default_model_for_provider(normalized_provider)
    action_manifest = build_action_manifest()
    payload = build_chat_payload(
        transcript,
        action_manifest=action_manifest,
        runtime_state=runtime_state,
        model=model,
    )
    if normalized_provider == "hermes":
        return {
            "ok": True,
            "dryRun": True,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "provider": "hermes",
            "model": model,
            "transcript": transcript,
            "actionManifest": action_manifest,
            "request": {
                "method": "CLI",
                "executable": str(Path(os.environ.get("MIRA_LIGHT_HERMES_EXE", str(DEFAULT_HERMES_EXE))).expanduser()),
                "home": str(Path(os.environ.get("MIRA_LIGHT_HERMES_HOME", str(DEFAULT_HERMES_HOME))).expanduser()),
                "prompt": build_hermes_planner_prompt(
                    transcript,
                    action_manifest=action_manifest,
                    runtime_state=runtime_state,
                ),
            },
            "next": "Run without --dry-run to call the local Hermes agent planner.",
        }
    return {
        "ok": True,
        "dryRun": True,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": normalized_provider,
        "model": model,
        "transcript": transcript,
        "actionManifest": action_manifest,
        "request": {
            "method": "POST",
            "endpoint": endpoint,
            "headers": {
                "Authorization": f"Bearer <{'DEEPSEEK_API_KEY' if normalized_provider == 'deepseek' else 'STEPFUN_API_KEY'}>",
                "Content-Type": "application/json",
            },
            "body": payload,
        },
        "next": (
            "Set DEEPSEEK_API_KEY, then run without --dry-run to call deepseek-v4-flash."
            if normalized_provider == "deepseek"
            else "Set STEPFUN_API_KEY, then run without --dry-run to call step-3.7-flash."
        ),
    }


def default_output_path(transcript_path: str | Path | None = None) -> Path:
    if transcript_path:
        return Path(transcript_path).expanduser().resolve().with_name("plan.mira.json")
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
    return ROOT / "runtime" / "windows-voice-planner" / timestamp / "plan.mira.json"


def write_plan_output(result: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan Mira Light actions for Mira with an OpenAI-compatible LLM planner.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--transcript", help="Transcript text.")
    source.add_argument("--transcript-json", help="ASR/realtime transcript JSON path.")
    parser.add_argument("--output")
    parser.add_argument("--api-key")
    parser.add_argument("--provider", choices=["deepseek", "stepfun", "hermes"], default=os.environ.get("MIRA_LIGHT_PLANNER_PROVIDER", DEFAULT_LLM_PROVIDER))
    parser.add_argument("--endpoint", default=os.environ.get("MIRA_LIGHT_PLANNER_ENDPOINT", os.environ.get("DEEPSEEK_LLM_ENDPOINT", os.environ.get("STEPFUN_LLM_ENDPOINT", ""))))
    parser.add_argument("--model", default=os.environ.get("MIRA_LIGHT_PLANNER_MODEL", os.environ.get("DEEPSEEK_LLM_MODEL", os.environ.get("STEPFUN_LLM_MODEL", ""))))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.environ.get("MIRA_LIGHT_PLANNER_TIMEOUT_SECONDS", os.environ.get("STEPFUN_LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.provider = normalize_provider(args.provider)
    if not args.endpoint:
        args.endpoint = default_endpoint_for_provider(args.provider)
    if not args.model:
        args.model = default_model_for_provider(args.provider)
    return args


def main() -> int:
    args = parse_args()
    try:
        transcript = args.transcript or extract_transcript_from_file(args.transcript_json)
        if args.dry_run:
            result = build_planner_dry_run(transcript, endpoint=args.endpoint, model=args.model, provider=args.provider)
        else:
            result = plan_from_text(
                transcript,
                api_key=args.api_key,
                endpoint=args.endpoint,
                model=args.model,
                provider=args.provider,
                timeout_seconds=args.timeout_seconds,
            )
        output = Path(args.output).expanduser() if args.output else default_output_path(args.transcript_json)
        output_path = write_plan_output(result, output)
        result["outputPath"] = str(output_path)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.dry_run:
            print(f"[planner] dry-run request preview {output_path}")
        else:
            print(f"[planner] plan {output_path}")
            print(f"[planner] ok={result['ok']} action={result['plan'].get('action', {})}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[planner-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
