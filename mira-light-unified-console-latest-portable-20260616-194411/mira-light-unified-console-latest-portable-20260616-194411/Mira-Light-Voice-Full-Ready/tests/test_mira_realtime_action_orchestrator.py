from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_realtime_action_orchestrator import (
    RealtimeActionConfig,
    RealtimeActionOrchestrator,
    build_local_fallback_plan,
    build_plan_action_request,
    build_voice_state_request,
    phase_for_realtime_event,
)


class MiraRealtimeActionOrchestratorTest(unittest.TestCase):
    def test_realtime_event_phase_mapping_tracks_listen_think_answer(self) -> None:
        self.assertEqual(phase_for_realtime_event({"type": "input_audio_buffer.speech_started"}), "listening")
        self.assertEqual(phase_for_realtime_event({"type": "input_audio_buffer.speech_stopped"}), "thinking")
        self.assertEqual(phase_for_realtime_event({"type": "response.audio.delta", "delta": "AAAA"}), "answer")
        self.assertEqual(phase_for_realtime_event({"type": "response.done"}), "idle")

    def test_voice_state_requests_use_unified_director_quick_actions(self) -> None:
        request = build_voice_state_request(
            "listening",
            director_url="http://127.0.0.1:8791",
            source="stepfun-realtime",
        )

        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["url"], "http://127.0.0.1:8791/api/quick-action/voice_motion_listening")
        self.assertEqual(request["payload"]["phase"], "listening")
        self.assertEqual(request["payload"]["source"], "stepfun-realtime")

    def test_orchestrator_dispatches_voice_phase_changes_once(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload, "token": token, "timeout": timeout_seconds})
            return {"ok": True}

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(director_url="http://127.0.0.1:8791"),
            post_json=fake_post,
        )

        first = orchestrator.handle_event({"type": "input_audio_buffer.speech_started"})
        duplicate = orchestrator.handle_event({"type": "input_audio_buffer.speech_started"})
        thinking = orchestrator.handle_event({"type": "input_audio_buffer.speech_stopped"})
        answer = orchestrator.handle_event({"type": "response.audio.delta", "delta": "AAAA"})

        self.assertEqual(len(calls), 3)
        self.assertEqual(first[0]["phase"], "listening")
        self.assertEqual(duplicate, [])
        self.assertEqual(thinking[0]["phase"], "thinking")
        self.assertEqual(answer[0]["phase"], "answer")
        self.assertTrue(calls[0]["url"].endswith("/api/quick-action/voice_motion_listening"))
        self.assertTrue(calls[1]["url"].endswith("/api/quick-action/voice_motion_thinking"))
        self.assertTrue(calls[2]["url"].endswith("/api/quick-action/voice_motion_answer"))

    def test_plan_action_request_routes_only_scene_or_trigger_to_bridge(self) -> None:
        scene_plan = {
            "action": {"type": "scene", "name": "voice_demo_tired"},
            "speech": {"shouldSpeak": True, "text": "辛苦了，我陪你缓一下。"},
        }
        trigger_plan = {
            "action": {"type": "trigger", "name": "voice_tired"},
            "speech": {"shouldSpeak": True, "text": "我听见了。"},
        }

        scene_request = build_plan_action_request(scene_plan, bridge_url="http://127.0.0.1:9783", transcript="我今天好累")
        trigger_request = build_plan_action_request(trigger_plan, bridge_url="http://127.0.0.1:9783", transcript="我今天好累")

        self.assertEqual(scene_request["url"], "http://127.0.0.1:9783/v1/mira-light/run-scene")
        self.assertEqual(scene_request["payload"]["scene"], "voice_demo_tired")
        self.assertFalse(scene_request["payload"]["async"])
        self.assertEqual(scene_request["payload"]["context"]["transcript"], "我今天好累")
        self.assertEqual(trigger_request["url"], "http://127.0.0.1:9783/v1/mira-light/trigger")
        self.assertEqual(trigger_request["payload"]["event"], "voice_tired")
        self.assertFalse(trigger_request["payload"]["async"])
        self.assertEqual(trigger_request["payload"]["payload"]["transcript"], "我今天好累")

    def test_transcript_completed_uses_planner_then_dispatches_semantic_action(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "action": {"type": "scene", "name": "voice_demo_tired"},
                    "speech": {"shouldSpeak": True, "text": "辛苦了，我陪你缓一下。"},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(bridge_url="http://127.0.0.1:9783", director_url=""),
            planner=fake_planner,
            post_json=fake_post,
        )

        actions = orchestrator.handle_event(
            {"type": "conversation.item.input_audio_transcription.completed", "transcript": "给我一点回应"}
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], "http://127.0.0.1:9783/v1/mira-light/run-scene")
        self.assertEqual(calls[0]["payload"]["scene"], "voice_demo_tired")
        self.assertFalse(calls[0]["payload"]["async"])
        self.assertEqual(actions[0]["kind"], "semantic-action")
        self.assertEqual(actions[0]["transcript"], "给我一点回应")

    def test_known_tired_transcript_uses_local_soul_plan_and_dispatches_trigger(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fail_if_called(transcript: str, runtime_state: dict | None = None) -> dict:
            raise AssertionError("known comfort intent should not need network planner")

        transcript = "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])
        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(bridge_url="http://127.0.0.1:19783", director_url=""),
            planner=fail_if_called,
            post_json=fake_post,
        )

        actions = orchestrator.handle_event(
            {"type": "conversation.item.input_audio_transcription.completed", "transcript": transcript}
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], "http://127.0.0.1:19783/v1/mira-light/trigger")
        self.assertEqual(calls[0]["payload"]["event"], "voice_tired")
        self.assertFalse(calls[0]["payload"]["async"])
        self.assertEqual(actions[0]["source"], "local-intent")
        self.assertEqual(actions[0]["plan"]["plan"]["action"], {"type": "trigger", "name": "voice_tired"})
        self.assertTrue(actions[0]["plan"]["plan"]["speech"]["shouldSpeak"])
        self.assertTrue(actions[0]["plan"]["plan"]["speech"]["text"])

    def test_affection_transcript_uses_local_action_group_instead_of_semantic_skip(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fail_if_called(transcript: str, runtime_state: dict | None = None) -> dict:
            raise AssertionError("affection intent should be locally routed to an existing scene")

        transcript = "".join(chr(code) for code in [0x6211, 0x5FC3, 0x52A8, 0x4E86])
        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(bridge_url="http://127.0.0.1:19783", director_url=""),
            planner=fail_if_called,
            post_json=fake_post,
        )

        result = orchestrator.dispatch_transcript(transcript)

        self.assertEqual(result["kind"], "semantic-action")
        self.assertEqual(result["source"], "local-intent")
        self.assertEqual(calls[0]["url"], "http://127.0.0.1:19783/v1/mira-light/run-scene")
        self.assertEqual(calls[0]["payload"]["scene"], "touch_affection")

    def test_keep_transcript_uses_presence_scene_instead_of_none_action(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(bridge_url="http://127.0.0.1:19783", director_url=""),
            planner=lambda transcript, runtime_state=None: {"ok": True, "plan": {"action": {"type": "none", "name": ""}}},
            post_json=fake_post,
        )

        result = orchestrator.dispatch_transcript("动作是KEEP，好好说话呀")

        self.assertEqual(result["kind"], "semantic-action")
        self.assertEqual(result["source"], "local-intent")
        self.assertEqual(calls[0]["payload"]["scene"], "cute_probe")

    def test_planner_network_failure_without_local_action_skips_safely(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def failing_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            raise RuntimeError("temporary network failure")

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(bridge_url="http://127.0.0.1:19783", director_url=""),
            planner=failing_planner,
            post_json=fake_post,
        )
        orchestrator.last_transcript = "different"

        result = orchestrator.dispatch_transcript("给我一点回应")

        self.assertEqual(calls, [])
        self.assertEqual(result["kind"], "semantic-skip")
        self.assertEqual(result["reason"], "planner-error")
        self.assertIn("temporary network failure", result["error"])

    def test_local_fallback_plan_contains_soul_reply_for_tired_intent(self) -> None:
        transcript = "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])

        result = build_local_fallback_plan(transcript, reason="unit")

        self.assertTrue(result["ok"])
        self.assertEqual(result["plan"]["action"], {"type": "trigger", "name": "voice_tired"})
        self.assertTrue(result["plan"]["speech"]["shouldSpeak"])
        self.assertTrue(result["plan"]["reply"])

    def test_invalid_or_none_plan_is_not_dispatched(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(bridge_url="http://127.0.0.1:9783", director_url=""),
            planner=lambda transcript, runtime_state=None: {
                "ok": True,
                "plan": {"action": {"type": "none", "name": ""}, "speech": {"shouldSpeak": True, "text": "我在。"}},
                "validation": {"ok": True},
            },
            post_json=fake_post,
        )

        actions = orchestrator.handle_event(
            {"type": "conversation.item.input_audio_transcription.completed", "transcript": "你好"}
        )

        self.assertEqual(actions[0]["kind"], "semantic-skip")
        self.assertEqual(actions[0]["reason"], "none-action")
        self.assertEqual(calls, [])


