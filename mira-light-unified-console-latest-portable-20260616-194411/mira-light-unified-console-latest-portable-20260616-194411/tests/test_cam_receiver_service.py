from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cam_receiver_service import prune_old_frames, write_frame_bytes_atomic


class CameraReceiverServiceTest(unittest.TestCase):
    def test_prune_old_frames_keeps_newest_jpegs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir)
            for index in range(5):
                (save_dir / f"20260524-12000{index}-frame-{index:06d}-seq-{index}.jpg").write_bytes(b"jpeg")
            (save_dir / "note.txt").write_text("keep", encoding="utf-8")

            removed = prune_old_frames(save_dir, max_saved_frames=3)

            self.assertEqual(removed, 2)
            self.assertEqual(
                [path.name for path in sorted(save_dir.glob("*.jpg"))],
                [
                    "20260524-120002-frame-000002-seq-2.jpg",
                    "20260524-120003-frame-000003-seq-3.jpg",
                    "20260524-120004-frame-000004-seq-4.jpg",
                ],
            )
            self.assertTrue((save_dir / "note.txt").exists())

    def test_prune_old_frames_can_be_disabled(self) -> None:
        with TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir)
            for index in range(2):
                (save_dir / f"frame-{index}.jpg").write_bytes(b"jpeg")

            removed = prune_old_frames(save_dir, max_saved_frames=0)

            self.assertEqual(removed, 0)
            self.assertEqual(len(list(save_dir.glob("*.jpg"))), 2)

    def test_write_frame_bytes_atomic_publishes_only_final_jpeg(self) -> None:
        with TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir)
            frame_path = save_dir / "frame-000001.jpg"

            write_frame_bytes_atomic(frame_path, b"jpeg payload")

            self.assertEqual(frame_path.read_bytes(), b"jpeg payload")
            self.assertEqual(list(save_dir.glob("*.tmp")), [])
            self.assertEqual([path.name for path in save_dir.glob("*.jpg")], ["frame-000001.jpg"])


if __name__ == "__main__":
    unittest.main()
