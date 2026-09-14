#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import job_store
import print_client


DEFAULT_STATE_DIR = job_store.DEFAULT_STATE_DIR


def parse_lpstat_jobs(stdout: str) -> set[str]:
    job_ids = set()
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        job_ids.add(stripped.split()[0])
    return job_ids


def parse_lpstat_job_details(stdout: str) -> dict[str, list[str]]:
    details: dict[str, list[str]] = {}
    current_job_id: str | None = None
    for line in stdout.splitlines():
        stripped = line.rstrip()
        if not stripped:
            continue
        if line[:1].isspace():
            if current_job_id is not None:
                details.setdefault(current_job_id, []).append(stripped.strip())
            continue
        current_job_id = stripped.split()[0]
        details.setdefault(current_job_id, [])
    return details


def normalize_printer_job_id(job_id: str) -> str:
    return (
        job_id.split("（", 1)[0]
        .split("(", 1)[0]
        .strip()
    )


def job_has_user_cancelled_alert(job_details: list[str]) -> bool:
    for line in job_details:
        normalized = line.replace("：", ":").lower()
        if "canceled-by-user" in normalized or "cancelled-by-user" in normalized:
            return True
    return False


def mark_job_completed(state_dir: Path, job_id: str) -> dict:
    return job_store.update_job(
        state_dir,
        job_id,
        status="print_completed",
        print_completed_at=job_store.current_iso(),
    )


def mark_job_cancelled(state_dir: Path, job_id: str) -> dict:
    return job_store.update_job(
        state_dir,
        job_id,
        status="print_cancelled",
        print_cancelled_at=job_store.current_iso(),
        print_cancel_reason="job-canceled-by-user",
    )


def poll_once(
    *,
    state_dir: Path = DEFAULT_STATE_DIR,
    runner=subprocess.run,
) -> dict[str, object]:
    queue_name = print_client.resolve_printer_queue_name(runner=runner)
    if not queue_name:
        raise RuntimeError("no printer queue available")
    active_result = runner(
        ["lpstat", "-W", "not-completed", "-o", queue_name],
        check=False,
        capture_output=True,
        text=True,
    )
    completed_result = runner(
        ["lpstat", "-W", "completed", "-o", queue_name],
        check=False,
        capture_output=True,
        text=True,
    )
    completed_long_result = runner(
        ["lpstat", "-l", "-W", "completed", "-o", queue_name],
        check=False,
        capture_output=True,
        text=True,
    )
    active_job_ids = parse_lpstat_jobs(active_result.stdout)
    completed_job_ids = parse_lpstat_jobs(completed_result.stdout)
    completed_job_details = parse_lpstat_job_details(completed_long_result.stdout)
    newly_completed: list[str] = []
    cancelled_job_ids: list[str] = []

    for job in job_store.list_jobs(state_dir):
        printer_job_id = job.get("printer_job_id")
        if not printer_job_id:
            continue
        normalized_job_id = normalize_printer_job_id(str(printer_job_id))
        if normalized_job_id in completed_job_ids:
            if job_has_user_cancelled_alert(completed_job_details.get(normalized_job_id, [])):
                if job.get("status") != "print_cancelled":
                    mark_job_cancelled(state_dir, job["job_id"])
                    cancelled_job_ids.append(normalized_job_id)
            elif job.get("status") != "print_completed":
                mark_job_completed(state_dir, job["job_id"])
                newly_completed.append(normalized_job_id)
        elif normalized_job_id in active_job_ids and job.get("status") != "print_active":
            job_store.update_job(
                state_dir,
                job["job_id"],
                status="print_active",
                print_active_at=job_store.current_iso(),
            )

    return {
        "queue_name": queue_name,
        "active_job_ids": sorted(active_job_ids),
        "completed_job_ids": sorted(newly_completed),
        "cancelled_job_ids": sorted(cancelled_job_ids),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Poll local lpstat output and update queued anime print jobs.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    args = parser.parse_args(argv)
    print(json.dumps(poll_once(state_dir=args.state_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
