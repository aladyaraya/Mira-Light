from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from stepfun_asr_client import (
    DEFAULT_HOTWORDS,
    build_dry_run_result,
    build_asr_payload,
    parse_sse_events,
    transcribe_audio_file,
    write_transcript_outputs,
)


def _write_test_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 160)


class StepFunAsrClientTest(unittest.TestCase):
    def test_build_payload_encodes_wav_and_mira_mary_hotwords(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "input.wav"
            _write_test_wav(audio_path)

            payload, audio_meta = build_asr_payload(audio_path, language="zh")

        self.assertEqual(payload["audio"]["input"]["format"]["type"], "wav")
        self.assertEqual(payload["audio"]["input"]["format"]["rate"], 16000)
        self.assertEqual(payload["audio"]["input"]["format"]["bits"], 16)
        self.assertEqual(payload["audio"]["input"]["format"]["channel"], 1)
        self.assertEqual(payload["audio"]["input"]["transcription"]["model"], "stepaudio-2.5-asr")
        self.assertEqual(payload["audio"]["input"]["transcription"]["language"], "zh")
        self.assertIn("米拉", payload["audio"]["input"]["transcription"]["hotwords"])
        self.assertIn("Mary", payload["audio"]["input"]["transcription"]["hotwords"])
        self.assertTrue(payload["audio"]["data"])
        self.assertEqual(audio_meta["sampleRate"], 16000)
        self.assertIn("Mira Light", DEFAULT_HOTWORDS)

    def test_parse_sse_events_prefers_done_text(self) -> None:
        lines = [
            "event: transcript.text.delta",
            'data: {"type":"transcript.text.delta","delta":"你"}',
            "",
            "event: transcript.text.done",
            'data: {"type":"transcript.text.done","text":"你好 Mary"}',
            "",
            "data: [DONE]",
        ]

        result = parse_sse_events(lines)

        self.assertEqual(result["text"], "你好 Mary")
        self.assertEqual(result["eventCount"], 2)
        self.assertEqual(result["events"][0]["type"], "transcript.text.delta")
        self.assertEqual(result["events"][1]["type"], "transcript.text.done")

    def test_transcribe_audio_file_builds_request_and_mary_context(self) -> None:
        captured: dict[str, object] = {}

        def fake_post(url, *, headers, json_payload, timeout_seconds):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json_payload
            captured["timeout"] = timeout_seconds
            return [
                "event: transcript.text.done",
                'data: {"type":"transcript.text.done","text":"我有点累了"}',
                "",
            ]

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "input.wav"
            _write_test_wav(audio_path)
            result = transcribe_audio_file(
                audio_path,
                api_key="secret",
                post_sse=fake_post,
                timeout_seconds=12,
            )

        self.assertEqual(result["ok"], True)
        self.assertEqual(result["text"], "我有点累了")
        self.assertEqual(captured["url"], "https://api.stepfun.com/v1/audio/asr/sse")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(captured["headers"]["Content-Type"], "application/json")
        payload = captured["payload"]
        self.assertIsInstance(payload, dict)
        encoded = payload["audio"]["data"]
        self.assertIsInstance(encoded, str)
        self.assertGreater(len(encoded), 0)
        self.assertEqual(result["personaContext"]["assistantName"], "Mary")
        self.assertIn("ASR only returns text", result["personaContext"]["note"])

    def test_dry_run_result_does_not_require_api_key_or_expose_base64_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "input.wav"
            _write_test_wav(audio_path)
            result = build_dry_run_result(audio_path, hotwords="Mary,暖光")

        self.assertEqual(result["ok"], True)
        self.assertEqual(result["dryRun"], True)
        self.assertEqual(result["request"]["method"], "POST")
        self.assertEqual(result["request"]["endpoint"], "https://api.stepfun.com/v1/audio/asr/sse")
        self.assertEqual(result["request"]["headers"]["Authorization"], "Bearer <STEPFUN_API_KEY>")
        self.assertEqual(result["request"]["body"]["audio"]["data"], "<base64 omitted>")
        self.assertGreater(result["request"]["body"]["audio"]["dataLength"], 0)
        self.assertIn("暖光", result["hotwords"])
        self.assertEqual(result["personaContext"]["assistantName"], "Mary")

    def test_write_transcript_outputs_writes_json_and_txt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "transcript.stepfun.json"
            json_path, txt_path = write_transcript_outputs({"ok": True, "text": "你好"}, output_path)

            self.assertEqual(json_path, output_path.resolve())
            self.assertEqual(txt_path.read_text(encoding="utf-8").strip(), "你好")
            written = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(written["ok"], True)
        self.assertEqual(written["text"], "你好")


if __name__ == "__main__":
    unittest.main()
