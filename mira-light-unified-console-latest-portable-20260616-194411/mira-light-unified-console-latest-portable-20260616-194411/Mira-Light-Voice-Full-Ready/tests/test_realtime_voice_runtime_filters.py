from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_realtime_voice_interaction import (
    DEFAULT_API_SYSTEM_PROMPT,
    UtteranceResult,
    apply_latency_preset,
    build_low_latency_system_prompt,
    calculate_rms_cv,
    low_energy_skip_reason,
    normalize_reply_text,
    parse_args,
    repetitive_transcript_details,
    transcribe_utterance,
)
from mira_voice_intents import is_brief_greeting, should_skip_short_reply


class RealtimeVoiceRuntimeFiltersTest(unittest.TestCase):
    def test_parse_args_reads_api_system_and_stt_prompt_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api_prompt = root / "api-system.md"
            stt_prompt = root / "stt.md"
            api_prompt.write_text("CUSTOM API SYSTEM PROMPT\nKeep replies short.\n", encoding="utf-8")
            stt_prompt.write_text("Mira Light Shenzhen demo terminology.\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {
                    "MIRA_LIGHT_LLM_SYSTEM_PROMPT_FILE": str(api_prompt),
                    "MIRA_LIGHT_STT_INITIAL_PROMPT_FILE": str(stt_prompt),
                },
                clear=False,
            ), patch.object(sys, "argv", ["mira_realtime_voice_interaction.py", "--mode", "fixed", "--dry-run-audio"]):
                args = parse_args()

            self.assertEqual(args.api_system_prompt, "CUSTOM API SYSTEM PROMPT\nKeep replies short.")
            self.assertEqual(args.initial_prompt, "Mira Light Shenzhen demo terminology.")

    def test_low_latency_preset_reduces_wait_but_keeps_small_profile(self) -> None:
        args = argparse.Namespace(
            latency_preset="low",
            vad_start_ms=150,
            vad_end_ms=650,
            history_turns=4,
            profile="small",
            api_system_prompt=DEFAULT_API_SYSTEM_PROMPT,
            startup_warmup=None,
            keep_warm_seconds=0.0,
        )
        applied = apply_latency_preset(args)
        self.assertEqual(args.vad_start_ms, 100)
        self.assertEqual(args.vad_end_ms, 400)
        self.assertEqual(args.history_turns, 2)
        self.assertEqual(args.profile, "small")
        self.assertTrue(args.startup_warmup)
        self.assertEqual(args.keep_warm_seconds, 90.0)
        self.assertEqual(applied["preset"], "low")

    def test_default_bridge_url_uses_voice_action_bridge_port(self) -> None:
        with patch.object(sys, "argv", ["mira_realtime_voice_interaction.py"]):
            args = parse_args()
        self.assertEqual(args.bridge_url, "http://127.0.0.1:19783")

    def test_low_latency_prompt_hint_prefers_short_replies(self) -> None:
        prompt = build_low_latency_system_prompt(DEFAULT_API_SYSTEM_PROMPT)
        self.assertIn("低延迟回复策略", prompt)
        self.assertIn("完整、自然的短句", prompt)

    def test_brief_greeting_is_detected(self) -> None:
        self.assertTrue(is_brief_greeting("你好。"))
        self.assertTrue(is_brief_greeting("hello!"))

    def test_non_greeting_is_not_detected_as_brief_greeting(self) -> None:
        self.assertFalse(is_brief_greeting("你好，我今天有点累。"))
        self.assertFalse(is_brief_greeting("你是谁"))

    def test_short_low_information_chat_is_skipped(self) -> None:
        self.assertTrue(should_skip_short_reply("嗯。", intent="chat"))
        self.assertTrue(should_skip_short_reply("啊", intent="chat"))

    def test_short_meaningful_transcript_is_not_skipped(self) -> None:
        self.assertFalse(should_skip_short_reply("你好。", intent="chat"))
        self.assertFalse(should_skip_short_reply("拜拜", intent="farewell"))

    def test_single_character_transcript_is_skipped_even_if_meaningful(self) -> None:
        self.assertTrue(should_skip_short_reply("唉", intent="sigh"))
        self.assertTrue(should_skip_short_reply("嗨", intent="chat"))

    def test_low_energy_continuous_utterance_is_skipped(self) -> None:
        reason = low_energy_skip_reason(
            {"captureMode": "continuous"},
            {"durationMs": 1269.0, "rms": 0.003872, "peak": 0.032471},
        )
        self.assertTrue(reason.startswith("low-rms-energy"))

    def test_ptt_utterance_is_not_skipped_by_low_energy_rule(self) -> None:
        reason = low_energy_skip_reason(
            {"captureMode": "ptt"},
            {"durationMs": 1269.0, "rms": 0.003872, "peak": 0.032471},
        )
        self.assertIsNone(reason)

    def test_constant_energy_audio_has_low_cv(self) -> None:
        samples = np.full(16000, 0.05, dtype=np.float32)
        self.assertLess(calculate_rms_cv(samples, 16000), 0.01)

    def test_modulated_speech_like_audio_has_high_cv(self) -> None:
        sample_rate = 16000
        t = np.arange(sample_rate, dtype=np.float32) / sample_rate
        carrier = np.sin(2 * np.pi * 220 * t).astype(np.float32)
        envelope = np.where((np.arange(sample_rate) // 1600) % 2 == 0, 0.08, 0.005).astype(np.float32)
        samples = carrier * envelope
        self.assertGreater(calculate_rms_cv(samples, sample_rate), 0.35)

    def test_stepfun_transcriber_preserves_stepfun_model_metadata(self) -> None:
        args = argparse.Namespace(
            model_repo="",
            profile="small",
            initial_prompt="Mira Light",
            transcriber="stepfun",
            language="zh",
        )
        utterance = UtteranceResult(
            samples=np.zeros(1600, dtype=np.float32),
            sample_rate=16000,
            source_meta={"captureMode": "fixed"},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"STEPFUN_API_KEY": "test-key", "STEPFUN_ASR_MODEL": "stepaudio-2.5-asr"}):
                with patch("tempfile.gettempdir", return_value=tmpdir):
                    with patch("stepfun_asr_client.transcribe_audio_file", return_value={"text": "你好", "language": "zh"}):
                        payload = transcribe_utterance(utterance, args=args)

        self.assertEqual(payload["text"], "你好")
        self.assertEqual(payload["modelRepo"], "stepfun:stepaudio-2.5-asr")
        self.assertEqual(payload["initialPrompt"], "Mira Light")

    def test_repetitive_transcript_is_detected(self) -> None:
        payload = {
            "text": "请" * 223,
            "segments": [
                {
                    "start": 0.0,
                    "end": 0.61,
                    "compression_ratio": 37.1666,
                }
            ],
        }
        details = repetitive_transcript_details(
            payload,
            audio_metrics={"durationMs": 619.0, "rms": 0.043194, "peak": 0.235138},
        )
        self.assertIsNotNone(details)
        assert details is not None
        self.assertEqual(details["reason"], "repetitive-transcript")
        self.assertEqual(details["dominantChar"], "请")

    def test_normal_transcript_is_not_flagged(self) -> None:
        payload = {
            "text": "你好，我们继续聊吧。",
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.2,
                    "compression_ratio": 1.2,
                }
            ],
        }
        details = repetitive_transcript_details(
            payload,
            audio_metrics={"durationMs": 1200.0, "rms": 0.016747, "peak": 0.117035},
        )
        self.assertIsNone(details)

    def test_repeated_word_transcript_is_detected(self) -> None:
        payload = {
            "text": "有 " + " ".join(["lawmakers"] * 23),
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.4,
                    "compression_ratio": 12.0,
                }
            ],
        }
        details = repetitive_transcript_details(
            payload,
            audio_metrics={"durationMs": 1400.0, "rms": 0.025, "peak": 0.12},
        )
        self.assertIsNotNone(details)
        assert details is not None
        self.assertEqual(details["reason"], "repetitive-transcript")
        self.assertEqual(details["mode"], "token")
        self.assertEqual(details["dominantToken"], "lawmakers")

    def test_instructional_reply_prefix_and_markdown_are_removed(self) -> None:
        text, flags = normalize_reply_text('你可以直接回： **“你可以叫我米拉，是一个温柔陪伴你的助手。”**')
        self.assertEqual(text, "你可以叫我米拉，是一个温柔陪伴你的助手。")
        self.assertTrue(flags["markdownStripped"])
        self.assertTrue(flags["instructionalPrefixStripped"])

    def test_normal_reply_text_is_preserved(self) -> None:
        text, flags = normalize_reply_text("你好呀，我在这里。")
        self.assertEqual(text, "你好呀，我在这里。")
        self.assertFalse(flags["instructionalPrefixStripped"])


if __name__ == "__main__":
    unittest.main()
