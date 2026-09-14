from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONSOLE_DIR = ROOT / "mira-light-unified-director-console"

if str(CONSOLE_DIR) not in sys.path:
    sys.path.insert(0, str(CONSOLE_DIR))

from show_orchestrator import BOOK_PROFILES, ResourceConflict, ResourceManager


class ResourceManagerTest(unittest.TestCase):
    def test_camera_stream_allows_multiple_readers(self) -> None:
        manager = ResourceManager(default_ttl_seconds=30)

        manager.acquire("preview", [{"resource": "camera_stream", "mode": "read"}])
        manager.acquire("book_follow", [{"resource": "camera_stream", "mode": "read"}])

        owners = manager.snapshot()["resources"]["camera_stream"]["owners"]
        self.assertEqual(owners, ["preview", "book_follow"])
        self.assertEqual(manager.owner_map()["camera_stream"], "shared")

    def test_exclusive_resource_conflicts(self) -> None:
        manager = ResourceManager(default_ttl_seconds=30)
        manager.acquire("book_follow", [{"resource": "servo_motion", "mode": "exclusive"}])

        with self.assertRaises(ResourceConflict) as raised:
            manager.acquire("offer_celebrate", [{"resource": "servo_motion", "mode": "exclusive"}])

        self.assertEqual(raised.exception.resource, "servo_motion")
        self.assertEqual(raised.exception.holders[0]["owner"], "book_follow")

    def test_expired_lock_is_pruned(self) -> None:
        manager = ResourceManager(default_ttl_seconds=0.001)
        manager.acquire("stale", [{"resource": "servo_motion", "mode": "exclusive"}])
        time.sleep(0.01)

        manager.acquire("fresh", [{"resource": "servo_motion", "mode": "exclusive"}], ttl_seconds=30)

        self.assertEqual(manager.owner_map()["servo_motion"], "fresh")

    def test_release_owner_can_release_selected_resources(self) -> None:
        manager = ResourceManager(default_ttl_seconds=30)
        manager.acquire(
            "photo",
            [
                {"resource": "camera_stream", "mode": "read"},
                {"resource": "render_print", "mode": "exclusive"},
            ],
        )

        manager.release_owner("photo", resources=["camera_stream"])

        owners = manager.owner_map()
        self.assertNotIn("camera_stream", owners)
        self.assertEqual(owners["render_print"], "photo")

    def test_yellow_book_profile_is_available(self) -> None:
        profile = BOOK_PROFILES["yellow_book"]

        self.assertEqual(profile["title"], "Big meets Little")
        self.assertEqual(profile["author"], "Yang Liu")
        self.assertIn("Mira", profile["summary"])


if __name__ == "__main__":
    unittest.main()
