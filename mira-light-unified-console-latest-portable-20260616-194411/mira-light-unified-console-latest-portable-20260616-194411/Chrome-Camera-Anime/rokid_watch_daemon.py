#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import job_store
import pipeline
import print_client
import rokid_render_pipeline
import xiaomi_home_print


DEFAULT_STATE_DIR = Path.home() / ".openclaw-chrome-camera-anime"
DEFAULT_CONFIG_PATH = DEFAULT_STATE_DIR / "rokid-watch-config.json"
DEFAULT_STATE_PATH = DEFAULT_STATE_DIR / "rokid-watch-state.json"
DEFAULT_REMOTE_DIR = "/sdcard/Download/Rokid AI"
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_STABLE_POLLS_REQUIRED = 2
DEFAULT_OUTPUT_DIR = pipeline.DEFAULT_OUTPUT_DIR / "rokid-watch"
DEFAULT_STYLE_SLUG = "rokid-ghibli"
DEFAULT_ROKID_PACKAGE = "com.rokid.sprite.aiapp"
DEFAULT_IMPORT_BUTTON_TEXT = "导入"
DEFAULT_IMPORT_BANNER_TEXT = "相册文件待导入"
DEFAULT_IMPORT_COOLDOWN_SECONDS = 5.0
DEFAULT_ALBUM_TAB_RESOURCE_ID = "com.rokid.sprite.aiapp:id/btn_media"
DEFAULT_ALBUM_NAV_COOLDOWN_SECONDS = 3.0
DEFAULT_PROCESS_RETRY_COOLDOWN_SECONDS = 15.0
DEFAULT_PRINT_BACKEND = "bridge"


def current_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp"
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.is_file():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def detect_adb_serial(
    adb_path: str | None = None,
    *,
    runner=subprocess.run,
) -> str:
    resolved_adb_path = adb_path or shutil.which("adb") or "adb"
    result = runner(
        [resolved_adb_path, "devices"],
        check=True,
        capture_output=True,
        text=True,
    )
    serials: list[str] = []
    for line in result.stdout.splitlines():
        if "\tdevice" not in line:
            continue
        serials.append(line.split("\t", 1)[0].strip())
    if not serials:
        return ""
    return serials[0]


def default_config(
    *,
    adb_path: str | None = None,
    adb_serial: str = "",
) -> dict[str, object]:
    return {
        "enabled": True,
        "poll_interval_seconds": DEFAULT_POLL_INTERVAL_SECONDS,
        "stable_polls_required": DEFAULT_STABLE_POLLS_REQUIRED,
        "adb_path": adb_path or shutil.which("adb") or "adb",
        "adb_serial": adb_serial,
        "remote_dir": DEFAULT_REMOTE_DIR,
        "auto_import_enabled": True,
        "rokid_package": DEFAULT_ROKID_PACKAGE,
        "import_button_text": DEFAULT_IMPORT_BUTTON_TEXT,
        "import_banner_text": DEFAULT_IMPORT_BANNER_TEXT,
        "import_cooldown_seconds": DEFAULT_IMPORT_COOLDOWN_SECONDS,
        "album_tab_resource_id": DEFAULT_ALBUM_TAB_RESOURCE_ID,
        "album_nav_cooldown_seconds": DEFAULT_ALBUM_NAV_COOLDOWN_SECONDS,
        "process_retry_cooldown_seconds": DEFAULT_PROCESS_RETRY_COOLDOWN_SECONDS,
        "state_dir": str(DEFAULT_STATE_DIR),
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "manifest_path": str(pipeline.DEFAULT_MANIFEST_PATH),
        "pipeline_state_path": str(pipeline.DEFAULT_STATE_PATH),
        "detector_script": str(pipeline.DEFAULT_FACE_DETECTOR),
        "api_url": pipeline.DEFAULT_API_URL,
        "model": pipeline.DEFAULT_MODEL,
        "size": pipeline.DEFAULT_SIZE,
        "response_format": pipeline.DEFAULT_RESPONSE_FORMAT,
        "style_slug": DEFAULT_STYLE_SLUG,
        "style_prompt": pipeline.DEFAULT_STYLE_PROMPT,
        "print_backend": DEFAULT_PRINT_BACKEND,
        "print_media": job_store.DEFAULT_PRINT_MEDIA,
        "phone_print_remote_dir": xiaomi_home_print.DEFAULT_REMOTE_DIR,
        "phone_print_component": xiaomi_home_print.DEFAULT_SEND_COMPONENT,
        "phone_print_target_printer_name": xiaomi_home_print.DEFAULT_TARGET_PRINTER_NAME,
        "phone_print_poll_timeout_seconds": xiaomi_home_print.DEFAULT_POLL_TIMEOUT_SECONDS,
        "phone_print_poll_interval_seconds": xiaomi_home_print.DEFAULT_POLL_INTERVAL_SECONDS,
        "timeout": pipeline.DEFAULT_TIMEOUT,
    }


