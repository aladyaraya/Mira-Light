from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_realtime_dialogue_console import (
    append_dialogue_history,
    build_dialogue_prompt,
    is_exit_command,
    turn_output_path,
)


class MiraRealtimeDialogueConsoleTest(unittest.TestCase):
    def test_exit_commands_are_recognized(self) -> None:
        for text in ("q", "quit", "exit", "/q", "/quit", "退出", "结束"):
            self.assertTrue(is_exit_command(text))
        self.assertFalse(is_exit_command("继续聊一会儿"))

    def test_exit_command_handles_redirected_power_shell_nul_bytes(self) -> None:
        self.assertTrue(is_exit_command("q\x00"))
        self.assertTrue(is_exit_command("\ufeff退出\x00"))

    def test_dialogue_prompt_includes_recent_history_and_current_user_text(self) -> None:
        history = [
            {"user": "你好", "assistant": "你好呀，我在这里。"},
            {"user": "你叫什么", "assistant": "我叫 Mary。"},
        ]

        prompt = build_dialogue_prompt("今天有点累", history)

        self.assertIn("Mary", prompt)
        self.assertIn("最近对话", prompt)
        self.assertIn("用户: 你叫什么", prompt)
        self.assertIn("Mary: 我叫 Mary。", prompt)
        self.assertIn("当前用户: 今天有点累", prompt)

    def test_append_dialogue_history_keeps_latest_turns(self) -> None:
        history = [{"user": str(index), "assistant": str(index)} for index in range(6)]

        updated = append_dialogue_history(history, "new", "reply", max_turns=3)

        self.assertEqual([item["user"] for item in updated], ["4", "5", "new"])
        self.assertEqual(updated[-1]["assistant"], "reply")

    def test_turn_output_path_is_stable_and_zero_padded(self) -> None:
        root = Path("runtime") / "dialogue"
        path = turn_output_path(root, 7)

        self.assertEqual(path, root / "turn-007" / "transcript.realtime.json")


if __name__ == "__main__":
    unittest.main()
