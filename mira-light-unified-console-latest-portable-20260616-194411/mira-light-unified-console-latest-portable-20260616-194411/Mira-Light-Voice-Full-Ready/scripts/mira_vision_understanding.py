#!/usr/bin/env python3
"""Multimodal vision understanding for Mira Light.

This module adds a *semantic* vision layer on top of the existing fast
OpenCV face tracker. Instead of only knowing "a face is at position X",
Mira can now understand what it sees: objects, people count, emotions,
gestures, environment, and scene context.

Architecture (two-tier vision):

    Tier 1 (existing, fast):  Camera -> OpenCV face detect -> servo tracking
                               ~15 fps, ~50ms latency, real-time control

    Tier 2 (new, semantic):   Camera -> VLM API (Doubao Vision) -> scene JSON
                               ~0.2-0.5 fps, ~1-3s latency, context awareness

The two tiers run in parallel. Tier 1 keeps the servo loop smooth; Tier 2
feeds rich scene descriptions into the LLM planner and action orchestrator
so Mira's behaviour becomes context-aware.

Usage:

    from person_tracker import PersonTracker
    from mira_vision_understanding import VisionUnderstandingEngine

    tracker = PersonTracker(camera_index=0)
    engine = VisionUnderstandingEngine(
        frame_provider=tracker.get_latest_frame,
        api_key=os.environ["ARK_API_KEY"],
    )
    tracker.start()
    engine.start()

    # ... later, anywhere in the planner / orchestrator:
    scene = engine.get_latest_scene()
    if scene and scene["person_count"] >= 2:
        runtime.run_scene("celebrate")

Environment variables:

    MIRA_VISION_API_KEY          API key (defaults to ARK_API_KEY)
    MIRA_VISION_ENDPOINT          OpenAI-compatible chat completions URL
    MIRA_VISION_MODEL             VLM model name
    MIRA_VISION_INTERVAL_SECONDS  How often to analyse a frame (default 3.0)
    MIRA_VISION_MAX_IMAGE_WIDTH   Resize before upload to control cost (default 768)
    MIRA_VISION_TIMEOUT_SECONDS   API call timeout (default 20)
    MIRA_VISION_ENABLED           Set to 0 to disable (default 1)
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DEFAULT_MODEL = "doubao-1.5-vision-pro-32k"
DEFAULT_INTERVAL_SECONDS = 3.0
DEFAULT_MAX_IMAGE_WIDTH = 768
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_JPEG_QUALITY = 75

# The system prompt asks the VLM to return strict JSON. This keeps the output
# parseable and cheap (short response). The schema is deliberately compact.
SCENE_ANALYSIS_PROMPT = """你是一个为桌面陪伴机器人 Mira 提供视觉理解的助手。
请分析这张摄像头画面，用简洁的 JSON 回答，不要输出 JSON 以外的内容。

JSON 格式如下：
{
  "scene_summary": "一句话描述当前场景",
  "person_count": 0,
  "dominant_emotion": "neutral|happy|sad|surprised|angry|focused|tired",
  "person_action": "描述主要人物在做什么，如坐着、站着、挥手、看手机、工作、喝水",
  "objects": ["画面中可见的关键物品，最多5个"],
  "environment": "indoor|outdoor|office|home|cafe|other",
  "lighting": "bright|normal|dim|dark",
  "interaction_cue": "none|waving|approaching|leaving|touching_screen|holding_object|looking_at_camera",
  "mood_suggestion": "建议 Mira 的情绪反应，如好奇、开心、害羞、警觉、困倦",
  "confidence": 0.0
}

