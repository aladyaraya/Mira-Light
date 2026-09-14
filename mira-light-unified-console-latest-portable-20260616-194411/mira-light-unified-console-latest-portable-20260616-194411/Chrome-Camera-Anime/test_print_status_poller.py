import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


RUNTIME_DIR = Path.home() / ".openclaw-chrome-camera-anime" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

import job_store
import mira_sync
import print_status_poller


class PrintStatusPollerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temp_dir.name) / "state"
        self.queue_name = "Test_Printer"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_runner(
        self,
        *,
        active_stdout: str = "",
        completed_stdout: str = "",
        completed_long_stdout: str = "",
    ):
        def fake_runner(command, check=False, capture_output=False, text=False):
            output_map = {
                ("lpstat", "-W", "not-completed", "-o", self.queue_name): active_stdout,
                ("lpstat", "-W", "completed", "-o", self.queue_name): completed_stdout,
                ("lpstat", "-l", "-W", "completed", "-o", self.queue_name): completed_long_stdout,
            }
            stdout = output_map.get(tuple(command))
            if stdout is None:
                raise AssertionError(f"unexpected command: {command}")
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        return fake_runner

    def test_completed_job_with_user_cancel_alert_is_not_marked_completed(self) -> None:
        job = job_store.create_job(self.state_dir, trigger="rokid-watch", queue_capture=False)
        job_store.update_job(
            self.state_dir,
            job["job_id"],
            status="print_submitted",
            printer_job_id="Test_Printer-42（1个文件）",
        )
        runner = self.make_runner(
            completed_stdout="Test_Printer-42 __USER__ 331776 Sun Mar 22 12:42:41 2026\n",
            completed_long_stdout=(
                "Test_Printer-42 __USER__ 331776 Sun Mar 22 12:42:41 2026\n"
                "\t警报：job-canceled-by-user\n"
                "\t已排队进行Test_Printer\n"
            ),
        )

        with patch.object(
            print_status_poller.print_client,
            "read_bridge_profile",
            return_value={"printer": {"queue_name": self.queue_name}},
        ):
            result = print_status_poller.poll_once(
                state_dir=self.state_dir,
                runner=runner,
            )

        updated = job_store.load_job(self.state_dir, job["job_id"])
        self.assertEqual("print_cancelled", updated["status"])
        self.assertIn("print_cancelled_at", updated)
        self.assertNotIn("print_completed_at", updated)
        self.assertEqual(["Test_Printer-42"], result["cancelled_job_ids"])
        self.assertEqual([], result["completed_job_ids"])

    def test_completed_job_without_cancel_alert_is_marked_completed(self) -> None:
        job = job_store.create_job(self.state_dir, trigger="rokid-watch", queue_capture=False)
        job_store.update_job(
            self.state_dir,
            job["job_id"],
            status="print_submitted",
            printer_job_id="Test_Printer-99（1个文件）",
        )
        runner = self.make_runner(
            completed_stdout="Test_Printer-99 __USER__ 331776 Sun Mar 22 12:42:41 2026\n",
            completed_long_stdout=(
                "Test_Printer-99 __USER__ 331776 Sun Mar 22 12:42:41 2026\n"
                "\t警报：processing-to-stop-point\n"
                "\t已排队进行Test_Printer\n"
            ),
        )

        with patch.object(
            print_status_poller.print_client,
            "read_bridge_profile",
            return_value={"printer": {"queue_name": self.queue_name}},
        ):
            result = print_status_poller.poll_once(
                state_dir=self.state_dir,
                runner=runner,
            )

        updated = job_store.load_job(self.state_dir, job["job_id"])
        self.assertEqual("print_completed", updated["status"])
        self.assertIn("print_completed_at", updated)
        self.assertEqual(["Test_Printer-99"], result["completed_job_ids"])
        self.assertEqual([], result["cancelled_job_ids"])

    def test_mira_sync_emits_print_cancelled_event(self) -> None:
        event_type, payload, summary = mira_sync._job_payload(
            {
                "job_id": "job-123",
                "status": "print_cancelled",
                "printer_job_id": "Test_Printer-42",
                "print_cancelled_at": "2026-03-22T04:42:41Z",
                "print_cancel_reason": "job-canceled-by-user",
            }
        )

        self.assertEqual("print_cancelled", event_type)
        self.assertEqual("Test_Printer-42", payload["printer_job_id"])
        self.assertEqual("2026-03-22T04:42:41Z", payload["print_cancelled_at"])
        self.assertEqual("job-canceled-by-user", payload["print_cancel_reason"])
        self.assertEqual("Print cancelled for job-123", summary)


if __name__ == "__main__":
    unittest.main()
