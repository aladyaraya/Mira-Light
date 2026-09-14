#!/usr/bin/env python3
import argparse
import concurrent.futures
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import job_store
import expression_monitor_control
import pipeline
import print_client
import xiaomi_home_print


DEFAULT_STATE_DIR = job_store.DEFAULT_STATE_DIR
DEFAULT_GENERATION_WORKERS = 2
DEFAULT_IDLE_SLEEP = 0.25
DEFAULT_PRINT_SUBMIT_DELAY_SECONDS = 80.0
DEFAULT_PRINT_BACKEND = "bridge"
INFLIGHT_PRINT_STATUSES = {"submitting_print", "print_submitted", "print_active"}


def log_event(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def normalize_printer_job_id(job_id: str) -> str:
    return (
        job_id.split("（", 1)[0]
        .split("(", 1)[0]
        .strip()
    )


def json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def compute_print_not_before_at(created_at: str, delay_seconds: float) -> str:
    ready_at = job_store.parse_iso(created_at) + timedelta(seconds=delay_seconds)
    return ready_at.isoformat().replace("+00:00", "Z")


def has_inflight_print_job(state_dir: Path) -> bool:
    for job in job_store.list_jobs(state_dir):
        if str(job.get("status") or "") in INFLIGHT_PRINT_STATUSES:
            return True
    return False


def should_fallback_from_expression_monitor(exc: Exception) -> bool:
    return str(exc).strip() in {
        "No face detected in expression monitor sample",
        "No primary subject detected in expression monitor sample",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run queued Chrome camera anime jobs.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--manifest", type=Path, default=pipeline.DEFAULT_MANIFEST_PATH)
    parser.add_argument("--landscape-state-path", type=Path, default=pipeline.DEFAULT_STATE_PATH)
    parser.add_argument("--output-dir", type=Path, default=pipeline.DEFAULT_OUTPUT_DIR)
    parser.add_argument("--capture-script", type=Path, default=pipeline.DEFAULT_CAPTURE_SCRIPT)
    parser.add_argument("--latest-image-path", type=Path, default=pipeline.DEFAULT_CAPTURE_IMAGE_PATH)
    parser.add_argument("--detector-script", type=Path, default=pipeline.DEFAULT_FACE_DETECTOR)
    parser.add_argument("--model", default=pipeline.DEFAULT_MODEL)
    parser.add_argument("--size", default=pipeline.DEFAULT_SIZE)
    parser.add_argument("--response-format", default=pipeline.DEFAULT_RESPONSE_FORMAT)
    parser.add_argument("--api-url", default=pipeline.DEFAULT_API_URL)
    parser.add_argument("--timeout", type=int, default=pipeline.DEFAULT_TIMEOUT)
    parser.add_argument("--style-slug", default="anime")
    parser.add_argument("--style-prompt", default=pipeline.DEFAULT_STYLE_PROMPT)
    parser.add_argument("--generation-workers", type=int, default=DEFAULT_GENERATION_WORKERS)
    parser.add_argument("--idle-sleep", type=float, default=DEFAULT_IDLE_SLEEP)
    parser.add_argument(
        "--print-submit-delay-seconds",
        type=float,
        default=float(os.environ.get("PRINT_SUBMIT_DELAY_SECONDS", DEFAULT_PRINT_SUBMIT_DELAY_SECONDS)),
    )
    return parser.parse_args(argv)


def pick_landscape(*, manifest_path: Path, state_path: Path) -> dict:
    entries = pipeline.load_landscape_manifest(manifest_path)
    return pipeline.choose_landscape(entries, state_path)


def generate_for_job(
    *,
    state_dir: Path,
    job_id: str,
    api_key: str,
    output_dir: Path,
    model: str,
    size: str,
    response_format: str,
    api_url: str,
    timeout: int,
    style_slug: str,
    style_prompt: str,
) -> dict[str, object]:
    job = job_store.load_job(state_dir, job_id)
    result = pipeline.generate_from_paths(
        api_key=api_key,
        portrait_path=Path(job["portrait_path"]),
        landscape_path=Path(job["landscape"]["path"]),
        output_dir=output_dir,
        model=model,
        size=size,
        response_format=response_format,
        api_url=api_url,
        timeout=timeout,
        style_slug=style_slug,
        style_prompt=style_prompt,
        pose_instruction=job.get("pose_instruction"),
        landscape_id=job["landscape"]["id"],
    )
    metadata_path = pipeline.write_output_metadata(
        Path(result["output_path"]),
        {
            "job_id": job["job_id"],
            "created_at": job["created_at"],
            "trigger": job.get("trigger"),
            "portrait_path": job.get("portrait_path"),
            "portrait_source_path": job.get("portrait_source_path"),
            "portrait_crop": job.get("portrait_crop"),
            "portrait_detection": job.get("portrait_detection"),
            "subject_selection": job.get("subject_selection"),
            "pose_instruction": job.get("pose_instruction"),
            "landscape": job.get("landscape"),
            "expression_monitor_sample": job.get("expression_monitor_sample"),
            "request_summary": result.get("request_summary"),
            "response_model": result.get("response_model"),
            "response_url": result.get("response_url"),
            "output_subject_validation": result.get("output_subject_validation"),
            "print_media": job.get("print_media"),
        },
    )
    result["metadata_path"] = str(metadata_path)
    return result


def process_capture_job(
    *,
    state_dir: Path,
    job_id: str,
    manifest_path: Path = pipeline.DEFAULT_MANIFEST_PATH,
    landscape_state_path: Path = pipeline.DEFAULT_STATE_PATH,
    capture_script: Path = pipeline.DEFAULT_CAPTURE_SCRIPT,
    latest_image_path: Path = pipeline.DEFAULT_CAPTURE_IMAGE_PATH,
    detector_script: Path = pipeline.DEFAULT_FACE_DETECTOR,
    capture_from_expression_monitor_impl=expression_monitor_control.capture_from_expression_monitor,
    capture_best_portrait_impl=None,
    prepare_generation_portrait_impl=None,
    pick_landscape_impl=None,
    choose_pose_impl=pipeline.choose_pose,
    stop_expression_monitor_impl=expression_monitor_control.stop_expression_monitor,
) -> dict:
    capture_best_portrait_impl = capture_best_portrait_impl or pipeline.capture_best_portrait
    prepare_generation_portrait_impl = (
        prepare_generation_portrait_impl or pipeline.prepare_generation_portrait
    )
    pick_landscape_impl = pick_landscape_impl or pick_landscape
    try:
        job = job_store.load_job(state_dir, job_id)
        artifact_path = job_store.artifact_dir(state_dir, job_id)
        try:
            portrait = capture_from_expression_monitor_impl(
                state_dir=state_dir,
                artifact_dir=artifact_path,
            )
        except Exception as exc:
            if not should_fallback_from_expression_monitor(exc):
                raise
            stop_expression_monitor_impl(state_dir)
            portrait = None
        if portrait is None:
            portrait = capture_best_portrait_impl(
                artifact_dir=artifact_path,
                capture_script=capture_script,
                latest_image_path=latest_image_path,
                detector_script=detector_script,
            )
        prepared_portrait = prepare_generation_portrait_impl(
            portrait_path=Path(portrait["portrait_path"]),
            artifact_dir=artifact_path,
            portrait_detection=portrait.get("portrait_detection"),
            subject_selection=portrait.get("subject_selection"),
        )
        landscape = pick_landscape_impl(
            manifest_path=manifest_path,
            state_path=landscape_state_path,
        )
        pose_instruction = choose_pose_impl()
        metadata = {
            **(job.get("metadata") or {}),
            "pose_instruction": pose_instruction,
        }
        return job_store.enqueue_job(
            state_dir,
            job_id,
            "generate",
            status="queued_generate",
            fields={
                "metadata": metadata,
                "portrait_path": prepared_portrait["portrait_path"],
                "portrait_source_path": prepared_portrait.get("portrait_source_path", portrait["portrait_path"]),
                **(
                    {"portrait_crop": prepared_portrait["portrait_crop"]}
                    if prepared_portrait.get("portrait_crop") is not None
                    else {}
                ),
                "portrait_detection": portrait["portrait_detection"],
                **(
                    {"subject_selection": portrait["subject_selection"]}
                    if "subject_selection" in portrait
                    else {}
                ),
                "pose_instruction": pose_instruction,
                **(
                    {"expression_monitor_sample": portrait["expression_monitor_sample"]}
                    if "expression_monitor_sample" in portrait
                    else {}
                ),
                "landscape": {
                    "id": landscape["id"],
                    "path": str(landscape["path"]),
                },
            },
        )
    except Exception as exc:
        failed_status = (
            "failed_no_face"
            if "No face detected" in str(exc) or "No primary subject detected" in str(exc)
            else "failed_capture"
        )
        stop_expression_monitor_impl(state_dir)
        return job_store.update_job(
            state_dir,
            job_id,
            status=failed_status,
            error=str(exc),
        )


def process_generation_job(
    *,
    state_dir: Path,
    job_id: str,
    api_key: str | None = None,
    output_dir: Path = pipeline.DEFAULT_OUTPUT_DIR,
    model: str = pipeline.DEFAULT_MODEL,
    size: str = pipeline.DEFAULT_SIZE,
    response_format: str = pipeline.DEFAULT_RESPONSE_FORMAT,
    api_url: str = pipeline.DEFAULT_API_URL,
    timeout: int = pipeline.DEFAULT_TIMEOUT,
    style_slug: str = "anime",
    style_prompt: str = pipeline.DEFAULT_STYLE_PROMPT,
    print_submit_delay_seconds: float = DEFAULT_PRINT_SUBMIT_DELAY_SECONDS,
    generate_for_job_impl=None,
    stop_expression_monitor_impl=expression_monitor_control.stop_expression_monitor,
) -> dict:
    generate_for_job_impl = generate_for_job_impl or generate_for_job
    api_key = api_key or os.environ.get("ARK_API_KEY", "")
    try:
        job = job_store.load_job(state_dir, job_id)
        result = generate_for_job_impl(
            state_dir=state_dir,
            job_id=job_id,
            api_key=api_key,
            output_dir=output_dir,
            model=model,
            size=size,
            response_format=response_format,
            api_url=api_url,
            timeout=timeout,
            style_slug=style_slug,
            style_prompt=style_prompt,
        )
        return job_store.enqueue_job(
            state_dir,
            job_id,
            "print",
            status="queued_print",
            fields={
                "print_backend": DEFAULT_PRINT_BACKEND,
                "output_path": result["output_path"],
                "metadata_path": result.get("metadata_path"),
                "response_model": result.get("response_model"),
                "print_not_before_at": compute_print_not_before_at(
                    str(job["created_at"]),
                    print_submit_delay_seconds,
                ),
            },
        )
    except Exception as exc:
        stop_expression_monitor_impl(state_dir)
        return job_store.update_job(
            state_dir,
            job_id,
            status="failed_generate",
            error=str(exc),
        )


def process_print_job(
    *,
    state_dir: Path,
    job_id: str,
    submit_print_job_impl=None,
    submit_mobile_print_job_impl=xiaomi_home_print.submit_print_job,
    stop_expression_monitor_impl=expression_monitor_control.stop_expression_monitor,
) -> dict:
    submit_print_job_impl = submit_print_job_impl or print_client.submit_print_job
    try:
        job = job_store.load_job(state_dir, job_id)
        if job.get("printer_job_id"):
            stop_expression_monitor_impl(state_dir)
            return job
        print_backend = str(job.get("print_backend") or DEFAULT_PRINT_BACKEND).strip() or DEFAULT_PRINT_BACKEND
        if print_backend == "xiaomi_home_share":
            print_response = submit_mobile_print_job_impl(
                Path(job["output_path"]),
                adb_path=str(job.get("adb_path") or ""),
                adb_serial=str(job.get("adb_serial") or ""),
                remote_dir=str(job.get("phone_print_remote_dir") or xiaomi_home_print.DEFAULT_REMOTE_DIR),
                component=str(job.get("phone_print_component") or xiaomi_home_print.DEFAULT_SEND_COMPONENT),
                printer_name=str(
                    job.get("phone_print_target_printer_name") or xiaomi_home_print.DEFAULT_TARGET_PRINTER_NAME
                ),
                poll_timeout_seconds=float(
                    job.get("phone_print_poll_timeout_seconds") or xiaomi_home_print.DEFAULT_POLL_TIMEOUT_SECONDS
                ),
                poll_interval_seconds=float(
                    job.get("phone_print_poll_interval_seconds") or xiaomi_home_print.DEFAULT_POLL_INTERVAL_SECONDS
                ),
            )
        else:
            print_response = submit_print_job_impl(
                Path(job["output_path"]),
                media=job.get("print_media", job_store.DEFAULT_PRINT_MEDIA),
            )
        updated = job_store.mark_print_submitted(
            state_dir,
            job_id,
            printer_job_id=normalize_printer_job_id(str(print_response["job_id"])),
            print_response=json_safe(print_response),
        )
        if bool(print_response.get("completed")):
            updated = job_store.update_job(
                state_dir,
                job_id,
                status="print_completed",
                print_completed_at=job_store.current_iso(),
            )
        stop_expression_monitor_impl(state_dir)
        return updated
    except Exception as exc:
        stop_expression_monitor_impl(state_dir)
        return job_store.update_job(
            state_dir,
            job_id,
            status="failed_print",
            error=str(exc),
        )


def watch_forever(args: argparse.Namespace) -> None:
    active_futures: dict[concurrent.futures.Future, str] = {}
    print_future: concurrent.futures.Future | None = None
    print_future_job_id = ""
    log_event(
        f"worker started state_dir={args.state_dir} output_dir={args.output_dir} "
        f"manifest={args.manifest}"
    )
    with (
        concurrent.futures.ThreadPoolExecutor(max_workers=args.generation_workers) as executor,
        concurrent.futures.ThreadPoolExecutor(max_workers=1) as print_executor,
    ):
        while True:
            for future in list(active_futures):
                if future.done():
                    job_id = active_futures.pop(future, "")
                    result = future.result()
                    log_event(f"generate finished job={job_id} status={result.get('status')} output={result.get('output_path', '-')}")
            if print_future is not None and print_future.done():
                result = print_future.result()
                log_event(f"print finished job={print_future_job_id} status={result.get('status')} error={result.get('error', '-')}")
                print_future = None
                print_future_job_id = ""

            while len(active_futures) < args.generation_workers:
                job = job_store.claim_next_job(
                    args.state_dir,
                    "generate",
                    claimed_status="generating",
                )
                if job is None:
                    break
                log_event(f"generate claimed job={job['job_id']}")
                future = executor.submit(
                    process_generation_job,
                    state_dir=args.state_dir,
                    job_id=job["job_id"],
                    api_key=os.environ.get("ARK_API_KEY", ""),
                    output_dir=args.output_dir,
                    model=args.model,
                    size=args.size,
                    response_format=args.response_format,
                    api_url=args.api_url,
                    timeout=args.timeout,
                    style_slug=args.style_slug,
                    style_prompt=args.style_prompt,
                    print_submit_delay_seconds=args.print_submit_delay_seconds,
                )
                active_futures[future] = job["job_id"]

            if print_future is None and not has_inflight_print_job(args.state_dir):
                print_job = job_store.claim_next_due_job(
                    args.state_dir,
                    "print",
                    due_field="print_not_before_at",
                    claimed_status="submitting_print",
                )
                if print_job is not None:
                    print_future_job_id = print_job["job_id"]
                    log_event(f"print claimed job={print_future_job_id}")
                    print_future = print_executor.submit(
                        process_print_job,
                        state_dir=args.state_dir,
                        job_id=print_job["job_id"],
                    )

            capture_job = job_store.claim_next_job(
                args.state_dir,
                "capture",
                claimed_status="capturing",
            )
            if capture_job is not None:
                log_event(f"capture claimed job={capture_job['job_id']}")
                result = process_capture_job(
                    state_dir=args.state_dir,
                    job_id=capture_job["job_id"],
                    manifest_path=args.manifest,
                    landscape_state_path=args.landscape_state_path,
                    capture_script=args.capture_script,
                    latest_image_path=args.latest_image_path,
                    detector_script=args.detector_script,
                )
                log_event(
                    f"capture finished job={capture_job['job_id']} "
                    f"status={result.get('status')} portrait={result.get('portrait_path', '-')}"
                )
                continue

            if active_futures:
                time.sleep(args.idle_sleep)
                continue
            time.sleep(args.idle_sleep)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    watch_forever(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
