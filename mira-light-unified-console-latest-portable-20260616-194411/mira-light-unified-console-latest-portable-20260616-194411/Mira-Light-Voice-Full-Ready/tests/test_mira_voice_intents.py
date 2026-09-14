from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_voice_intents import action_for_intent, classify_intent


class MiraVoiceIntentTests(unittest.TestCase):
    def test_raise_head_routes_to_wake_up_scene(self) -> None:
        intent = classify_intent("你能不能把头抬高一点呢？")

        self.assertEqual(intent, "scene:wake_up")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "wake_up"})

    def test_praise_after_dance_routes_to_praise_trigger(self) -> None:
        intent = classify_intent("你跳得不错，蛮不错的。")

        self.assertEqual(intent, "praise")
        self.assertEqual(action_for_intent(intent), {"type": "trigger", "name": "praise_detected"})


if __name__ == "__main__":
    unittest.main()
