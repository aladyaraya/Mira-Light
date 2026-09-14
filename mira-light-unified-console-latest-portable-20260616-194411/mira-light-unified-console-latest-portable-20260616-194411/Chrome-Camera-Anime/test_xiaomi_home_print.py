import sys
import tempfile
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parent.parent
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

import rokid_watch_daemon
import xiaomi_home_print
import job_store


PREVIEW_NO_FOCUS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" package="com.xiaomi.smarthome" bounds="[0,0][1080,2183]">
    <node index="0" resource-id="hannto.printer.mint:id/title_bar_return" class="android.widget.ImageView" clickable="true" focusable="true" focused="false" bounds="[0,87][168,225]" />
    <node index="1" resource-id="hannto.printer.mint:id/title_bar_preview_share" class="android.widget.ImageView" clickable="true" focusable="true" focused="false" bounds="[821,101][931,211]" />
    <node index="2" resource-id="hannto.printer.mint:id/title_bar_print" class="android.widget.ImageView" clickable="true" focusable="true" focused="false" bounds="[931,101][1041,211]" />
    <node index="3" text="打印预览" resource-id="hannto.printer.mint:id/title_bar_title" class="android.widget.TextView" clickable="false" focusable="false" focused="false" bounds="[430,119][650,193]" />
  </node>
</hierarchy>
"""

PREVIEW_BACK_FOCUSED_XML = PREVIEW_NO_FOCUS_XML.replace('title_bar_return" class="android.widget.ImageView" clickable="true" focusable="true" focused="false"', 'title_bar_return" class="android.widget.ImageView" clickable="true" focusable="true" focused="true"')
PREVIEW_SHARE_FOCUSED_XML = PREVIEW_NO_FOCUS_XML.replace('title_bar_preview_share" class="android.widget.ImageView" clickable="true" focusable="true" focused="false"', 'title_bar_preview_share" class="android.widget.ImageView" clickable="true" focusable="true" focused="true"')
PREVIEW_PRINT_FOCUSED_XML = PREVIEW_NO_FOCUS_XML.replace('title_bar_print" class="android.widget.ImageView" clickable="true" focusable="true" focused="false"', 'title_bar_print" class="android.widget.ImageView" clickable="true" focusable="true" focused="true"')

DEVICE_LIST_NO_FOCUS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" package="com.xiaomi.smarthome" bounds="[0,0][1080,2183]">
    <node index="0" resource-id="device_row_one" class="android.widget.LinearLayout" clickable="true" focusable="true" focused="false" bounds="[0,300][1080,500]">
      <node index="0" text="小米米家照片打印机1S" class="android.widget.TextView" clickable="false" focusable="false" focused="false" bounds="[120,340][760,420]" />
    </node>
    <node index="1" resource-id="device_row_two" class="android.widget.LinearLayout" clickable="true" focusable="true" focused="false" bounds="[0,520][1080,720]">
      <node index="0" text="米家口袋照片打印机1S" class="android.widget.TextView" clickable="false" focusable="false" focused="false" bounds="[120,560][760,640]" />
    </node>
  </node>
</hierarchy>
"""

DEVICE_LIST_ROW_ONE_FOCUSED_XML = DEVICE_LIST_NO_FOCUS_XML.replace('device_row_one" class="android.widget.LinearLayout" clickable="true" focusable="true" focused="false"', 'device_row_one" class="android.widget.LinearLayout" clickable="true" focusable="true" focused="true"')
DEVICE_LIST_ROW_TWO_FOCUSED_XML = DEVICE_LIST_NO_FOCUS_XML.replace('device_row_two" class="android.widget.LinearLayout" clickable="true" focusable="true" focused="false"', 'device_row_two" class="android.widget.LinearLayout" clickable="true" focusable="true" focused="true"')
STATUS_PAGE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" package="com.xiaomi.smarthome" bounds="[0,0][1080,2183]">
    <node index="0" text="正在传输" class="android.widget.TextView" clickable="false" focusable="false" focused="false" bounds="[90,980][420,1060]" />
    <node index="1" resource-id="hannto.printer.mint:id/layout_cancel_job" class="android.widget.LinearLayout" clickable="true" focusable="true" focused="false" bounds="[0,1900][360,2100]" />
  </node>
</hierarchy>
"""
COMPLETION_PAGE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" package="com.xiaomi.smarthome" bounds="[0,0][1080,2183]">
    <node index="0" text="打印完成" class="android.widget.TextView" clickable="false" focusable="false" focused="false" bounds="[350,1000][730,1080]" />
  </node>
</hierarchy>
"""


