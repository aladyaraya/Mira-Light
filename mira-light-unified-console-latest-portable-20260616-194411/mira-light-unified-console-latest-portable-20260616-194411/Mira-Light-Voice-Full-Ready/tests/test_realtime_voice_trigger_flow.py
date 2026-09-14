from __future__ import annotations

import unittest

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_voice_intents import action_for_intent, bridge_payload_for_intent, classify_intent, scene_for_command


class RealtimeVoiceTriggerFlowTest(unittest.TestCase):
    def test_tired_transcript_maps_to_voice_tired_path(self) -> None:
        intent = classify_intent("我今天好累啊")
        self.assertEqual(intent, "comfort")
        payload = bridge_payload_for_intent(intent, "我今天好累啊")
        self.assertEqual(payload["source"], "voice-realtime")
        self.assertEqual(payload["transcript"], "我今天好累啊")

    def test_sigh_transcript_maps_to_sigh_path(self) -> None:
        intent = classify_intent("唉")
        self.assertEqual(intent, "sigh")
        payload = bridge_payload_for_intent(intent, "唉")
        self.assertEqual(payload["source"], "voice-realtime")
        self.assertEqual(payload["transcript"], "唉")

    def test_farewell_payload_keeps_center_direction_default(self) -> None:
        intent = classify_intent("拜拜")
        self.assertEqual(intent, "farewell")
        payload = bridge_payload_for_intent(intent, "拜拜")
        self.assertEqual(payload["direction"], "center")

    def test_praise_maps_to_praise_trigger(self) -> None:
        intent = classify_intent("你好可爱")
        self.assertEqual(intent, "praise")
        action = action_for_intent(intent)
        self.assertEqual(action, {"type": "trigger", "name": "praise_detected"})

    def test_affection_words_map_to_touch_affection_scene(self) -> None:
        transcript = "".join(chr(code) for code in [0x6211, 0x5FC3, 0x52A8, 0x4E86])

        intent = classify_intent(transcript)

        self.assertEqual(intent, "affection")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "touch_affection"})

    def test_keep_words_map_to_presence_scene(self) -> None:
        transcript = "动作是KEEP，好好说话呀"

        intent = classify_intent(transcript)

        self.assertEqual(intent, "keep_presence")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "cute_probe"})

    def test_reflective_words_map_to_daydream_scene(self) -> None:
        transcript = "问我为什么固执而执着？"

        intent = classify_intent(transcript)

        self.assertEqual(intent, "reflective")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "daydream"})

    def test_criticism_maps_to_criticism_trigger(self) -> None:
        intent = classify_intent("你今天有点不太行")
        self.assertEqual(intent, "criticism")
        action = action_for_intent(intent)
        self.assertEqual(action, {"type": "trigger", "name": "criticism_detected"})

    def test_negative_feedback_wins_over_liked_substring(self) -> None:
        transcript = "".join(chr(code) for code in [0x4E0D, 0x559C, 0x6B22, 0x4F60])

        intent = classify_intent(transcript)

        self.assertEqual(intent, "criticism")
        self.assertEqual(action_for_intent(intent), {"type": "trigger", "name": "criticism_detected"})

    def test_console_scene_command_maps_to_run_scene(self) -> None:
        intent = classify_intent("启动跳舞模式")
        self.assertEqual(intent, "scene:celebrate")
        action = action_for_intent(intent)
        self.assertEqual(action, {"type": "scene", "name": "celebrate"})

    def test_natural_dance_command_maps_to_celebrate_scene(self) -> None:
        intent = classify_intent("那你就去跳吧")
        self.assertEqual(intent, "scene:celebrate")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "celebrate"})

    def test_sleep_scene_command_maps_to_run_scene(self) -> None:
        self.assertEqual(scene_for_command("进入睡觉"), "sleep")
        self.assertEqual(action_for_intent(classify_intent("进入睡觉")), {"type": "scene", "name": "sleep"})

    def test_tracking_scene_command_maps_to_run_scene(self) -> None:
        self.assertEqual(scene_for_command("开始追踪目标"), "track_target")
        self.assertEqual(action_for_intent(classify_intent("开始追踪目标")), {"type": "scene", "name": "track_target"})

    def test_left_turn_command_maps_to_left_look_scene(self) -> None:
        self.assertEqual(scene_for_command("Mira左转"), "look_left")
        self.assertEqual(action_for_intent(classify_intent("Mira左转")), {"type": "scene", "name": "look_left"})

    def test_right_turn_command_maps_to_right_look_scene(self) -> None:
        self.assertEqual(scene_for_command("米娅看右边"), "look_right")
        self.assertEqual(action_for_intent(classify_intent("米娅看右边")), {"type": "scene", "name": "look_right"})

    def test_wake_scene_command_maps_to_run_scene(self) -> None:
        self.assertEqual(scene_for_command("执行起床"), "wake_up")
        self.assertEqual(action_for_intent(classify_intent("执行起床")), {"type": "scene", "name": "wake_up"})

    def test_happy_emotion_maps_to_celebration_scene(self) -> None:
        intent = classify_intent("我现在很开心")
        self.assertEqual(intent, "celebrate_mood")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "celebrate"})

    def test_sleepy_emotion_maps_to_sleep_scene(self) -> None:
        intent = classify_intent("我有点困了")
        self.assertEqual(intent, "sleep_mood")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "sleep"})

    def test_startled_emotion_maps_to_startle_scene(self) -> None:
        intent = classify_intent("刚刚有点吓到")
        self.assertEqual(intent, "startle_mood")
        self.assertEqual(action_for_intent(intent), {"type": "scene", "name": "startle_sound"})


if __name__ == "__main__":
    unittest.main()
