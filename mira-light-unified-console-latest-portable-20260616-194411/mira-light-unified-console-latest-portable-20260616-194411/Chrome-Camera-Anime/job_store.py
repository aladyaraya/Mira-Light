#!/usr/bin/env python3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_STATE_DIR = Path(__file__).resolve().parent / ".runtime" / "state"
JOBS_DIRNAME = "jobs"
QUEUES_DIRNAME = "queues"
DEFAULT_PRINT_MEDIA = "4x6.Fullbleed"


def current_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso(iso_text: str) -> datetime:
    return datetime.fromisoformat(iso_text.replace("Z", "+00:00"))


def jobs_dir(state_dir: Path) -> Path:
    return state_dir / JOBS_DIRNAME


def queues_dir(state_dir: Path) -> Path:
    return state_dir / QUEUES_DIRNAME


def queue_dir(state_dir: Path, queue_name: str) -> Path:
    return queues_dir(state_dir) / queue_name


def ensure_state_tree(state_dir: Path) -> None:
    jobs_dir(state_dir).mkdir(parents=True, exist_ok=True)
    for queue_name in ("capture", "generate", "print"):
        queue_dir(state_dir, queue_name).mkdir(parents=True, exist_ok=True)


def job_dir(state_dir: Path, job_id: str) -> Path:
    return jobs_dir(state_dir) / job_id


def job_path(state_dir: Path, job_id: str) -> Path:
    return job_dir(state_dir, job_id) / "job.json"


def artifact_dir(state_dir: Path, job_id: str) -> Path:
    return job_dir(state_dir, job_id) / "artifacts"


def _queue_marker_name(created_at: str, job_id: str) -> str:
    return f"{created_at.replace('-', '').replace(':', '')}_{job_id}.json"


def _queue_marker_path(state_dir: Path, queue_name: str, created_at: str, job_id: str) -> Path:
    return queue_dir(state_dir, queue_name) / _queue_marker_name(created_at, job_id)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp"
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def load_job(state_dir: Path, job_id: str) -> dict:
    return json.loads(job_path(state_dir, job_id).read_text(encoding="utf-8"))


def save_job(state_dir: Path, job: dict) -> dict:
    _write_json(job_path(state_dir, job["job_id"]), job)
    return job


def create_job(
    state_dir: Path,
    *,
    trigger: str = "manual",
    metadata: dict | None = None,
    now_iso: str | None = None,
    queue_capture: bool = True,
) -> dict:
    ensure_state_tree(state_dir)
    created_at = now_iso or current_iso()
    job_id = f"job-{created_at.replace('-', '').replace(':', '').replace('T', '-').replace('Z', '')}-{uuid.uuid4().hex[:8]}"
    job = {
        "job_id": job_id,
        "trigger": trigger,
        "metadata": metadata or {},
        "status": "queued_capture" if queue_capture else "created",
        "created_at": created_at,
        "updated_at": created_at,
        "print_media": DEFAULT_PRINT_MEDIA,
    }
    job_dir(state_dir, job_id).mkdir(parents=True, exist_ok=True)
    artifact_dir(state_dir, job_id).mkdir(parents=True, exist_ok=True)
    save_job(state_dir, job)
    if queue_capture:
        _write_json(
            _queue_marker_path(state_dir, "capture", created_at, job_id),
            {"job_id": job_id, "queue": "capture", "created_at": created_at},
        )
    return job


def list_queue_job_ids(state_dir: Path, queue_name: str) -> list[str]:
    ensure_state_tree(state_dir)
    paths = sorted(queue_dir(state_dir, queue_name).glob("*.json"))
    return [json.loads(path.read_text(encoding="utf-8"))["job_id"] for path in paths]


def update_job(state_dir: Path, job_id: str, *, now_iso: str | None = None, **fields) -> dict:
    job = load_job(state_dir, job_id)
    job.update(fields)
    job["updated_at"] = now_iso or current_iso()
    return save_job(state_dir, job)


def claim_next_job(
    state_dir: Path,
    queue_name: str,
    *,
    claimed_status: str,
    now_iso: str | None = None,
) -> dict | None:
    ensure_state_tree(state_dir)
    entries = sorted(queue_dir(state_dir, queue_name).glob("*.json"))
    if not entries:
        return None

    entry_path = entries[0]
    payload = json.loads(entry_path.read_text(encoding="utf-8"))
    entry_path.unlink()
    claimed_at = now_iso or current_iso()
    return update_job(
        state_dir,
        payload["job_id"],
        now_iso=claimed_at,
        status=claimed_status,
        **{f"{queue_name}_claimed_at": claimed_at},
    )


def claim_next_due_job(
    state_dir: Path,
    queue_name: str,
    *,
    due_field: str,
    claimed_status: str,
    now_iso: str | None = None,
) -> dict | None:
    ensure_state_tree(state_dir)
    claimed_at = now_iso or current_iso()
    now_dt = parse_iso(claimed_at)

    eligible_entries: list[tuple[datetime, datetime, Path, dict]] = []
    for entry_path in sorted(queue_dir(state_dir, queue_name).glob("*.json")):
        payload = json.loads(entry_path.read_text(encoding="utf-8"))
        job = load_job(state_dir, payload["job_id"])
        due_value = job.get(due_field)
        due_at = parse_iso(str(due_value)) if due_value else parse_iso(str(payload["created_at"]))
        if due_at > now_dt:
            continue
        queued_at = parse_iso(str(payload["created_at"]))
        eligible_entries.append((due_at, queued_at, entry_path, payload))

    if not eligible_entries:
        return None

    _, _, entry_path, payload = min(
        eligible_entries,
        key=lambda item: (item[0], item[1], item[3]["job_id"]),
    )
    entry_path.unlink()
    return update_job(
        state_dir,
        payload["job_id"],
        now_iso=claimed_at,
        status=claimed_status,
        **{f"{queue_name}_claimed_at": claimed_at},
    )
    return None


def enqueue_job(
    state_dir: Path,
    job_id: str,
    queue_name: str,
    *,
    status: str,
    fields: dict | None = None,
    now_iso: str | None = None,
) -> dict:
    ensure_state_tree(state_dir)
    queued_at = now_iso or current_iso()
    job = update_job(
        state_dir,
        job_id,
        now_iso=queued_at,
        status=status,
        **(fields or {}),
    )
    _write_json(
        _queue_marker_path(state_dir, queue_name, queued_at, job_id),
        {"job_id": job_id, "queue": queue_name, "created_at": queued_at},
    )
    return job


def list_jobs(state_dir: Path) -> list[dict]:
    ensure_state_tree(state_dir)
    jobs = []
    for path in sorted(jobs_dir(state_dir).glob("*/job.json")):
        jobs.append(json.loads(path.read_text(encoding="utf-8")))
    return jobs


def mark_print_submitted(
    state_dir: Path,
    job_id: str,
    *,
    printer_job_id: str,
    print_response: dict,
    now_iso: str | None = None,
) -> dict:
    job = load_job(state_dir, job_id)
    if job.get("printer_job_id"):
        return job

    submitted_at = now_iso or current_iso()
    job.update(
        {
            "status": "print_submitted",
            "printer_job_id": printer_job_id,
            "print_response": print_response,
            "print_submitted_at": submitted_at,
            "updated_at": submitted_at,
        }
    )
    return save_job(state_dir, job)
