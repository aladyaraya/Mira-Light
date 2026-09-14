from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_shenzhen_demo import (  # noqa: E402
    SHENZHEN_DEMO_CUES,
    build_cue_plan_request,
    build_dry_run_payload,
)


class MiraShenzhenDemoTest(unittest.TestCase):
    def test_shenzhen_demo_has_required_p0_cues(self) -> None:
        required = {"wake", "tired", "praise", "celebrate", "farewell", "sleep"}

        self.assertTrue(required.issubset(set(SHENZHEN_DEMO_CUES)))

    def test_cue_plan_request_uses_local_voice_lab_planner_by_default(self) -> None:
        request = build_cue_plan_request(
            "tired",
            bridge_url="http://127.0.0.1:19783",
            use_stepfun=False,
            dispatch=True,
        )

        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["url"], "http://127.0.0.1:19783/v1/mira-light/voice-lab/plan")
        self.assertFalse(request["payload"]["useStepFun"])
        self.assertTrue(request["payload"]["dispatch"])
        self.assertIn("source", request["payload"]["context"])
        self.assertEqual(request["expectedAction"], {"type": "trigger", "name": "voice_tired"})

    def test_dry_run_payload_includes_audio_asset_and_no_cloud_dependency(self) -> None:
        args = argparse.Namespace(
            cue="celebrate",
            bridge_url="http://127.0.0.1:19783",
            use_stepfun=False,
            dispatch=True,
            no_audio=False,
            audio_wait=False,
            audio_voice="tts",
        )

        payload = build_dry_run_payload(args)

        self.assertTrue(payload["dryRun"])
        self.assertEqual(payload["mode"], "shenzhen-local-demo")
        self.assertEqual(payload["cue"], "celebrate")
        self.assertEqual(payload["audio"]["asset"], "shenzhen_demo/celebrate.wav")
        self.assertFalse(payload["request"]["payload"]["useStepFun"])
        self.assertTrue(payload["request"]["payload"]["dispatch"])


if __name__ == "__main__":
    unittest.main()
