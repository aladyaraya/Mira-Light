import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parent.parent
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

import mira_sync
import rokid_watch_daemon


class MiraSyncStabilityTests(unittest.TestCase):
    def test_scan_and_queue_events_tolerates_invalid_watch_state_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            (state_dir / "watch-state.json").write_text("", encoding="utf-8")

            result = mira_sync.scan_and_queue_events(state_dir)

            self.assertEqual([], result["queued_events"])
            self.assertTrue((state_dir / "mira-sync" / "checkpoint.json").is_file())

    def test_scan_and_queue_events_skips_invalid_job_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            job_dir = state_dir / "jobs" / "job-bad"
            job_dir.mkdir(parents=True)
            (job_dir / "job.json").write_text("", encoding="utf-8")

            result = mira_sync.scan_and_queue_events(state_dir)

            self.assertEqual([], result["queued_events"])
            self.assertTrue((state_dir / "mira-sync" / "sync-status.json").is_file())


class RokidWatchStabilityTests(unittest.TestCase):
    def test_poll_once_continues_remote_scan_when_import_check_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            config_path = state_dir / "rokid-watch-config.json"
            state_path = state_dir / "rokid-watch-state.json"
            remote_path = "/sdcard/Download/Rokid AI/img-20260324-182020-f7-P0-0.jpg"

            config = {
                **rokid_watch_daemon.default_config(adb_path="/tmp/adb", adb_serial="__ADB_SERIAL__"),
                "state_dir": str(state_dir),
                "output_dir": str(state_dir / "output"),
                "enabled": True,
            }
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            state_path.write_text(
                json.dumps(
                    {
                        "initialized": True,
                        "files": {
                            remote_path: {
                                "last_seen_size": 12345,
                                "stable_polls": 1,
                                "processed": False,
                                "processed_size": None,
                                "processed_reason": None,
                                "last_error": None,
                                "last_attempt_at": None,
                            }
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            def import_check_fails(**_kwargs):
                raise subprocess.CalledProcessError(
                    1,
                    [
                        "__HOME__/Library/Android/sdk/platform-tools/adb",
                        "-s",
                        "__ADB_SERIAL__",
                        "shell",
                        "dumpsys activity activities",
                    ],
                )

            def list_remote_images_impl(**_kwargs):
                return [{"remote_path": remote_path, "size": 12345}]

            def process_remote_image_impl(*, remote_item, config):
                self.assertEqual(remote_path, remote_item["remote_path"])
                self.assertEqual(str(state_dir), config["state_dir"])
                return {
                    "job_id": "job-1",
                    "remote_path": remote_item["remote_path"],
                    "local_path": str(state_dir / "artifacts" / "img.jpg"),
                    "output_path": str(state_dir / "output" / "generated.jpg"),
                    "metadata_path": str(state_dir / "output" / "generated.metadata.json"),
                    "printer_job_id": "printer-job-1",
                    "deduplicated": False,
                    "printed": True,
                }

            result = rokid_watch_daemon.poll_once(
                config_path=config_path,
                state_path=state_path,
                maybe_trigger_import_impl=import_check_fails,
                list_remote_images_impl=list_remote_images_impl,
                process_remote_image_impl=process_remote_image_impl,
            )

            self.assertEqual([remote_path], result["processed_remote_paths"])
            self.assertEqual("import_check_failed", result["import"]["reason"])
            self.assertIn("dumpsys activity activities", result["import"]["error"])

            persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(1, persisted_state["last_seen_count"])
            self.assertTrue(persisted_state["files"][remote_path]["processed"])


if __name__ == "__main__":
    unittest.main()
