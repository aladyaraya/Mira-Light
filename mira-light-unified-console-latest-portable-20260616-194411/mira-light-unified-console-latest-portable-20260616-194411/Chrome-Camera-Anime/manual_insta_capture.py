#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import expression_monitor_control
import job_store
import pipeline
import print_client
import worker_daemon


DEFAULT_CAMERA_NAME = "Insta360 Link 2 Pro"
DEFAULT_OUTPUT_DIR = pipeline.DEFAULT_OUTPUT_DIR / "manual-insta"
DEFAULT_STYLE_SLUG = "insta-manual"
DEFAULT_STYLE_PROMPT = "自然光、空气感、电影截图感的吉卜力旅行场景插画，允许保留原照片中的多人关系，人物带自然微笑"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-shot manual trigger for Insta360 capture and anime rendering."
    )
    parser.add_argument("--state-dir", type=Path, default=job_store.DEFAULT_STATE_DIR)
    parser.add_argument("--camera-name", default=DEFAULT_CAMERA_NAME)
    parser.add_argument("--imagesnap-bin", default=shutil.which("imagesnap") or "")
    parser.add_argument("--list-cameras", action="store_true", help="List available imagesnap cameras and exit.")
    parser.add_argument("--capture-only", action="store_true", help="Capture from Insta360 and stop before rendering.")
    parser.add_argument("--print", dest="should_print", action="store_true", help="Submit the rendered image to the Xiaomi print bridge.")
    parser.add_argument("--no-print", dest="should_print", action="store_false", help="Render only and skip printer submission.")
    parser.add_argument("--print-media", default=job_store.DEFAULT_PRINT_MEDIA)
    parser.add_argument("--manifest", type=Path, default=pipeline.DEFAULT_MANIFEST_PATH)
    parser.add_argument("--landscape-state-path", type=Path, default=pipeline.DEFAULT_STATE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--detector-script", type=Path, default=pipeline.DEFAULT_FACE_DETECTOR)
    parser.add_argument("--model", default=pipeline.DEFAULT_MODEL)
    parser.add_argument("--size", default=pipeline.DEFAULT_SIZE)
    parser.add_argument("--response-format", default=pipeline.DEFAULT_RESPONSE_FORMAT)
    parser.add_argument("--api-url", default=pipeline.DEFAULT_API_URL)
    parser.add_argument("--timeout", type=int, default=pipeline.DEFAULT_TIMEOUT)
    parser.add_argument("--style-slug", default=DEFAULT_STYLE_SLUG)
    parser.add_argument("--style-prompt", default=DEFAULT_STYLE_PROMPT)
    parser.add_argument("--burst-count", type=int, default=pipeline.DEFAULT_BURST_COUNT)
    parser.add_argument("--burst-interval-seconds", type=float, default=pipeline.DEFAULT_BURST_INTERVAL_SECONDS)
    parser.add_argument("--warmup-ms", type=int, default=350)
    parser.set_defaults(should_print=True)
    return parser.parse_args(argv)


def list_imagesnap_cameras(imagesnap_bin: str) -> list[str]:
    if not imagesnap_bin:
        raise RuntimeError("imagesnap not found in PATH")
    result = subprocess.run(
        [imagesnap_bin, "-l"],
        check=True,
        capture_output=True,
        text=True,
    )
    cameras: list[str] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("=>"):
            continue
        cameras.append(stripped.removeprefix("=>").strip())
    return cameras


def resolve_camera_name(imagesnap_bin: str, requested_name: str) -> str:
    cameras = list_imagesnap_cameras(imagesnap_bin)
    if not cameras:
        raise RuntimeError("no camera devices reported by imagesnap")

    normalized_requested = requested_name.strip().lower()
    if normalized_requested:
        for camera_name in cameras:
            if camera_name.lower() == normalized_requested:
                return camera_name
        for camera_name in cameras:
            if normalized_requested in camera_name.lower():
                return camera_name
        raise RuntimeError(
            f"camera '{requested_name}' not found; available cameras: {', '.join(cameras)}"
        )

    for camera_name in cameras:
        if "insta" in camera_name.lower():
            return camera_name
    return cameras[0]


def capture_insta_frame(
    *,
    latest_image_path: Path,
    imagesnap_bin: str,
    camera_name: str,
    warmup_ms: int,
) -> Path:
    latest_image_path.parent.mkdir(parents=True, exist_ok=True)
    warmup_seconds = max(float(warmup_ms) / 1000.0, 0.0)
    subprocess.run(
        [
            imagesnap_bin,
            "-d",
            camera_name,
            "-q",
            "-w",
            f"{warmup_seconds:.3f}",
            str(latest_image_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if not latest_image_path.is_file():
        raise FileNotFoundError(f"missing captured image: {latest_image_path}")
    return latest_image_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.list_cameras:
        print(
            json.dumps(
                {
                    "ok": True,
                    "cameras": list_imagesnap_cameras(args.imagesnap_bin),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not args.imagesnap_bin:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "imagesnap not found in PATH",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    resolved_camera_name = resolve_camera_name(args.imagesnap_bin, args.camera_name)
    job = job_store.create_job(
        args.state_dir,
        trigger="manual_insta_capture",
        metadata={
            "camera_name": resolved_camera_name,
            "source": "manual_insta_capture",
            "should_print": bool(args.should_print),
        },
        queue_capture=False,
    )
    artifact_dir = job_store.artifact_dir(args.state_dir, job["job_id"])
    latest_image_path = artifact_dir / "latest-insta.jpg"

    try:
        # Free the webcam before manual capture to avoid monitor contention.
        expression_monitor_control.stop_expression_monitor(args.state_dir)

        portrait = pipeline.capture_best_portrait(
            artifact_dir=artifact_dir,
            capture_script=Path(args.imagesnap_bin),
            latest_image_path=latest_image_path,
            detector_script=args.detector_script,
            burst_count=args.burst_count,
            burst_interval_seconds=args.burst_interval_seconds,
            capture_image=lambda *, capture_script, latest_image_path: capture_insta_frame(
                latest_image_path=latest_image_path,
                imagesnap_bin=args.imagesnap_bin,
                camera_name=resolved_camera_name,
                warmup_ms=args.warmup_ms,
            ),
        )
        prepared_portrait = pipeline.prepare_generation_portrait(
            portrait_path=Path(portrait["portrait_path"]),
            artifact_dir=artifact_dir,
            portrait_detection=portrait.get("portrait_detection"),
            subject_selection=portrait.get("subject_selection"),
        )
        landscape = worker_daemon.pick_landscape(
            manifest_path=args.manifest,
            state_path=args.landscape_state_path,
        )
        pose_instruction = pipeline.choose_pose()

        job = job_store.update_job(
            args.state_dir,
            job["job_id"],
            status="captured",
            metadata={
                **(job.get("metadata") or {}),
                "pose_instruction": pose_instruction,
            },
            portrait_path=prepared_portrait["portrait_path"],
            portrait_source_path=prepared_portrait.get("portrait_source_path", portrait["portrait_path"]),
            portrait_crop=prepared_portrait.get("portrait_crop"),
            portrait_detection=portrait["portrait_detection"],
            subject_selection=portrait.get("subject_selection"),
            pose_instruction=pose_instruction,
            landscape={
                "id": landscape["id"],
                "path": str(landscape["path"]),
            },
            print_media=args.print_media,
        )

        if args.capture_only:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "job_id": job["job_id"],
                        "status": "captured",
                        "camera_name": resolved_camera_name,
                        "portrait_path": job["portrait_path"],
                        "portrait_source_path": job.get("portrait_source_path"),
                        "portrait_crop": job.get("portrait_crop"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        api_key = os.environ.get("ARK_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Provide ARK_API_KEY before rendering")

        generation = pipeline.generate_from_paths(
            api_key=api_key,
            portrait_path=Path(job["portrait_path"]),
            landscape_path=Path(job["landscape"]["path"]),
            output_dir=args.output_dir,
            model=args.model,
            size=args.size,
            response_format=args.response_format,
            api_url=args.api_url,
            timeout=args.timeout,
            style_slug=args.style_slug,
            style_prompt=args.style_prompt,
            pose_instruction=job.get("pose_instruction"),
            landscape_id=job["landscape"]["id"],
            detector_script=args.detector_script,
            allow_multiple_people=True,
        )
        job = job_store.update_job(
            args.state_dir,
            job["job_id"],
            status="generated",
            generation=generation,
            output_path=generation["output_path"],
            metadata_path=generation.get("metadata_path"),
        )

        print_response = None
        if args.should_print:
            print_response = print_client.submit_print_job(
                Path(generation["output_path"]),
                media=args.print_media,
            )
            job = job_store.mark_print_submitted(
                args.state_dir,
                job["job_id"],
                printer_job_id=worker_daemon.normalize_printer_job_id(str(print_response["job_id"])),
                print_response=worker_daemon.json_safe(print_response),
            )

        print(
            json.dumps(
                {
                    "ok": True,
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "camera_name": resolved_camera_name,
                    "portrait_path": job.get("portrait_path"),
                    "output_path": job.get("output_path"),
                    "metadata_path": job.get("metadata_path"),
                    "printer_job_id": job.get("printer_job_id"),
                    "print_response": print_response,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        error_text = str(exc).strip()
        failed_status = "failed_capture"
        if job.get("portrait_path"):
            failed_status = "failed_generate"
        if job.get("output_path") and args.should_print:
            failed_status = "failed_print"
        job_store.update_job(
            args.state_dir,
            job["job_id"],
            status=failed_status,
            error=error_text,
        )
        print(
            json.dumps(
                {
                    "ok": False,
                    "job_id": job["job_id"],
                    "status": failed_status,
                    "error": error_text,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
