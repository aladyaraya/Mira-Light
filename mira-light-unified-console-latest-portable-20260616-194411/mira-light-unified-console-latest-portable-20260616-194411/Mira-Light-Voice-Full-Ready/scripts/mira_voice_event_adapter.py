"""Mira Light 语音事件适配器.

替代 RealtimeActionOrchestrator 的状态机，把 StepFun 实时语音事件
转换为动作混合器事件。

关键改进:
    - 不维护 current_phase / cooldown / last_transcript 状态
    - 不做抢占式 stop+restart，通过事件总线发送事件
    - 助手回复关键词匹配保留（纯逻辑，不涉及状态管理）
    - 视觉主动动作保留

设计文档: docs/plans/2026-06-21-action-mixer-design.md
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Callable

from mira_event_bus import EventBus, emit_voice, emit_voice_done, emit_vision, emit_touch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 复用 RealtimeActionOrchestrator 的纯逻辑部分
# ---------------------------------------------------------------------------

# 从 mira_realtime_action_orchestrator 导入关键词映射和工具函数
try:
    from mira_realtime_action_orchestrator import (
        ASSISTANT_ACTION_KEYWORDS,
        VOICE_PHASE_QUICK_ACTIONS,
        extract_final_transcript,
        phase_for_realtime_event,
        build_voice_state_request,
    )
    _HAS_ORCHESTRATOR_DEPS = True
except ImportError:
    _HAS_ORCHESTRATOR_DEPS = False
    ASSISTANT_ACTION_KEYWORDS = {}
    VOICE_PHASE_QUICK_ACTIONS = {}
    extract_final_transcript = lambda event: None  # noqa: E731
    phase_for_realtime_event = lambda event: None  # noqa: E731
    build_voice_state_request = lambda *a, **kw: None  # noqa: E731

try:
    from mira_voice_intents import action_for_intent, classify_intent, is_brief_greeting, should_skip_short_reply
    _HAS_VOICE_INTENTS = True
except ImportError:
    _HAS_VOICE_INTENTS = False

try:
    from stepfun_llm_planner import build_local_structured_plan, plan_from_text, validate_plan
    _HAS_LLM_PLANNER = True
except ImportError:
    _HAS_LLM_PLANNER = False


# ---------------------------------------------------------------------------
# VoiceEventAdapter
# ---------------------------------------------------------------------------


class VoiceEventAdapter:
    """把 StepFun 实时语音事件转换为动作混合器事件.

    替代 RealtimeActionOrchestrator 的状态机：
        - 不维护 current_phase / cooldown / last_transcript
        - 不做抢占式 stop+restart
        - 通过事件总线发送事件，由 ActionMixer 仲裁

    保留的纯逻辑:
        - 助手回复关键词匹配（ASSISTANT_ACTION_KEYWORDS）
        - 语音阶段识别（listening/thinking/answer）
        - 语义意图分类（classify_intent）
        - LLM 规划（plan_from_text）

    使用方式:
        adapter = VoiceEventAdapter(event_bus=bus)
        # 在 StepFun 事件循环中
        for event in stepfun_events:
            adapter.handle_event(event)
    """

    def __init__(
        self,
        event_bus: EventBus,
        *,
        director_url: str | None = None,
        director_token: str | None = None,
        source: str = "stepfun-realtime",
        voice_state_enabled: bool = True,
        assistant_action_enabled: bool = True,
        semantic_action_enabled: bool = True,
        post_json: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.director_url = director_url
        self.director_token = director_token
        self.source = source
        self.voice_state_enabled = voice_state_enabled
        self.assistant_action_enabled = assistant_action_enabled
        self.semantic_action_enabled = semantic_action_enabled
        self._post_json = post_json  # 用于 voice phase 快速动作（导演台）

        # 最小状态：只保留去重，不保留 cooldown
        self._last_assistant_text: str = ""
        self._last_transcript: str = ""
        self._current_phase: str = "idle"

        # 统计
        self._stats = {
            "eventsHandled": 0,
            "voicePhasesDispatched": 0,
            "semanticActionsDispatched": 0,
            "assistantActionsDispatched": 0,
            "actionsSkipped": 0,
        }

    # -- 主入口 --

    def handle_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """处理 StepFun 实时语音事件，返回已发送的动作列表.

        替代 RealtimeActionOrchestrator.handle_event
        """
        self._stats["eventsHandled"] += 1
        actions: list[dict[str, Any]] = []

        # 1. 语音阶段（listening/thinking/answer）
        phase = phase_for_realtime_event(event)
        if phase:
            phase_action = self._dispatch_voice_phase(phase)
            if phase_action:
                actions.append(phase_action)

        # 2. 用户转写 → 语义动作
        transcript = extract_final_transcript(event)
        if transcript:
            semantic_action = self._dispatch_transcript(transcript)
            if semantic_action:
                actions.append(semantic_action)

        # 3. 助手回复 → 关键词匹配动作
        assistant_text = self._extract_assistant_text(event)
        if assistant_text:
            assistant_action = self._dispatch_assistant_text(assistant_text)
            if assistant_action:
                actions.append(assistant_action)

        return actions

    # -- 语音阶段 --

    def _dispatch_voice_phase(self, phase: str) -> dict[str, Any] | None:
        """语音阶段动作（listening/thinking/answer）.

        这些是快速动作，直接发到导演台，不经过混合器（因为它们是
        轻量级的灯效提示，不需要抢占跟踪）。
        """
        if phase == "idle":
            self._current_phase = "idle"
            return None
        if phase == self._current_phase:
            return None
        self._current_phase = phase

        if not self.voice_state_enabled or not self.director_url:
            return None

        # 语音阶段动作直接发导演台，不经过混合器
        request = build_voice_state_request(
            phase,
            director_url=self.director_url,
            source=self.source,
        )
        if not request:
            return None

        try:
            if self._post_json:
                response = self._post_json(
                    request["url"],
                    request["payload"],
                    token=self.director_token,
                )
            else:
                response = {"ok": True, "skipped": "no_post_json"}
        except Exception as exc:  # noqa: BLE001
            response = {"ok": False, "error": str(exc)}

        self._stats["voicePhasesDispatched"] += 1
        return {
            "kind": "voice-state",
            "phase": phase,
            "request": request,
            "response": response,
        }

    # -- 语义动作 --

    def _dispatch_transcript(self, transcript: str) -> dict[str, Any] | None:
        """用户转写 → 语义动作（通过事件总线发到混合器）.

        替代 RealtimeActionOrchestrator.dispatch_transcript
        不做 cooldown，不做抢占式 stop+restart。
        """
        # 去重（最小状态）
        if transcript == self._last_transcript:
            self._stats["actionsSkipped"] += 1
            return None
        self._last_transcript = transcript

        if not self.semantic_action_enabled:
            return None

        # 短回复跳过
        if _HAS_VOICE_INTENTS and should_skip_short_reply(transcript):
            self._stats["actionsSkipped"] += 1
            return None

        # 简短问候跳过
        if _HAS_VOICE_INTENTS and is_brief_greeting(transcript):
            self._stats["actionsSkipped"] += 1
            return None

        # 意图分类
        action = None
        if _HAS_VOICE_INTENTS:
            action = action_for_intent(transcript)
        elif _HAS_LLM_PLANNER:
            plan = plan_from_text(transcript)
            if validate_plan(plan):
                action = plan

        if not action or action.get("type") == "none":
            return None

        action_type = action.get("type")
        action_name = action.get("name")
        if not action_name:
            return None

        # 通过事件总线发送（不直接调 bridge，不抢占）
        if action_type == "scene":
            emit_voice(self.event_bus, action_name, {
                "source": self.source,
                "transcript": transcript,
            })
            self._stats["semanticActionsDispatched"] += 1
            return {
                "kind": "semantic-scene",
                "scene": action_name,
                "transcript": transcript,
            }
        elif action_type == "trigger":
            emit_touch(self.event_bus, action_name, {
                "source": self.source,
                "transcript": transcript,
            })
            self._stats["semanticActionsDispatched"] += 1
            return {
                "kind": "semantic-trigger",
                "trigger": action_name,
                "transcript": transcript,
            }

        return None

    # -- 助手回复关键词匹配 --

    def _dispatch_assistant_text(self, text: str) -> dict[str, Any] | None:
        """助手回复 → 关键词匹配动作（通过事件总线发到混合器）.

        替代 RealtimeActionOrchestrator.dispatch_assistant_text
        不做 cooldown，只做去重。
        """
        text = text.strip()
        if not text:
            return None
        if text == self._last_assistant_text:
            self._stats["actionsSkipped"] += 1
            return None
        self._last_assistant_text = text

        if not self.assistant_action_enabled:
            return None

        # 关键词匹配（最长优先）
        matched_action = None
        matched_keyword = None
        sorted_keywords = sorted(
            ASSISTANT_ACTION_KEYWORDS.items(),
            key=lambda kv: len(kv[0]),
            reverse=True,
        )
        for keyword, action in sorted_keywords:
            if keyword in text:
                matched_action = action
                matched_keyword = keyword
                break

        if not matched_action:
            return None

        action_type = matched_action["type"]
        action_name = matched_action["name"]

        # 通过事件总线发送（不直接调 bridge，不抢占）
        if action_type == "scene":
            emit_voice(self.event_bus, action_name, {
                "source": "assistant-text",
                "transcript": text,
                "keyword": matched_keyword,
            })
            self._stats["assistantActionsDispatched"] += 1
            return {
                "kind": "assistant-scene",
                "scene": action_name,
                "keyword": matched_keyword,
                "text": text,
            }
        elif action_type == "trigger":
            emit_touch(self.event_bus, action_name, {
                "source": "assistant-text",
                "transcript": text,
                "keyword": matched_keyword,
            })
            self._stats["assistantActionsDispatched"] += 1
            return {
                "kind": "assistant-trigger",
                "trigger": action_name,
                "keyword": matched_keyword,
                "text": text,
            }

        return None

    # -- 助手回复结束 --

    def on_response_done(self) -> None:
        """助手回复结束，通知混合器弹出 L2.

        在 StepFun 的 response.done 事件时调用。
        """
        emit_voice_done(self.event_bus, self._last_assistant_text or "")

    # -- 视觉主动动作 --

    def check_vision_proactive_action(self) -> dict[str, Any] | None:
        """检查 VLM 是否检测到强交互信号.

        保留自 RealtimeActionOrchestrator.check_vision_proactive_action
        但通过事件总线发送，不直接调 bridge。
        """
        try:
            from mira_vision_context import get_latest_scene
            from mira_vision_understanding import vision_scene_to_action
        except Exception:
            return None

        scene = get_latest_scene()
        if scene is None:
            return None

        strong_cues = {"waving", "approaching", "touching_screen"}
        if scene.interaction_cue not in strong_cues:
            return None

        action = vision_scene_to_action(scene)
        if action is None:
            return None

        # 通过事件总线发送
        action_name = action.get("name", "")
        if action_name:
            emit_voice(self.event_bus, action_name, {
                "source": "vision-proactive",
                "cue": scene.interaction_cue,
            })

        return {
            "kind": "vision-proactive",
            "cue": scene.interaction_cue,
            "action": action,
        }

    # -- 状态查询 --

    def get_stats(self) -> dict[str, Any]:
        return dict(self._stats)

    def get_state(self) -> dict[str, Any]:
        return {
            "currentPhase": self._current_phase,
            "lastTranscript": self._last_transcript,
            "lastAssistantText": self._last_assistant_text,
            "stats": self.get_stats(),
        }

    # -- 内部方法 --

    def _extract_assistant_text(self, event: dict[str, Any]) -> str | None:
        """从 StepFun 事件中提取助手回复文本."""
        event_type = str(event.get("type") or "")
        if event_type == "response.audio_transcript.done":
            return str(event.get("transcript") or "").strip()
        if event_type == "response.text.done":
            return str(event.get("text") or "").strip()
        return None
