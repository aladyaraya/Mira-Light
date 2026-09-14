from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from teach_motion import clean_trajectory, export_fixed_script, normalize_frames


class TeachMotionTests(unittest.TestCase):
    def test_clean_trajectory_rejects_duplicate_and_jump_frames(self) -> None:
        payload = {
            "frames": [
                {"tMs": 0, "positions": {"0": 2048, "1": 2048, "2": 2048, "3": 2048}},
                {"tMs": 40, "positions": {"0": 2048, "1": 2048, "2": 2048, "3": 2048}},
                {"tMs": 80, "positions": {"0": 2050, "1": 2052, "2": 2054, "3": 2056}},
                {"tMs": 120, "positions": {"0": 3500, "1": 2052, "2": 2054, "3": 2056}},
                {"tMs": 160, "positions": {"0": 2054, "1": 2056, "2": 2058, "3": 2060}},
            ]
        }

        cleaned = clean_trajectory(payload, smoothing_alpha=0.0)

        self.assertEqual(cleaned["frameCount"], 3)
        self.assertEqual(cleaned["safety"]["rejected"]["duplicate"], 1)
        self.assertEqual(cleaned["safety"]["rejected"]["jump"], 1)
        self.assertEqual(cleaned["frames"][-1]["positions"]["3"], 2060)

    def test_normalize_frames_rebases_time(self) -> None:
        frames = normalize_frames(
            {
                "frames": [
                    {"tMs": 500, "positions": {"0": 1, "1": 2, "2": 3, "3": 4}},
                    {"tMs": 540, "positions": {"0": 2, "1": 3, "2": 4, "3": 5}},
                ]
            }
        )

        self.assertEqual([frame["tMs"] for frame in frames], [0, 40])

    def test_export_fixed_script_uses_common_remote_step_and_pose_commands(self) -> None:
        script = export_fixed_script(
            {
                "frames": [
                    {"tMs": 0, "positions": {"0": 2048, "1": 2048, "2": 2048, "3": 2048}},
                    {"tMs": 80, "positions": {"0": 2050, "1": 2052, "2": 2054, "3": 2056}},
                ]
            },
            name="Hand Nuzzle Test!",
            title="Hand Nuzzle Test",
            speed=240,
            start_speed=160,
        )

        self.assertIn("from common import RemoteStep, build_parser, exit_from_plan", script)
        self.assertIn("pose 2048 2048 2048 2048 --speeds 160 160 160 160 --time 900", script)
        self.assertIn("pose 2050 2052 2054 2056 --speeds 240 240 240 240 --time 80", script)
        self.assertIn("Taught motion playback: Hand Nuzzle Test.", script)


if __name__ == "__main__":
    unittest.main()
