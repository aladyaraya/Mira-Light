#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_REMOTE_DIR = "/sdcard/Pictures/OpenClawRokidPrints"
DEFAULT_SEND_COMPONENT = "com.xiaomi.smarthome/.printer.SendPrintActivity"
DEFAULT_TARGET_PRINTER_NAME = "米家口袋照片打印机1S"
DEFAULT_POLL_TIMEOUT_SECONDS = 180.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_PREVIEW_TITLE = "打印预览"
PREVIEW_PRINT_RESOURCE_ID = "hannto.printer.mint:id/title_bar_print"
PREVIEW_SHARE_RESOURCE_ID = "hannto.printer.mint:id/title_bar_preview_share"
PREVIEW_BACK_RESOURCE_ID = "hannto.printer.mint:id/title_bar_return"
PRINT_STATUS_RESOURCE_ID = "hannto.printer.mint:id/layout_cancel_job"
PRINT_STATUS_HINTS = ("正在传输", "准备中", "打印中")
PRINT_COMPLETED_TEXT = "打印完成"


def current_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def adb_base_command(*, adb_path: str | None = None, adb_serial: str | None = None) -> list[str]:
    command = [adb_path or "adb"]
    if adb_serial:
        command.extend(["-s", adb_serial])
    return command


def push_file(
    source_path: Path,
    *,
    remote_dir: str = DEFAULT_REMOTE_DIR,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> str:
    source_path = Path(source_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"missing local print image: {source_path}")

    runner(
        [*adb_base_command(adb_path=adb_path, adb_serial=adb_serial), "shell", "mkdir", "-p", remote_dir],
        check=True,
        capture_output=True,
        text=True,
    )
    remote_path = f"{remote_dir.rstrip('/')}/{source_path.name}"
    runner(
        [*adb_base_command(adb_path=adb_path, adb_serial=adb_serial), "push", str(source_path), remote_path],
        check=True,
        capture_output=True,
        text=True,
    )
    return remote_path


def start_send_intent(
    *,
    remote_path: str,
    component: str = DEFAULT_SEND_COMPONENT,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> dict[str, str]:
    result = runner(
        [
            *adb_base_command(adb_path=adb_path, adb_serial=adb_serial),
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.intent.action.SEND",
            "-t",
            "image/jpeg",
            "-n",
            component,
            "--grant-read-uri-permission",
            "--eu",
            "android.intent.extra.STREAM",
            f"file://{remote_path}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = {
        "status": "ok",
        "stdout": result.stdout.strip(),
        "component": component,
    }
    match = re.search(r"Activity:\s+([^\s]+)", result.stdout)
    if match:
        payload["activity"] = match.group(1)
    return payload


def current_foreground_component(
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> str:
    result = runner(
        [
            *adb_base_command(adb_path=adb_path, adb_serial=adb_serial),
            "shell",
            "dumpsys",
            "activity",
            "activities",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"topResumedActivity=ActivityRecord\{[^ ]+ u\d+ ([^ ]+)\}", result.stdout)
    if match:
        return match.group(1)
    match = re.search(r"ResumedActivity:\s+ActivityRecord\{[^ ]+ u\d+ ([^ ]+)\}", result.stdout)
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
    stdout = result.stdout.strip()
    if stdout.startswith("ERROR:"):
        raise RuntimeError(stdout)
    xml_start = stdout.find("<?xml")
    if xml_start == -1:
        raise RuntimeError(f"unexpected UI hierarchy output: {stdout}")
    return stdout[xml_start:]


def send_keyevent(
    key_name: str,
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    runner=subprocess.run,
) -> None:
    runner(
        [*adb_base_command(adb_path=adb_path, adb_serial=adb_serial), "shell", "input", "keyevent", key_name],
        check=True,
        capture_output=True,
        text=True,
    )


def _parse_ui_root(ui_xml: str) -> ET.Element:
    return ET.fromstring(ui_xml)


def _iter_nodes(ui_xml: str) -> list[ET.Element]:
    return list(_parse_ui_root(ui_xml).iter("node"))


def _find_node_by_resource_id(ui_xml: str, resource_id: str) -> ET.Element | None:
    for node in _iter_nodes(ui_xml):
        if str(node.attrib.get("resource-id") or "") == resource_id:
            return node
    return None


def _find_node_by_text(ui_xml: str, text: str) -> ET.Element | None:
    for node in _iter_nodes(ui_xml):
        if str(node.attrib.get("text") or "") == text:
            return node
    return None


def _find_focused_node(ui_xml: str) -> ET.Element | None:
    for node in _iter_nodes(ui_xml):
        if str(node.attrib.get("focused") or "").lower() == "true":
            return node
    return None


def _parse_bounds(bounds_text: str) -> tuple[int, int, int, int] | None:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_text.strip())
    if not match:
        return None
    return tuple(map(int, match.groups()))


def _bounds_contain(
    outer_bounds: tuple[int, int, int, int] | None,
    inner_bounds: tuple[int, int, int, int] | None,
) -> bool:
    if outer_bounds is None or inner_bounds is None:
        return False
    left, top, right, bottom = outer_bounds
    inner_left, inner_top, inner_right, inner_bottom = inner_bounds
    return left <= inner_left and top <= inner_top and right >= inner_right and bottom >= inner_bottom


def is_preview_page(ui_xml: str) -> bool:
    return _find_node_by_resource_id(ui_xml, PREVIEW_PRINT_RESOURCE_ID) is not None or _find_node_by_text(
        ui_xml,
        DEFAULT_PREVIEW_TITLE,
    ) is not None


def is_status_page(ui_xml: str) -> bool:
    if _find_node_by_resource_id(ui_xml, PRINT_STATUS_RESOURCE_ID) is not None:
        return True
    for hint in PRINT_STATUS_HINTS:
        if _find_node_by_text(ui_xml, hint) is not None:
            return True
    return False


def is_completion_page(ui_xml: str) -> bool:
    return _find_node_by_text(ui_xml, PRINT_COMPLETED_TEXT) is not None


def has_target_printer(ui_xml: str, printer_name: str) -> bool:
    return _find_node_by_text(ui_xml, printer_name) is not None


def focus_preview_print_button(
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    dump_ui_hierarchy_impl=dump_ui_hierarchy,
    send_keyevent_impl=send_keyevent,
    attempts: int = 8,
) -> None:
    for _ in range(attempts):
        ui_xml = dump_ui_hierarchy_impl(adb_path=adb_path, adb_serial=adb_serial)
        target_node = _find_node_by_resource_id(ui_xml, PREVIEW_PRINT_RESOURCE_ID)
        if target_node is None:
            raise RuntimeError("preview print button not visible")
        if str(target_node.attrib.get("focused") or "").lower() == "true":
            return

        focused = _find_focused_node(ui_xml)
        if focused is None:
            send_keyevent_impl("TAB", adb_path=adb_path, adb_serial=adb_serial)
            continue

        focused_resource_id = str(focused.attrib.get("resource-id") or "")
        if focused_resource_id in (PREVIEW_BACK_RESOURCE_ID, PREVIEW_SHARE_RESOURCE_ID):
            send_keyevent_impl("DPAD_RIGHT", adb_path=adb_path, adb_serial=adb_serial)
            continue

        send_keyevent_impl("TAB", adb_path=adb_path, adb_serial=adb_serial)

    raise RuntimeError("unable to focus Xiaomi print button")


def select_printer_from_device_list(
    *,
    printer_name: str,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    dump_ui_hierarchy_impl=dump_ui_hierarchy,
    send_keyevent_impl=send_keyevent,
    attempts: int = 20,
) -> None:
    for _ in range(attempts):
        ui_xml = dump_ui_hierarchy_impl(adb_path=adb_path, adb_serial=adb_serial)
        printer_node = _find_node_by_text(ui_xml, printer_name)
        if printer_node is None:
            raise RuntimeError(f"target printer not visible: {printer_name}")

        focused = _find_focused_node(ui_xml)
        printer_bounds = _parse_bounds(str(printer_node.attrib.get("bounds") or ""))
        focused_bounds = _parse_bounds(str((focused.attrib.get("bounds") if focused is not None else "") or ""))
        if focused is not None and _bounds_contain(focused_bounds, printer_bounds):
            send_keyevent_impl("DPAD_CENTER", adb_path=adb_path, adb_serial=adb_serial)
            return

        send_keyevent_impl("TAB", adb_path=adb_path, adb_serial=adb_serial)

    raise RuntimeError(f"unable to focus target printer: {printer_name}")


def submit_print_job(
    source_path: Path,
    *,
    adb_path: str | None = None,
    adb_serial: str | None = None,
    remote_dir: str = DEFAULT_REMOTE_DIR,
    component: str = DEFAULT_SEND_COMPONENT,
    printer_name: str = DEFAULT_TARGET_PRINTER_NAME,
    poll_timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    push_file_impl=push_file,
    start_send_intent_impl=start_send_intent,
    current_foreground_component_impl=current_foreground_component,
    dump_ui_hierarchy_impl=dump_ui_hierarchy,
    send_keyevent_impl=send_keyevent,
    time_module=time,
) -> dict[str, object]:
    remote_path = push_file_impl(
        Path(source_path),
        remote_dir=remote_dir,
        adb_path=adb_path,
        adb_serial=adb_serial,
    )
    share_response = start_send_intent_impl(
        remote_path=remote_path,
        component=component,
        adb_path=adb_path,
        adb_serial=adb_serial,
    )

    selected_printer = False
    submitted_from_preview = False
    deadline = time_module.time() + poll_timeout_seconds

    while time_module.time() < deadline:
        activity = current_foreground_component_impl(adb_path=adb_path, adb_serial=adb_serial)
        ui_xml = dump_ui_hierarchy_impl(adb_path=adb_path, adb_serial=adb_serial)

        if is_completion_page(ui_xml):
            return {
                "job_id": f"xiaomi-home-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "backend": "xiaomi_home_share",
                "remote_path": remote_path,
                "activity": activity,
                "printer_name": printer_name,
                "submitted_via_preview": submitted_from_preview,
                "selected_printer": selected_printer,
                "completed": True,
                "share_response": share_response,
            }

        if is_status_page(ui_xml):
            time_module.sleep(poll_interval_seconds)
            continue

        if has_target_printer(ui_xml, printer_name) and not is_preview_page(ui_xml):
            select_printer_from_device_list(
                printer_name=printer_name,
                adb_path=adb_path,
                adb_serial=adb_serial,
                dump_ui_hierarchy_impl=dump_ui_hierarchy_impl,
                send_keyevent_impl=send_keyevent_impl,
            )
            selected_printer = True
            time_module.sleep(poll_interval_seconds)
            continue

        if is_preview_page(ui_xml) and not submitted_from_preview:
            focus_preview_print_button(
                adb_path=adb_path,
                adb_serial=adb_serial,
                dump_ui_hierarchy_impl=dump_ui_hierarchy_impl,
                send_keyevent_impl=send_keyevent_impl,
            )
            send_keyevent_impl("DPAD_CENTER", adb_path=adb_path, adb_serial=adb_serial)
            submitted_from_preview = True
            time_module.sleep(poll_interval_seconds)
            continue

        time_module.sleep(poll_interval_seconds)

    raise TimeoutError(f"timed out waiting for Xiaomi Home print submission for {source_path}")
