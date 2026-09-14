from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_runtime_memory import MiraRuntimeMemory


class MiraRuntimeMemoryTest(unittest.TestCase):
    def test_recent_turns_are_kept_small_and_exposed_to_runtime_state(self) -> None:
        memory = MiraRuntimeMemory(max_turns=2)

        memory.record_turn("第一句", reply="我在。", action={"type": "none", "name": ""}, emotion="curious")
        memory.record_turn("第二句", reply="听见啦。", action={"type": "scene", "name": "cute_probe"}, emotion="curious")
        memory.record_turn("第三句", reply="慢慢说。", action={"type": "trigger", "name": "voice_tired"}, emotion="warm_caring")

        state = memory.build_runtime_state(voice_phase="thinking")

        self.assertEqual(state["voicePhase"], "thinking")
        self.assertEqual([turn["user"] for turn in state["memory"]["recentTurns"]], ["第二句", "第三句"])
        self.assertEqual(state["memory"]["lastReply"], "慢慢说。")
        self.assertEqual(state["memory"]["lastAction"], {"type": "trigger", "name": "voice_tired"})
        self.assertEqual(state["memory"]["lastEmotion"], "warm_caring")

    def test_memory_update_from_planner_result_is_recorded_without_auto_promoting_long_term(self) -> None:
        memory = MiraRuntimeMemory(max_turns=4)
        action = {
            "kind": "semantic-skip",
            "reason": "none-action",
            "plan": {
                "reply": "我记得啦，这次多说一点。",
                "emotion": "warm_caring",
                "action": {"type": "none", "name": ""},
                "speech": {"shouldSpeak": True, "text": "我记得啦，这次多说一点。"},
                "memoryUpdate": {
                    "session": "用户希望 Mira 回复不要太短。",
                    "longTermCandidate": "用户偏好 Mira 自然一点，可以稍微多说。",
                },
            },
        }

        memory.record_planner_result("你要好好说话呀", action)
        state = memory.build_runtime_state()

        self.assertEqual(state["memory"]["sessionNotes"], ["用户希望 Mira 回复不要太短。"])
        self.assertEqual(state["memory"]["longTermCandidates"], ["用户偏好 Mira 自然一点，可以稍微多说。"])
        self.assertEqual(state["memory"]["recentTurns"][0]["reply"], "我记得啦，这次多说一点。")

    def test_pending_refinement_signal_is_not_recorded_as_empty_turn(self) -> None:
        memory = MiraRuntimeMemory(max_turns=4)

        memory.record_planner_result(
            "晚上好",
            {"kind": "semantic-skip", "reason": "needs-llm-refinement", "transcript": "晚上好"},
        )

        self.assertEqual(memory.build_runtime_state()["memory"]["recentTurns"], [])

    def test_memory_snapshot_round_trips_as_json(self) -> None:
        memory = MiraRuntimeMemory(max_turns=3)
        memory.record_turn("我好累啊", reply="靠近一点点。", action={"type": "trigger", "name": "voice_tired"})

        with self.subTest("round trip"):
            payload = memory.to_dict()
            restored = MiraRuntimeMemory.from_dict(payload)

        self.assertEqual(restored.build_runtime_state()["memory"]["recentTurns"][0]["user"], "我好累啊")
        self.assertEqual(restored.build_runtime_state()["memory"]["lastAction"], {"type": "trigger", "name": "voice_tired"})

    def test_memory_file_round_trips_for_realtime_reconnects(self) -> None:
        memory = MiraRuntimeMemory(max_turns=3)
        memory.record_turn("别忘了我刚才说的", reply="我记着呢。", action={"type": "none", "name": ""})

        with self.subTest("persist"):
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as tmp:
                path = Path(tmp) / "mira-live-memory.json"
                memory.write_json(path)
                restored = MiraRuntimeMemory.read_json(path)

        state = restored.build_runtime_state()
        self.assertEqual(state["memory"]["recentTurns"][0]["user"], "别忘了我刚才说的")
        self.assertEqual(state["memory"]["lastReply"], "我记着呢。")


if __name__ == "__main__":
    unittest.main()