规则：
- person_count 为画面中可见的人数。
- 如果没有人，person_action 填 "none"，dominant_emotion 填 "neutral"。
- interaction_cue 用于判断人是否在和 Mira 互动。
- confidence 是你对整体判断的把握 (0.0-1.0)。
- 只输出 JSON，不要解释。"""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SceneUnderstanding:
    """Structured result of a single VLM scene analysis."""
    scene_summary: str = ""
    person_count: int = 0
    dominant_emotion: str = "neutral"
    person_action: str = "none"
    objects: list[str] = field(default_factory=list)
    environment: str = "indoor"
    lighting: str = "normal"
    interaction_cue: str = "none"
    mood_suggestion: str = "neutral"
    confidence: float = 0.0
    timestamp: float = 0.0
    raw_response: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_summary": self.scene_summary,
            "person_count": self.person_count,
            "dominant_emotion": self.dominant_emotion,
            "person_action": self.person_action,
            "objects": self.objects,
            "environment": self.environment,
            "lighting": self.lighting,
            "interaction_cue": self.interaction_cue,
            "mood_suggestion": self.mood_suggestion,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
        }

    def to_tracking_context(self) -> dict[str, Any]:
        """Convert to a context dict that can be merged into tracking events."""
        return {
            "vision_context": {
                "scene_summary": self.scene_summary,
                "person_count": self.person_count,
                "emotion": self.dominant_emotion,
                "action": self.person_action,
                "interaction_cue": self.interaction_cue,
                "mood_suggestion": self.mood_suggestion,
                "objects": self.objects,
                "environment": self.environment,
                "lighting": self.lighting,
                "confidence": round(self.confidence, 3),
            }
        }


# ---------------------------------------------------------------------------
# Image encoding
# ---------------------------------------------------------------------------

def encode_frame_to_data_uri(
    frame: np.ndarray,
    *,
    max_width: int = DEFAULT_MAX_IMAGE_WIDTH,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
) -> str:
    """Encode an OpenCV BGR frame as a JPEG data URI for the VLM API.

    The frame is resized so its width does not exceed *max_width*, which
    keeps upload size and API token cost under control.
    """
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / w
        new_size = (max_width, max(1, int(h * scale)))
        frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG")
    encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


# ---------------------------------------------------------------------------
# VLM API client
# ---------------------------------------------------------------------------

class VLMClient:
    """OpenAI-compatible vision-language model client.

    Works with:
    - Volces Ark (Doubao Vision):  https://ark.cn-beijing.volces.com/api/v3/chat/completions
    - StepFun (step-1v):           https://api.stepfun.com/v1/chat/completions
    - Any OpenAI-compatible endpoint that accepts image_url content parts.
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout

    def analyze_frame(self, frame: np.ndarray, prompt: str = SCENE_ANALYSIS_PROMPT) -> dict[str, Any]:
        """Send a frame to the VLM and return the parsed JSON scene description."""
        data_uri = encode_frame_to_data_uri(frame)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请分析这张画面。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                    ],
                },
            ],
            "max_tokens": 512,
            "temperature": 0.3,
        }

        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"VLM request failed ({exc.code}): {error_body}") from exc

        content = body["choices"][0]["message"]["content"]
        return self._extract_json(content)

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any]:
        """Extract a JSON object from the model response, tolerating markdown fences."""
        text = content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            text = "\n".join(lines).strip()
        # Find the first { and last } to extract the JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {"scene_summary": content, "confidence": 0.0}
        return json.loads(text[start : end + 1])


# ---------------------------------------------------------------------------
# VisionUnderstandingEngine
# ---------------------------------------------------------------------------

