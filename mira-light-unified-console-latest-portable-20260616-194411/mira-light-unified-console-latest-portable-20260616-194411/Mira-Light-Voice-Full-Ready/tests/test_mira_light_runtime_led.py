from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_light_runtime import LED_PIXEL_COUNT, MiraLightRuntime  # noqa: E402


class MiraLightRuntimeLedTest(unittest.TestCase):
    def test_dry_run_vector_led_uses_payload_brightness_for_rgb_pixels(self) -> None:
        runtime = MiraLightRuntime(base_url="tcp://127.0.0.1:9527", dry_run=True)
        pixels = [{"r": 255, "g": 128, "b": 32} for _ in range(LED_PIXEL_COUNT)]

        result = runtime.get_client().set_led({"mode": "vector", "brightness": 210, "pixels": pixels})

        self.assertEqual(result["mode"], "vector")
        self.assertEqual(result["brightness"], 210)
        self.assertEqual(result["pixelSignals"][0][3], 210)


if __name__ == "__main__":
    unittest.main()
