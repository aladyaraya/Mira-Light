from __future__ import annotations

from pathlib import Path
import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scenes import SCENES  # noqa: E402


def test_voice_demo_tired_reuses_existing_affection_and_sleep_motion_groups() -> None:
    steps = SCENES["voice_demo_tired"]["steps"]
    pose_names = [step.get("name") for step in steps if step.get("type") == "pose"]
    control_payloads = [step["payload"] for step in steps if step.get("type") == "control"]

    assert "farewell_bow" not in pose_names
    assert {"mode": "absolute", "servo1": 94, "servo2": 100, "servo3": 108, "servo4": 90} in control_payloads
    assert {"mode": "absolute", "servo1": 90, "servo2": 104, "servo3": 110, "servo4": 86} in control_payloads
    assert {"mode": "absolute", "servo1": 90, "servo2": 94, "servo3": 96, "servo4": 98} in control_payloads
