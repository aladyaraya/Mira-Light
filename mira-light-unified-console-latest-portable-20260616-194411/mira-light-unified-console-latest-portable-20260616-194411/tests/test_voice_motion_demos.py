import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSOLE_DIR = ROOT / "mira-light-unified-director-console"
sys.path.insert(0, str(CONSOLE_DIR))

import voice_motion_demos as demos  # noqa: E402
import answer_demo  # noqa: E402


class VoiceMotionDemosTest(unittest.TestCase):
    def test_video_mapping_matches_0525_labels(self) -> None:
        self.assertEqual(demos.get_demo("listening").video, "0df6af9bf4b0303177c7b607efc3e988-听.mp4")
        self.assertEqual(demos.get_demo("thinking").video, "0b5c990939c341f348ffc253b333e121-思考.mp4")
        self.assertEqual(demos.get_demo("answer").video, "25059b3751e232cdc7c054d3ce610046-答.mp4")

    def test_steps_keep_per_pose_speeds_and_safe_poses(self) -> None:
        for demo_id in ("listening", "thinking", "answer"):
            payload = demos.demo_payload(demo_id, include_script=False)
            self.assertEqual(payload["amplitudeScale"], 1.0)
            self.assertEqual(payload["speedScale"], 2.0)
            self.assertEqual(payload["poseBias"], [0, 0, 0, 0])
            for _label, pose, speeds, hold in payload["steps"]:
                self.assertEqual(len(pose), 4)
                self.assertEqual(len(speeds), 4)
                self.assertGreaterEqual(hold, 0.0)
                self.assertTrue(all(demos.CLAMP_LO <= value <= demos.CLAMP_HI for value in pose))
                self.assertTrue(all(value > 0 for value in speeds))

    def test_thinking_uses_requested_joint_amplitude_scaling(self) -> None:
        payload = demos.demo_payload("thinking", include_script=False)
        self.assertEqual(payload["poseOrigin"], [2048, 2150, 2048, 2130])
        self.assertEqual(payload["poseScale"], [3.0, 3.0, -5.0, 5.0])
        self.assertEqual(payload["steps"][0][1], [2048, 2324, 2408, 2130])
        self.assertEqual(payload["steps"][2][1], [2384, 2384, 2408, 2408])
        self.assertEqual(payload["steps"][2][2], [440, 260, 260, 350])

    def test_thinking_joint_02_is_reversed_to_high_side(self) -> None:
        payload = demos.demo_payload("thinking", include_script=False)
        p2_values = [pose[2] for _label, pose, _speeds, _hold in payload["steps"]]
        self.assertGreaterEqual(min(p2_values), demos.CLAMP_HI)
        self.assertEqual(max(p2_values), demos.CLAMP_HI)

    def test_thinking_lowers_while_swinging_in_three_groups(self) -> None:
        payload = demos.demo_payload("thinking", include_script=False)
        first_seven = payload["steps"][:7]
        p0_values = [pose[0] for _label, pose, _speeds, _hold in first_seven]
        p2_values = [pose[2] for _label, pose, _speeds, _hold in first_seven]
        labels = [label for label, _pose, _speeds, _hold in first_seven]
        self.assertLess(min(p0_values), 1950)
        self.assertGreater(max(p0_values), 2350)
        self.assertEqual(max(p2_values), demos.CLAMP_HI)
        for group in ("1", "2", "3"):
            self.assertIn(f"thought swing {group} left", labels)
            self.assertIn(f"thought swing {group} right", labels)

    def test_normalized_timeline_is_cumulative_compatibility_view(self) -> None:
        timeline = demos.normalized_timeline("listening")
        steps = demos.normalized_steps("listening")
        self.assertEqual(len(timeline), len(steps))
        self.assertEqual(timeline[0], (0.0, [2048, 2170, 1752, 2130], "enter book gaze"))
        self.assertGreater(timeline[-1][0], timeline[0][0])

    def test_listening_keeps_joint_02_down_for_book_search(self) -> None:
        payload = demos.demo_payload("listening", include_script=False)
        p2_values = [pose[2] for _label, pose, _speeds, _hold in payload["steps"]]
        p0_values = [pose[0] for _label, pose, _speeds, _hold in payload["steps"]]
        labels = [label for label, _pose, _speeds, _hold in payload["steps"]]
        self.assertLessEqual(max(p2_values), 1752)
        self.assertEqual(min(p2_values), demos.CLAMP_LO)
        self.assertLess(min(p0_values), 1820)
        self.assertGreater(max(p0_values), 2280)
        self.assertEqual(payload["steps"][4][2], [380, 210, 210, 310])
        self.assertIn("find book left", labels)
        self.assertIn("find book right", labels)

    def test_board_script_uses_step_speeds(self) -> None:
        script = demos.render_board_script("answer")
        self.assertIn("STEPS = json.loads", script)
        self.assertIn('"punch up"', script)
        self.assertIn('[860, 500, 500, 640]', script)
        self.assertIn('"--speeds"', script)
        self.assertNotIn("SPEEDS = json.loads", script)

    def test_answer_uses_larger_joint_02_03_amplitude(self) -> None:
        payload = demos.demo_payload("answer", include_script=False)
        self.assertEqual(payload["poseScale"], [2.0, 2.0, 2.5, 2.5])
        punch = next(row for row in payload["steps"] if row[0] == "punch up")
        laugh_right = next(row for row in payload["steps"] if row[0] == "laugh right")
        self.assertEqual(punch[1], [2048, 2408, 2408, 2130])
        self.assertEqual(laugh_right[1], [2392, 2408, 2078, 2408])

    def test_answer_repeats_to_exactly_thirteen_seconds(self) -> None:
        payload = demos.demo_payload("answer", include_script=False)
        self.assertEqual(payload["baseScriptSteps"], len(demos.ANSWER_SCRIPT))
        self.assertEqual(payload["repeatToSeconds"], 13.0)
        self.assertEqual(payload["scriptDurationSeconds"], 13.0)
        self.assertGreater(payload["timelineMarkers"], len(demos.ANSWER_SCRIPT))
        self.assertAlmostEqual(sum(step[3] for step in payload["steps"]), 13.0, places=3)

    def test_answer_demo_wrapper_uses_new_answer_timeline(self) -> None:
        self.assertEqual(answer_demo.TIMELINE, demos.normalized_timeline("answer"))
        self.assertEqual(answer_demo.normalized_timeline(), demos.normalized_timeline("answer"))


if __name__ == "__main__":
    unittest.main()