class FakeTime:
    def __init__(self) -> None:
        self.current = 0.0

    def time(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds


class XiaomiHomePrintTests(unittest.TestCase):
    def test_focus_preview_print_button_uses_keyboard_navigation(self):
        dumps = iter(
            [
                PREVIEW_NO_FOCUS_XML,
                PREVIEW_BACK_FOCUSED_XML,
                PREVIEW_SHARE_FOCUSED_XML,
                PREVIEW_PRINT_FOCUSED_XML,
            ]
        )
        sent_keys: list[str] = []

        xiaomi_home_print.focus_preview_print_button(
            dump_ui_hierarchy_impl=lambda **_kwargs: next(dumps),
            send_keyevent_impl=lambda key_name, **_kwargs: sent_keys.append(key_name),
        )

        self.assertEqual(["TAB", "DPAD_RIGHT", "DPAD_RIGHT"], sent_keys)

    def test_select_printer_from_device_list_uses_focus_cycle(self):
        dumps = iter(
            [
                DEVICE_LIST_NO_FOCUS_XML,
                DEVICE_LIST_ROW_ONE_FOCUSED_XML,
                DEVICE_LIST_ROW_TWO_FOCUSED_XML,
            ]
        )
        sent_keys: list[str] = []

        xiaomi_home_print.select_printer_from_device_list(
            printer_name="米家口袋照片打印机1S",
            dump_ui_hierarchy_impl=lambda **_kwargs: next(dumps),
            send_keyevent_impl=lambda key_name, **_kwargs: sent_keys.append(key_name),
        )

        self.assertEqual(["TAB", "TAB", "DPAD_CENTER"], sent_keys)

    def test_submit_print_job_waits_until_completion_page(self):
        dumps = iter(
            [
                PREVIEW_PRINT_FOCUSED_XML,
                PREVIEW_PRINT_FOCUSED_XML,
                STATUS_PAGE_XML,
                COMPLETION_PAGE_XML,
            ]
        )
        sent_keys: list[str] = []
        fake_time = FakeTime()

        result = xiaomi_home_print.submit_print_job(
            Path("/tmp/rendered.jpg"),
            push_file_impl=lambda *_args, **_kwargs: "/sdcard/Pictures/OpenClawRokidPrints/rendered.jpg",
            start_send_intent_impl=lambda **_kwargs: {"status": "ok", "activity": "com.xiaomi.smarthome/.printer.SendPrintActivity"},
            current_foreground_component_impl=lambda **_kwargs: "com.xiaomi.smarthome/.frame.plugin.runtime.activity.PluginHostActivity",
            dump_ui_hierarchy_impl=lambda **_kwargs: next(dumps),
            send_keyevent_impl=lambda key_name, **_kwargs: sent_keys.append(key_name),
            poll_timeout_seconds=5.0,
            poll_interval_seconds=0.5,
            time_module=fake_time,
        )

        self.assertEqual(["DPAD_CENTER"], sent_keys)
        self.assertTrue(result["completed"])
        self.assertTrue(result["submitted_via_preview"])


class RokidWatchXiaomiBackendTests(unittest.TestCase):
    def test_process_remote_image_queues_xiaomi_home_backend_for_worker_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            output_dir = state_dir / "output"
            output_dir.mkdir(parents=True)
            remote_path = "/sdcard/Download/Rokid AI/img-20260324-183100-demo.jpg"

            config = {
                **rokid_watch_daemon.default_config(adb_path="/tmp/adb", adb_serial="__ADB_SERIAL__"),
                "state_dir": str(state_dir),
                "output_dir": str(output_dir),
                "print_backend": "xiaomi_home_share",
                "phone_print_target_printer_name": "米家口袋照片打印机1S",
            }

            def pull_remote_image_impl(*, remote_path, local_path, **_kwargs):
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(b"source-image")
                return local_path

            def generate_stylized_remote_image_impl(**_kwargs):
                rendered_path = output_dir / "rendered.jpg"
                rendered_path.write_bytes(b"rendered-image")
                return {
                    "output_path": str(rendered_path),
                    "image_url": "https://example.invalid/rendered.jpg",
                }

            bridge_calls: list[Path] = []
            mobile_calls: list[tuple[Path, str]] = []

            def submit_print_job_impl(source_path, **_kwargs):
                bridge_calls.append(source_path)
                return {"job_id": "bridge-job-1"}

            def submit_mobile_print_job_impl(source_path, *, printer_name, **_kwargs):
                mobile_calls.append((source_path, printer_name))
                return {"job_id": "xiaomi-job-1", "backend": "xiaomi_home_share"}

            result = rokid_watch_daemon.process_remote_image(
                remote_item={"remote_path": remote_path, "size": 128},
                config=config,
                pull_remote_image_impl=pull_remote_image_impl,
                generate_stylized_remote_image_impl=generate_stylized_remote_image_impl,
                submit_print_job_impl=submit_print_job_impl,
                submit_mobile_print_job_impl=submit_mobile_print_job_impl,
            )

            self.assertEqual([], bridge_calls)
            self.assertEqual([], mobile_calls)
            self.assertEqual("queued_print", result["status"])
            persisted_job = job_store.load_job(state_dir, result["job_id"])
            self.assertEqual("queued_print", persisted_job["status"])
            self.assertEqual("xiaomi_home_share", persisted_job["print_backend"])
            self.assertEqual("米家口袋照片打印机1S", persisted_job["phone_print_target_printer_name"])


if __name__ == "__main__":
    unittest.main()
