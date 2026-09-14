from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONSOLE_DIR = ROOT / "mira-light-unified-director-console"

if str(CONSOLE_DIR) not in sys.path:
    sys.path.insert(0, str(CONSOLE_DIR))

import shenzhen_console


class TouchSensitivityConsoleTest(unittest.TestCase):
    def test_identifies_known_touch_sensitivity_preset(self) -> None:
        config = dict(shenzhen_console.TOUCH_SENSITIVITY_PRESETS["sensitive"]["values"])
        config["version"] = 14

        self.assertEqual(shenzhen_console.identify_touch_sensitivity_preset(config), "sensitive")

    def test_custom_touch_sensitivity_is_not_forced_into_preset(self) -> None:
        config = dict(shenzhen_console.TOUCH_SENSITIVITY_PRESETS["balanced"]["values"])
        config["lamp_thr"] = 256

        self.assertIsNone(shenzhen_console.identify_touch_sensitivity_preset(config))

    def test_render_touch_sensitivity_script_updates_mapping_and_restarts_service(self) -> None:
        script = shenzhen_console.render_touch_sensitivity_script("balanced")

        self.assertIn("/home/sunrise/Desktop/touch_mapping.json", script)
        self.assertIn('"lamp_thr": 258', script)
        self.assertIn("systemctl restart mira-touch.service", script)
        self.assertIn("TOUCH_BACKUP=", script)

    def test_unknown_touch_sensitivity_preset_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            shenzhen_console.render_touch_sensitivity_script("too-hot")


if __name__ == "__main__":
    unittest.main()
