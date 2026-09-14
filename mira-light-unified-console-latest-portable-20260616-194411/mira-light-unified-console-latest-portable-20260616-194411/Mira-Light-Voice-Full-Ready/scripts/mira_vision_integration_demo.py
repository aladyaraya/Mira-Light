#!/usr/bin/env python3
"""Integration example: wire multimodal vision into Mira Light runtime.

This script demonstrates the three integration patterns:

1. Vision-enriched tracking  — merge VLM scene context into tracking events.
2. Vision-driven actions     — trigger Mira scenes based on what it sees.
3. Vision-aware LLM planning  — feed scene descriptions to the voice planner.

Run:
    # Set your API key first
    set ARK_API_KEY=your_key_here

    # Standalone vision test (camera + VLM only)
    python mira_vision_understanding.py --preview

    # Full integration demo
    python mira_vision_integration_demo.py
"""

from __future__ import annotations

import os
import time
from typing import Any

# These imports assume the script runs from the scripts/ directory.
from person_tracker import PersonTracker
from mira_vision_understanding import (
    VisionUnderstandingEngine,
    VisionAwareTrackingController,
    vision_scene_to_action,
    SceneUnderstanding,
)


# ---------------------------------------------------------------------------
# Pattern 1: Vision-enriched tracking (drop-in replacement for TrackingController)
# ---------------------------------------------------------------------------

def demo_vision_enriched_tracking() -> None:
    """Replace TrackingController with VisionAwareTrackingController.

    The runtime receives the same tracking events as before, but each event
    now includes a 'vision' key with the latest VLM scene understanding.
    The runtime ignores unknown keys, so this is fully backward-compatible.
    """
    from mira_light_runtime import MiraLightRuntime

    runtime = MiraLightRuntime.from_env()
    tracker = PersonTracker(camera_index=0, profile="default")
    engine = VisionUnderstandingEngine(
        frame_provider=tracker.get_latest_frame,
        interval_seconds=3.0,
        skip_when_no_face=False,
    )

    controller = VisionAwareTrackingController(
        runtime=runtime,
        tracker=tracker,
        vision_engine=engine,
        update_interval_ms=120.0,
        on_event=lambda e: print(
            f"[enriched] zone={e['tracking'].get('horizontal_zone')} "
            f"vision={e.get('vision', {}).get('vision_context', {}).get('scene_summary', 'N/A')}"
        ),
    )
    controller.start()
    try:
        time.sleep(60)  # run for 1 minute
    finally:
        controller.stop()


# ---------------------------------------------------------------------------
# Pattern 2: Vision-driven actions (react to what Mira sees)
# ---------------------------------------------------------------------------

def demo_vision_driven_actions() -> None:
    """Trigger Mira scenes based on VLM interaction cues and mood.

    When the VLM detects someone waving, Mira celebrates.
    When it detects someone approaching, Mira gets curious.
    When it detects tiredness, Mira goes to sleep.
    """
    from mira_light_runtime import MiraLightRuntime

    runtime = MiraLightRuntime.from_env()
    tracker = PersonTracker(camera_index=0, profile="default")
    tracker.start()

    last_action_key = ""
    last_action_time = 0.0
    cooldown = 8.0  # seconds between vision-triggered actions

    def on_scene(scene: SceneUnderstanding) -> None:
        nonlocal last_action_key, last_action_time

        action = vision_scene_to_action(scene)
        if action is None:
            return

        action_key = f"{action['type']}:{action['name']}"
        now = time.time()
        if action_key == last_action_key and (now - last_action_time) < cooldown:
            return  # avoid repeating the same action

        print(f"[vision-action] {action_key} <- cue={scene.interaction_cue} mood={scene.mood_suggestion}")
        try:
            if action["type"] == "scene":
                runtime.run_scene(action["name"])
            elif action["type"] == "trigger":
                runtime.fire_trigger(action["name"])
        except Exception as exc:
            print(f"[vision-action] error: {exc}")

        last_action_key = action_key
        last_action_time = now

    engine = VisionUnderstandingEngine(
        frame_provider=tracker.get_latest_frame,
        interval_seconds=3.0,
        on_scene_update=on_scene,
    )
    engine.start()

    try:
        time.sleep(120)
    finally:
        engine.stop()
        tracker.stop()


# ---------------------------------------------------------------------------
# Pattern 3: Vision-aware LLM planning (feed scene context to the planner)
# ---------------------------------------------------------------------------

def build_vision_aware_system_prompt(scene: SceneUnderstanding | None) -> str:
    """Append live vision context to the Mira pet system prompt.

    The existing LLM planner (stepfun_llm_planner.py) uses a fixed system
    prompt. By injecting a short vision context line, the planner's responses
    become aware of what Mira currently sees.
    """
    base_prompt = (
        "你是 Mira，一个刚刚拥有感知的小光宠。"
        "少说话，多用动作；不要长篇解释；不要说自己是 AI。"
    )
    if scene is None:
        return base_prompt

    vision_line = (
        f"\n\n[当前视觉感知] 你现在看到：{scene.scene_summary}。"
        f"画面中有 {scene.person_count} 人，对方似乎在{scene.person_action}，"
        f"情绪状态约为{scene.dominant_emotion}。"
        f"环境：{scene.environment}，光线：{scene.lighting}。"
        f"建议你的情绪倾向：{scene.mood_suggestion}。"
        f"请结合你看到的场景来决定反应。"
    )
    return base_prompt + vision_line


def demo_vision_aware_planning() -> None:
    """Show how the vision context flows into the LLM planner.

    In production, you would modify stepfun_llm_planner.py's
    plan_from_text() to call build_vision_aware_system_prompt() and pass
    the result as the system message. This demo just prints the prompt.
    """
    tracker = PersonTracker(camera_index=0, profile="default")
    tracker.start()

    engine = VisionUnderstandingEngine(
        frame_provider=tracker.get_latest_frame,
        interval_seconds=5.0,
    )
    engine.start()

    try:
        for _ in range(10):
            scene = engine.get_latest_scene()
            prompt = build_vision_aware_system_prompt(scene)
            print(f"\n{'='*60}\n[Vision-aware system prompt]:\n{prompt}\n{'='*60}")
            time.sleep(5.0)
    finally:
        engine.stop()
        tracker.stop()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Mira Light vision integration demo")
    parser.add_argument(
        "--pattern",
        choices=["enriched", "actions", "planning"],
        default="actions",
        help="Integration pattern to demo (default: actions)",
    )
    args = parser.parse_args()

    if not os.environ.get("ARK_API_KEY") and not os.environ.get("MIRA_VISION_API_KEY"):
        print("ERROR: set ARK_API_KEY or MIRA_VISION_API_KEY")
        return 2

    if args.pattern == "enriched":
        demo_vision_enriched_tracking()
    elif args.pattern == "actions":
        demo_vision_driven_actions()
    elif args.pattern == "planning":
        demo_vision_aware_planning()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
