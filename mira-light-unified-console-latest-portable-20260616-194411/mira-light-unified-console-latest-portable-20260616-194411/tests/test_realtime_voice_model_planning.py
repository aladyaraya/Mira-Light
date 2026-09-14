from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_READY_SCRIPTS_DIR = ROOT / "Mira-Light-Voice-Full-Ready" / "scripts"
LAUNCHER_PATH = ROOT / "Start-Mira-Light-Windows-Full-Realtime.ps1"

if str(FULL_READY_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(FULL_READY_SCRIPTS_DIR))

from mira_realtime_action_orchestrator import RealtimeActionConfig, RealtimeActionOrchestrator


class RealtimeVoiceModelPlanningTest(unittest.TestCase):
    def test_require_model_planning_bypasses_local_keyword_action(self) -> None:
        planner_calls: list[tuple[str, dict[str, object] | None]] = []
        posts: list[tuple[str, dict[str, object]]] = []

        def planner(transcript: str, runtime_state: dict[str, object] | None = None) -> dict[str, object]:
            planner_calls.append((transcript, runtime_state))
            return {
                "provider": "unit-planner",
                "model": "unit-model",
                "plan": {
                    "reply": "我来啦",
                    "emotion": "happy",
                    "intent": {"name": "celebrate", "confidence": 0.93},
                    "action": {"type": "scene", "name": "happy_dance"},
                    "reason": "unit-test-model-choice",
                    "speech": {"shouldSpeak": True, "text": "我来啦", "ttsEmotion": "happy"},
                    "safety": {"requiresConfirmation": False, "reason": ""},
                },
                "validation": {"ok": True},
            }

        def post_json(
            url: str,
            payload: dict[str, object],
            *,
            token: str = "",
            timeout_seconds: int = 5,
        ) -> dict[str, object]:
            posts.append((url, payload))
            return {"ok": True}

        orchestrator = RealtimeActionOrchestrator(
            RealtimeActionConfig(
                bridge_url="http://bridge.test",
                voice_state_enabled=False,
                semantic_cooldown_seconds=0.0,
                require_model_planning=True,
            ),
            planner=planner,
            post_json=post_json,
        )

        result = orchestrator.dispatch_transcript("我今天好累啊")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["kind"], "semantic-action")
        self.assertEqual(result["source"], "llm-planner")
        self.assertEqual(result["provider"], "unit-planner")
        self.assertEqual(result["model"], "unit-model")
        self.assertEqual(planner_calls[0][0], "我今天好累啊")
        self.assertEqual(len(posts), 1)
        self.assertTrue(posts[0][0].endswith("/v1/mira-light/run-scene"))
        self.assertEqual(posts[0][1]["scene"], "happy_dance")

    def test_windows_launcher_dry_run_defaults_to_planner_owned_reply(self) -> None:
        env = os.environ.copy()
        for key in (
            "MIRA_LIGHT_PLANNER_OWNS_REPLY",
            "MIRA_LIGHT_NO_REALTIME_PLAYBACK",
            "MIRA_LIGHT_ALLOW_LOCAL_SEMANTIC_FALLBACK",
            "MIRA_LIGHT_REQUIRE_MODEL_PLANNING",
        ):
            env.pop(key, None)

        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(LAUNCHER_PATH),
                "-DryRun",
                "-Json",
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PlannerOwnsReply: True", completed.stdout)
        self.assertIn("RealtimePlayback: False", completed.stdout)
        self.assertIn("RequireModelPlanning: True", completed.stdout)

        json_start = completed.stdout.find("{")
        self.assertGreaterEqual(json_start, 0, completed.stdout)
        preview = json.loads(completed.stdout[json_start:])
        self.assertTrue(preview["audio"]["plannerOwnsReply"])
        self.assertFalse(preview["audio"]["realtimePlayback"])
        self.assertTrue(preview["actions"]["requireModelPlanning"])


if __name__ == "__main__":
    unittest.main()
