from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stepfun_llm_planner as planner


class StepFunLlmPlannerTest(unittest.TestCase):
    def test_default_planner_provider_is_stepfun_3_7_flash(self) -> None:
        self.assertEqual(planner.DEFAULT_LLM_PROVIDER, "stepfun")
        self.assertEqual(planner.default_endpoint_for_provider("stepfun"), "https://api.stepfun.com/v1/chat/completions")
        self.assertEqual(planner.default_model_for_provider("stepfun"), "step-3.7-flash")

    def test_llm_action_manifest_is_compact(self) -> None:
        manifest = planner.build_llm_action_manifest()
        self.assertIn("sceneNames", manifest)
        self.assertIn("triggerNames", manifest)
        self.assertNotIn("sceneItems", manifest)

    def test_action_manifest_exposes_scene_readiness_for_motion_planning(self) -> None:
        manifest = planner.build_action_manifest()
        look_left = next(item for item in manifest["sceneItems"] if item["name"] == "look_left")

        self.assertEqual(look_left["readiness"], "ready")

    def test_planner_system_prompt_includes_local_agent_context(self) -> None:
        prompt = planner.planner_system_prompt()

        self.assertIn("本地 Agent 记忆与人格文件", prompt)
        self.assertIn("## SOUL.md", prompt)
        self.assertIn("body-first", prompt)

    def test_planner_user_prompt_tells_llm_to_plan_body_first(self) -> None:
        prompt = planner.planner_user_prompt("Mira左转", planner.build_llm_action_manifest(), {"voicePhase": "thinking"})

        self.assertIn("motionPlanningHint", prompt)
        self.assertIn("先根据用户情绪和指令选择动作组", prompt)
        self.assertIn("thinking", prompt)

    def test_planner_user_prompt_exposes_runtime_memory_and_memory_update_schema(self) -> None:
        prompt = planner.planner_user_prompt(
            "晚上好",
            planner.build_llm_action_manifest(),
            {
                "voicePhase": "thinking",
                "memory": {
                    "recentTurns": [{"user": "你要多说一点", "reply": "我记住啦。"}],
                    "sessionNotes": ["用户希望 Mira 回复不要太短。"],
                },
            },
        )

        self.assertIn("memoryUpdate", prompt)
        self.assertIn("longTermCandidate", prompt)
        self.assertIn("用户希望 Mira 回复不要太短。", prompt)

    def test_empty_proxy_disables_requests_environment_proxy_lookup(self) -> None:
        self.assertEqual(planner.build_requests_proxies(""), {"http": None, "https": None})

    def test_proxy_url_configures_both_http_schemes(self) -> None:
        self.assertEqual(
            planner.build_requests_proxies("socks5h://127.0.0.1:10808"),
            {
                "http": "socks5h://127.0.0.1:10808",
                "https": "socks5h://127.0.0.1:10808",
            },
        )

    def test_deepseek_dry_run_redacts_deepseek_key(self) -> None:
        result = planner.build_planner_dry_run("hello", provider="deepseek")

        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["model"], "deepseek-v4-flash")
        self.assertEqual(result["request"]["endpoint"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(result["request"]["headers"]["Authorization"], "Bearer <DEEPSEEK_API_KEY>")

    def test_hermes_dry_run_uses_local_cli_without_api_key_header(self) -> None:
        result = planner.build_planner_dry_run("hello", provider="hermes")

        self.assertEqual(result["provider"], "hermes")
        self.assertEqual(result["model"], "hermes-agent")
        self.assertEqual(result["request"]["method"], "CLI")
        self.assertNotIn("headers", result["request"])

    def test_parse_plan_content_extracts_json_from_agent_stdout(self) -> None:
        content = 'Hermes: ok\n{"reply":"我在听。","action":{"type":"none","name":""},"speech":{"shouldSpeak":true,"text":"我在听。"}}\n'

        parsed = planner.parse_plan_content(content)

        self.assertEqual(parsed["reply"], "我在听。")
        self.assertEqual(parsed["action"], {"type": "none", "name": ""})

    def test_hermes_planner_invokes_local_cli_and_parses_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_home = Path(tmp) / "home"
            hermes_home.mkdir()
            hermes_exe = Path(tmp) / "hermes.exe"
            hermes_exe.write_text("", encoding="utf-8")

            class Completed:
                returncode = 0
                stdout = '{"reply":"我在听。","action":{"type":"none","name":""},"speech":{"shouldSpeak":true,"text":"我在听。"}}'
                stderr = ""

            with patch.dict(
                os.environ,
                {
                    "MIRA_LIGHT_HERMES_HOME": str(hermes_home),
                    "MIRA_LIGHT_HERMES_EXE": str(hermes_exe),
                    "STEPFUN_API_KEY": "stepfun-key",
                    "OPENAI_API_KEY": "",
                },
                clear=False,
            ), patch("subprocess.run", return_value=Completed()) as run:
                plan = planner.run_hermes_planner(
                    "你好",
                    action_manifest=planner.build_llm_action_manifest(),
                    runtime_state={"voicePhase": "thinking"},
                    timeout_seconds=3,
                )

        self.assertEqual(plan["reply"], "我在听。")
        self.assertEqual(run.call_args.args[0][0], str(hermes_exe))
        self.assertEqual(run.call_args.kwargs["env"]["HERMES_HOME"], str(hermes_home))
        self.assertEqual(run.call_args.kwargs["env"]["OPENAI_API_KEY"], "stepfun-key")

    def test_post_json_uses_explicit_disabled_proxy_when_proxy_is_blank(self) -> None:
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json() -> dict[str, bool]:
                return {"ok": True}

        with patch("requests.post", return_value=FakeResponse()) as post:
            self.assertEqual(
                planner.post_json_request(
                    "https://example.invalid",
                    headers={"Authorization": "Bearer test"},
                    json_payload={"model": "step-3.7-flash"},
                    timeout_seconds=3,
                    proxy_url="",
                ),
                {"ok": True},
            )

        self.assertEqual(post.call_args.kwargs["proxies"], {"http": None, "https": None})

    def test_post_json_retries_transient_request_failure(self) -> None:
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json() -> dict[str, bool]:
                return {"ok": True}

        calls = {"count": 0}

        def flaky_post(*_: object, **__: object) -> FakeResponse:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("SSLEOFError: unexpected eof")
            return FakeResponse()

        with patch("requests.post", side_effect=flaky_post), patch.dict(os.environ, {"MIRA_LIGHT_PLANNER_HTTP_RETRIES": "1"}, clear=False):
            result = planner.post_json_request(
                "https://example.invalid",
                headers={"Authorization": "Bearer test"},
                json_payload={"model": "deepseek-v4-flash"},
                timeout_seconds=3,
                proxy_url="",
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls["count"], 2)

    def test_planner_prompt_file_overrides_default_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt_path = Path(tmp) / "planner.md"
            prompt_path.write_text("planner prompt from file", encoding="utf-8")
            with patch.dict(os.environ, {"MIRA_LIGHT_PLANNER_SYSTEM_PROMPT_FILE": str(prompt_path)}, clear=False):
                prompt = planner.planner_system_prompt()

        self.assertIn("planner prompt from file", prompt)
        self.assertIn("本地 Agent 记忆与人格文件", prompt)

    def test_obvious_intent_uses_local_shortcut_without_cloud_request(self) -> None:
        def should_not_call_remote(*_: object, **__: object) -> dict[str, object]:
            raise AssertionError("remote planner should not be called")

        local_plan = {
            "reply": "我也喜欢你",
            "emotion": "happy",
            "intent": {"name": "praise", "confidence": 0.92},
            "action": {"type": "trigger", "name": "praise_detected"},
            "reason": "local-shortcut",
            "speech": {"shouldSpeak": True, "text": "我也喜欢你", "ttsEmotion": "happy"},
            "safety": {"requiresConfirmation": False, "reason": ""},
        }
        with patch.object(planner, "should_use_local_shortcut", return_value=True), patch.object(
            planner,
            "build_fast_local_structured_plan",
            return_value=local_plan,
        ):
            result = planner.plan_from_text(
                "unit shortcut",
                api_key="test-key",
                provider="deepseek",
                post_json=should_not_call_remote,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "local-shortcut")
        self.assertEqual(result["plan"]["action"], {"type": "trigger", "name": "praise_detected"})
        self.assertEqual(result["latencyMs"], 0)


if __name__ == "__main__":
    unittest.main()