def ensure_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    detect_adb_serial_impl=detect_adb_serial,
) -> dict[str, object]:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_json(config_path, default={})
    adb_path = str(existing.get("adb_path") or shutil.which("adb") or "adb")
    detected_serial = str(existing.get("adb_serial") or "").strip()
    if not detected_serial:
        try:
            detected_serial = str(detect_adb_serial_impl(adb_path=adb_path) or "").strip()
        except Exception:
            detected_serial = ""
    config = {
        **default_config(adb_path=adb_path, adb_serial=detected_serial),
        **existing,
    }
    if not config.get("adb_serial") and detected_serial:
        config["adb_serial"] = detected_serial
    write_json(config_path, config)
    return config


def set_enabled(config_path: Path = DEFAULT_CONFIG_PATH, enabled: bool = True) -> dict[str, object]:
    config = ensure_config(config_path)
    config["enabled"] = bool(enabled)
    write_json(config_path, config)
    return config


def adb_base_command(*, adb_path: str | None = None, adb_serial: str | None = None) -> list[str]:
    command = [adb_path or shutil.which("adb") or "adb"]
    if adb_serial:
        command.extend(["-s", adb_serial])
    return command


def list_remote_images(
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    remote_dir: str = DEFAULT_REMOTE_DIR,
    runner=subprocess.run,
) -> list[dict[str, object]]:
    escaped_remote_dir = remote_dir.replace('"', '\\"')
    shell_script = (
        f'cd "{escaped_remote_dir}" 2>/dev/null || exit 0; '
        'for file in img-*.jpg; do '
        '[ -f "$file" ] || continue; '
        'size=$(wc -c < "$file" | tr -d " "); '
        f'printf "%s/%s\\t%s\\n" "{escaped_remote_dir}" "$file" "$size"; '
        "done"
    )
    result = runner(
        [*adb_base_command(adb_path=adb_path, adb_serial=adb_serial), "shell", shell_script],
        check=True,
        capture_output=True,
        text=True,
    )
    items: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        remote_path, separator, size_text = line.partition("\t")
        if not separator:
            continue
        remote_path = remote_path.strip()
        size_text = size_text.strip()
        if not remote_path or not size_text.isdigit():
            continue
        items.append({"remote_path": remote_path, "size": int(size_text)})
    items.sort(key=lambda item: str(item["remote_path"]))
    return items


