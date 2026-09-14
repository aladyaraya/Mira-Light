#!/usr/bin/env python3
"""Route StepAudio realtime events into safe Mira Light actions.

This layer keeps the realtime voice model and the hardware boundary separate:

StepAudio event stream -> voice-state quick actions + bounded semantic actions

The LLM/planner may only select whitelisted scene or trigger names. This module
never accepts raw servo angles, TCP frames, LED values, shell commands, or Python
commands from a model response.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from typing import Any, Callable
import urllib.error
import urllib.request

from mira_voice_intents import action_for_intent, classify_intent, is_brief_greeting, should_skip_short_reply
from stepfun_llm_planner import build_local_structured_plan, plan_from_text, validate_plan


DEFAULT_BRIDGE_URL = "http://127.0.0.1:19783"
VOICE_PHASE_QUICK_ACTIONS = {
    "listening": "voice_motion_listening",
    "thinking": "voice_motion_thinking",
    "answer": "voice_motion_answer",
}

PostJson = Callable[..., dict[str, Any]]
Planner = Callable[..., dict[str, Any]]
GENERIC_LLM_ACTION_NAMES = {"curious_observe", "cute_probe"}

# Mary's reply text → bridge action mapping
# When StepFun's realtime model replies with action descriptions like
# "歪头，蹭蹭", we extract the keywords and map them to board actions.
#
# ═══ HIGH-EQ EMPATHIC MAPPING ═══
# 用户表达情绪 → Mira做出共情回应（不是镜像模仿）
# 例如：用户说"我好生气" → Mira做sad_comfort（温柔安抚），不是angry_pout
# 例如：用户说"我害怕" → Mira做love_heart（温暖保护），不是alert_startle
#
# IMPORTANT: Matching uses longest-keyword-first priority.
# When multiple keywords match, the longest (most specific) wins.
ASSISTANT_ACTION_KEYWORDS: dict[str, dict[str, str]] = {
    # ── 共情回应：长关键词优先 ──
    # 用户开心 → Mira一起开心
    "开心跳舞": {"type": "scene", "name": "happy_dance"},
    "跳个开心的舞": {"type": "scene", "name": "happy_dance"},
    "快乐跳舞": {"type": "scene", "name": "happy_dance"},
    "欢快跳舞": {"type": "scene", "name": "happy_dance"},
    "我好开心": {"type": "scene", "name": "happy_dance"},
    "太开心了": {"type": "scene", "name": "happy_dance"},

    # 用户愤怒/生气 → Mira温柔安抚（不跟着生气）
    "气死我了": {"type": "scene", "name": "sad_comfort"},
    "太气人了": {"type": "scene", "name": "sad_comfort"},
    "我很生气": {"type": "scene", "name": "sad_comfort"},
    "气炸了": {"type": "scene", "name": "sad_comfort"},
    "气坏了": {"type": "scene", "name": "sad_comfort"},
    "气死了": {"type": "scene", "name": "sad_comfort"},
    "好生气": {"type": "scene", "name": "sad_comfort"},
    "气呼呼": {"type": "scene", "name": "sad_comfort"},
    "发脾气": {"type": "scene", "name": "sad_comfort"},
    "发火": {"type": "scene", "name": "sad_comfort"},
    "生气": {"type": "scene", "name": "sad_comfort"},
    "愤怒": {"type": "scene", "name": "sad_comfort"},
    "好气": {"type": "scene", "name": "sad_comfort"},

    # 用户难过/伤心 → Mira陪伴安慰
    "我好难过": {"type": "scene", "name": "sad_comfort"},
    "我好伤心": {"type": "scene", "name": "sad_comfort"},
    "好难过啊": {"type": "scene", "name": "sad_comfort"},
    "心情不好": {"type": "scene", "name": "sad_comfort"},
    "情绪低落": {"type": "scene", "name": "sad_comfort"},
    "好沮丧": {"type": "scene", "name": "sad_comfort"},
    "好失落": {"type": "scene", "name": "sad_comfort"},
    "难过": {"type": "scene", "name": "sad_comfort"},
    "伤心": {"type": "scene", "name": "sad_comfort"},
    "不开心": {"type": "scene", "name": "sad_comfort"},
    "好难过": {"type": "scene", "name": "sad_comfort"},
    "好伤心": {"type": "scene", "name": "sad_comfort"},
    "悲伤": {"type": "scene", "name": "sad_comfort"},
    "安慰": {"type": "scene", "name": "sad_comfort"},

    # 用户疲倦 → Mira安抚陪伴
    "我好累": {"type": "scene", "name": "sad_comfort"},
    "好累啊": {"type": "scene", "name": "sad_comfort"},
    "累死了": {"type": "scene", "name": "sad_comfort"},
    "心力交瘁": {"type": "scene", "name": "sad_comfort"},
    "疲惫": {"type": "scene", "name": "sad_comfort"},

    # 用户害怕/受惊 → Mira温暖保护
    "吓死我了": {"type": "scene", "name": "love_heart"},
    "吓我一跳": {"type": "scene", "name": "love_heart"},
    "好可怕": {"type": "scene", "name": "love_heart"},
    "好害怕": {"type": "scene", "name": "love_heart"},
    "害怕": {"type": "scene", "name": "love_heart"},
    "好怕": {"type": "scene", "name": "love_heart"},
    "我怕": {"type": "scene", "name": "love_heart"},
    "恐惧": {"type": "scene", "name": "love_heart"},
    "受惊吓": {"type": "scene", "name": "love_heart"},
    "吓一跳": {"type": "scene", "name": "love_heart"},
    "吓到了": {"type": "scene", "name": "love_heart"},
    "吓坏了": {"type": "scene", "name": "love_heart"},

    # 用户害羞 → Mira温柔鼓励
    "不好意思": {"type": "scene", "name": "love_heart"},
    "羞死了": {"type": "scene", "name": "love_heart"},
    "好害羞": {"type": "scene", "name": "love_heart"},
    "太害羞了": {"type": "scene", "name": "love_heart"},
    "别夸了": {"type": "scene", "name": "love_heart"},
    "不要夸我": {"type": "scene", "name": "love_heart"},
    "害羞": {"type": "scene", "name": "love_heart"},
    "脸红": {"type": "scene", "name": "love_heart"},
    "羞羞": {"type": "scene", "name": "love_heart"},
    "羞涩": {"type": "scene", "name": "love_heart"},

    # 用户困惑 → Mira认真帮忙思考
    "什么意思": {"type": "scene", "name": "thinking_ponder"},
    "怎么回事": {"type": "scene", "name": "thinking_ponder"},
    "一头雾水": {"type": "scene", "name": "thinking_ponder"},
    "搞不清楚": {"type": "scene", "name": "thinking_ponder"},
    "什么玩意": {"type": "scene", "name": "thinking_ponder"},
    "什么情况": {"type": "scene", "name": "thinking_ponder"},
    "不明白": {"type": "scene", "name": "thinking_ponder"},
    "听不懂": {"type": "scene", "name": "thinking_ponder"},
    "搞不懂": {"type": "scene", "name": "thinking_ponder"},
    "不理解": {"type": "scene", "name": "thinking_ponder"},
    "没听懂": {"type": "scene", "name": "thinking_ponder"},
    "没明白": {"type": "scene", "name": "thinking_ponder"},
    "一脸懵": {"type": "scene", "name": "thinking_ponder"},
    "懵了": {"type": "scene", "name": "thinking_ponder"},
    "困惑": {"type": "scene", "name": "thinking_ponder"},
    "迷茫": {"type": "scene", "name": "thinking_ponder"},
    "不懂": {"type": "scene", "name": "thinking_ponder"},

    # 用户好奇 → Mira一起好奇
    "好奇探头": {"type": "scene", "name": "curious_peek"},
    "探头看看": {"type": "scene", "name": "curious_peek"},
    "偷看一下": {"type": "scene", "name": "curious_peek"},
    "好奇地看": {"type": "scene", "name": "curious_peek"},
    "偷偷看": {"type": "scene", "name": "curious_peek"},
    "暗中观察": {"type": "scene", "name": "curious_peek"},
    "偷瞄": {"type": "scene", "name": "curious_peek"},

    # 用户伸懒腰 → Mira一起放松
    "伸懒腰": {"type": "scene", "name": "stretch_yawn"},
    "打哈欠": {"type": "scene", "name": "stretch_yawn"},
    "伸个懒腰": {"type": "scene", "name": "stretch_yawn"},
    "打个哈欠": {"type": "scene", "name": "stretch_yawn"},
    "伸展一下": {"type": "scene", "name": "stretch_yawn"},
    "伸伸手": {"type": "scene", "name": "stretch_yawn"},

    # 用户打招呼 → Mira热情回礼
    "打招呼": {"type": "scene", "name": "greeting_wave"},
    "挥挥手": {"type": "scene", "name": "greeting_wave"},
    "打个招呼": {"type": "scene", "name": "greeting_wave"},
    "你好呀": {"type": "scene", "name": "greeting_wave"},
    "你好你好": {"type": "scene", "name": "greeting_wave"},
    "欢迎欢迎": {"type": "scene", "name": "greeting_wave"},
    "挥手致意": {"type": "scene", "name": "greeting_wave"},

    # 用户思考 → Mira一起想
    "想一想": {"type": "scene", "name": "thinking_ponder"},
    "让我想想": {"type": "scene", "name": "thinking_ponder"},
    "思考一下": {"type": "scene", "name": "thinking_ponder"},
    "让我思考": {"type": "scene", "name": "thinking_ponder"},
    "琢磨一下": {"type": "scene", "name": "thinking_ponder"},
    "考虑一下": {"type": "scene", "name": "thinking_ponder"},
    "让我考虑": {"type": "scene", "name": "thinking_ponder"},
    "沉思一下": {"type": "scene", "name": "thinking_ponder"},

    # 用户骄傲 → Mira为用户骄傲
    "我很厉害": {"type": "scene", "name": "proud_chest"},
    "我很棒": {"type": "scene", "name": "proud_chest"},
    "我超厉害": {"type": "scene", "name": "proud_chest"},
    "我做到了": {"type": "scene", "name": "proud_chest"},
    "了不起": {"type": "scene", "name": "proud_chest"},
    "骄傲": {"type": "scene", "name": "proud_chest"},
    "自豪": {"type": "scene", "name": "proud_chest"},
    "得意": {"type": "scene", "name": "proud_chest"},

    # 用户困倦 → Mira轻声哄睡
    "困死了": {"type": "scene", "name": "sleepy_drowse"},
    "困得不行": {"type": "scene", "name": "sleepy_drowse"},
    "打瞌睡": {"type": "scene", "name": "sleepy_drowse"},
    "好困啊": {"type": "scene", "name": "sleepy_drowse"},
    "眼皮打架": {"type": "scene", "name": "sleepy_drowse"},
    "困了": {"type": "scene", "name": "sleepy_drowse"},
    "犯困": {"type": "scene", "name": "sleepy_drowse"},
    "打盹": {"type": "scene", "name": "sleepy_drowse"},
    "好困": {"type": "scene", "name": "sleepy_drowse"},
    "想睡觉": {"type": "scene", "name": "sleepy_drowse"},

    # 用户欢乐 → Mira一起笑
    "笑死我了": {"type": "scene", "name": "laugh_giggle"},
    "太好笑了": {"type": "scene", "name": "laugh_giggle"},
    "哈哈哈": {"type": "scene", "name": "laugh_giggle"},
    "笑一个": {"type": "scene", "name": "laugh_giggle"},
    "笑死了": {"type": "scene", "name": "laugh_giggle"},
    "好好笑": {"type": "scene", "name": "laugh_giggle"},
    "好搞笑": {"type": "scene", "name": "laugh_giggle"},
    "逗乐": {"type": "scene", "name": "laugh_giggle"},
    "大笑": {"type": "scene", "name": "laugh_giggle"},
    "好笑": {"type": "scene", "name": "laugh_giggle"},

    # 用户表达爱意 → Mira温暖回应
    "我爱你": {"type": "scene", "name": "love_heart"},
    "喜欢你": {"type": "scene", "name": "love_heart"},
    "爱心发射": {"type": "scene", "name": "love_heart"},
    "么么哒": {"type": "scene", "name": "love_heart"},
    "比个心": {"type": "scene", "name": "love_heart"},
    "爱心": {"type": "scene", "name": "love_heart"},
    "比心": {"type": "scene", "name": "love_heart"},
    "亲亲": {"type": "scene", "name": "love_heart"},

    # 用户感谢 → Mira谦逊鞠躬
    "太感谢了": {"type": "scene", "name": "bow_thanks"},
    "非常感谢": {"type": "scene", "name": "bow_thanks"},
    "谢谢你": {"type": "scene", "name": "bow_thanks"},
    "感谢感谢": {"type": "scene", "name": "bow_thanks"},
    "鞠躬": {"type": "scene", "name": "bow_thanks"},
    "谢谢": {"type": "scene", "name": "bow_thanks"},
    "感谢": {"type": "scene", "name": "bow_thanks"},
    "多谢": {"type": "scene", "name": "bow_thanks"},
    "感恩": {"type": "scene", "name": "bow_thanks"},

    # 用户兴奋 → Mira一起兴奋
    "太激动了": {"type": "scene", "name": "excited_bounce"},
    "太棒了": {"type": "scene", "name": "excited_bounce"},
    "好兴奋": {"type": "scene", "name": "excited_bounce"},
    "热血沸腾": {"type": "scene", "name": "excited_bounce"},
    "激动死了": {"type": "scene", "name": "excited_bounce"},
    "超兴奋": {"type": "scene", "name": "excited_bounce"},
    "兴奋": {"type": "scene", "name": "excited_bounce"},
    "好激动": {"type": "scene", "name": "excited_bounce"},

    # ── 原始场景关键词（最低优先级）──
    "蹭蹭": {"type": "scene", "name": "touch_affection"},
    "靠近": {"type": "scene", "name": "touch_affection"},
    "撒娇": {"type": "scene", "name": "touch_affection"},
    "歪头": {"type": "scene", "name": "cute_probe"},
    "卖萌": {"type": "scene", "name": "cute_probe"},
    "好奇": {"type": "scene", "name": "curious_observe"},
    "缩一下": {"type": "scene", "name": "hand_avoid"},
    "躲一下": {"type": "scene", "name": "hand_avoid"},
    "后退": {"type": "scene", "name": "hand_avoid"},
    "发呆": {"type": "scene", "name": "daydream"},
    "睡觉": {"type": "scene", "name": "sleep"},
    "睡着": {"type": "scene", "name": "sleep"},
    "亮一下": {"type": "scene", "name": "celebrate"},
    "轻轻晃": {"type": "scene", "name": "celebrate"},
    "跳舞": {"type": "scene", "name": "celebrate"},
    "庆祝": {"type": "scene", "name": "celebrate"},
    "起床": {"type": "scene", "name": "wake_up"},
    "叹气": {"type": "trigger", "name": "sigh_detected"},
    "开心": {"type": "trigger", "name": "praise_detected"},
}


@dataclass
class RealtimeActionConfig:
    bridge_url: str = DEFAULT_BRIDGE_URL
    director_url: str = ""
    bridge_token: str = ""
    director_token: str = ""
    source: str = "stepfun-realtime"
    voice_state_enabled: bool = True
    semantic_actions_enabled: bool = True
    request_timeout_seconds: int = 5
    semantic_cooldown_seconds: float = 1.0
    suppress_duplicate_action_seconds: float = 2.0
    assistant_action_enabled: bool = True
    assistant_action_cooldown_seconds: float = 5.0
    # ── Two-phase refinement ──
    # When enabled, dispatch_transcript does Phase 1 only (fast local keyword
    # match + immediate execution). refine_transcript must be called afterwards
    # to run the LLM planner and compare/override/cancel the Phase 1 action.
    two_phase_refinement_enabled: bool = False
    # When enabled, every final user transcript must go through the configured
    # semantic planner before any scene or trigger is dispatched.
    require_model_planning: bool = False


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def phase_for_realtime_event(event: dict[str, Any]) -> str | None:
    event_type = str(event.get("type") or "")
    if event_type in {"input_audio_buffer.speech_started", "conversation.item.input_audio_buffer.speech_started"}:
        return "listening"
    if event_type in {
        "input_audio_buffer.speech_stopped",
        "input_audio_buffer.committed",
        "conversation.item.input_audio_transcription.completed",
    }:
        return "thinking"
    if event_type in {
        "response.audio.delta",
        "response.audio_transcript.delta",
        "response.text.delta",
        "response.output_text.delta",
    }:
        return "answer"
    if event_type in {"response.done", "response.completed"}:
        return "idle"
    return None


def extract_final_transcript(event: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "")
    if event_type not in {"conversation.item.input_audio_transcription.completed"}:
        return ""
    return str(event.get("transcript") or "").strip()


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def build_voice_state_request(
    phase: str,
    *,
    director_url: str,
    source: str = "stepfun-realtime",
) -> dict[str, Any]:
    action_id = VOICE_PHASE_QUICK_ACTIONS.get(phase)
    if not action_id:
        raise ValueError(f"Unsupported voice phase: {phase}")
    return {
        "method": "POST",
        "url": _join_url(director_url, f"/api/quick-action/{action_id}"),
        "payload": {
            "source": source,
            "phase": phase,
            "async": True,
            "createdAt": now_iso(),
        },
    }


def _unwrap_plan(plan_or_result: dict[str, Any]) -> dict[str, Any]:
    nested = plan_or_result.get("plan")
    return nested if isinstance(nested, dict) else plan_or_result


def build_plan_action_request(
    plan_or_result: dict[str, Any],
    *,
    bridge_url: str,
    transcript: str,
    source: str = "stepfun-realtime",
) -> dict[str, Any] | None:
    plan = _unwrap_plan(plan_or_result)
    action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
    action_type = str(action.get("type") or "none")
    action_name = str(action.get("name") or "")
    speech = plan.get("speech") if isinstance(plan.get("speech"), dict) else {}
    context = {
        "source": source,
        "transcript": transcript,
        "speech": speech,
        "planner": str(plan_or_result.get("provider") or plan.get("provider") or "local-or-llm"),
        "plannerModel": str(plan_or_result.get("model") or plan.get("model") or ""),
    }

    if action_type == "none":
        return None
    if action_type == "scene":
        return {
            "method": "POST",
            "url": _join_url(bridge_url, "/v1/mira-light/run-scene"),
            "payload": {
                "scene": action_name,
                "async": True,
                "cueMode": "voice-realtime",
                "silentMode": False,
                "context": context,
            },
        }
    if action_type == "trigger":
        return {
            "method": "POST",
            "url": _join_url(bridge_url, "/v1/mira-light/trigger"),
            "payload": {
                "event": action_name,
                "async": True,
                "payload": {
                    **context,
                    "cueMode": "voice-realtime",
                    "silentMode": False,
                },
            },
        }
    raise ValueError(f"Unsupported action type: {action_type}")


def _headers(token: str = "") -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def post_json_request(
    url: str,
    payload: dict[str, Any],
    *,
    token: str = "",
    timeout_seconds: int = 5,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=_headers(token),
        method="POST",
    )
    # Use a no-proxy opener for local bridge/director requests.
    # urllib.request.urlopen reads HTTPS_PROXY env which breaks local requests.
    no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with no_proxy_opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8").strip()
            return json.loads(raw) if raw else {"ok": True}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        return {"ok": False, "error": f"HTTP {exc.code}: {detail}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": str(exc)}


def build_local_fallback_plan(transcript: str, *, reason: str = "") -> dict[str, Any]:
    plan = build_local_structured_plan(
        transcript,
        reason="local keyword fallback" + (f": {reason}" if reason else ""),
    )
    validation = validate_plan(plan)
    return {
        "ok": bool(validation.get("ok")),
        "provider": "local-keyword-fallback",
        "transcript": transcript,
        "plan": plan,
        "validation": validation,
        "fallbackReason": reason,
    }


def default_planner(transcript: str, runtime_state: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return plan_from_text(transcript, runtime_state=runtime_state)
    except Exception as exc:  # noqa: BLE001 - realtime voice must keep local command fallback usable
        return build_local_fallback_plan(transcript, reason=str(exc))


def llm_action_suppression_reason(transcript: str, plan: dict[str, Any], *, has_pending: bool = False) -> str | None:
    """Suppress only weak generic LLM motion, not concrete semantic actions."""
    action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
    action_type = str(action.get("type") or "none")
    action_name = str(action.get("name") or "")
    if action_type == "none" or action_name not in GENERIC_LLM_ACTION_NAMES:
        return None

    local_intent = classify_intent(transcript)
    if is_brief_greeting(transcript) or should_skip_short_reply(transcript, intent=local_intent):
        return "llm-generic-action-low-info"

    intent = plan.get("intent") if isinstance(plan.get("intent"), dict) else {}
    try:
        confidence = float(intent.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    if has_pending and confidence < 0.85:
        return "llm-generic-action-low-confidence"
    if local_intent == "chat" and confidence < 0.75:
        return "llm-generic-action-low-confidence"
    return None


class RealtimeActionOrchestrator:
    """State machine that routes voice events into safe Mira Light actions.

    State tracking:
      - current_phase: idle / listening / thinking / answer
      - last_transcript: deduplication guard
      - last_semantic_action_time: cooldown timer (prevents rapid-fire actions)
      - last_action_name: duplicate action suppression within cooldown window
    """

    def __init__(
        self,
        config: RealtimeActionConfig | None = None,
        *,
        planner: Planner | None = None,
        post_json: PostJson = post_json_request,
    ) -> None:
        self.config = config or RealtimeActionConfig()
        self.planner = planner or default_planner
        self.post_json = post_json
        # ── State machine ──
        self.current_phase: str = "idle"
        self.last_transcript: str = ""
        self.last_semantic_action_time: float = 0.0
        self.last_action_name: str = ""
        self._action_count: int = 0
        self.last_assistant_text: str = ""
        self.last_assistant_action_time: float = 0.0
        # ── Voice-state cooldown to prevent servo jitter ──
        self._last_voice_state_time: float = 0.0
        self._voice_state_cooldown_seconds: float = float(
            os.environ.get("MIRA_LIGHT_VOICE_STATE_COOLDOWN_SECONDS", "2.0")
        )
        # ── Two-phase refinement state ──
        self.pending_refinement: bool = False
        self.pending_refinement_action: dict[str, Any] | None = None
        self.pending_refinement_transcript: str = ""
        # ── Vision-driven proactive action state ──
        self._last_vision_action_time: float = 0.0
        self._last_vision_cue: str = ""
        self._vision_cooldown_seconds: float = float(
            os.environ.get("MIRA_VISION_ACTION_COOLDOWN_SECONDS", "10.0")
        )

    def check_vision_proactive_action(self) -> dict[str, Any] | None:
        """Check if the VLM detected a strong interaction cue that should
        trigger a Mira action proactively, without waiting for voice input.

        Returns an action dict if a vision-triggered action should fire,
        or None if no action is needed. Respects a cooldown to avoid
        repeating the same action.

        This method is safe to call periodically (e.g. once per second)
        from the voice loop. It is a no-op when vision is disabled.
        """
        try:
            from mira_vision_context import get_latest_scene
            from mira_vision_understanding import vision_scene_to_action
        except Exception:
            return None

        scene = get_latest_scene()
        if scene is None:
            return None

        # Only react to strong interaction cues, not passive scene descriptions
        strong_cues = {"waving", "approaching", "touching_screen"}
        if scene.interaction_cue not in strong_cues:
            return None

        action = vision_scene_to_action(scene)
        if action is None:
            return None

        now = datetime.now().timestamp()
        cue_key = f"{scene.interaction_cue}:{action.get('name', '')}"
        # Cooldown: don't repeat the same vision action too quickly
        if cue_key == self._last_vision_cue and (now - self._last_vision_action_time) < self._vision_cooldown_seconds:
            return None

        self._last_vision_action_time = now
        self._last_vision_cue = cue_key

        return {
            "kind": "vision-proactive",
            "source": "vision",
            "transcript": "",
            "action": action,
            "scene_summary": scene.scene_summary,
            "interaction_cue": scene.interaction_cue,
            "confidence": round(scene.confidence, 3),
        }

    def _post_with_scene_preemption(self, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        response = self.post_json(
            request["url"],
            request["payload"],
            token=self.config.bridge_token,
            timeout_seconds=self.config.request_timeout_seconds,
        )
        error_text = str(response.get("error") or "") if isinstance(response, dict) else ""
        if not (isinstance(response, dict) and response.get("ok") is False and "Another scene is already running" in error_text):
            return response, None

        stop_response = self.post_json(
            _join_url(self.config.bridge_url, "/v1/mira-light/stop"),
            {},
            token=self.config.bridge_token,
            timeout_seconds=self.config.request_timeout_seconds,
        )
        response = self.post_json(
            request["url"],
            request["payload"],
            token=self.config.bridge_token,
            timeout_seconds=self.config.request_timeout_seconds,
        )
        return response, stop_response

    def _stop_current_scene(self) -> dict[str, Any]:
        """Send a stop request to the bridge to halt whatever scene is running."""
        return self.post_json(
            _join_url(self.config.bridge_url, "/v1/mira-light/stop"),
            {},
            token=self.config.bridge_token,
            timeout_seconds=self.config.request_timeout_seconds,
        )

    def handle_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        phase = phase_for_realtime_event(event)
        if phase:
            phase_action = self.dispatch_voice_phase(phase)
            if phase_action:
                actions.append(phase_action)

        transcript = extract_final_transcript(event)
        if transcript:
            semantic_action = self.dispatch_transcript(transcript)
            if semantic_action:
                actions.append(semantic_action)
        return actions

    def dispatch_voice_phase(self, phase: str) -> dict[str, Any] | None:
        if phase == "idle":
            self.current_phase = "idle"
            return None
        if phase == self.current_phase:
            return None
        self.current_phase = phase

        if not self.config.voice_state_enabled:
            return None

        # Voice-state cooldown: prevent rapid servo jitter from
        # listening->thinking->answer transitions on every audio chunk.
        import time as _time
        now = _time.monotonic()
        elapsed = now - self._last_voice_state_time
        if elapsed < self._voice_state_cooldown_seconds:
            return None  # suppress this phase change
        self._last_voice_state_time = now

        # Voice phase actions require a director endpoint.
        # The bridge does NOT support voice_motion_xxx triggers.
        if not self.config.director_url:
            return None

        request = build_voice_state_request(
            phase,
            director_url=self.config.director_url,
            source=self.config.source,
        )
        response = self.post_json(
            request["url"],
            request["payload"],
            token=self.config.director_token,
            timeout_seconds=self.config.request_timeout_seconds,
        )
        return {
            "kind": "voice-state",
            "phase": phase,
            "request": request,
            "response": response,
        }

    def dispatch_assistant_text(self, text: str) -> dict[str, Any] | None:
        """Parse Mary's reply text for action keywords and dispatch to bridge.

        The StepFun realtime model replies with text like '歪头，蹭蹭' or
        '靠近，亮一下'. We extract the FIRST matching action keyword and
        send it to the board as a scene or trigger.
        """
        import time as _time

        text = text.strip()
        if not text:
            return None
        if text == self.last_assistant_text:
            return None
        self.last_assistant_text = text

        if not self.config.assistant_action_enabled:
            return None

        # Cooldown check
        now = _time.monotonic()
        elapsed = now - self.last_assistant_action_time
        if elapsed < self.config.assistant_action_cooldown_seconds:
            return {"kind": "assistant-action-skip", "reason": "cooldown", "text": text}

        # Find first matching action keyword using longest-keyword-first priority.
        # When multiple keywords match, the longest (most specific) one wins.
        # e.g. "开心跳舞" (4 chars) beats "跳舞" (2 chars).
        # Minimum keyword length: 3 chars to avoid false positives from
        # short words like "怕", "累", "气" appearing in normal text.
        matched_action = None
        matched_keyword = None
        sorted_keywords = sorted(
            ASSISTANT_ACTION_KEYWORDS.items(),
            key=lambda kv: len(kv[0]),
            reverse=True,  # longest first
        )
        for keyword, action in sorted_keywords:
            if len(keyword) < 3:
                continue  # skip overly short keywords
            if keyword in text:
                matched_action = action
                matched_keyword = keyword
                break

        if not matched_action:
            return None

        # Build and send bridge request
        action_type = matched_action["type"]
        action_name = matched_action["name"]

        if action_type == "scene":
            url = _join_url(self.config.bridge_url, "/v1/mira-light/run-scene")
            payload = {
                "scene": action_name,
                "source": "assistant-text",
                "transcript": text,
            }
        else:
            url = _join_url(self.config.bridge_url, "/v1/mira-light/trigger")
            payload = {
                "event": action_name,
                "source": "assistant-text",
                "transcript": text,
            }

        try:
            response, preempt = self._post_with_scene_preemption({
                "url": url,
                "payload": payload,
            })
            self.last_assistant_action_time = now
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
            preempt = None

        return {
            "kind": "assistant-action",
            "text": text,
            "keyword": matched_keyword,
            "action": matched_action,
            "url": url,
            "response": response,
            "preemptResponse": preempt,
        }

    def _check_cooldown(self, action_name: str) -> str | None:
        """Return a skip reason if the action should be suppressed, else None."""
        import time as _time

        now = _time.monotonic()
        elapsed = now - self.last_semantic_action_time

        # Global cooldown: suppress any semantic action within N seconds of the last one
        if elapsed < self.config.semantic_cooldown_seconds:
            return f"cooldown ({elapsed:.1f}s < {self.config.semantic_cooldown_seconds}s)"

        # Duplicate action suppression: same action name within a wider window
        if (
            action_name
            and action_name == self.last_action_name
            and elapsed < self.config.suppress_duplicate_action_seconds
        ):
            return f"duplicate-action '{action_name}' ({elapsed:.1f}s < {self.config.suppress_duplicate_action_seconds}s)"

        return None

    def _record_action(self, action_name: str) -> None:
        import time as _time

        self.last_semantic_action_time = _time.monotonic()
        self.last_action_name = action_name
        self._action_count += 1

    def _dispatch_model_planned_transcript(self, text: str) -> dict[str, Any] | None:
        runtime_state = {"voicePhase": self.current_phase}
        try:
            plan_result = self.planner(text, runtime_state=runtime_state)
        except Exception as exc:  # noqa: BLE001
            return {
                "kind": "semantic-skip",
                "reason": "planner-error",
                "transcript": text,
                "source": "llm-planner",
                "error": str(exc),
            }

        plan = _unwrap_plan(plan_result)
        provider = str(plan_result.get("provider") or plan.get("provider") or "")
        model = str(plan_result.get("model") or plan.get("model") or "")
        if provider == "local-keyword-fallback":
            return {
                "kind": "semantic-skip",
                "reason": "model-planning-required",
                "transcript": text,
                "source": "llm-planner",
                "provider": provider,
                "model": model,
                "plan": plan,
            }

        validation = plan_result.get("validation") if isinstance(plan_result.get("validation"), dict) else validate_plan(plan)
        if not validation.get("ok"):
            return {
                "kind": "semantic-skip",
                "reason": "invalid-plan",
                "transcript": text,
                "source": "llm-planner",
                "provider": provider,
                "model": model,
                "plan": plan,
                "validation": validation,
            }

        request = build_plan_action_request(
            plan_result,
            bridge_url=self.config.bridge_url,
            transcript=text,
            source=self.config.source,
        )
        if request is None:
            return {
                "kind": "semantic-skip",
                "reason": "none-action",
                "transcript": text,
                "source": "llm-planner",
                "provider": provider,
                "model": model,
                "plan": plan,
                "validation": validation,
            }

        suppression_reason = llm_action_suppression_reason(text, plan, has_pending=False)
        if suppression_reason:
            return {
                "kind": "semantic-skip",
                "reason": suppression_reason,
                "transcript": text,
                "source": "llm-planner",
                "provider": provider,
                "model": model,
                "plan": plan,
                "validation": validation,
            }

        action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
        action_name = str(action.get("name") or "")
        cooldown_reason = self._check_cooldown(action_name)
        if cooldown_reason:
            return {
                "kind": "semantic-skip",
                "reason": f"cooldown: {cooldown_reason}",
                "transcript": text,
                "source": "llm-planner",
                "provider": provider,
                "model": model,
                "plan": plan,
                "validation": validation,
            }

        response, preempt_response = self._post_with_scene_preemption(request)
        self._record_action(action_name)
        result = {
            "kind": "semantic-action",
            "transcript": text,
            "plan": plan,
            "source": "llm-planner",
            "provider": provider,
            "model": model,
            "validation": validation,
            "request": request,
            "response": response,
        }
        if preempt_response is not None:
            result["preemptResponse"] = preempt_response
        return result

    def dispatch_transcript(self, transcript: str) -> dict[str, Any] | None:
        text = transcript.strip()
        if not text:
            return None
        # Dedup is handled by cooldown; skipping duplicates here breaks repeated action commands.
        self.last_transcript = text

        if not self.config.semantic_actions_enabled:
            return {"kind": "semantic-skip", "reason": "semantic-actions-disabled", "transcript": text}

        if self.config.require_model_planning:
            return self._dispatch_model_planned_transcript(text)

        # ── Step 1: LOCAL INTENT FIRST ──
        # Local keyword classification is instant and reliable for known commands.
        import os
        disable_local = os.environ.get("MIRA_LIGHT_DISABLE_LOCAL_INTENT", "").strip().lower() in {"1", "true", "yes", "on"}
        
        local_action = None
        local_intent = "chat"
        if not disable_local:
            local_intent = classify_intent(text)
            local_action = action_for_intent(local_intent)

        if local_action and local_action.get("type") != "none":
            # Local intent matched a concrete action (scene/trigger).
            # Build a local plan and dispatch immediately — skip LLM entirely.
            plan = build_local_fallback_plan(text, reason="local-intent-priority")
            validation = plan.get("validation") if isinstance(plan.get("validation"), dict) else validate_plan(_unwrap_plan(plan))
            if validation.get("ok"):
                request = build_plan_action_request(
                    plan,
                    bridge_url=self.config.bridge_url,
                    transcript=text,
                    source=self.config.source,
                )
                if request is not None:
                    # Cooldown / debounce guard
                    action_name = str(local_action.get("name") or "")
                    cooldown_reason = self._check_cooldown(action_name)
                    if cooldown_reason:
                        return {
                            "kind": "semantic-skip",
                            "reason": f"cooldown: {cooldown_reason}",
                            "transcript": text,
                            "plan": plan,
                        }

                    response, preempt_response = self._post_with_scene_preemption(request)
                    self._record_action(action_name)
                    result = {
                        "kind": "semantic-action",
                        "transcript": text,
                        "plan": plan,
                        "source": "local-intent",
                        "intent": local_intent,
                        "request": request,
                        "response": response,
                    }
                    if preempt_response is not None:
                        result["preemptResponse"] = preempt_response

                    # ── TWO-PHASE: mark pending refinement for LLM ──
                    if self.config.two_phase_refinement_enabled:
                        self.pending_refinement = True
                        self.pending_refinement_action = {
                            "type": local_action.get("type"),
                            "name": action_name,
                        }
                        self.pending_refinement_transcript = text
                        result["phase"] = 1
                        result["pending_refinement"] = True

                    return result

        # ── TWO-PHASE: no local match, defer entirely to refine_transcript ──
        if self.config.two_phase_refinement_enabled:
            self.pending_refinement = False
            self.pending_refinement_action = None
            self.pending_refinement_transcript = text
            return {
                "kind": "semantic-skip",
                "reason": "needs-llm-refinement",
                "phase": 1,
                "transcript": text,
            }

        # ── Step 2: LLM PLANNER (only for chat / ambiguous intents) ──
        runtime_state = {"voicePhase": self.current_phase}
        try:
            plan_result = self.planner(text, runtime_state=runtime_state)
        except Exception as exc:  # noqa: BLE001
            fallback_plan = build_local_fallback_plan(text, reason=f"planner-error: {exc}")
            fallback_action = _unwrap_plan(fallback_plan).get("action")
            if isinstance(fallback_action, dict) and fallback_action.get("type") not in ("none", ""):
                plan_result = fallback_plan
                fallback_source = "local-fallback"
            else:
                return {
                    "kind": "semantic-skip",
                    "reason": "planner-error",
                    "transcript": text,
                    "error": str(exc),
                    "plan": fallback_plan,
                }
        else:
            fallback_source = ""
        plan = _unwrap_plan(plan_result)
        validation = plan_result.get("validation") if isinstance(plan_result.get("validation"), dict) else validate_plan(plan)

        # If LLM plan fails validation, fall back to local plan instead of skipping
        if not validation.get("ok"):
            fallback_plan = build_local_fallback_plan(text, reason="llm-validation-failed")
            fallback_validation = validate_plan(fallback_plan)
            fallback_action = fallback_plan.get("action") if isinstance(fallback_plan.get("action"), dict) else {}
            if fallback_validation.get("ok") and fallback_action.get("type") not in ("none", ""):
                plan = fallback_plan
                validation = fallback_validation
            else:
                return {
                    "kind": "semantic-skip",
                    "reason": "invalid-plan",
                    "transcript": text,
                    "plan": plan,
                    "validation": validation,
                }

        request = build_plan_action_request(
            plan,
            bridge_url=self.config.bridge_url,
            transcript=text,
            source=self.config.source,
        )
        if request is None:
            return {
                "kind": "semantic-skip",
                "reason": "none-action",
                "transcript": text,
                "plan": plan,
                "validation": validation,
            }

        suppression_reason = llm_action_suppression_reason(text, plan, has_pending=False)
        if suppression_reason:
            return {
                "kind": "semantic-skip",
                "reason": suppression_reason,
                "transcript": text,
                "plan": plan,
                "validation": validation,
            }

        # ── Cooldown / debounce guard ──
        action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
        action_name = str(action.get("name") or "")
        cooldown_reason = self._check_cooldown(action_name)
        if cooldown_reason:
            return {
                "kind": "semantic-skip",
                "reason": f"cooldown: {cooldown_reason}",
                "transcript": text,
                "plan": plan,
                "validation": validation,
            }

        response, preempt_response = self._post_with_scene_preemption(request)
        self._record_action(action_name)
        result = {
            "kind": "semantic-action",
            "transcript": text,
            "plan": plan,
            "source": fallback_source or "llm-planner",
            "validation": validation,
            "request": request,
            "response": response,
        }
        if preempt_response is not None:
            result["preemptResponse"] = preempt_response
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Phase 2: LLM refinement
    # ──────────────────────────────────────────────────────────────────────

    def refine_transcript(self, transcript: str) -> dict[str, Any] | None:
        """Phase 2 of two-phase refinement.

        Runs the LLM planner and compares its result with the Phase 1 action:

        - Phase 1 executed an action (pending_refinement=True):
            * LLM agrees  -> semantic-confirm  (do nothing, keep Phase 1 action)
            * LLM differs -> semantic-override (stop Phase 1, start LLM action)
            * LLM says none -> semantic-cancel (stop Phase 1, go idle)
        - Phase 1 did NOT execute (pending_refinement=False):
            * Execute LLM result directly (same as the classic Step 2 path)

        After this call, pending refinement state is always cleared.
        """
        text = transcript.strip()
        if not text:
            return None

        if not self.config.two_phase_refinement_enabled:
            return None

        # Guard against stale refinement requests (different transcript)
        if text != self.pending_refinement_transcript:
            return None

        has_pending = self.pending_refinement
        pending_action = self.pending_refinement_action

        # Clear pending state — refinement is one-shot
        def clear_pending_if_current() -> None:
            if text == self.pending_refinement_transcript:
                self.pending_refinement = False
                self.pending_refinement_action = None
                self.pending_refinement_transcript = ""

        # ── Run LLM planner ──
        runtime_state = {"voicePhase": self.current_phase}
        try:
            plan_result = self.planner(text, runtime_state=runtime_state)
        except Exception as exc:  # noqa: BLE001
            clear_pending_if_current()
            if has_pending:
                # LLM failed but Phase 1 action is already running — keep it
                return {
                    "kind": "semantic-refinement-error",
                    "transcript": text,
                    "error": str(exc),
                    "pending_action_kept": pending_action,
                }
            # No Phase 1 action — try local fallback
            fallback_plan = build_local_fallback_plan(text, reason=f"planner-error: {exc}")
            fallback_action = _unwrap_plan(fallback_plan).get("action")
            if isinstance(fallback_action, dict) and fallback_action.get("type") not in ("none", ""):
                plan_result = fallback_plan
            else:
                return {
                    "kind": "semantic-skip",
                    "reason": "planner-error",
                    "transcript": text,
                    "error": str(exc),
                    "plan": fallback_plan,
                }

        plan = _unwrap_plan(plan_result)
        validation = plan_result.get("validation") if isinstance(plan_result.get("validation"), dict) else validate_plan(plan)

        if text != self.pending_refinement_transcript:
            return {
                "kind": "semantic-refinement-stale",
                "reason": "newer-transcript-arrived",
                "transcript": text,
                "latest_transcript": self.pending_refinement_transcript,
                "plan": plan,
                "validation": validation,
            }

        clear_pending_if_current()

        if not validation.get("ok"):
            if has_pending:
                return {
                    "kind": "semantic-refinement-skip",
                    "reason": "invalid-plan",
                    "transcript": text,
                    "pending_action_kept": pending_action,
                    "validation": validation,
                }
            fallback_plan = build_local_fallback_plan(text, reason="llm-validation-failed")
            fallback_validation = validate_plan(fallback_plan)
            fallback_action = fallback_plan.get("action") if isinstance(fallback_plan.get("action"), dict) else {}
            if fallback_validation.get("ok") and fallback_action.get("type") not in ("none", ""):
                plan = fallback_plan
                validation = fallback_validation
            else:
                return {
                    "kind": "semantic-skip",
                    "reason": "invalid-plan",
                    "transcript": text,
                    "plan": plan,
                    "validation": validation,
                }

        llm_action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
        llm_action_type = str(llm_action.get("type") or "none")
        llm_action_name = str(llm_action.get("name") or "")
        suppression_reason = llm_action_suppression_reason(text, plan, has_pending=has_pending)

        # ── Compare LLM result with Phase 1 action ──
        if has_pending and pending_action:
            pending_name = str(pending_action.get("name") or "")

            # Case 1: LLM says no action needed -> cancel Phase 1
            if llm_action_type == "none":
                stop_response = self._stop_current_scene()
                return {
                    "kind": "semantic-cancel",
                    "transcript": text,
                    "reason": "llm-overrides-with-none",
                    "cancelled_action": pending_action,
                    "stop_response": stop_response,
                    "plan": plan,
                }

            # Case 2: LLM agrees with Phase 1 -> confirm (no bridge call)
            if llm_action_name == pending_name:
                return {
                    "kind": "semantic-confirm",
                    "transcript": text,
                    "confirmed_action": pending_action,
                    "plan": plan,
                }

            if suppression_reason:
                return {
                    "kind": "semantic-refinement-skip",
                    "reason": suppression_reason,
                    "transcript": text,
                    "pending_action_kept": pending_action,
                    "plan": plan,
                    "validation": validation,
                }

            # Case 3: LLM disagrees -> override (stop Phase 1, start LLM action)
            request = build_plan_action_request(
                plan,
                bridge_url=self.config.bridge_url,
                transcript=text,
                source=self.config.source,
            )
            if request is not None:
                response, preempt_response = self._post_with_scene_preemption(request)
                self._record_action(llm_action_name)
                result: dict[str, Any] = {
                    "kind": "semantic-override",
                    "transcript": text,
                    "overridden_action": pending_action,
                    "new_action": {"type": llm_action_type, "name": llm_action_name},
                    "plan": plan,
                    "source": "llm-refinement",
                    "validation": validation,
                    "request": request,
                    "response": response,
                }
                if preempt_response is not None:
                    result["preemptResponse"] = preempt_response
                return result

            # LLM action type is not none but request is None — treat as confirm
            return {
                "kind": "semantic-confirm",
                "transcript": text,
                "confirmed_action": pending_action,
                "plan": plan,
            }

        # ── No Phase 1 action — execute LLM result directly ──
        request = build_plan_action_request(
            plan,
            bridge_url=self.config.bridge_url,
            transcript=text,
            source=self.config.source,
        )
        if request is None:
            return {
                "kind": "semantic-skip",
                "reason": "none-action",
                "transcript": text,
                "plan": plan,
                "validation": validation,
            }

        if suppression_reason:
            return {
                "kind": "semantic-skip",
                "reason": suppression_reason,
                "transcript": text,
                "plan": plan,
                "validation": validation,
            }

        action_name = llm_action_name
        cooldown_reason = self._check_cooldown(action_name)
        if cooldown_reason:
            return {
                "kind": "semantic-skip",
                "reason": f"cooldown: {cooldown_reason}",
                "transcript": text,
                "plan": plan,
                "validation": validation,
            }

        response, preempt_response = self._post_with_scene_preemption(request)
        self._record_action(action_name)
        result = {
            "kind": "semantic-action",
            "transcript": text,
            "plan": plan,
            "source": "llm-refinement",
            "validation": validation,
            "request": request,
            "response": response,
        }
        if preempt_response is not None:
            result["preemptResponse"] = preempt_response
        return result
