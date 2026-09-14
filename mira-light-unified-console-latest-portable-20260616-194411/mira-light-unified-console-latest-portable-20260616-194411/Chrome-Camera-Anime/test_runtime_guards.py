import tempfile
import unittest
from pathlib import Path
import sys


RUNTIME_DIR = Path.home() / ".openclaw-chrome-camera-anime" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

import job_store
import install_launchd
import rokid_watch_daemon
import worker_daemon


class RuntimeGuardsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temp_dir.name) / "state"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def rokid_config(self) -> dict[str, object]:
        return {
            "state_dir": str(self.state_dir),
            "output_dir": str(self.output_dir),
            "print_media": job_store.DEFAULT_PRINT_MEDIA,
            "adb_path": "adb",
            "adb_serial": "serial",
            "model": "test-model",
            "size": "1920x1920",
            "response_format": "url",
            "api_url": "https://example.invalid",
            "timeout": 30,
            "style_slug": "rokid-ghibli",
            "style_prompt": "test style",
        }

    def test_create_job_without_capture_queue_does_not_enqueue_capture(self) -> None:
        job = job_store.create_job(
            self.state_dir,
            trigger="rokid-watch",
            metadata={"source": "rokid-watch"},
            queue_capture=False,
        )

        self.assertEqual("created", job["status"])
        self.assertEqual([], job_store.list_queue_job_ids(self.state_dir, "capture"))
        self.assertTrue(job_store.job_path(self.state_dir, job["job_id"]).is_file())

    def test_install_launchd_runtime_copy_items_include_xiaomi_phone_backend(self) -> None:
        self.assertIn("xiaomi_home_print.py", install_launchd.RUNTIME_COPY_ITEMS)

    def test_process_print_job_is_idempotent_when_printer_job_id_exists(self) -> None:
        job = job_store.create_job(self.state_dir, trigger="chrome_launch")
        output_path = self.output_dir / "already-printed.jpeg"
        output_path.write_bytes(b"already-printed")
        job_store.update_job(
            self.state_dir,
            job["job_id"],
            status="print_submitted",
            output_path=str(output_path),
            printer_job_id="__CUPS_QUEUE_NAME__-42",
        )

        submit_calls: list[tuple[tuple, dict]] = []

        def fake_submit(*args, **kwargs):
            submit_calls.append((args, kwargs))
            raise AssertionError("submit_print_job should not be called twice")

        updated = worker_daemon.process_print_job(
            state_dir=self.state_dir,
            job_id=job["job_id"],
            submit_print_job_impl=fake_submit,
            stop_expression_monitor_impl=lambda *_args, **_kwargs: None,
        )

        self.assertEqual([], submit_calls)
        self.assertEqual("__CUPS_QUEUE_NAME__-42", updated["printer_job_id"])
        self.assertEqual("print_submitted", updated["status"])

    def test_claim_next_due_job_prefers_earliest_ready_time_over_enqueue_time(self) -> None:
        first = job_store.create_job(
            self.state_dir,
            trigger="chrome_launch",
            queue_capture=False,
            now_iso="2026-03-24T10:00:00Z",
        )
        second = job_store.create_job(
            self.state_dir,
            trigger="rokid-watch",
            queue_capture=False,
            now_iso="2026-03-24T10:00:01Z",
        )
        job_store.enqueue_job(
            self.state_dir,
            first["job_id"],
            "print",
            status="queued_print",
            now_iso="2026-03-24T10:00:02Z",
            fields={"print_not_before_at": "2026-03-24T10:02:00Z"},
        )
        job_store.enqueue_job(
            self.state_dir,
            second["job_id"],
            "print",
            status="queued_print",
            now_iso="2026-03-24T10:00:03Z",
            fields={"print_not_before_at": "2026-03-24T10:01:00Z"},
        )

        claimed = job_store.claim_next_due_job(
            self.state_dir,
            "print",
            due_field="print_not_before_at",
            claimed_status="submitting_print",
            now_iso="2026-03-24T10:03:00Z",
        )

        self.assertIsNotNone(claimed)
        self.assertEqual(second["job_id"], claimed["job_id"])

    def test_process_generation_job_uses_80_second_print_delay(self) -> None:
        job = job_store.create_job(
            self.state_dir,
            trigger="chrome_launch",
            queue_capture=False,
            now_iso="2026-03-24T10:48:54Z",
        )
        portrait_path = self.output_dir / "portrait.jpg"
        portrait_path.write_bytes(b"portrait")
        landscape_path = self.output_dir / "landscape.jpg"
        landscape_path.write_bytes(b"landscape")
        job_store.update_job(
            self.state_dir,
            job["job_id"],
            portrait_path=str(portrait_path),
            landscape={"id": "fig1", "path": str(landscape_path)},
        )

        rendered_path = self.output_dir / "rendered.jpeg"
        rendered_path.write_bytes(b"rendered")

        updated = worker_daemon.process_generation_job(
            state_dir=self.state_dir,
            job_id=job["job_id"],
            generate_for_job_impl=lambda **_kwargs: {
                "output_path": str(rendered_path),
                "metadata_path": str(self.output_dir / "rendered.metadata.json"),
                "response_model": "test-model",
            },
        )

        self.assertEqual("queued_print", updated["status"])
        self.assertEqual("2026-03-24T10:50:14Z", updated["print_not_before_at"])
        self.assertEqual("bridge", updated["print_backend"])

    def test_rokid_process_remote_image_deduplicates_same_content(self) -> None:
        payload = b"same-rokid-image"
        print_calls: list[tuple[str, str]] = []
        generated_count = 0

        def fake_pull(*, remote_path: str, local_path: Path, **_kwargs) -> Path:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payload)
            return local_path

        def fake_generate(**kwargs):
            nonlocal generated_count
            generated_count += 1
            output_path = self.output_dir / f"generated-{generated_count}.jpeg"
            output_path.write_bytes(f"generated-{generated_count}".encode("utf-8"))
            return {
                "output_path": str(output_path),
                "request_summary": {"model": kwargs["model"]},
                "response_model": kwargs["model"],
                "response_url": f"https://example.invalid/{generated_count}.jpeg",
            }

        def fake_submit(output_path: Path, media: str):
            print_calls.append((output_path.name, media))
            return {"job_id": f"printer-{len(print_calls)}"}

        first = rokid_watch_daemon.process_remote_image(
            remote_item={"remote_path": "/sdcard/Download/Rokid AI/img-a.jpg", "size": len(payload)},
            config=self.rokid_config(),
            pull_remote_image_impl=fake_pull,
            generate_stylized_remote_image_impl=fake_generate,
            submit_print_job_impl=fake_submit,
        )
        second = rokid_watch_daemon.process_remote_image(
            remote_item={"remote_path": "/sdcard/Download/Rokid AI/img-b.jpg", "size": len(payload)},
            config=self.rokid_config(),
            pull_remote_image_impl=fake_pull,
            generate_stylized_remote_image_impl=fake_generate,
            submit_print_job_impl=fake_submit,
        )

        self.assertEqual(0, len(print_calls))
        self.assertEqual(1, generated_count)
        self.assertTrue(second["deduplicated"])
        self.assertFalse(second["printed"])
        self.assertEqual(first["job_id"], second["duplicate_of_job_id"])

    def test_rokid_process_remote_image_queues_print_in_shared_fifo_queue(self) -> None:
        payload = b"rokid-image"
        submit_calls: list[str] = []
        submit_mobile_calls: list[str] = []

        def fake_pull(*, remote_path: str, local_path: Path, **_kwargs) -> Path:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payload)
            return local_path

        def fake_generate(**_kwargs):
            output_path = self.output_dir / "rokid-generated.jpeg"
            output_path.write_bytes(b"generated")
            return {
                "output_path": str(output_path),
                "request_summary": {"model": "test-model"},
                "response_model": "test-model",
                "response_url": "https://example.invalid/generated.jpeg",
            }

        def fake_submit(source_path: Path, **_kwargs):
            submit_calls.append(source_path.name)
            return {"job_id": "bridge-job-1"}

        def fake_submit_mobile(source_path: Path, **_kwargs):
            submit_mobile_calls.append(source_path.name)
            return {"job_id": "xiaomi-job-1"}

        result = rokid_watch_daemon.process_remote_image(
            remote_item={"remote_path": "/sdcard/Download/Rokid AI/img-c.jpg", "size": len(payload)},
            config={**self.rokid_config(), "print_backend": "xiaomi_home_share"},
            pull_remote_image_impl=fake_pull,
            generate_stylized_remote_image_impl=fake_generate,
            submit_print_job_impl=fake_submit,
            submit_mobile_print_job_impl=fake_submit_mobile,
        )

        self.assertEqual([], submit_calls)
        self.assertEqual([], submit_mobile_calls)
        self.assertFalse(result["printed"])
        self.assertEqual("queued_print", result["status"])
        self.assertEqual([result["job_id"]], job_store.list_queue_job_ids(self.state_dir, "print"))

        persisted = job_store.load_job(self.state_dir, result["job_id"])
        self.assertEqual("queued_print", persisted["status"])
        self.assertEqual("xiaomi_home_share", persisted["print_backend"])
        self.assertIn("print_not_before_at", persisted)


if __name__ == "__main__":
    unittest.main()
