#!/usr/bin/env python3
import base64
import json
import os
import re
import subprocess
import urllib.request
from typing import Any
from pathlib import Path


DEFAULT_PROFILE_PATH = Path(os.environ.get("OPENCLAW_PRINTER_BRIDGE_PROFILE", Path.home() / ".openclaw-printer-bridge" / "profile.json"))
DEFAULT_ENV_PATH = Path(os.environ.get("OPENCLAW_PRINTER_BRIDGE_ENV", Path.home() / ".openclaw-printer-bridge.env"))
DEFAULT_BRIDGE_URL = os.environ.get("OPENCLAW_PRINTER_BRIDGE_URL", "http://127.0.0.1:9771")
DEFAULT_MEDIA = "4x6.Fullbleed"
DEFAULT_TIMEOUT = 30
QUEUE_SUFFIX_PATTERN = re.compile(r"__\d+_$")
DISABLED_QUEUE_MARKERS = ("disabled", "已停用")


def read_bridge_profile(profile_path: Path = DEFAULT_PROFILE_PATH) -> dict:
    return json.loads(profile_path.read_text(encoding="utf-8"))


def write_bridge_profile(profile_path: Path, payload: dict[str, Any]) -> None:
    profile_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_queue_family(queue_name: str) -> str:
    return QUEUE_SUFFIX_PATTERN.sub("", queue_name.strip())


def _parse_default_queue_name(stdout: str) -> str:
    text = stdout.strip()
    if not text:
        return ""
    for separator in ("：", ":"):
        if separator in text:
            return text.rsplit(separator, 1)[-1].strip()
    return text.splitlines()[-1].strip()


def list_cups_queues(*, runner=subprocess.run) -> list[str]:
    result = runner(
        ["lpstat", "-e"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read_default_queue_name(*, runner=subprocess.run) -> str:
    result = runner(
        ["lpstat", "-d"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return _parse_default_queue_name(result.stdout)


def queue_is_enabled(queue_name: str, *, runner=subprocess.run) -> bool:
    result = runner(
        ["lpstat", "-p", queue_name],
        check=False,
        capture_output=True,
        text=True,
    )
    status_text = f"{result.stdout}\n{result.stderr}".lower()
    return not any(marker in status_text for marker in DISABLED_QUEUE_MARKERS)


def resolve_printer_queue_name(
    profile_path: Path = DEFAULT_PROFILE_PATH,
    *,
    runner=subprocess.run,
    persist: bool = True,
) -> str:
    profile = read_bridge_profile(profile_path) if profile_path.is_file() else {}
    printer_payload = profile.get("printer") if isinstance(profile, dict) else {}
    if not isinstance(printer_payload, dict):
        printer_payload = {}

    configured_queue_name = str(printer_payload.get("queue_name") or "").strip()
    display_name = str(printer_payload.get("display_name") or configured_queue_name).strip()
    available_queues = list_cups_queues(runner=runner)
    if not available_queues:
        return configured_queue_name

    family = _normalize_queue_family(configured_queue_name or display_name)
    matching_queues = [
        queue_name
        for queue_name in available_queues
        if family and _normalize_queue_family(queue_name) == family
    ]
    if not matching_queues:
        if configured_queue_name in available_queues:
            resolved_queue_name = configured_queue_name
        else:
            default_queue_name = read_default_queue_name(runner=runner)
            resolved_queue_name = default_queue_name if default_queue_name in available_queues else available_queues[0]
    else:
        enabled_matching_queues = [
            queue_name
            for queue_name in matching_queues
            if queue_is_enabled(queue_name, runner=runner)
        ]
        default_queue_name = read_default_queue_name(runner=runner)
        if default_queue_name in enabled_matching_queues:
            resolved_queue_name = default_queue_name
        elif configured_queue_name in enabled_matching_queues:
            resolved_queue_name = configured_queue_name
        elif enabled_matching_queues:
            resolved_queue_name = enabled_matching_queues[0]
        elif default_queue_name in matching_queues:
            resolved_queue_name = default_queue_name
        elif configured_queue_name in matching_queues:
            resolved_queue_name = configured_queue_name
        else:
            resolved_queue_name = matching_queues[0]

    if (
        persist
        and profile_path.is_file()
        and resolved_queue_name
        and resolved_queue_name != configured_queue_name
    ):
        printer_payload["queue_name"] = resolved_queue_name
        printer_payload["display_name"] = resolved_queue_name
        profile["printer"] = printer_payload
        write_bridge_profile(profile_path, profile)
    return resolved_queue_name


def resolve_bridge_url(profile_path: Path = DEFAULT_PROFILE_PATH) -> str:
    if os.environ.get("OPENCLAW_PRINTER_BRIDGE_URL"):
        return os.environ["OPENCLAW_PRINTER_BRIDGE_URL"]
    if profile_path.is_file():
        return str(read_bridge_profile(profile_path)["bridge"]["local_url"])
    return DEFAULT_BRIDGE_URL


def read_bridge_token(env_path: Path = DEFAULT_ENV_PATH) -> str:
    if os.environ.get("OPENCLAW_PRINTER_BRIDGE_TOKEN"):
        return os.environ["OPENCLAW_PRINTER_BRIDGE_TOKEN"]
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("export OPENCLAW_PRINTER_BRIDGE_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("bridge token not found")


def submit_print_job(
    source_path: Path,
    *,
    media: str = DEFAULT_MEDIA,
    bridge_url: str | None = None,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    urlopen_impl=urllib.request.urlopen,
) -> dict[str, object]:
    bridge_url = bridge_url or resolve_bridge_url()
    token = token or read_bridge_token()
    payload = {
        "content_base64": base64.b64encode(source_path.read_bytes()).decode("ascii"),
        "filename": source_path.name,
        "media": media,
        "fit_to_page": False,
    }
    request = urllib.request.Request(
        f"{bridge_url}/v1/printers/default/print-image",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen_impl(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
