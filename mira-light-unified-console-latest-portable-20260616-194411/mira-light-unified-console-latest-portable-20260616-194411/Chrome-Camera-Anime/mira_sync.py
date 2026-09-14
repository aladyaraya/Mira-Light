#!/usr/bin/env python3
import copy
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_STATE_DIR = Path.home() / ".openclaw-chrome-camera-anime"
SYNC_DIRNAME = "mira-sync"
OUTBOX_DIRNAME = "outbox"
DELIVERED_DIRNAME = "delivered"
CHECKPOINT_FILENAME = "checkpoint.json"
SYNC_STATUS_FILENAME = "sync-status.json"
DEFAULT_HOOK_URL = "http://127.0.0.1:18791/hooks/agent"
DEFAULT_HOOK_NAME = "ChromeCameraAnime"
DEFAULT_HOOK_AGENT_ID = "main"
DEFAULT_HOOK_WAKE_MODE = "now"
DEFAULT_TIMEOUT = 20


def current_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clone_default(default):
    return copy.deepcopy(default)


def read_json(path: Path, default=None):
    if not path.is_file():
        return _clone_default(default if default is not None else {})
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return _clone_default(default if default is not None else {})
    if not raw.strip():
        return _clone_default(default if default is not None else {})
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _clone_default(default if default is not None else {})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp"
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def sync_dir(state_dir: Path) -> Path:
    return state_dir / SYNC_DIRNAME


def outbox_dir(state_dir: Path) -> Path:
    return sync_dir(state_dir) / OUTBOX_DIRNAME


def delivered_dir(state_dir: Path) -> Path:
    return sync_dir(state_dir) / DELIVERED_DIRNAME


def checkpoint_path(state_dir: Path) -> Path:
    return sync_dir(state_dir) / CHECKPOINT_FILENAME


def sync_status_path(state_dir: Path) -> Path:
    return sync_dir(state_dir) / SYNC_STATUS_FILENAME


def ensure_sync_tree(state_dir: Path) -> None:
    outbox_dir(state_dir).mkdir(parents=True, exist_ok=True)
    delivered_dir(state_dir).mkdir(parents=True, exist_ok=True)


def load_checkpoint(state_dir: Path) -> dict:
    return read_json(checkpoint_path(state_dir))


def save_checkpoint(state_dir: Path, checkpoint: dict) -> None:
    write_json(checkpoint_path(state_dir), checkpoint)


def _default_sync_status() -> dict[str, object]:
    return {
        "updated_at": None,
        "last_scan_at": None,
        "last_delivery_attempt_at": None,
        "last_delivery_error": None,
        "last_skipped_reason": None,
        "last_success_at": None,
        "pending_count": 0,
        "delivered_count": 0,
    }


def load_sync_status(state_dir: Path) -> dict[str, object]:
    payload = _default_sync_status()
    payload.update(read_json(sync_status_path(state_dir)))
    return payload


def save_sync_status(state_dir: Path, status: dict[str, object]) -> dict[str, object]:
    ensure_sync_tree(state_dir)
    payload = _default_sync_status()
    payload.update(status)
    payload["pending_count"] = len(list(outbox_dir(state_dir).glob("*.json")))
    payload["delivered_count"] = len(list(delivered_dir(state_dir).glob("*.json")))
    payload["updated_at"] = current_iso()
    write_json(sync_status_path(state_dir), payload)
    return payload


def update_sync_status(state_dir: Path, **changes: object) -> dict[str, object]:
    status = load_sync_status(state_dir)
    status.update(changes)
    return save_sync_status(state_dir, status)


def _sanitize_for_filename(text: str) -> str:
    return (
        text.replace("-", "")
        .replace(":", "")
        .replace("T", "-")
        .replace("Z", "")
        .replace(".", "")
    )


