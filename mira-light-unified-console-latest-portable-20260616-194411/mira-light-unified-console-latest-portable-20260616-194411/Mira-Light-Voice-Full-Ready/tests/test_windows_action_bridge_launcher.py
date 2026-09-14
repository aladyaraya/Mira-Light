from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


VOICE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = VOICE_ROOT.parent


def run_powershell(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", *args],
        cwd=str(PACKAGE_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


class WindowsActionBridgeLauncherTest(unittest.TestCase):
    def test_action_bridge_launcher_dry_run_uses_separate_voice_action_port(self) -> None:
        script = PACKAGE_ROOT / "Start-Mira-Light-Windows-Action-Bridge.ps1"

        result = run_powershell(
            "-File",
            str(script),
            "-DryRun",
            "-Json",
            "-Port",
            "19783",
            "-BaseUrl",
            "tcp://192.168.0.183:9527",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["bridgeUrl"], "http://127.0.0.1:19783")
        self.assertIn("--port", payload["command"])
        self.assertIn("19783", payload["command"])
        self.assertIn("tcp://192.168.0.183:9527", payload["command"])

    def test_action_bridge_launcher_runtime_dry_run_adds_bridge_server_flag(self) -> None:
        script = PACKAGE_ROOT / "Start-Mira-Light-Windows-Action-Bridge.ps1"

        result = run_powershell(
            "-File",
            str(script),
            "-DryRun",
            "-Json",
            "-RuntimeDryRun",
            "-Port",
            "19784",
            "-BaseUrl",
            "tcp://192.168.0.183:9527",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["runtimeDryRun"])
        self.assertIn("--dry-run", payload["command"])
        self.assertIn("19784", payload["command"])

    def test_full_realtime_launcher_dry_run_defaults_to_action_bridge_port(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Start-Mira-Light-Windows-Full-Realtime.ps1"),
            "-DryRun",
            "-Json",
            "-NoSemanticActions",
            "-NoPlay",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('"bridgeUrl": "http://127.0.0.1:19783"', result.stdout)
        self.assertIn('"directorUrl": ""', result.stdout)
        self.assertIn('"voiceStateActions": false', result.stdout)
        self.assertIn('"assistantTextActions": false', result.stdout)
        self.assertIn('"twoPhaseRefinement": true', result.stdout)
        self.assertIn('"plannerReply": {', result.stdout)
        self.assertIn('"enabled": true', result.stdout)

    def test_full_realtime_launcher_loads_env_file_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "stepfun.env"
            env_file.write_text(
                "\n".join(
                    [
                        "STEPFUN_PROXY_URL=socks5h://unit-proxy:10808",
                        "STEPFUN_REALTIME_MODEL=unit-realtime-model",
                        "STEPFUN_REALTIME_VOICE=unit-voice",
                        "MIRA_LIGHT_WINDOWS_MIC_DEVICE=Unit Test Mic",
                        "STEPFUN_REALTIME_INPUT_SAMPLE_RATE=16000",
                        "STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE=16000",
                        "STEPFUN_REALTIME_MIC_CHUNK_MS=80",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_powershell(
                "-File",
                str(PACKAGE_ROOT / "Start-Mira-Light-Windows-Full-Realtime.ps1"),
                "-DryRun",
                "-Json",
                "-NoSemanticActions",
                "-NoPlay",
                "-EnvFile",
                str(env_file),
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('"model": "unit-realtime-model"', result.stdout)
        self.assertIn('"proxy": "socks5h://unit-proxy:10808"', result.stdout)
        self.assertIn('"inputDevice": "Unit Test Mic"', result.stdout)
        self.assertIn('"inputSampleRate": 16000', result.stdout)
        self.assertIn('"chunkMs": 80', result.stdout)

    def test_full_realtime_launcher_explicit_empty_proxy_overrides_environment_proxy(self) -> None:
        result = run_powershell(
            "-Command",
            "$env:STEPFUN_PROXY_URL='socks5h://127.0.0.1:10808'; "
            "& '.\\Start-Mira-Light-Windows-Full-Realtime.ps1' -DryRun -Json -NoSemanticActions -NoPlay -ProxyUrl ''",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('"proxy": ""', result.stdout)

    def test_stepfun_llm_launcher_no_proxy_clears_env_proxy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "stepfun.env"
            env_file.write_text(
                "\n".join(
                    [
                        "STEPFUN_API_KEY=test-key",
                        "STEPFUN_PROXY_URL=socks5h://unit-proxy:10808",
                        "STEPFUN_LLM_MODEL=unit-llm-model",
                        "MIRA_LIGHT_PLANNER_SYSTEM_PROMPT_FILE=config/prompts/stepfun_planner_system_prompt.md",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_powershell(
                "-File",
                str(PACKAGE_ROOT / "Start-Mira-Light-StepFun-LLM.ps1"),
                "-Transcript",
                "unit test",
                "-DryRun",
                "-Json",
                "-NoProxy",
                "-EnvFile",
                str(env_file),
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Model: unit-llm-model", result.stdout)
        self.assertIn("Proxy: ", result.stdout)
        self.assertNotIn("Proxy: socks5h://unit-proxy:10808", result.stdout)

    def test_windows_demo_launcher_local_dry_run_builds_cue_runner_command(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Start-Mira-Light-Windows-Demo.ps1"),
            "-Mode",
            "local-demo",
            "-Cue",
            "tired",
            "-DryRun",
            "-Json",
            "-NoAudio",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "local-demo")
        self.assertEqual(payload["cue"], "tired")
        self.assertEqual(payload["bridgeUrl"], "http://127.0.0.1:19783")
        self.assertIn("mira_shenzhen_demo.py", payload["script"])
        self.assertIn("--cue tired", payload["command"])
        self.assertNotIn("--use-stepfun", payload["command"])

    def test_tired_demo_launcher_dry_run_builds_voice_tired_trigger(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Invoke-Mira-Tired-Demo.ps1"),
            "-DryRun",
            "-Json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["url"], "http://127.0.0.1:19783/v1/mira-light/trigger")
        self.assertEqual(payload["body"]["event"], "voice_tired")
        self.assertEqual(payload["body"]["payload"]["transcript"], "我好累啊")
        self.assertTrue(payload["body"]["payload"]["silentMode"])

    def test_local_voice_loop_launcher_dry_run_builds_minimal_loop_command(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Invoke-Mira-Local-Voice-Loop.ps1"),
            "-DryRun",
            "-Json",
            "-SpeakReply",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "local-minimal-voice-loop")
        self.assertEqual(payload["bridgeUrl"], "http://127.0.0.1:19783")
        self.assertTrue(payload["speakReply"])
        self.assertEqual(payload["expectedAction"], {"type": "trigger", "name": "voice_tired"})
        self.assertIn("mira_local_voice_loop.py", payload["script"])
        self.assertIn("--speak-reply", payload["command"])

    def test_hardware_motion_acceptance_launcher_requires_board_ack(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Test-Mira-Hardware-Motion-Acceptance.ps1"),
            "-DryRun",
            "-Json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "hardware-motion-acceptance")
        self.assertEqual(payload["boardHost"], "192.168.0.183")
        self.assertEqual(payload["boardPort"], 9527)
        self.assertTrue(payload["requiresAck"])
        self.assertTrue(payload["requiresPositionChange"])
        self.assertEqual(payload["positionDeltaThreshold"], 20)
        self.assertIn("mira_hardware_motion_acceptance.py", payload["script"])

    def test_board_network_diagnostics_launcher_dry_run(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Diagnose-Mira-Board-Network.ps1"),
            "-DryRun",
            "-Json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "mira-board-network-diagnostics")
        self.assertEqual(payload["boardHost"], "192.168.0.183")
        self.assertEqual(payload["boardPort"], 9527)
        self.assertTrue(
            any("Test-Mira-Hardware-Motion-Acceptance.ps1" in item for item in payload["command"]),
            payload["command"],
        )
        self.assertIn("-SkipPositionChangeCheck", payload["command"])

    def test_board_network_repair_launcher_dry_run(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Repair-Mira-Board-Network.ps1"),
            "-DryRun",
            "-Json",
            "-BoardHost",
            "192.168.0.183",
            "-Gateway",
            "192.168.123.254",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "mira-board-network-repair")
        self.assertEqual(payload["boardHost"], "192.168.0.183")
        self.assertEqual(payload["gateway"], "192.168.123.254")
        self.assertFalse(payload["willApplyRoute"])
        self.assertFalse(payload["willUpdateConfig"])
        self.assertIn("route ADD 192.168.0.183", payload["adminRouteCommand"])
        self.assertEqual(len(payload["configPaths"]), 2)

    def test_full_sync_launcher_dry_run_prints_preview_without_starting_voice_loop(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Start-Mira-Light-Windows-Full-Sync.ps1"),
            "-DryRun",
            "-Json",
            "-NoPlay",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        json_start = result.stdout.find("{")
        self.assertGreaterEqual(json_start, 0, result.stdout)
        payload = json.loads(result.stdout[json_start:])
        self.assertEqual(payload["bridgeUrl"], "http://127.0.0.1:19783")
        self.assertIn("--transcriber stepfun", payload["command"])
        self.assertIn("--min-speech-cv 0.35", payload["command"])

    def test_full_sync_launcher_dry_run_bridge_uses_runtime_dry_run(self) -> None:
        result = run_powershell(
            "-File",
            str(PACKAGE_ROOT / "Start-Mira-Light-Windows-Full-Sync.ps1"),
            "-DryRun",
            "-Json",
            "-DryRunBridge",
            "-BridgePort",
            "19784",
            "-NoPlay",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        json_start = result.stdout.find("{")
        self.assertGreaterEqual(json_start, 0, result.stdout)
        payload = json.loads(result.stdout[json_start:])
        self.assertEqual(payload["bridgeUrl"], "http://127.0.0.1:19784")
        self.assertIn("-RuntimeDryRun", payload["bridgeCommand"])
        self.assertNotIn("-DryRun -Json", payload["bridgeCommand"])

    def test_export_full_sync_trace_packages_text_and_json_without_audio_by_default(self) -> None:
        script = PACKAGE_ROOT / "Export-Mira-Light-Windows-Full-Sync-Trace.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = root / "session"
            turn = session / "turn-001"
            turn.mkdir(parents=True)
            (session / "session.json").write_text('{"ok":true}\n', encoding="utf-8")
            (turn / "turn.json").write_text('{"intent":"chat"}\n', encoding="utf-8")
            (turn / "transcript.txt").write_text("mira 跳个舞吧\n", encoding="utf-8")
            (turn / "reply.txt").write_text("啾。\n", encoding="utf-8")
            (turn / "input.wav").write_bytes(b"fake wav")
            output_dir = root / "exports"

            result = run_powershell(
                "-File",
                str(script),
                "-SessionDir",
                str(session),
                "-OutputDir",
                str(output_dir),
                "-Json",
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            zip_path = Path(payload["zipPath"])
            self.assertTrue(zip_path.exists())
            self.assertIn("turn-001/turn.json", payload["included"])
            self.assertIn("turn-001/transcript.txt", payload["included"])
            self.assertNotIn("turn-001/input.wav", payload["included"])

    def test_export_full_sync_trace_skips_newer_empty_sessions(self) -> None:
        script = PACKAGE_ROOT / "Export-Mira-Light-Windows-Full-Sync-Trace.ps1"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_dir = root / "runtime"
            valid_session = runtime_dir / "2026-06-18T10-00-00"
            valid_turn = valid_session / "turn-001"
            valid_turn.mkdir(parents=True)
            (valid_turn / "turn.json").write_text('{"intent":"chat"}\n', encoding="utf-8")
            empty_session = runtime_dir / "2026-06-18T11-00-00"
            empty_session.mkdir(parents=True)
            (empty_session / "session.json").write_text('{"ok":true}\n', encoding="utf-8")
            output_dir = root / "exports"

            result = run_powershell(
                "-File",
                str(script),
                "-RuntimeDir",
                str(runtime_dir),
                "-OutputDir",
                str(output_dir),
                "-Json",
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(Path(payload["sessionDir"]).name, valid_session.name)
            self.assertIn("turn-001/turn.json", payload["included"])


if __name__ == "__main__":
    unittest.main()
