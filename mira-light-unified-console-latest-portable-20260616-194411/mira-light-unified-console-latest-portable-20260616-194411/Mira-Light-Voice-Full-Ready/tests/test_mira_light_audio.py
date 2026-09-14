from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mira_light_audio import AudioCuePlayer


class MiraLightAudioVoicePresetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.player = AudioCuePlayer(dry_run=True)

    def test_gentle_sister_mode_uses_expected_preset(self) -> None:
        with patch.object(self.player, "_find_command", return_value="/tmp/speaker-hp-tts-play"):
            command = self.player._build_speech_command("你好", voice="gentle_sister")
        self.assertEqual(
            command,
            [
                "/tmp/speaker-hp-tts-play",
                "--voice",
                "zh-CN-XiaoyiNeural",
                "--lang",
                "zh-CN",
                "--rate",
                "-12%",
                "--pitch",
                "-20%",
                "你好",
            ],
        )

    def test_warm_gentleman_mode_uses_expected_preset(self) -> None:
        with patch.object(self.player, "_find_command", return_value="/tmp/speaker-hp-tts-play"):
            command = self.player._build_speech_command("你好", voice="warm_gentleman")
        self.assertEqual(
            command,
            [
                "/tmp/speaker-hp-tts-play",
                "--voice",
                "zh-CN-YunxiNeural",
                "--lang",
                "zh-CN",
                "--rate",
                "-6%",
                "--pitch",
                "-6%",
                "你好",
            ],
        )

    def test_legacy_alias_resolves_to_gentle_sister(self) -> None:
        with patch.object(self.player, "_find_command", return_value="/tmp/speaker-hp-tts-play"):
            command = self.player._build_speech_command("你好", voice="female")
        self.assertEqual(command[2], "zh-CN-XiaoyiNeural")
        self.assertEqual(command[8], "-20%")

    def test_prepare_command_prefers_hp_then_beosound_then_builtin(self) -> None:
        player = AudioCuePlayer(dry_run=True)

        def fake_find(name: str) -> str | None:
            mapping = {
                "speaker-beosound-use": "/tmp/speaker-beosound-use",
            }
            return mapping.get(name)

        with patch.object(player, "_find_command", side_effect=fake_find):
            command = player._resolve_prepare_command()
        self.assertEqual(command, ["/tmp/speaker-beosound-use"])

    def test_play_command_prefers_builtin_helper_before_afplay(self) -> None:
        def fake_find(name: str) -> str | None:
            mapping = {
                "speaker-builtin-play": "/tmp/speaker-builtin-play",
                "afplay": "/usr/bin/afplay",
            }
            return mapping.get(name)

        with patch.object(self.player, "_find_command", side_effect=fake_find):
            command = self.player._build_play_command(Path("/tmp/test.wav"))
        self.assertEqual(command, ["/tmp/speaker-builtin-play", str(Path("/tmp/test.wav"))])

    def test_windows_sapi_fallback_uses_encoded_command(self) -> None:
        with patch.object(self.player, "_find_command", return_value=None):
            with patch("sys.platform", "win32"):
                command = self.player._build_speech_command("Mira says 'hi'\n下一句", voice="warm_gentleman")

        self.assertEqual(command[0].lower(), "powershell")
        self.assertIn("-EncodedCommand", command)
        self.assertNotIn("Mira says 'hi'", command)

    def test_windows_asset_playback_fallback_uses_encoded_command(self) -> None:
        with patch.object(self.player, "_find_command", return_value=None):
            with patch("sys.platform", "win32"):
                command = self.player._build_play_command(Path("C:/tmp/dance.mp3"))

        self.assertEqual(command[0].lower(), "powershell")
        self.assertIn("-EncodedCommand", command)
        self.assertNotIn("dance.mp3", command)

    def test_run_decodes_non_utf8_process_output_safely(self) -> None:
        player = AudioCuePlayer(dry_run=False)
        completed = subprocess.CompletedProcess(args=["powershell"], returncode=0, stdout=b"\xd5", stderr=None)

        with patch("subprocess.run", return_value=completed):
            result = player._run(["powershell", "-EncodedCommand", "..."], wait=True, description="speech:tts")

        self.assertTrue(result["ok"])
        self.assertEqual(result["stdout"], "\ufffd")
        self.assertEqual(result["stderr"], "")


if __name__ == "__main__":
    unittest.main()
