#!/usr/bin/env python3
"""Vision context bridge for Mira Light planner and orchestrator.

This module is the single integration point between the multimodal vision
understanding engine (mira_vision_understanding.py) and the rest of the
Mira Light stack (planner, orchestrator, voice entry points).

It provides:
- A process-wide singleton vision engine that any module can read from.
- Helper functions that format scene understanding into prompt fragments
  and runtime_state fields, so the planner and orchestrator can become
  vision-aware with minimal code changes.
- Graceful degradation: if the vision engine is not started or no scene
  is available yet, all helpers return empty/neutral values and the rest
  of the system behaves exactly as before.

Design goal: zero-config backward compatibility. If MIRA_VISION_ENABLED=0
or no API key is set, this module is a no-op.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Callable

from mira_vision_understanding import (
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_MAX_IMAGE_WIDTH,
    DEFAULT_TIMEOUT_SECONDS,
    SceneUnderstanding,
    VisionUnderstandingEngine,
)


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------

_engine: VisionUnderstandingEngine | None = None
_engine_lock = threading.Lock()
_frame_provider: Callable[[], Any] | None = None


def set_frame_provider(provider: Callable[[], Any]) -> None:
    """Register the camera frame provider (typically PersonTracker.get_latest_frame).

    Must be called before get_vision_engine() so the engine can be created
    with the correct frame source.
    """
    global _frame_provider
    _frame_provider = provider


def get_vision_engine() -> VisionUnderstandingEngine | None:
    """Return the process-wide vision engine, creating it on first call.

    Returns None if vision is disabled or no frame provider is set.
    """
    global _engine
    if os.environ.get("MIRA_VISION_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None
    with _engine_lock:
        if _engine is not None:
            return _engine
        if _frame_provider is None:
            return None
        api_key = (
            os.environ.get("MIRA_VISION_API_KEY")
            or os.environ.get("ARK_API_KEY")
            or ""
        )
        if not api_key:
            return None
        _engine = VisionUnderstandingEngine(
            frame_provider=_frame_provider,
            api_key=api_key,
            endpoint=os.environ.get("MIRA_VISION_ENDPOINT") or None,
            model=os.environ.get("MIRA_VISION_MODEL") or None,
            interval_seconds=float(
                os.environ.get("MIRA_VISION_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
            ),
            max_image_width=int(
                os.environ.get("MIRA_VISION_MAX_IMAGE_WIDTH", str(DEFAULT_MAX_IMAGE_WIDTH))
            ),
            timeout_seconds=int(
                os.environ.get("MIRA_VISION_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
            ),
        )
        return _engine


def start_vision_engine() -> VisionUnderstandingEngine | None:
    """Convenience: get the engine and start it. Safe to call multiple times."""
    engine = get_vision_engine()
    if engine is not None and not engine.is_running():
        engine.start()
    return engine


def stop_vision_engine() -> None:
    """Stop the process-wide vision engine if it is running."""
    global _engine
    with _engine_lock:
        if _engine is not None and _engine.is_running():
            _engine.stop()


def get_latest_scene() -> SceneUnderstanding | None:
    """Return the latest scene understanding, or None if unavailable."""
    engine = get_vision_engine()
    if engine is None:
        return None
    return engine.get_latest_scene()


# ---------------------------------------------------------------------------
# Prompt / runtime_state injection helpers
# ---------------------------------------------------------------------------

def vision_prompt_fragment(scene: SceneUnderstanding | None = None) -> str:
    """Build a short vision context string for the LLM system prompt.

    Returns an empty string if no scene is available, so the caller can
    unconditionally append it without checking.
    """
    scene = scene if scene is not None else get_latest_scene()
    if scene is None:
        return ""
    return (
        f"\n\n[当前视觉感知] 你现在看到：{scene.scene_summary}。"
        f"画面中有 {scene.person_count} 人，对方似乎在{scene.person_action}，"
        f"情绪状态约为{scene.dominant_emotion}。"
        f"环境：{scene.environment}，光线：{scene.lighting}。"
        f"互动信号：{scene.interaction_cue}。"
        f"建议你的情绪倾向：{scene.mood_suggestion}。"
        f"请结合你看到的场景来决定反应。如果对方在挥手或靠近，可以更主动地回应。"
    )


def vision_runtime_state_fragment(scene: SceneUnderstanding | None = None) -> dict[str, Any]:
    """Build a vision context dict for the planner's runtime_state field.

    Returns an empty dict if no scene is available.
    """
    scene = scene if scene is not None else get_latest_scene()
    if scene is None:
        return {}
    return {
        "vision": {
            "scene_summary": scene.scene_summary,
            "person_count": scene.person_count,
            "emotion": scene.dominant_emotion,
            "action": scene.person_action,
            "interaction_cue": scene.interaction_cue,
            "mood_suggestion": scene.mood_suggestion,
            "objects": scene.objects,
            "environment": scene.environment,
            "lighting": scene.lighting,
            "confidence": round(scene.confidence, 3),
        }
    }


def vision_transcript_prefix(transcript: str, scene: SceneUnderstanding | None = None) -> str:
    """Optionally prefix the user transcript with a vision hint.

    This is used when the planner does not support runtime_state injection
    (e.g. the local shortcut path). It keeps the transcript readable while
    giving the LLM a hint about what Mira currently sees.
    """
    scene = scene if scene is not None else get_latest_scene()
    if scene is None or not scene.scene_summary:
        return transcript
    return f"[视觉: {scene.scene_summary[:40]}] {transcript}"