def _stable_hash(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _event_filename(event: dict) -> str:
    observed_at = str(event.get("observed_at") or current_iso())
    event_id = str(event.get("event_id") or _stable_hash(event))
    return f"{_sanitize_for_filename(observed_at)}_{event_id}.json"


def _compact_payload_for_event(event_type: str, payload: dict, summary: str, observed_at: str, job_id: str | None) -> dict:
    event = {
        "event_type": event_type,
        "observed_at": observed_at,
        "summary": summary,
        "payload": payload,
        "source": "chrome_camera_anime",
    }
    if job_id:
        event["job_id"] = job_id
    event["event_id"] = f"{event_type}-{_stable_hash(event)}"
    return event


def queue_event(state_dir: Path, event: dict) -> dict:
    ensure_sync_tree(state_dir)
    payload = dict(event)
    payload.setdefault("event_id", f"{payload.get('event_type', 'event')}-{_stable_hash(payload)}")
    write_json(outbox_dir(state_dir) / _event_filename(payload), payload)
    return payload


def _read_events(directory: Path) -> list[dict]:
    if not directory.is_dir():
        return []
    events = []
    for path in sorted(directory.glob("*.json")):
        payload = read_json(path, default=None)
        if isinstance(payload, dict) and payload:
            events.append(payload)
    return events


def list_pending_events(state_dir: Path) -> list[dict]:
    return _read_events(outbox_dir(state_dir))


def list_delivered_events(state_dir: Path) -> list[dict]:
    return _read_events(delivered_dir(state_dir))


def _watch_state_events(state_dir: Path, checkpoint: dict) -> tuple[list[dict], dict]:
    events: list[dict] = []
    watch_state = read_json(state_dir / "watch-state.json")
    next_checkpoint = dict(checkpoint.get("watch_state", {}))
    observed_at = current_iso()

    last_job_id = watch_state.get("last_job_id")
    if last_job_id and last_job_id != next_checkpoint.get("last_job_id"):
        events.append(
            _compact_payload_for_event(
                "chrome_launch_detected",
                {
                    "chrome_running": bool(watch_state.get("chrome_running", False)),
                    "job_id": last_job_id,
                },
                f"Chrome launch detected for {last_job_id}",
                observed_at,
                str(last_job_id),
            )
        )

    expression_monitor_pid = watch_state.get("expression_monitor_pid")
    if expression_monitor_pid and expression_monitor_pid != next_checkpoint.get("expression_monitor_pid"):
        events.append(
            _compact_payload_for_event(
                "expression_monitor_started",
                {
                    "pid": int(expression_monitor_pid),
                    "already_running": bool(watch_state.get("expression_monitor_already_running", False)),
                },
                f"Expression monitor started with pid={expression_monitor_pid}",
                observed_at,
                str(last_job_id) if last_job_id else None,
            )
        )

    next_checkpoint["last_job_id"] = last_job_id
    next_checkpoint["expression_monitor_pid"] = expression_monitor_pid
    return events, next_checkpoint


def _expression_sample_fingerprint(sample: dict) -> str:
    relevant = {
        "timestamp": sample.get("timestamp"),
        "face_detected": sample.get("face_detected"),
        "face_count": sample.get("face_count"),
        "expression": sample.get("expression"),
        "mood_trend": sample.get("mood_trend"),
        "confidence": sample.get("confidence"),
        "largest_face_area_ratio": sample.get("largest_face_area_ratio"),
    }
    return _stable_hash(relevant)


def _expression_events(state_dir: Path, checkpoint: dict) -> tuple[list[dict], dict]:
    latest_path = state_dir / "expression-monitor" / "latest.json"
    sample = read_json(latest_path)
    if not sample:
        return [], dict(checkpoint.get("expression_state", {}))

    fingerprint = _expression_sample_fingerprint(sample)
    next_checkpoint = dict(checkpoint.get("expression_state", {}))
    if fingerprint == next_checkpoint.get("fingerprint"):
        return [], next_checkpoint

    payload = {
        "face_detected": bool(sample.get("face_detected", False)),
        "face_count": int(sample.get("face_count", 0)),
        "expression": sample.get("expression", "unknown"),
        "mood_trend": sample.get("mood_trend", "unknown"),
        "confidence": float(sample.get("confidence", 0.0)),
        "largest_face_area_ratio": float(sample.get("largest_face_area_ratio", 0.0)),
    }
    event = _compact_payload_for_event(
        "expression_sample_updated",
        payload,
        (
            "Expression sample updated "
            f"expression={payload['expression']} mood={payload['mood_trend']}"
        ),
        str(sample.get("timestamp") or current_iso()),
        None,
    )
    next_checkpoint["fingerprint"] = fingerprint
    next_checkpoint["timestamp"] = sample.get("timestamp")
    return [event], next_checkpoint


def _job_payload(job: dict) -> tuple[str | None, dict, str]:
    status = str(job.get("status", "unknown"))
    expression_sample = job.get("expression_monitor_sample") or {}
    landscape = job.get("landscape") or {}
    job_id = str(job.get("job_id", ""))

    if status == "capturing":
        return (
            "capture_started",
            {"status": status},
            f"Capture started for {job_id}",
        )
    if status == "queued_generate":
        return (
            "portrait_selected",
            {
                "landscape_id": landscape.get("id"),
                "expression": expression_sample.get("expression"),
                "mood_trend": expression_sample.get("mood_trend"),
                "face_count": (job.get("portrait_detection") or {}).get("face_count"),
            },
            (
                f"Portrait selected for {job_id}"
                + (f" landscape={landscape.get('id')}" if landscape.get("id") else "")
            ),
        )
    if status == "generating":
        return (
            "generation_started",
            {
                "landscape_id": landscape.get("id"),
                "print_media": job.get("print_media"),
            },
            f"Generation started for {job_id}",
        )
    if status == "queued_print":
        return (
            "image_generated",
            {
                "output_path": job.get("output_path"),
                "metadata_path": job.get("metadata_path"),
                "response_model": job.get("response_model"),
                "landscape_id": landscape.get("id"),
                "expression": expression_sample.get("expression"),
                "mood_trend": expression_sample.get("mood_trend"),
            },
            f"Image generated for {job_id}",
        )
    if status == "submitting_print":
        return (
            "print_submitting",
            {"print_media": job.get("print_media")},
            f"Print submitting for {job_id}",
        )
    if status == "print_submitted":
        return (
            "print_submitted",
            {
                "printer_job_id": job.get("printer_job_id"),
                "print_media": job.get("print_media"),
            },
            f"Print submitted for {job_id}",
        )
    if status == "print_active":
        return (
            "print_active",
            {"printer_job_id": job.get("printer_job_id")},
            f"Print active for {job_id}",
        )
    if status == "print_completed":
        return (
            "print_completed",
            {
                "printer_job_id": job.get("printer_job_id"),
                "print_completed_at": job.get("print_completed_at"),
            },
            f"Print completed for {job_id}",
        )
    if status == "print_cancelled":
        return (
            "print_cancelled",
            {
                "printer_job_id": job.get("printer_job_id"),
                "print_cancelled_at": job.get("print_cancelled_at"),
                "print_cancel_reason": job.get("print_cancel_reason"),
            },
            f"Print cancelled for {job_id}",
        )
    if status.startswith("failed_"):
        return (
            "job_failed",
            {
                "failure_status": status,
                "error": job.get("error"),
            },
            f"Job failed for {job_id}: {status}",
        )
    return None, {}, ""


def _job_fingerprint(job: dict) -> str:
    return _stable_hash(
        {
            "status": job.get("status"),
            "updated_at": job.get("updated_at"),
            "error": job.get("error"),
            "landscape": job.get("landscape"),
            "portrait_detection": job.get("portrait_detection"),
            "expression_monitor_sample": job.get("expression_monitor_sample"),
            "output_path": job.get("output_path"),
            "metadata_path": job.get("metadata_path"),
            "response_model": job.get("response_model"),
            "printer_job_id": job.get("printer_job_id"),
            "print_completed_at": job.get("print_completed_at"),
            "print_cancelled_at": job.get("print_cancelled_at"),
            "print_cancel_reason": job.get("print_cancel_reason"),
        }
    )


def _job_events(state_dir: Path, checkpoint: dict) -> tuple[list[dict], dict]:
    jobs_root = state_dir / "jobs"
    if not jobs_root.is_dir():
        return [], dict(checkpoint.get("jobs", {}))

    events: list[dict] = []
    next_checkpoint = dict(checkpoint.get("jobs", {}))

    for job_path in sorted(jobs_root.glob("*/job.json")):
        job = read_json(job_path, default=None)
        if not isinstance(job, dict) or not job:
            continue
        job_id = str(job.get("job_id", ""))
        fingerprint = _job_fingerprint(job)
        if next_checkpoint.get(job_id) == fingerprint:
            continue
        next_checkpoint[job_id] = fingerprint
        event_type, payload, summary = _job_payload(job)
        if not event_type:
            continue
        events.append(
            _compact_payload_for_event(
                event_type,
                payload,
                summary,
                str(job.get("updated_at") or job.get("created_at") or current_iso()),
                job_id,
            )
        )
    return events, next_checkpoint


def collect_events(state_dir: Path, checkpoint: dict | None = None) -> tuple[list[dict], dict]:
    checkpoint = checkpoint or load_checkpoint(state_dir)
    events: list[dict] = []

    watch_events, watch_state = _watch_state_events(state_dir, checkpoint)
    job_events, jobs_state = _job_events(state_dir, checkpoint)
    expression_events, expression_state = _expression_events(state_dir, checkpoint)

    events.extend(watch_events)
    events.extend(job_events)
    events.extend(expression_events)

    next_checkpoint = {
        "watch_state": watch_state,
        "jobs": jobs_state,
        "expression_state": expression_state,
    }
    return events, next_checkpoint


def scan_and_queue_events(state_dir: Path) -> dict[str, object]:
    ensure_sync_tree(state_dir)
    checkpoint = load_checkpoint(state_dir)
    events, next_checkpoint = collect_events(state_dir, checkpoint=checkpoint)
    queued_events = [queue_event(state_dir, event) for event in events]
    save_checkpoint(state_dir, next_checkpoint)
    status = update_sync_status(
        state_dir,
        last_scan_at=current_iso(),
    )
    return {"queued_events": queued_events, "checkpoint": next_checkpoint, "status": status}


def default_openclaw_config_path() -> Path:
    path = os.environ.get("OPENCLAW_CONFIG_PATH")
    if path:
        return Path(path)
    return Path.home() / ".openclaw" / "openclaw.json"


def _read_gateway_token(config_path: Path | None = None) -> str:
    config_path = config_path or default_openclaw_config_path()
    payload = read_json(config_path)
    return str(payload.get("gateway", {}).get("auth", {}).get("token", "")).strip()


def resolve_hook_config(config_path: Path | None = None) -> dict[str, str] | None:
    token = os.environ.get("OPENCLAW_HOOK_TOKEN", "").strip() or _read_gateway_token(config_path)
    if not token:
        return None
    return {
        "url": os.environ.get("OPENCLAW_HOOK_URL", DEFAULT_HOOK_URL).strip() or DEFAULT_HOOK_URL,
        "token": token,
        "name": os.environ.get("OPENCLAW_HOOK_NAME", DEFAULT_HOOK_NAME).strip() or DEFAULT_HOOK_NAME,
        "agent_id": os.environ.get("OPENCLAW_HOOK_AGENT_ID", DEFAULT_HOOK_AGENT_ID).strip() or DEFAULT_HOOK_AGENT_ID,
        "wake_mode": os.environ.get("OPENCLAW_HOOK_WAKE_MODE", DEFAULT_HOOK_WAKE_MODE).strip() or DEFAULT_HOOK_WAKE_MODE,
    }


def build_hook_message(event: dict) -> str:
    parts = [f"ChromeCameraAnime event_type={event.get('event_type', 'unknown')}"]
    if event.get("job_id"):
        parts.append(f"job_id={event['job_id']}")
    payload = event.get("payload") or {}
    for key in ("landscape_id", "expression", "mood_trend", "printer_job_id", "failure_status"):
        value = payload.get(key)
        if value:
            parts.append(f"{key}={value}")
    summary = str(event.get("summary", "")).strip()
    if summary:
        parts.append(f"summary={summary}")
    return " ".join(parts)


def send_hook_event(
    event: dict,
    *,
    hook_config: dict[str, str],
    timeout: int = DEFAULT_TIMEOUT,
    urlopen_impl=urllib.request.urlopen,
) -> dict[str, object]:
    payload = {
        "message": build_hook_message(event),
        "name": hook_config["name"],
        "agentId": hook_config["agent_id"],
        "wakeMode": hook_config["wake_mode"],
    }
    request = urllib.request.Request(
        hook_config["url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {hook_config['token']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen_impl(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def deliver_pending_events(
    state_dir: Path,
    *,
    hook_config: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    urlopen_impl=urllib.request.urlopen,
) -> dict[str, object]:
    ensure_sync_tree(state_dir)
    if hook_config is None:
        hook_config = resolve_hook_config()
    if not hook_config:
        status = update_sync_status(
            state_dir,
            last_delivery_attempt_at=current_iso(),
            last_delivery_error=None,
            last_skipped_reason="hook_unconfigured",
        )
        return {"delivered_event_ids": [], "skipped_reason": "hook_unconfigured", "status": status}

    delivered_event_ids: list[str] = []
    last_success_at: str | None = None
    last_delivery_attempt_at = current_iso()
    for path in sorted(outbox_dir(state_dir).glob("*.json")):
        event = read_json(path, default=None)
        if not isinstance(event, dict) or not event:
            continue
        try:
            response = send_hook_event(
                event,
                hook_config=hook_config,
                timeout=timeout,
                urlopen_impl=urlopen_impl,
            )
        except Exception as exc:
            status = update_sync_status(
                state_dir,
                last_delivery_attempt_at=last_delivery_attempt_at,
                last_delivery_error=str(exc),
                last_skipped_reason=None,
                last_success_at=last_success_at or load_sync_status(state_dir).get("last_success_at"),
            )
            return {
                "delivered_event_ids": delivered_event_ids,
                "error": str(exc),
                "status": status,
            }
        delivered = {
            **event,
            "delivery": {
                "delivered_at": current_iso(),
                "response": response,
            },
        }
        write_json(delivered_dir(state_dir) / path.name, delivered)
        path.unlink()
        delivered_event_ids.append(str(event.get("event_id")))
        last_success_at = str(delivered["delivery"]["delivered_at"])
    status = update_sync_status(
        state_dir,
        last_delivery_attempt_at=last_delivery_attempt_at,
        last_delivery_error=None,
        last_skipped_reason=None,
        last_success_at=last_success_at or load_sync_status(state_dir).get("last_success_at"),
    )
    return {"delivered_event_ids": delivered_event_ids, "status": status}
