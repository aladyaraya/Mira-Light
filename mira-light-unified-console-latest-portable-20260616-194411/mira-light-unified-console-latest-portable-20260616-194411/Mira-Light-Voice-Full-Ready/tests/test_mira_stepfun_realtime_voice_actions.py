from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_stepfun_realtime_voice_actions import (
    DEFAULT_INPUT_SAMPLE_RATE,
    DEFAULT_OUTPUT_SAMPLE_RATE,
    DEFAULT_WEBSOCKET_PING_INTERVAL,
    DEFAULT_WEBSOCKET_PING_TIMEOUT,
    action_console_summary,
    build_semantic_planner,
    build_websocket_connect_kwargs,
    build_live_session_preview,
    decode_audio_delta,
    display_update_for_event,
    planner_reply_text_from_action,
    planner_playback_enabled,
    parse_args,
    pcm16_bytes_from_float32,
    realtime_playback_enabled,
    should_speak_planner_reply_action,
    should_run_phase2_refinement,
    validate_audio_routing,
)
from mira_runtime_memory import MiraRuntimeMemory


class MiraStepFunRealtimeVoiceActionsTest(unittest.TestCase):
    def test_parse_args_uses_windows_mic_device_env_as_realtime_fallback(self) -> None:
        with patch.dict("os.environ", {"MIRA_LIGHT_WINDOWS_MIC_DEVICE": "Unit Test Mic"}, clear=True):
            args = parse_args(["--dry-run"])

        self.assertEqual(args.input_device, "Unit Test Mic")

    def test_pcm16_bytes_from_float32_clamps_and_serializes_mono_audio(self) -> None:
        pcm = pcm16_bytes_from_float32([-2.0, -1.0, 0.0, 0.5, 2.0])

        self.assertEqual(len(pcm), 10)
        self.assertEqual(int.from_bytes(pcm[0:2], "little", signed=True), -32767)
        self.assertEqual(int.from_bytes(pcm[2:4], "little", signed=True), -32767)
        self.assertEqual(int.from_bytes(pcm[4:6], "little", signed=True), 0)
        self.assertEqual(int.from_bytes(pcm[6:8], "little", signed=True), 16383)
        self.assertEqual(int.from_bytes(pcm[8:10], "little", signed=True), 32767)

    def test_decode_audio_delta_returns_pcm_bytes_only_for_audio_delta_events(self) -> None:
        self.assertEqual(decode_audio_delta({"type": "response.audio.delta", "delta": "AQACAA=="}), b"\x01\x00\x02\x00")
        self.assertEqual(decode_audio_delta({"type": "response.text.delta", "delta": "hi"}), b"")

    def test_display_update_for_event_extracts_user_and_assistant_text(self) -> None:
        user_event = {"type": "conversation.item.input_audio_transcription.completed", "transcript": "我今天好累"}
        assistant_part_event = {
            "type": "response.content_part.done",
            "part": {"type": "audio", "transcript": "辛苦了，我陪你缓一下。"},
        }
        assistant_item_event = {
            "type": "response.output_item.done",
            "item": {
                "content": [
                    {"type": "audio", "transcript": "我在这里。"},
                ]
            },
        }

        self.assertEqual(display_update_for_event(user_event), {"role": "user", "text": "我今天好累"})
        self.assertEqual(display_update_for_event(assistant_part_event), {"role": "assistant", "text": "辛苦了，我陪你缓一下。"})
        self.assertEqual(display_update_for_event(assistant_item_event), {"role": "assistant", "text": "我在这里。"})

    def test_planner_reply_text_from_action_extracts_short_speech_output(self) -> None:
        action = {
            "kind": "semantic-action",
            "plan": {
                "speech": {"shouldSpeak": True, "text": "Rest a little. I will stay close."},
                "action": {"type": "scene", "name": "voice_demo_tired"},
            },
        }

        self.assertEqual(
            planner_reply_text_from_action(action),
            "Rest a little. I will stay close.",
        )

    def test_planner_reply_text_from_action_accepts_legacy_reply_shape(self) -> None:
        action = {
            "kind": "semantic-skip",
            "reason": "none-action",
            "plan": {
                "reply": "I hear you. That sounds important.",
                "action": {"type": "none"},
            },
        }

        self.assertEqual(
            planner_reply_text_from_action(action),
            "I hear you. That sounds important.",
        )
        self.assertEqual(planner_reply_text_from_action({"kind": "semantic-skip", "plan": {}}), "")

    def test_planner_reply_text_from_action_unwraps_local_plan_result(self) -> None:
        action = {
            "kind": "semantic-action",
            "source": "local-intent",
            "plan": {
                "ok": True,
                "plan": {
                    "speech": {"shouldSpeak": True, "text": "I am here. Lean on me first."},
                    "action": {"type": "trigger", "name": "voice_tired"},
                },
            },
        }

        self.assertEqual(
            planner_reply_text_from_action(action),
            "I am here. Lean on me first.",
        )

    def test_planner_reply_text_from_action_reads_semantic_confirm_plan(self) -> None:
        action = {
            "kind": "semantic-confirm",
            "confirmed_action": {"type": "scene", "name": "celebrate"},
            "plan": {
                "speech": {"shouldSpeak": True, "text": "Good morning. I will dance now."},
                "action": {"type": "scene", "name": "celebrate"},
            },
        }

        self.assertEqual(
            planner_reply_text_from_action(action),
            "Good morning. I will dance now.",
        )

    def test_action_console_summary_includes_action_reason_and_bridge_error(self) -> None:
        summary = action_console_summary(
            {
                "kind": "semantic-action",
                "source": "local-intent",
                "plan": {"action": {"type": "scene", "name": "celebrate"}},
                "response": {"ok": False, "error": "ConnectionRefusedError: board refused 192.168.0.183:9527"},
            },
            "dance",
        )

        self.assertIn("scene=celebrate", summary)
        self.assertIn("source=local-intent", summary)
        self.assertIn("ok=false", summary)
        self.assertIn("ConnectionRefusedError", summary)

    def test_action_console_summary_exposes_cooldown_skip_reason(self) -> None:
        summary = action_console_summary(
            {
                "kind": "semantic-skip",
                "reason": "cooldown: duplicate-action 'celebrate' (3.7s < 5.0s)",
                "plan": {"plan": {"action": {"type": "scene", "name": "celebrate"}}},
            },
            "dance again",
        )

        self.assertIn("semantic-skip", summary)
        self.assertIn("scene=celebrate", summary)
        self.assertIn("duplicate-action", summary)

    def test_live_session_preview_redacts_key_and_shows_parallel_action_layers(self) -> None:
        args = argparse.Namespace(
            endpoint="wss://api.stepfun.com/v1/realtime",
            model="stepaudio-2.5-realtime",
            voice="wenrounansheng",
            proxy_url="socks5h://127.0.0.1:10808",
            websocket_ping_interval=20,
            websocket_ping_timeout=10,
            input_device="default",
            input_sample_rate=24000,
            output_sample_rate=24000,
            chunk_ms=40,
            bridge_url="http://127.0.0.1:9783",
            director_url="",
            no_voice_state_actions=False,
            no_semantic_actions=False,
            no_play=False,
            seconds=30.0,
            speak_planner_reply=True,
            planner_reply_voice="tts",
            planner_reply_wait=False,
            assistant_text_actions=False,
            llm_actions_for_ambiguous=True,
            planner_provider="deepseek",
            planner_model="deepseek-v4-flash",
        )

        preview = build_live_session_preview(args)

        self.assertEqual(preview["connection"]["headers"]["Authorization"], "Bearer <STEPFUN_API_KEY>")
        self.assertEqual(preview["connection"]["proxy"], "socks5h://127.0.0.1:10808")
        self.assertEqual(preview["connection"]["websocket"], {"pingInterval": 20.0, "pingTimeout": 10.0})
        self.assertEqual(preview["audio"]["inputSampleRate"], 24000)
        self.assertEqual(preview["audio"]["outputSampleRate"], 24000)
        self.assertFalse(preview["actions"]["voiceStateActions"])
        self.assertTrue(preview["actions"]["semanticActions"])
        self.assertEqual(preview["actions"]["directorUrl"], "")
        self.assertEqual(preview["actions"]["bridgeUrl"], "http://127.0.0.1:9783")
        self.assertFalse(preview["actions"]["assistantTextActions"])
        self.assertTrue(preview["actions"]["llmActionsForAmbiguous"])
        self.assertEqual(preview["actions"]["plannerProvider"], "deepseek")
        self.assertEqual(preview["actions"]["plannerModel"], "deepseek-v4-flash")
        self.assertEqual(
            preview["actions"]["plannerReply"],
            {"enabled": True, "voice": "tts", "wait": False, "playback": True, "ownsReply": False},
        )
        self.assertIn("session.update", [event["type"] for event in preview["events"]])

    def test_parse_args_accepts_legacy_full_mode_flags(self) -> None:
        args = parse_args(
            [
                "--mode",
                "enter-vad",
                "--device",
                "Windows Mic",
                "--profile",
                "fast",
                "--latency-preset",
                "low",
                "--vad-start-ms",
                "80",
                "--vad-end-ms",
                "1200",
                "--no-startup-warmup",
                "--no-trigger",
                "--dry-run-audio",
                "--speak-planner-reply",
                "--planner-reply-voice",
                "say",
                "--planner-reply-wait",
                "--dry-run",
            ]
        )

        self.assertEqual(args.mode, "enter-vad")
        self.assertEqual(args.input_device, "Windows Mic")
        self.assertTrue(args.no_semantic_actions)
        self.assertTrue(args.no_play)
        self.assertTrue(args.speak_planner_reply)
        self.assertEqual(args.planner_reply_voice, "say")
        self.assertTrue(args.planner_reply_wait)
        self.assertFalse(args.assistant_text_actions)

    def test_realtime_and_planner_playback_can_be_controlled_independently(self) -> None:
        args = parse_args(["--dry-run", "--speak-planner-reply", "--no-realtime-playback"])

        self.assertFalse(realtime_playback_enabled(args))
        self.assertTrue(planner_playback_enabled(args))

        muted = parse_args(["--dry-run", "--no-play", "--speak-planner-reply"])
        self.assertFalse(realtime_playback_enabled(muted))
        self.assertFalse(planner_playback_enabled(muted))

    def test_default_planner_provider_uses_stepfun(self) -> None:
        args = parse_args(["--dry-run"])

        self.assertEqual(args.planner_provider, "stepfun")
        self.assertEqual(args.planner_model, "step-3.7-flash")

    def test_audio_routing_rejects_dual_realtime_and_planner_playback(self) -> None:
        args = parse_args(["--dry-run", "--speak-planner-reply", "--planner-playback"])

        with self.assertRaisesRegex(RuntimeError, "Audio routing conflict"):
            validate_audio_routing(args)

    def test_planner_owns_reply_disables_realtime_playback_but_keeps_planner_playback(self) -> None:
        args = parse_args(["--dry-run", "--speak-planner-reply", "--planner-owns-reply"])

        self.assertFalse(realtime_playback_enabled(args))
        self.assertTrue(planner_playback_enabled(args))
        validate_audio_routing(args)
        preview = build_live_session_preview(args)
        self.assertTrue(preview["audio"]["plannerOwnsReply"])
        self.assertTrue(preview["actions"]["plannerReply"]["ownsReply"])

    def test_should_speak_planner_reply_includes_none_action_reply(self) -> None:
        none_action = {
            "kind": "semantic-skip",
            "reason": "none-action",
            "plan": {
                "speech": {"shouldSpeak": True, "text": "我听见啦，慢慢说。"},
                "action": {"type": "none", "name": ""},
            },
        }
        stale = {
            "kind": "semantic-refinement-stale",
            "plan": {"speech": {"shouldSpeak": True, "text": "旧回复"}},
        }

        self.assertTrue(should_speak_planner_reply_action(none_action))
        self.assertFalse(should_speak_planner_reply_action(stale))

    def test_parse_args_accepts_hermes_provider_and_removes_deepseek_defaults(self) -> None:
        args = parse_args(["--dry-run", "--planner-provider", "hermes"])

        self.assertEqual(args.planner_provider, "hermes")
        self.assertEqual(args.planner_endpoint, "")
        self.assertEqual(args.planner_model, "hermes-agent")

    def test_llm_actions_for_ambiguous_are_enabled_by_default_and_can_be_disabled(self) -> None:
        args = parse_args(["--dry-run"])
        self.assertTrue(args.llm_actions_for_ambiguous)

        disabled = parse_args(["--dry-run", "--no-llm-actions-for-ambiguous"])
        self.assertFalse(disabled.llm_actions_for_ambiguous)

    def test_phase2_refinement_only_runs_for_unmatched_phase1_transcripts(self) -> None:
        local_action = {
            "kind": "semantic-action",
            "source": "local-intent",
            "plan": {"action": {"type": "scene", "name": "look_left"}},
        }
        unmatched = {"kind": "semantic-skip", "reason": "needs-llm-refinement"}

        self.assertFalse(should_run_phase2_refinement(local_action))
        self.assertTrue(should_run_phase2_refinement(unmatched))
        self.assertFalse(should_run_phase2_refinement(unmatched, llm_actions_for_ambiguous=False))

    def test_websocket_connect_kwargs_can_disable_client_keepalive_for_proxy_sessions(self) -> None:
        args = parse_args(
            [
                "--proxy-url",
                "socks5h://127.0.0.1:10808",
                "--websocket-ping-interval",
                "0",
                "--websocket-ping-timeout",
                "0",
                "--dry-run",
            ]
        )

        kwargs = build_websocket_connect_kwargs(args)

        self.assertIsNone(kwargs["ping_interval"])
        self.assertIsNone(kwargs["ping_timeout"])
        self.assertEqual(kwargs["proxy"], "socks5h://127.0.0.1:10808")

    def test_semantic_planner_uses_dedicated_planner_key_and_proxy(self) -> None:
        captured: dict[str, object] = {}

        def fake_plan_from_text(transcript: str, **kwargs: object) -> dict[str, object]:
            captured["transcript"] = transcript
            captured.update(kwargs)
            return {
                "ok": True,
                "plan": {
                    "reply": "唔？",
                    "action": {"type": "none", "name": ""},
                    "speech": {"shouldSpeak": True, "text": "唔？"},
                },
                "validation": {"ok": True},
            }

        args = parse_args(
            [
                "--api-key",
                "realtime-stepfun-key",
                "--planner-api-key",
                "planner-deepseek-key",
                "--planner-provider",
                "deepseek",
                "--planner-model",
                "deepseek-v4-flash",
                "--proxy-url=",
                "--dry-run",
            ]
        )

        planner = build_semantic_planner(args, plan_func=fake_plan_from_text)
        result = planner("晚上好", runtime_state={"voicePhase": "answer"})

        self.assertTrue(result["ok"])
        self.assertEqual(captured["transcript"], "晚上好")
        self.assertEqual(captured["api_key"], "planner-deepseek-key")
        self.assertEqual(captured["provider"], "deepseek")
        self.assertEqual(captured["model"], "deepseek-v4-flash")
        self.assertEqual(captured["proxy_url"], "")
        self.assertEqual(captured["runtime_state"], {"voicePhase": "answer"})

    def test_semantic_planner_can_route_to_hermes_provider_without_realtime_key_leak(self) -> None:
        captured: dict[str, object] = {}

        def fake_plan_from_text(transcript: str, **kwargs: object) -> dict[str, object]:
            captured["transcript"] = transcript
            captured.update(kwargs)
            return {
                "ok": True,
                "plan": {
                    "reply": "我在听。",
                    "action": {"type": "none", "name": ""},
                    "speech": {"shouldSpeak": True, "text": "我在听。"},
                },
                "validation": {"ok": True},
            }

        args = parse_args(
            [
                "--api-key",
                "realtime-stepfun-key",
                "--planner-provider",
                "hermes",
                "--proxy-url=",
                "--dry-run",
            ]
        )

        planner = build_semantic_planner(args, plan_func=fake_plan_from_text)
        result = planner("你好", runtime_state={"voicePhase": "thinking"})

        self.assertTrue(result["ok"])
        self.assertEqual(captured["api_key"], None)
        self.assertEqual(captured["provider"], "hermes")
        self.assertEqual(captured["model"], "hermes-agent")
        self.assertEqual(captured["runtime_state"], {"voicePhase": "thinking"})

    def test_semantic_planner_merges_runtime_memory_into_runtime_state(self) -> None:
        captured: dict[str, object] = {}

        def fake_plan_from_text(transcript: str, **kwargs: object) -> dict[str, object]:
            captured["transcript"] = transcript
            captured.update(kwargs)
            return {
                "ok": True,
                "plan": {
                    "reply": "记得啦。",
                    "action": {"type": "none", "name": ""},
                    "speech": {"shouldSpeak": True, "text": "记得啦。"},
                },
                "validation": {"ok": True},
            }

        memory = MiraRuntimeMemory(max_turns=4)
        memory.record_turn("你要多说一点", reply="我记住啦。", action={"type": "none", "name": ""})
        args = parse_args(["--dry-run", "--planner-provider", "deepseek", "--planner-api-key", "planner-key"])

        planner = build_semantic_planner(args, plan_func=fake_plan_from_text, runtime_memory=memory)
        planner("晚上好", runtime_state={"voicePhase": "thinking", "turnId": "unit-turn"})

        runtime_state = captured["runtime_state"]
        self.assertIsInstance(runtime_state, dict)
        self.assertEqual(runtime_state["voicePhase"], "thinking")
        self.assertEqual(runtime_state["turnId"], "unit-turn")
        self.assertEqual(runtime_state["memory"]["recentTurns"][0]["user"], "你要多说一点")

    def test_default_sample_rates_match_stepfun_realtime_reference(self) -> None:
        """StepFun realtime API / official demo use 24kHz for both input and output."""
        args = parse_args(["--dry-run"])

        self.assertEqual(args.input_sample_rate, 24000)
        self.assertEqual(args.output_sample_rate, 24000)
        self.assertEqual(DEFAULT_INPUT_SAMPLE_RATE, 24000)
        self.assertEqual(DEFAULT_OUTPUT_SAMPLE_RATE, 24000)

    def test_default_websocket_keepalive_is_enabled(self) -> None:
        args = parse_args(["--dry-run"])

        self.assertEqual(args.websocket_ping_interval, DEFAULT_WEBSOCKET_PING_INTERVAL)
        self.assertEqual(args.websocket_ping_timeout, DEFAULT_WEBSOCKET_PING_TIMEOUT)
        kwargs = build_websocket_connect_kwargs(args)
        self.assertEqual(kwargs["ping_interval"], DEFAULT_WEBSOCKET_PING_INTERVAL)
        self.assertEqual(kwargs["ping_timeout"], DEFAULT_WEBSOCKET_PING_TIMEOUT)
        self.assertIsNone(kwargs["proxy"])


if __name__ == "__main__":
    unittest.main()