class TwoPhaseRefinementTest(unittest.TestCase):
    """Tests for the two-phase state machine (local keyword -> LLM refinement)."""

    def test_phase1_local_match_executes_immediately_and_sets_pending(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fail_if_called(transcript: str, runtime_state: dict | None = None) -> dict:
            raise AssertionError("planner must not be called in Phase 1")

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fail_if_called,
            post_json=fake_post,
        )

        transcript = "".join(chr(c) for c in [0x6211, 0x597D, 0x7D2F, 0x554A])  # 我好累啊
        result = orchestrator.dispatch_transcript(transcript)

        self.assertEqual(len(calls), 1)
        self.assertEqual(result["kind"], "semantic-action")
        self.assertEqual(result["source"], "local-intent")
        self.assertTrue(result["pending_refinement"])
        self.assertEqual(result["phase"], 1)
        self.assertTrue(orchestrator.pending_refinement)
        self.assertIsNotNone(orchestrator.pending_refinement_action)

    def test_phase2_llm_confirms_same_action_no_extra_bridge_call(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "action": {"type": "trigger", "name": "voice_tired"},
                    "speech": {"shouldSpeak": True, "text": "辛苦了。"},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )

        transcript = "".join(chr(c) for c in [0x6211, 0x597D, 0x7D2F, 0x554A])
        orchestrator.dispatch_transcript(transcript)
        self.assertEqual(len(calls), 1)  # Phase 1 only

        refinement = orchestrator.refine_transcript(transcript)
        self.assertEqual(refinement["kind"], "semantic-confirm")
        self.assertEqual(len(calls), 1)  # No extra bridge call for confirm
        self.assertFalse(orchestrator.pending_refinement)

    def test_phase2_llm_overrides_different_action_stops_and_starts(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "action": {"type": "scene", "name": "celebrate"},
                    "speech": {"shouldSpeak": True, "text": "开心一下！"},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )

        transcript = "".join(chr(c) for c in [0x6211, 0x597D, 0x7D2F, 0x554A])  # matches comfort -> voice_tired
        orchestrator.dispatch_transcript(transcript)
        self.assertEqual(len(calls), 1)  # Phase 1: trigger voice_tired

        refinement = orchestrator.refine_transcript(transcript)
        self.assertEqual(refinement["kind"], "semantic-override")
        self.assertEqual(refinement["new_action"]["name"], "celebrate")
        # Phase 2: run-scene (preemption is optimistic — only stops on conflict)
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1]["url"].endswith("/v1/mira-light/run-scene"))

    def test_phase2_llm_cancels_with_none_action_stops_scene(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "action": {"type": "none", "name": ""},
                    "speech": {"shouldSpeak": True, "text": "我在。"},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )

        transcript = "".join(chr(c) for c in [0x6211, 0x597D, 0x7D2F, 0x554A])
        orchestrator.dispatch_transcript(transcript)
        self.assertEqual(len(calls), 1)

        refinement = orchestrator.refine_transcript(transcript)
        self.assertEqual(refinement["kind"], "semantic-cancel")
        self.assertEqual(len(calls), 2)  # Phase 1 + stop
        self.assertTrue(calls[1]["url"].endswith("/v1/mira-light/stop"))

    def test_phase1_no_local_match_defers_to_phase2_llm(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "action": {"type": "scene", "name": "voice_demo_tired"},
                    "speech": {"shouldSpeak": True, "text": "辛苦了。"},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )

        result = orchestrator.dispatch_transcript("给我一点回应")
        self.assertEqual(result["kind"], "semantic-skip")
        self.assertEqual(result["reason"], "needs-llm-refinement")
        self.assertEqual(len(calls), 0)  # No action in Phase 1

        refinement = orchestrator.refine_transcript("给我一点回应")
        self.assertEqual(refinement["kind"], "semantic-action")
        self.assertEqual(refinement["source"], "llm-refinement")
        self.assertEqual(len(calls), 1)  # LLM action executed

    def test_phase2_suppresses_low_info_generic_llm_action(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "intent": {"label": "chat", "confidence": 0.4},
                    "action": {"type": "scene", "name": "cute_probe"},
                    "speech": {"shouldSpeak": True, "text": "Hi."},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )

        transcript = "".join(chr(c) for c in [0x4F60, 0x597D])
        result = orchestrator.dispatch_transcript(transcript)
        self.assertEqual(result["reason"], "needs-llm-refinement")

        refinement = orchestrator.refine_transcript(transcript)
        self.assertEqual(refinement["kind"], "semantic-skip")
        self.assertEqual(refinement["reason"], "llm-generic-action-low-info")
        self.assertEqual(calls, [])

    def test_phase2_allows_concrete_llm_action_without_keyword_match(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "intent": {"label": "request_posture", "confidence": 0.82},
                    "action": {"type": "scene", "name": "wake_up"},
                    "speech": {"shouldSpeak": True, "text": "I will lift up."},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )

        result = orchestrator.dispatch_transcript("show me a brighter posture")
        self.assertEqual(result["reason"], "needs-llm-refinement")

        refinement = orchestrator.refine_transcript("show me a brighter posture")
        self.assertEqual(refinement["kind"], "semantic-action")
        self.assertEqual(refinement["source"], "llm-refinement")
        self.assertEqual(refinement["plan"]["action"]["name"], "wake_up")
        self.assertEqual(len(calls), 1)

    def test_phase2_stale_llm_result_does_not_dispatch_after_new_transcript(self) -> None:
        calls: list[dict] = []
        orchestrator_ref: dict[str, RealtimeActionOrchestrator] = {}

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            orchestrator_ref["value"].dispatch_transcript("later ordinary chat")
            return {
                "ok": True,
                "plan": {
                    "intent": {"label": "request_posture", "confidence": 0.9},
                    "action": {"type": "scene", "name": "wake_up"},
                    "speech": {"shouldSpeak": True, "text": "I will lift up."},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )
        orchestrator_ref["value"] = orchestrator

        first = orchestrator.dispatch_transcript("show me a brighter posture")
        self.assertEqual(first["reason"], "needs-llm-refinement")

        refinement = orchestrator.refine_transcript("show me a brighter posture")
        self.assertEqual(refinement["kind"], "semantic-refinement-stale")
        self.assertEqual(refinement["reason"], "newer-transcript-arrived")
        self.assertEqual(calls, [])

    def test_phase2_llm_error_keeps_phase1_action(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def failing_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            raise RuntimeError("network timeout")

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=True,
            ),
            planner=failing_planner,
            post_json=fake_post,
        )

        transcript = "".join(chr(c) for c in [0x6211, 0x597D, 0x7D2F, 0x554A])
        orchestrator.dispatch_transcript(transcript)
        self.assertEqual(len(calls), 1)  # Phase 1 executed

        refinement = orchestrator.refine_transcript(transcript)
        self.assertEqual(refinement["kind"], "semantic-refinement-error")
        self.assertEqual(len(calls), 1)  # No extra calls, Phase 1 action kept

    def test_two_phase_disabled_falls_back_to_classic_behavior(self) -> None:
        calls: list[dict] = []

        def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
            calls.append({"url": url, "payload": payload})
            return {"ok": True}

        def fake_planner(transcript: str, runtime_state: dict | None = None) -> dict:
            return {
                "ok": True,
                "plan": {
                    "action": {"type": "scene", "name": "voice_demo_tired"},
                    "speech": {"shouldSpeak": True, "text": "辛苦了。"},
                },
                "validation": {"ok": True},
            }

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://127.0.0.1:19783",
                director_url="",
                two_phase_refinement_enabled=False,
            ),
            planner=fake_planner,
            post_json=fake_post,
        )

        # No local match -> goes to LLM directly (classic behavior)
        result = orchestrator.dispatch_transcript("给我一点回应")
        self.assertEqual(result["kind"], "semantic-action")
        self.assertEqual(len(calls), 1)

        # refine_transcript should return None when two-phase is disabled
        refinement = orchestrator.refine_transcript("给我一点回应")
        self.assertIsNone(refinement)


if __name__ == "__main__":
    unittest.main()
