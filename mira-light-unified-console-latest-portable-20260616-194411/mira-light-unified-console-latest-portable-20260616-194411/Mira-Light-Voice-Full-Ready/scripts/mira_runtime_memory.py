#!/usr/bin/env python3
"""Small runtime memory for Mira realtime voice sessions."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _plan_from_action_like(action: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(action, dict):
        return {}
    plan = action.get("plan") if isinstance(action.get("plan"), dict) else {}
    if isinstance(plan.get("plan"), dict):
        plan = plan["plan"]
    return plan if isinstance(plan, dict) else {}


def _reply_from_plan(plan: dict[str, Any]) -> str:
    speech = plan.get("speech") if isinstance(plan.get("speech"), dict) else {}
    if speech.get("shouldSpeak") is False:
        return ""
    return _text(speech.get("text") or plan.get("reply"))


def _action_from_plan(plan: dict[str, Any]) -> dict[str, str]:
    action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
    return {
        "type": _text(action.get("type") or "none") or "none",
        "name": _text(action.get("name")),
    }


def _append_unique(items: list[str], value: Any, *, limit: int) -> None:
    text = _text(value)
    if not text:
        return
    if text in items:
        return
    items.append(text)
    del items[:-limit]


class MiraRuntimeMemory:
    """Bounded, explicit session memory passed into the planner."""

    def __init__(
        self,
        *,
        max_turns: int = 12,
        max_session_notes: int = 12,
        max_long_term_candidates: int = 20,
    ) -> None:
        self.max_turns = max(1, int(max_turns))
        self.max_session_notes = max(1, int(max_session_notes))
        self.max_long_term_candidates = max(1, int(max_long_term_candidates))
        self.recent_turns: deque[dict[str, Any]] = deque(maxlen=self.max_turns)
        self.session_notes: list[str] = []
        self.long_term_candidates: list[str] = []

    def record_turn(
        self,
        user: str,
        *,
        reply: str = "",
        action: dict[str, Any] | None = None,
        emotion: str = "",
        source: str = "",
    ) -> None:
        action_payload = deepcopy(action) if isinstance(action, dict) else {"type": "none", "name": ""}
        self.recent_turns.append(
            {
                "at": datetime.now().isoformat(timespec="seconds"),
                "user": _text(user),
                "reply": _text(reply),
                "action": action_payload,
                "emotion": _text(emotion),
                "source": _text(source),
            }
        )

    def record_planner_result(self, user: str, action_result: dict[str, Any] | None) -> None:
        plan = _plan_from_action_like(action_result)
        if not plan:
            return
        memory_update = plan.get("memoryUpdate") if isinstance(plan.get("memoryUpdate"), dict) else {}
        _append_unique(self.session_notes, memory_update.get("session"), limit=self.max_session_notes)
        _append_unique(
            self.long_term_candidates,
            memory_update.get("longTermCandidate"),
            limit=self.max_long_term_candidates,
        )
        self.record_turn(
            user,
            reply=_reply_from_plan(plan),
            action=_action_from_plan(plan),
            emotion=_text(plan.get("emotion")),
            source=_text(action_result.get("source") if isinstance(action_result, dict) else ""),
        )

    def build_runtime_state(self, *, voice_phase: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
        turns = list(self.recent_turns)
        last_turn = turns[-1] if turns else {}
        state: dict[str, Any] = {
            "voicePhase": _text(voice_phase),
            "memory": {
                "recentTurns": turns,
                "sessionNotes": list(self.session_notes),
                "longTermCandidates": list(self.long_term_candidates),
                "lastReply": _text(last_turn.get("reply")),
                "lastAction": deepcopy(last_turn.get("action") or {"type": "none", "name": ""}),
                "lastEmotion": _text(last_turn.get("emotion")),
            },
        }
        if extra:
            state.update(deepcopy(extra))
        return state

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "maxTurns": self.max_turns,
            "maxSessionNotes": self.max_session_notes,
            "maxLongTermCandidates": self.max_long_term_candidates,
            "recentTurns": list(self.recent_turns),
            "sessionNotes": list(self.session_notes),
            "longTermCandidates": list(self.long_term_candidates),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MiraRuntimeMemory":
        memory = cls(
            max_turns=int(payload.get("maxTurns") or 12),
            max_session_notes=int(payload.get("maxSessionNotes") or 12),
            max_long_term_candidates=int(payload.get("maxLongTermCandidates") or 20),
        )
        for turn in payload.get("recentTurns") or []:
            if isinstance(turn, dict):
                memory.recent_turns.append(deepcopy(turn))
        memory.session_notes = [_text(item) for item in payload.get("sessionNotes") or [] if _text(item)]
        memory.long_term_candidates = [
            _text(item) for item in payload.get("longTermCandidates") or [] if _text(item)
        ]
        return memory

    def resize(self, *, max_turns: int | None = None) -> None:
        if max_turns is None:
            return
        resolved_max_turns = max(1, int(max_turns))
        if resolved_max_turns == self.max_turns:
            return
        turns = list(self.recent_turns)[-resolved_max_turns:]
        self.max_turns = resolved_max_turns
        self.recent_turns = deque(turns, maxlen=self.max_turns)

    @classmethod
    def read_json(cls, path: str | Path, *, max_turns: int | None = None) -> "MiraRuntimeMemory":
        source = Path(path)
        if not source.exists():
            return cls(max_turns=max_turns or 12)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(max_turns=max_turns or 12)
        if not isinstance(payload, dict):
            return cls(max_turns=max_turns or 12)
        memory = cls.from_dict(payload)
        memory.resize(max_turns=max_turns)
        return memory

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target
