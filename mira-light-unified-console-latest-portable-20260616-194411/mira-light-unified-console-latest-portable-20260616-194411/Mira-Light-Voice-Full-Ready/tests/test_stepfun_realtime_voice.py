from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
import base64
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from stepfun_realtime_voice import (
    DEFAULT_REALTIME_MODEL,
    MIRA_REALTIME_INSTRUCTIONS,
    build_response_create_event,
    build_realtime_text_prompt_dry_run,
    build_realtime_dry_run,
    build_realtime_url,
    build_websocket_connect_kwargs,
    build_session_update_event,
    build_text_message_event,
    collect_realtime_audio_pcm,
    extract_realtime_summary,
    write_pcm16_wav,
)
from mira_agent_prompt_context import append_agent_context, load_agent_context


def _write_test_wav(path: Path, frames: int = 1600) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * frames)


class StepFunRealtimeVoiceTest(unittest.TestCase):
    def test_build_realtime_url_uses_stepaudio_25_realtime_model(self) -> None:
        self.assertEqual(DEFAULT_REALTIME_MODEL, "stepaudio-2.5-realtime")
        self.assertEqual(
            build_realtime_url("wss://api.stepfun.com/v1/realtime", DEFAULT_REALTIME_MODEL),
            "wss://api.stepfun.com/v1/realtime?model=stepaudio-2.5-realtime",
        )

    def test_session_update_event_sets_mira_light_pet_instruction_and_server_vad(self) -> None:
        event = build_session_update_event(voice="wenrounansheng")

        self.assertEqual(event["type"], "session.update")
        self.assertEqual(event["session"]["modalities"], ["text", "audio"])
        self.assertEqual(event["session"]["input_audio_format"], "pcm16")
        self.assertEqual(event["session"]["output_audio_format"], "pcm16")
        self.assertEqual(event["session"]["voice"], "wenrounansheng")
        self.assertEqual(event["session"]["turn_detection"]["type"], "server_vad")
        self.assertIn("你是 Mira，一个刚刚拥有感知的小光宠", event["session"]["instructions"])
        self.assertIn("好奇", event["session"]["instructions"])
        self.assertIn("害羞", event["session"]["instructions"])
        self.assertIn("亲近", event["session"]["instructions"])
        self.assertIn("警觉", event["session"]["instructions"])
        self.assertIn("开心", event["session"]["instructions"])
        self.assertIn("困倦", event["session"]["instructions"])
        self.assertIn("少说话，多用动作", event["session"]["instructions"])
        self.assertIn("你的文字回应通常不超过 12 个字", event["session"]["instructions"])
        self.assertIn("不说“我是一个 AI”", event["session"]["instructions"])
        self.assertIn("不要直接输出舵机角度", event["session"]["instructions"])
        self.assertIn("本地 Agent 记忆与人格文件", event["session"]["instructions"])
        self.assertIn("## IDENTITY.md", event["session"]["instructions"])
        self.assertIn("tiny embodied pet soul", event["session"]["instructions"])

    def test_agent_context_loader_reads_mira_voice_spark_workspace(self) -> None:
        context = load_agent_context()

        self.assertIn("## IDENTITY.md", context)
        self.assertIn("## SOUL.md", context)
        self.assertIn("## AGENTS.md", context)
        self.assertIn("small living presence", context)

    def test_append_agent_context_keeps_base_prompt_when_workspace_missing(self) -> None:
        with patch.dict("os.environ", {"MIRA_LIGHT_AGENT_WORKSPACE": "__missing_agent_workspace__"}, clear=False):
            self.assertEqual(append_agent_context("base prompt"), "base prompt")

    def test_session_update_event_prefers_external_realtime_prompt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt_path = Path(tmp) / "realtime.md"
            prompt_path.write_text("CUSTOM REALTIME PROMPT\nShort voice only.\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"MIRA_LIGHT_REALTIME_SYSTEM_PROMPT_FILE": str(prompt_path)},
                clear=False,
            ):
                event = build_session_update_event(voice="wenrounansheng")

        self.assertIn("CUSTOM REALTIME PROMPT\nShort voice only.", event["session"]["instructions"])
        self.assertIn("本地 Agent 记忆与人格文件", event["session"]["instructions"])

    def test_response_create_event_reuses_mira_instruction_boundary(self) -> None:
        event = build_response_create_event()

        self.assertEqual(event["type"], "response.create")
        self.assertEqual(event["response"]["modalities"], ["text", "audio"])
        self.assertIn(MIRA_REALTIME_INSTRUCTIONS, event["response"]["instructions"])
        self.assertIn("本地 Agent 记忆与人格文件", event["response"]["instructions"])

    def test_text_message_event_builds_user_input_text_item(self) -> None:
        event = build_text_message_event("请用中文说一句你好")

        self.assertEqual(event["type"], "conversation.item.create")
        self.assertEqual(event["item"]["type"], "message")
        self.assertEqual(event["item"]["role"], "user")
        self.assertEqual(event["item"]["content"][0]["type"], "input_text")
        self.assertEqual(event["item"]["content"][0]["text"], "请用中文说一句你好")

    def test_text_prompt_dry_run_builds_voice_reply_events(self) -> None:
        result = build_realtime_text_prompt_dry_run("请用 Mary 的语气打个招呼", proxy_url="socks5h://127.0.0.1:10808")

        self.assertTrue(result["ok"])
        self.assertTrue(result["dryRun"])
        self.assertEqual(result["mode"], "text-prompt")
        event_types = [item["type"] for item in result["events"]]
        self.assertEqual(event_types, ["session.update", "conversation.item.create", "response.create"])
        self.assertEqual(result["connection"]["headers"]["Authorization"], "Bearer <STEPFUN_API_KEY>")
        self.assertEqual(result["connection"]["proxy"], "socks5h://127.0.0.1:10808")

    def test_empty_proxy_disables_websockets_environment_proxy_lookup(self) -> None:
        self.assertEqual(build_websocket_connect_kwargs("")["proxy"], None)
        self.assertEqual(
            build_websocket_connect_kwargs("socks5h://127.0.0.1:10808")["proxy"],
            "socks5h://127.0.0.1:10808",
        )

    def test_dry_run_builds_realtime_audio_events_without_leaking_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "input.wav"
            _write_test_wav(audio_path)
            result = build_realtime_dry_run(audio_path, chunk_ms=50)

        self.assertTrue(result["ok"])
        self.assertTrue(result["dryRun"])
        self.assertEqual(result["connection"]["url"], "wss://api.stepfun.com/v1/realtime?model=stepaudio-2.5-realtime")
        self.assertEqual(result["connection"]["headers"]["Authorization"], "Bearer <STEPFUN_API_KEY>")
        event_types = [item["type"] for item in result["events"]]
        self.assertEqual(event_types[0], "session.update")
        self.assertIn("input_audio_buffer.append", event_types)
        self.assertEqual(event_types[-1], "response.create")
        self.assertNotIn("input_audio_buffer.commit", event_types)
        append_event = next(item for item in result["events"] if item["type"] == "input_audio_buffer.append")
        self.assertEqual(append_event["audio"], "<base64 omitted>")
        self.assertGreater(append_event["audioBytes"], 0)

    def test_extract_realtime_summary_collects_user_transcript_text_and_audio_size(self) -> None:
        events = [
            {"type": "conversation.item.input_audio_transcription.completed", "transcript": "我今天好累"},
            {"type": "response.text.done", "text": "辛苦了，我在这里。"},
            {"type": "response.audio.delta", "delta": "QUJD"},
            {"type": "response.audio.done"},
        ]

        summary = extract_realtime_summary(events)

        self.assertEqual(summary["userTranscript"], "我今天好累")
        self.assertEqual(summary["assistantText"], "辛苦了，我在这里。")
        self.assertEqual(summary["audioBase64Bytes"], 4)
        self.assertTrue(summary["audioDone"])

    def test_collect_realtime_audio_and_write_pcm16_wav(self) -> None:
        events = [
            {"type": "response.audio.delta", "delta": base64.b64encode(b"\x01\x00\x02\x00").decode("ascii")},
            {"type": "response.audio.delta", "delta": base64.b64encode(b"\x03\x00\x04\x00").decode("ascii")},
        ]
        pcm = collect_realtime_audio_pcm(events)

        self.assertEqual(pcm, b"\x01\x00\x02\x00\x03\x00\x04\x00")

        with tempfile.TemporaryDirectory() as tmp:
            path = write_pcm16_wav(pcm, Path(tmp) / "reply.wav", sample_rate=24000)
            with wave.open(str(path), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getframerate(), 24000)
                self.assertEqual(wav.readframes(wav.getnframes()), pcm)


if __name__ == "__main__":
    unittest.main()