def current_foreground_package(
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> str:
    result = runner(
        [
            *adb_base_command(adb_path=adb_path, adb_serial=adb_serial),
            "shell",
            "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity'",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"([A-Za-z0-9_.]+)/[A-Za-z0-9_.$]+", result.stdout)
    return match.group(1) if match else ""


def dump_ui_hierarchy(
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> str:
    result = runner(
        [
            *adb_base_command(adb_path=adb_path, adb_serial=adb_serial),
            "shell",
            "uiautomator dump /sdcard/window_dump.xml >/dev/null 2>&1; cat /sdcard/window_dump.xml",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_bounds_center(bounds_text: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_text.strip())
    if not match:
        return None
    left, top, right, bottom = map(int, match.groups())
    return ((left + right) // 2, (top + bottom) // 2)


def find_import_button_center(
    ui_xml: str,
    *,
    button_text: str = DEFAULT_IMPORT_BUTTON_TEXT,
    banner_text: str = DEFAULT_IMPORT_BANNER_TEXT,
) -> tuple[int, int] | None:
    root = ET.fromstring(ui_xml)
    nodes = list(root.iter("node"))
    banner_present = any(banner_text in str(node.attrib.get("text") or "") for node in nodes)
    if not banner_present:
        return None
    for node in nodes:
        text = str(node.attrib.get("text") or "")
        content_desc = str(node.attrib.get("content-desc") or "")
        if text == button_text or content_desc == button_text:
            return parse_bounds_center(str(node.attrib.get("bounds") or ""))
    return None


def find_node_center_by_resource_id(ui_xml: str, *, resource_id: str) -> tuple[int, int] | None:
    root = ET.fromstring(ui_xml)
    for node in root.iter("node"):
        if str(node.attrib.get("resource-id") or "") != resource_id:
            continue
        return parse_bounds_center(str(node.attrib.get("bounds") or ""))
    return None


def tap_screen(
    x: int,
    y: int,
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> None:
    runner(
        [*adb_base_command(adb_path=adb_path, adb_serial=adb_serial), "shell", "input", "tap", str(x), str(y)],
        check=True,
        capture_output=True,
        text=True,
    )


def maybe_trigger_import(
    *,
    config: dict[str, object],
    state: dict[str, object],
    state_path: Path,
    current_foreground_package_impl=current_foreground_package,
    dump_ui_hierarchy_impl=dump_ui_hierarchy,
    tap_screen_impl=tap_screen,
    now_timestamp: float | None = None,
) -> dict[str, object]:
    if not bool(config.get("auto_import_enabled", True)):
        return {"import_tapped": False, "reason": "disabled"}

    now_timestamp = float(now_timestamp if now_timestamp is not None else time.time())
    last_import_tap_at = float(state.get("last_import_tap_at") or 0.0)
    cooldown_seconds = float(config.get("import_cooldown_seconds") or DEFAULT_IMPORT_COOLDOWN_SECONDS)
    if last_import_tap_at and now_timestamp - last_import_tap_at < cooldown_seconds:
        return {"import_tapped": False, "reason": "cooldown"}

    foreground_package = current_foreground_package_impl(
        adb_path=str(config.get("adb_path") or ""),
        adb_serial=str(config.get("adb_serial") or ""),
    )
    if foreground_package != str(config.get("rokid_package") or DEFAULT_ROKID_PACKAGE):
        return {"import_tapped": False, "reason": "foreground_mismatch", "foreground_package": foreground_package}

    ui_xml = dump_ui_hierarchy_impl(
        adb_path=str(config.get("adb_path") or ""),
        adb_serial=str(config.get("adb_serial") or ""),
    )
    center = find_import_button_center(
        ui_xml,
        button_text=str(config.get("import_button_text") or DEFAULT_IMPORT_BUTTON_TEXT),
        banner_text=str(config.get("import_banner_text") or DEFAULT_IMPORT_BANNER_TEXT),
    )
    if center is None:
        last_album_nav_tap_at = float(state.get("last_album_nav_tap_at") or 0.0)
        album_nav_cooldown_seconds = float(
            config.get("album_nav_cooldown_seconds") or DEFAULT_ALBUM_NAV_COOLDOWN_SECONDS
        )
        if last_album_nav_tap_at and now_timestamp - last_album_nav_tap_at < album_nav_cooldown_seconds:
            return {"import_tapped": False, "reason": "awaiting_album_page"}

        album_center = find_node_center_by_resource_id(
            ui_xml,
            resource_id=str(config.get("album_tab_resource_id") or DEFAULT_ALBUM_TAB_RESOURCE_ID),
        )
        if album_center is None:
            return {"import_tapped": False, "reason": "button_not_found"}
        tap_screen_impl(
            album_center[0],
            album_center[1],
            adb_path=str(config.get("adb_path") or ""),
            adb_serial=str(config.get("adb_serial") or ""),
        )
        state["last_album_nav_tap_at"] = now_timestamp
        write_json(state_path, state)
        return {"import_tapped": False, "reason": "navigated_to_album", "tap_center": [album_center[0], album_center[1]]}

    tap_screen_impl(
        center[0],
        center[1],
        adb_path=str(config.get("adb_path") or ""),
        adb_serial=str(config.get("adb_serial") or ""),
    )
    state["last_import_tap_at"] = now_timestamp
    write_json(state_path, state)
    return {"import_tapped": True, "reason": "tapped", "tap_center": [center[0], center[1]]}


def pull_remote_image(
    *,
    remote_path: str,
    local_path: Path,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> Path:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    runner(
        [*adb_base_command(adb_path=adb_path, adb_serial=adb_serial), "pull", remote_path, str(local_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    if not local_path.is_file():
        raise FileNotFoundError(f"missing pulled Rokid image: {local_path}")
    return local_path


def process_remote_image(
    *,
    remote_item: dict[str, object],
    config: dict[str, object],
    pull_remote_image_impl=pull_remote_image,
    generate_stylized_remote_image_impl=rokid_render_pipeline.generate_from_image_path,
    submit_print_job_impl=print_client.submit_print_job,
    submit_mobile_print_job_impl=xiaomi_home_print.submit_print_job,
) -> dict[str, object]:
    state_dir = Path(str(config.get("state_dir") or DEFAULT_STATE_DIR))
    output_dir = Path(str(config.get("output_dir") or DEFAULT_OUTPUT_DIR))
    remote_path = str(remote_item["remote_path"])
    remote_size = int(remote_item["size"])

    job = job_store.create_job(
        state_dir,
        trigger="rokid-watch",
        metadata={
            "source": "rokid-watch",
            "remote_path": remote_path,
            "remote_size": remote_size,
        },
        queue_capture=False,
    )
    artifact_dir = job_store.artifact_dir(state_dir, job["job_id"])
    local_path = artifact_dir / Path(remote_path).name
    pull_remote_image_impl(
        remote_path=remote_path,
        local_path=local_path,
        adb_path=str(config.get("adb_path") or ""),
        adb_serial=str(config.get("adb_serial") or ""),
    )
    source_fingerprint = hashlib.sha256(local_path.read_bytes()).hexdigest()
    duplicate_job: dict[str, object] | None = None
    for existing in job_store.list_jobs(state_dir):
        if existing.get("job_id") == job["job_id"]:
            continue
        if existing.get("source_fingerprint") != source_fingerprint:
            continue
        duplicate_job = existing
        break

    if duplicate_job is not None:
        job_store.update_job(
            state_dir,
            job["job_id"],
            status="deduplicated",
            source_image_path=str(local_path),
            source_fingerprint=source_fingerprint,
            output_path=duplicate_job.get("output_path"),
            metadata_path=duplicate_job.get("metadata_path"),
            generation=duplicate_job.get("generation"),
            printer_job_id=duplicate_job.get("printer_job_id"),
            print_response=duplicate_job.get("print_response"),
            duplicate_of_job_id=duplicate_job.get("job_id"),
        )
        return {
            "job_id": job["job_id"],
            "remote_path": remote_path,
            "local_path": str(local_path),
            "output_path": str(duplicate_job.get("output_path") or ""),
            "metadata_path": str(duplicate_job.get("metadata_path") or ""),
            "printer_job_id": str(duplicate_job.get("printer_job_id") or ""),
            "deduplicated": True,
            "duplicate_of_job_id": str(duplicate_job.get("job_id") or ""),
            "printed": False,
        }

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    generation = generate_stylized_remote_image_impl(
        api_key=os.environ.get("ARK_API_KEY", ""),
        image_path=local_path,
        output_dir=output_dir,
        model=str(config.get("model") or pipeline.DEFAULT_MODEL),
        size=str(config.get("size") or pipeline.DEFAULT_SIZE),
        response_format=str(config.get("response_format") or pipeline.DEFAULT_RESPONSE_FORMAT),
        api_url=str(config.get("api_url") or pipeline.DEFAULT_API_URL),
        timeout=int(config.get("timeout") or pipeline.DEFAULT_TIMEOUT),
        style_slug=str(config.get("style_slug") or DEFAULT_STYLE_SLUG),
        style_prompt=str(config.get("style_prompt") or rokid_render_pipeline.DEFAULT_STYLE_PROMPT),
        timestamp=timestamp,
    )
    output_path = Path(str(generation["output_path"]))
    metadata_path = pipeline.write_output_metadata(
        output_path,
        {
            "job_id": job["job_id"],
            "trigger": "rokid-watch",
            "created_at": job["created_at"],
            "remote_path": remote_path,
            "remote_size": remote_size,
            "source_image_path": str(local_path),
            **generation,
            "print_backend": str(config.get("print_backend") or DEFAULT_PRINT_BACKEND),
            "print_media": str(config.get("print_media") or job_store.DEFAULT_PRINT_MEDIA),
        },
    )
    job_store.update_job(
        state_dir,
        job["job_id"],
        status="generated",
        source_image_path=str(local_path),
        source_fingerprint=source_fingerprint,
        generation=generation,
        output_path=str(output_path),
        metadata_path=str(metadata_path),
    )

    print_backend = str(config.get("print_backend") or DEFAULT_PRINT_BACKEND).strip() or DEFAULT_PRINT_BACKEND
    queued_job = job_store.enqueue_job(
        state_dir,
        job["job_id"],
        "print",
        status="queued_print",
        fields={
            "print_backend": print_backend,
            "print_media": str(config.get("print_media") or job_store.DEFAULT_PRINT_MEDIA),
            "print_not_before_at": job_store.current_iso(),
            "output_path": str(output_path),
            "metadata_path": str(metadata_path),
            "adb_path": str(config.get("adb_path") or ""),
            "adb_serial": str(config.get("adb_serial") or ""),
            "phone_print_remote_dir": str(
                config.get("phone_print_remote_dir") or xiaomi_home_print.DEFAULT_REMOTE_DIR
            ),
            "phone_print_component": str(
                config.get("phone_print_component") or xiaomi_home_print.DEFAULT_SEND_COMPONENT
            ),
            "phone_print_target_printer_name": str(
                config.get("phone_print_target_printer_name") or xiaomi_home_print.DEFAULT_TARGET_PRINTER_NAME
            ),
            "phone_print_poll_timeout_seconds": float(
                config.get("phone_print_poll_timeout_seconds") or xiaomi_home_print.DEFAULT_POLL_TIMEOUT_SECONDS
            ),
            "phone_print_poll_interval_seconds": float(
                config.get("phone_print_poll_interval_seconds") or xiaomi_home_print.DEFAULT_POLL_INTERVAL_SECONDS
            ),
        },
    )
    return {
        "job_id": job["job_id"],
        "remote_path": remote_path,
        "local_path": str(local_path),
        "output_path": str(output_path),
        "metadata_path": str(metadata_path),
        "printer_job_id": "",
        "deduplicated": False,
        "printed": False,
        "status": str(queued_job.get("status") or ""),
    }


def normalize_state(state: dict | None = None) -> dict[str, object]:
    payload = dict(state or {})
    files = payload.get("files")
    if not isinstance(files, dict):
        payload["files"] = {}
    payload["initialized"] = bool(payload.get("initialized", False))
    return payload


def poll_once(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
    detect_adb_serial_impl=detect_adb_serial,
    maybe_trigger_import_impl=maybe_trigger_import,
    list_remote_images_impl=list_remote_images,
    process_remote_image_impl=process_remote_image,
) -> dict[str, object]:
    config = ensure_config(config_path, detect_adb_serial_impl=detect_adb_serial_impl)
    result = {
        "enabled": bool(config.get("enabled", True)),
        "processed_remote_paths": [],
    }
    if not result["enabled"]:
        return result

    state = normalize_state(load_json(state_path, default={}))
    try:
        result["import"] = maybe_trigger_import_impl(
            config=config,
            state=state,
            state_path=state_path,
        )
        state.pop("last_import_error", None)
    except Exception as exc:
        error_text = str(exc).strip()
        state["last_import_error"] = error_text
        result["import"] = {
            "import_tapped": False,
            "reason": "import_check_failed",
            "error": error_text,
        }
    remote_items = list_remote_images_impl(
        adb_path=str(config.get("adb_path") or ""),
        adb_serial=str(config.get("adb_serial") or ""),
        remote_dir=str(config.get("remote_dir") or DEFAULT_REMOTE_DIR),
    )
    state["last_polled_at"] = current_iso()
    state["last_seen_count"] = len(remote_items)

    if not state["initialized"]:
        for item in remote_items:
            remote_path = str(item["remote_path"])
            size = int(item["size"])
            state["files"][remote_path] = {
                "last_seen_size": size,
                "stable_polls": int(config.get("stable_polls_required") or DEFAULT_STABLE_POLLS_REQUIRED),
                "processed": True,
                "processed_size": size,
                "processed_reason": "initial_baseline",
            }
        state["initialized"] = True
        write_json(state_path, state)
        return result

    for item in remote_items:
        remote_path = str(item["remote_path"])
        size = int(item["size"])
        entry = state["files"].get(remote_path)
        if not isinstance(entry, dict):
            state["files"][remote_path] = {
                "last_seen_size": size,
                "stable_polls": 1,
                "processed": False,
                "processed_size": None,
                "processed_reason": None,
                "last_error": None,
                "last_attempt_at": None,
            }
            continue

        if entry.get("processed") and int(entry.get("processed_size") or -1) == size:
            entry["last_seen_size"] = size
            entry["stable_polls"] = max(
                int(entry.get("stable_polls") or 0),
                int(config.get("stable_polls_required") or DEFAULT_STABLE_POLLS_REQUIRED),
            )
            continue

        if int(entry.get("last_seen_size") or -1) == size:
            entry["stable_polls"] = int(entry.get("stable_polls") or 0) + 1
        else:
            entry["last_seen_size"] = size
            entry["stable_polls"] = 1
        entry["last_seen_size"] = size

        if entry.get("processed"):
            continue

        last_attempt_at = float(entry.get("last_attempt_at") or 0.0)
        retry_cooldown = float(config.get("process_retry_cooldown_seconds") or DEFAULT_PROCESS_RETRY_COOLDOWN_SECONDS)
        if last_attempt_at and (time.time() - last_attempt_at) < retry_cooldown:
            continue

        if int(entry.get("stable_polls") or 0) < int(config.get("stable_polls_required") or DEFAULT_STABLE_POLLS_REQUIRED):
            continue

        entry["last_attempt_at"] = time.time()
        try:
            processed = process_remote_image_impl(
                remote_item=item,
                config=config,
            )
        except Exception as exc:
            entry["last_error"] = str(exc)
            continue

        entry["processed"] = True
        entry["processed_size"] = size
        entry["processed_reason"] = "processed"
        entry["last_error"] = None
        entry["last_result"] = processed
        result["processed_remote_paths"].append(remote_path)

    write_json(state_path, state)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch the Rokid download folder and auto-render + print new photos.")
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--poll-once", action="store_true", help="Run a single poll iteration and exit.")
    parser.add_argument("--set-enabled", choices=("true", "false"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.set_enabled is not None:
        updated = set_enabled(args.config_path, args.set_enabled == "true")
        print(json.dumps(updated, ensure_ascii=False, indent=2))
        return 0

    if args.poll_once:
        result = poll_once(config_path=args.config_path, state_path=args.state_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    while True:
        try:
            config = ensure_config(args.config_path)
            poll_once(config_path=args.config_path, state_path=args.state_path)
            sleep_seconds = float(config.get("poll_interval_seconds") or DEFAULT_POLL_INTERVAL_SECONDS)
        except Exception as exc:
            print(f"[rokid-watch] {exc}", file=sys.stderr)
            sleep_seconds = DEFAULT_POLL_INTERVAL_SECONDS
        time.sleep(max(sleep_seconds, 0.2))


if __name__ == "__main__":
    raise SystemExit(main())