class VisionUnderstandingEngine:
    """Background engine that periodically analyses camera frames with a VLM.

    Design principles:
    - Non-blocking: runs in its own daemon thread.
    - Cost-controlled: analyses at most one frame per *interval_seconds*.
    - Skip-aware: can skip analysis when no face is detected (optional).
    - Graceful degradation: if the API fails, the last good result is kept.
    """

    def __init__(
        self,
        frame_provider: Callable[[], np.ndarray | None],
        *,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        interval_seconds: float | None = None,
        max_image_width: int = DEFAULT_MAX_IMAGE_WIDTH,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        skip_when_no_face: bool = False,
        face_check: Callable[[], bool] | None = None,
        on_scene_update: Callable[[SceneUnderstanding], None] | None = None,
    ) -> None:
        """Args:
            frame_provider: Callable that returns the latest camera frame (BGR ndarray)
                            or None if no frame is available. Typically
                            PersonTracker.get_latest_frame.
            api_key: VLM API key. Defaults to env MIRA_VISION_API_KEY or ARK_API_KEY.
            endpoint: OpenAI-compatible chat completions URL.
            model: VLM model name.
            interval_seconds: Minimum time between VLM calls (cost control).
            max_image_width: Resize frames before upload to limit token cost.
            timeout_seconds: Per-request timeout.
            skip_when_no_face: If True, skip VLM calls when no face is detected.
            face_check: Optional callable returning True if a face is present.
            on_scene_update: Callback invoked whenever a new scene analysis completes.
        """
        self.frame_provider = frame_provider
        self.api_key = (
            api_key
            or os.environ.get("MIRA_VISION_API_KEY")
            or os.environ.get("ARK_API_KEY")
            or ""
        )
        self.endpoint = endpoint or os.environ.get("MIRA_VISION_ENDPOINT", DEFAULT_ENDPOINT)
        self.model = model or os.environ.get("MIRA_VISION_MODEL", DEFAULT_MODEL)
        self.interval_seconds = interval_seconds or float(
            os.environ.get("MIRA_VISION_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
        )
        self.max_image_width = max_image_width
        self.timeout_seconds = timeout_seconds
        self.skip_when_no_face = skip_when_no_face
        self.face_check = face_check
        self.on_scene_update = on_scene_update

        self._client: VLMClient | None = None
        self._latest_scene: SceneUnderstanding | None = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._call_count = 0
        self._error_count = 0
        self._last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return os.environ.get("MIRA_VISION_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}

    def start(self) -> None:
        if self._running:
            return
        if not self.enabled:
            print("[vision] disabled by MIRA_VISION_ENABLED=0")
            return
        if not self.api_key:
            print("[vision] WARNING: no API key set (MIRA_VISION_API_KEY or ARK_API_KEY). Engine will start but calls will fail.")
        self._client = VLMClient(
            api_key=self.api_key,
            endpoint=self.endpoint,
            model=self.model,
            timeout=self.timeout_seconds,
        )
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(
            f"[vision] started: model={self.model} interval={self.interval_seconds}s "
            f"max_width={self.max_image_width}px"
        )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        print("[vision] stopped")

    def is_running(self) -> bool:
        return self._running

    def get_latest_scene(self) -> SceneUnderstanding | None:
        with self._lock:
            return self._latest_scene

    def get_stats(self) -> dict[str, Any]:
        return {
            "calls": self._call_count,
            "errors": self._error_count,
            "last_error": self._last_error,
            "running": self._running,
        }

    def analyze_once(self) -> SceneUnderstanding | None:
        """Perform a single VLM analysis on the latest frame (blocking)."""
        frame = self.frame_provider()
        if frame is None:
            return None
        if self.skip_when_no_face and self.face_check and not self.face_check():
            return None
        if self._client is None:
            return None
        try:
            result = self._client.analyze_frame(frame)
            scene = self._parse_scene(result)
            with self._lock:
                self._latest_scene = scene
            self._call_count += 1
            if self.on_scene_update:
                self.on_scene_update(scene)
            return scene
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            print(f"[vision] analysis error: {exc}")
            return None

    def _loop(self) -> None:
        while self._running:
            self.analyze_once()
            # Sleep in small increments so stop() is responsive
            slept = 0.0
            while slept < self.interval_seconds and self._running:
                time.sleep(0.2)
                slept += 0.2

    @staticmethod
    def _parse_scene(raw: dict[str, Any]) -> SceneUnderstanding:
        """Parse the VLM JSON response into a SceneUnderstanding dataclass."""
        return SceneUnderstanding(
            scene_summary=str(raw.get("scene_summary", "")),
            person_count=int(raw.get("person_count", 0)),
            dominant_emotion=str(raw.get("dominant_emotion", "neutral")),
            person_action=str(raw.get("person_action", "none")),
            objects=list(raw.get("objects", [])),
            environment=str(raw.get("environment", "indoor")),
            lighting=str(raw.get("lighting", "normal")),
            interaction_cue=str(raw.get("interaction_cue", "none")),
            mood_suggestion=str(raw.get("mood_suggestion", "neutral")),
            confidence=float(raw.get("confidence", 0.0)),
            timestamp=time.time(),
            raw_response=raw,
        )


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

class VisionAwareTrackingController:
    """Wraps the existing TrackingController to enrich events with vision context.

    This is a drop-in enhancement: it reads tracking events from PersonTracker
    and merges the latest VLM scene understanding into each event before
    forwarding to the runtime. The runtime's apply_tracking_event() ignores
    unknown keys, so this is fully backward-compatible.
    """

    def __init__(
        self,
        runtime: Any,
        tracker: Any,  # PersonTracker
        vision_engine: VisionUnderstandingEngine,
        *,
        update_interval_ms: float = 120.0,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.runtime = runtime
        self.tracker = tracker
        self.vision_engine = vision_engine
        self.update_interval_ms = update_interval_ms
        self.on_event = on_event
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._running:
            return
        self.tracker.start()
        self.vision_engine.start()
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()
        print("[vision-tracking] started (face tracking + VLM scene understanding)")

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        self.vision_engine.stop()
        self.tracker.stop()
        print("[vision-tracking] stopped")

    def _control_loop(self) -> None:
        while not self._stop_event.is_set():
            event = self.tracker.get_latest_event()
            if event is not None:
                # Enrich the tracking event with VLM scene context
                scene = self.vision_engine.get_latest_scene()
                if scene is not None:
                    event["vision"] = scene.to_tracking_context()
                try:
                    self.runtime.apply_tracking_event(event, source="vision")
                    if self.on_event:
                        self.on_event(event)
                except Exception as exc:
                    print(f"[vision-tracking] error: {exc}")
            self._stop_event.wait(self.update_interval_ms / 1000.0)


# ---------------------------------------------------------------------------
# Scene-to-action mapping
# ---------------------------------------------------------------------------

# Maps VLM interaction cues and mood suggestions to Mira scenes/triggers.
# This lets Mira react to what it *understands*, not just face position.
VISION_ACTION_MAP: dict[str, dict[str, str]] = {
    # interaction_cue -> Mira action
    "waving": {"type": "scene", "name": "celebrate"},
    "approaching": {"type": "scene", "name": "curious_observe"},
    "leaving": {"type": "scene", "name": "farewell"},
    "touching_screen": {"type": "scene", "name": "touch_affection"},
    "holding_object": {"type": "scene", "name": "curious_observe"},
    "looking_at_camera": {"type": "scene", "name": "cute_probe"},
    # mood_suggestion -> Mira action
    "mood:curious": {"type": "scene", "name": "curious_observe"},
    "mood:happy": {"type": "scene", "name": "celebrate"},
    "mood:shy": {"type": "scene", "name": "cute_probe"},
    "mood:alert": {"type": "scene", "name": "curious_observe"},
    "mood:tired": {"type": "scene", "name": "sleep"},
}


def vision_scene_to_action(scene: SceneUnderstanding) -> dict[str, str] | None:
    """Map a VLM scene understanding to a Mira action, or None if no action.

    Priority: interaction_cue > mood_suggestion.
    """
    cue = scene.interaction_cue
    if cue and cue != "none" and cue in VISION_ACTION_MAP:
        return VISION_ACTION_MAP[cue]
    mood_key = f"mood:{scene.mood_suggestion}"
    if mood_key in VISION_ACTION_MAP:
        return VISION_ACTION_MAP[mood_key]
    return None


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Mira Light multimodal vision understanding")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--api-key", default=os.environ.get("ARK_API_KEY", ""))
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--max-width", type=int, default=DEFAULT_MAX_IMAGE_WIDTH)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)

    if not args.api_key:
        print("ERROR: set ARK_API_KEY or pass --api-key")
        return 2

    # Import here to avoid circular dependency in standalone mode
    from person_tracker import PersonTracker

    tracker = PersonTracker(camera_index=args.camera, profile="default")
    tracker.start()

    engine = VisionUnderstandingEngine(
        frame_provider=tracker.get_latest_frame,
        api_key=args.api_key,
        endpoint=args.endpoint,
        model=args.model,
        interval_seconds=args.interval,
        max_image_width=args.max_width,
        on_scene_update=lambda s: print(
            f"\n[scene] {s.scene_summary} | "
            f"people={s.person_count} emotion={s.dominant_emotion} "
            f"action={s.person_action} cue={s.interaction_cue} "
            f"mood={s.mood_suggestion} conf={s.confidence:.2f}"
        ),
    )
    engine.start()

    try:
        while True:
            scene = engine.get_latest_scene()
            if scene:
                action = vision_scene_to_action(scene)
                if action:
                    print(f"  -> suggested action: {action}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        tracker.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
