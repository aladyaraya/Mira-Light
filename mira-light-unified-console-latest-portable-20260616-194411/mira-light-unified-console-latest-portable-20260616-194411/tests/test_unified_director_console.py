from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "mira-light-unified-director-console" / "shenzhen_console.py"
MODULE_DIR = MODULE_PATH.parent
WEB_DIR = MODULE_DIR / "web"
INDEX_PATH = WEB_DIR / "index.html"
APP_JS_PATH = WEB_DIR / "app.js"
REGISTRY_PATH = MODULE_DIR / "scene_registry.json"

if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("unified_director_console", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("unified_director_console", module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


console = load_module()


class UnifiedDirectorConsoleSshTest(unittest.TestCase):
    def setUp(self) -> None:
        console.PLINK_HOSTKEY_CACHE.clear()

    def test_extract_plink_hostkey_from_batch_error(self) -> None:
        stderr = """
The host key is not cached for this server:
  192.168.0.183 (port 22)
The server's ssh-ed25519 key fingerprint is:
  ssh-ed25519 255 SHA256:K8oyEoddaZ4keNu39exAqMJLDEcncgoQGcRPQ898Bb4
Connection abandoned.
FATAL ERROR: Cannot confirm a host key in batch mode
"""
        self.assertEqual(
            console.extract_plink_hostkey(stderr),
            "ssh-ed25519 255 SHA256:K8oyEoddaZ4keNu39exAqMJLDEcncgoQGcRPQ898Bb4",
        )

    def test_resolve_plink_hostkey_defaults_for_demo_board(self) -> None:
        with mock.patch.dict(console.os.environ, {}, clear=True):
            self.assertEqual(
                console.resolve_plink_hostkey(host="192.168.0.183", port=22, user="root"),
                "SHA256:K8oyEoddaZ4keNu39exAqMJLDEcncgoQGcRPQ898Bb4",
            )

    def test_run_remote_script_retries_plink_with_learned_hostkey_and_caches_it(self) -> None:
        learned_hostkey = "ssh-ed25519 255 SHA256:K8oyEoddaZ4keNu39exAqMJLDEcncgoQGcRPQ898Bb4"
        commands: list[list[str]] = []
        responses = [
            subprocess.CompletedProcess(
                args=["plink.exe"],
                returncode=1,
                stdout="",
                stderr=(
                    "The server's ssh-ed25519 key fingerprint is:\n"
                    f"  {learned_hostkey}\n"
                    "FATAL ERROR: Cannot confirm a host key in batch mode\n"
                ),
            ),
            subprocess.CompletedProcess(args=["plink.exe"], returncode=0, stdout="ok\n", stderr=""),
            subprocess.CompletedProcess(args=["plink.exe"], returncode=0, stdout="cached\n", stderr=""),
        ]

        def fake_run_local_command(command: list[str], timeout_seconds: float, env=None):
            commands.append(command)
            return responses.pop(0)

        with (
            mock.patch.object(console.shutil, "which", return_value="plink.exe"),
            mock.patch.object(console.os, "name", "nt"),
            mock.patch.object(console, "adapt_board_script", side_effect=lambda script: script),
            mock.patch.object(console, "run_local_command", side_effect=fake_run_local_command),
            mock.patch.dict(console.os.environ, {}, clear=True),
        ):
            first = console._run_remote_script_unlocked(
                script="echo test",
                host="192.168.0.184",
                port=22,
                user="root",
                password="",
                timeout_seconds=3.0,
            )
            second = console._run_remote_script_unlocked(
                script="echo test",
                host="192.168.0.184",
                port=22,
                user="root",
                password="",
                timeout_seconds=3.0,
            )

        self.assertEqual(first["returnCode"], 0)
        self.assertEqual(second["returnCode"], 0)
        self.assertEqual(len(commands), 3)
        self.assertNotIn("-hostkey", commands[0])
        self.assertIn("-hostkey", commands[1])
        self.assertEqual(commands[1][commands[1].index("-hostkey") + 1], learned_hostkey)
        self.assertIn("-hostkey", commands[2])
        self.assertEqual(commands[2][commands[2].index("-hostkey") + 1], learned_hostkey)


class UnifiedDirectorConsoleFrontendTest(unittest.TestCase):
    def test_light_showcase_panel_is_visible_on_primary_console(self) -> None:
        html = INDEX_PATH.read_text(encoding="utf-8")

        self.assertIn("灯光展示", html)
        self.assertIn('id="light-showcase-grid"', html)

    def test_light_showcase_renders_only_bounded_light_actions(self) -> None:
        app_js = APP_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("LIGHT_SHOWCASE_IDS", app_js)
        self.assertIn("function renderLightShowcase", app_js)
        self.assertIn('action.risk !== "light-only"', app_js)
        self.assertIn("renderLightShowcase();", app_js)


class UnifiedDirectorConsoleRegistryTest(unittest.TestCase):
    def test_emergency_stop_does_not_kill_board_tcp_bridge(self) -> None:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        emergency = next(action for action in registry["quickActions"] if action["id"] == "force_stop_neutral")
        stop_script = emergency["commands"][0]["command"]

        self.assertNotIn("[s]ervo_.*", stop_script)
        self.assertNotIn("rdk_bus_servo_tcp_bridge.py", stop_script)


if __name__ == "__main__":
    unittest.main()
