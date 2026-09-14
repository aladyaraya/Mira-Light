from __future__ import annotations

import argparse
import json
import unittest

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from track_target_event_extractor import (
    ExtractorState,
    build_event,
    choose_selected_target,
    detect_hand_arm_cue,
    detect_tabletop_object_candidates,
    find_latest_jpg,
    hold_selected_target,
    load_image,
    make_control_hint,
    write_event_outputs,
)


class DummyFrame:
    shape = (120, 200, 3)


class TrackTargetEventExtractorTest(unittest.TestCase):
    def make_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            face_near_area_ratio=0.10,
            face_mid_area_ratio=0.03,
            motion_near_area_ratio=0.18,
            motion_mid_area_ratio=0.06,
            hold_missing_frames=3,
            selected_target_max_center_distance=0.16,
            selected_target_max_size_delta=0.045,
            selected_target_switch_margin=0.22,
            default_target_mode="person_follow",
            tabletop_roi_top=0.16,
            tabletop_roi_bottom=0.96,
            tabletop_roi_left=0.08,
            tabletop_roi_right=0.92,
            tabletop_min_area_ratio=0.004,
            tabletop_max_area_ratio=0.65,
            tabletop_min_edge_ratio=0.05,
            tabletop_min_motion_ratio=0.01,
            tabletop_min_aspect_ratio=0.45,
            tabletop_max_aspect_ratio=2.2,
            tabletop_hold_missing_frames=6,
            tabletop_switch_margin=0.34,
            tabletop_max_center_distance=0.22,
            tabletop_max_size_delta=0.065,
            tabletop_max_aspect_delta=0.48,
            enable_tabletop_book_color=True,
            tabletop_book_hue_min=14,
            tabletop_book_hue_max=43,
            tabletop_book_min_saturation=70,
            tabletop_book_min_value=80,
            tabletop_book_min_color_ratio=0.22,
            tabletop_book_min_aspect_ratio=0.35,
            tabletop_book_max_aspect_ratio=4.2,
            tabletop_book_min_rectangularity=0.46,
            tabletop_book_min_solidity=0.72,
            tabletop_book_min_edge_ratio=0.012,
            tabletop_book_max_edge_ratio=0.24,
            tabletop_book_min_inner_edge_ratio=0.012,
            tabletop_book_max_corner_count=6,
            tabletop_book_selection_bonus=0.42,
            hand_cue_min_area_ratio=0.0015,
            hand_cue_max_area_ratio=0.06,
            hand_cue_min_center_y=0.34,
            hand_cue_min_motion_ratio=0.12,
            hand_cue_min_confidence=0.55,
        )

    def test_find_latest_jpg_ignores_frames_pruned_during_scan(self) -> None:
        with TemporaryDirectory() as tmpdir:
            captures_dir = Path(tmpdir)
            older = captures_dir / "20260524-120000-frame-000001-seq-1.jpg"
            newer = captures_dir / "20260524-120001-frame-000002-seq-2.jpg"
            missing = captures_dir / "20260524-120002-frame-000003-seq-3.jpg"
            older.write_bytes(b"old")
            newer.write_bytes(b"new")
            missing.symlink_to(captures_dir / "already-pruned.jpg")

            self.assertEqual(find_latest_jpg(captures_dir), newer)

    def test_load_image_returns_none_for_empty_or_missing_frame(self) -> None:
        with TemporaryDirectory() as tmpdir:
            captures_dir = Path(tmpdir)
            empty = captures_dir / "empty.jpg"
            missing = captures_dir / "missing.jpg"
            empty.write_bytes(b"")

            self.assertIsNone(load_image(empty))
            self.assertIsNone(load_image(missing))

    def test_write_event_outputs_replaces_latest_json_atomically(self) -> None:
        with TemporaryDirectory() as tmpdir:
            latest_event = Path(tmpdir) / "vision.latest.json"
            events_jsonl = Path(tmpdir) / "vision.events.jsonl"
            event = {"event_type": "target_updated", "tracking": {"detector": "book_cover_color"}}

            write_event_outputs(event, latest_event, events_jsonl)

            self.assertEqual(json.loads(latest_event.read_text(encoding="utf-8")), event)
            self.assertEqual(json.loads(events_jsonl.read_text(encoding="utf-8").strip()), event)
            self.assertFalse((Path(tmpdir) / ".vision.latest.json.tmp").exists())

    def test_multi_target_payload_promotes_to_multi_person_scene(self) -> None:
        event = build_event(
            path=ROOT / "fixtures" / "vision_events" / "multi_person_left_right.json",
            frame=DummyFrame(),
            bbox=(10, 10, 50, 60),
            detector="haar_face",
            target_class="person",
            confidence=0.92,
            state=ExtractorState(last_target_present=True),
            args=self.make_args(),
            target_count=2,
            multi_target_payload={"primaryDirection": "left", "secondaryDirection": "right", "targetCount": 2},
        )

        self.assertEqual(event["event_type"], "multi_target_seen")
        self.assertEqual(event["scene_hint"]["name"], "multi_person_demo")
        self.assertEqual(event["tracking"]["target_count"], 2)
        self.assertEqual(event["payload"]["primaryDirection"], "left")
        self.assertEqual(event["payload"]["secondaryDirection"], "right")

    def test_tabletop_book_multi_target_stays_in_tracking_scene(self) -> None:
        selected_target = {
            "track_id": 4,
            "lock_state": "candidate",
            "reason": "highest score among multiple visible tabletop targets",
            "target_class": "book",
            "target_subclass": "yellow_book",
            "target_mode": "tabletop_follow",
            "detector": "book_cover_color",
            "confidence": 0.99,
            "bbox_norm": {"x": 0.42, "y": 0.16, "w": 0.27, "h": 0.71},
            "center_norm": {"x": 0.56, "y": 0.51},
            "horizontal_zone": "center",
            "vertical_zone": "middle",
            "size_norm": 0.194,
            "distance_band": "near",
            "approach_state": "unknown",
            "selection_score": 2.5,
        }

        event = build_event(
            path=ROOT / "fixtures" / "vision_events" / "multi_person_left_right.json",
            frame=DummyFrame(),
            bbox=(84, 19, 54, 85),
            detector="book_cover_color",
            target_class="book",
            confidence=0.99,
            state=ExtractorState(last_target_present=True),
            args=self.make_args(),
            target_mode="tabletop_follow",
            target_count=4,
            selected_target=selected_target,
            multi_target_payload={"primaryDirection": "center", "secondaryDirection": "right", "targetCount": 4},
        )

        self.assertEqual(event["event_type"], "target_updated")
        self.assertEqual(event["scene_hint"]["name"], "track_target")
        self.assertEqual(event["tracking"]["detector"], "book_cover_color")
        self.assertEqual(event["tracking"]["target_subclass"], "yellow_book")
        self.assertEqual(event["control_hint"]["feedback_profile"], "tabletop_book")

    def test_build_event_surfaces_owner_face_metadata(self) -> None:
        selected_target = {
            "track_id": 5,
            "lock_state": "locked",
            "reason": "single visible target",
            "target_class": "person",
            "target_mode": "person_follow",
            "detector": "haar_face",
            "confidence": 0.94,
            "bbox_norm": {"x": 0.30, "y": 0.18, "w": 0.18, "h": 0.26},
            "center_norm": {"x": 0.39, "y": 0.31},
            "horizontal_zone": "left",
            "vertical_zone": "upper",
            "size_norm": 0.046,
            "distance_band": "mid",
            "approach_state": "stable",
            "selection_score": 1.26,
            "owner_face_found": True,
            "owner_id": "owner_main",
            "owner_confidence": 0.91,
            "owner_direction": "left",
        }

        event = build_event(
            path=ROOT / "fixtures" / "vision_events" / "track_target_update_right.json",
            frame=DummyFrame(),
            bbox=(60, 24, 44, 52),
            detector="haar_face",
            target_class="person",
            confidence=0.94,
            state=ExtractorState(last_target_present=True),
            args=self.make_args(),
            target_mode="person_follow",
            target_count=1,
            selected_target=selected_target,
            owner_observation={"owner_id": "owner_main", "owner_confidence": 0.91, "owner_direction": "left"},
        )

        self.assertTrue(event["tracking"]["owner_face_found"])
        self.assertEqual(event["tracking"]["owner_id"], "owner_main")
        self.assertEqual(event["tracking"]["owner_direction"], "left")
        self.assertEqual(event["selected_target"]["owner_id"], "owner_main")

    def test_hold_selected_target_keeps_recent_target_alive_for_short_occlusion(self) -> None:
        state = ExtractorState(
            last_target_present=True,
            missing_frame_count=2,
            last_selected_target={
                "track_id": 7,
                "lock_state": "locked",
                "reason": "previous selected target still visible",
                "target_class": "person",
                "detector": "haar_face",
                "confidence": 0.92,
                "bbox_norm": {"x": 0.4, "y": 0.2, "w": 0.2, "h": 0.3},
                "center_norm": {"x": 0.5, "y": 0.35},
                "horizontal_zone": "center",
                "vertical_zone": "middle",
                "size_norm": 0.06,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.1,
            },
        )

        held = hold_selected_target(state, self.make_args())

        self.assertIsNotNone(held)
        self.assertEqual(held["track_id"], 7)
        self.assertEqual(held["lock_state"], "held")
        self.assertIn("short occlusion hold", held["reason"])
        self.assertLess(float(held["confidence"]), 0.92)

    def test_hold_selected_target_uses_longer_tabletop_hold_policy(self) -> None:
        state = ExtractorState(
            last_target_present=True,
            missing_frame_count=5,
            last_selected_target={
                "track_id": 17,
                "lock_state": "locked",
                "reason": "previous selected tabletop target still visible",
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "detector": "tabletop_object",
                "confidence": 0.84,
                "bbox_norm": {"x": 0.42, "y": 0.60, "w": 0.22, "h": 0.16},
                "center_norm": {"x": 0.53, "y": 0.68},
                "horizontal_zone": "center",
                "vertical_zone": "lower",
                "size_norm": 0.035,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.22,
                "edge_ratio": 0.19,
                "motion_ratio": 0.03,
                "aspect_ratio": 1.37,
            },
        )

        held = hold_selected_target(state, self.make_args())

        self.assertIsNotNone(held)
        self.assertEqual(held["track_id"], 17)
        self.assertIn("tabletop occlusion hold", held["reason"])

    def test_operator_lock_prefers_requested_track_when_visible(self) -> None:
        state = ExtractorState(selected_track_id=3)
        tracks = [
            {
                "track_id": 3,
                "detector": "haar_face",
                "target_class": "person",
                "confidence": 0.88,
                "center_norm": {"x": 0.2, "y": 0.4},
                "selection_score": 1.0,
            },
            {
                "track_id": 8,
                "detector": "haar_face",
                "target_class": "person",
                "confidence": 0.91,
                "center_norm": {"x": 0.65, "y": 0.38},
                "selection_score": 1.2,
            },
        ]

        selected = choose_selected_target(
            tracks,
            state,
            operator_state={"lockSelectedTrackId": 8},
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["track_id"], 8)
        self.assertEqual(selected["lock_state"], "operator_locked")

    def test_tabletop_selection_prefers_yellow_book_over_generic_object(self) -> None:
        state = ExtractorState(selected_track_id=11)
        tracks = [
            {
                "track_id": 11,
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "detector": "tabletop_object",
                "confidence": 0.83,
                "center_norm": {"x": 0.50, "y": 0.52},
                "bbox_norm": {"x": 0.08, "y": 0.16, "w": 0.84, "h": 0.72},
                "size_norm": 0.60,
                "selection_score": 2.2,
            },
            {
                "track_id": 17,
                "target_class": "book",
                "target_subclass": "yellow_book",
                "target_mode": "tabletop_follow",
                "detector": "book_cover_color",
                "confidence": 0.87,
                "center_norm": {"x": 0.86, "y": 0.79},
                "bbox_norm": {"x": 0.80, "y": 0.63, "w": 0.12, "h": 0.33},
                "size_norm": 0.04,
                "selection_score": 1.36,
            },
        ]

        selected = choose_selected_target(tracks, state, args=self.make_args())

        self.assertIsNotNone(selected)
        self.assertEqual(selected["track_id"], 17)
        self.assertEqual(selected["detector"], "book_cover_color")
        self.assertEqual(selected["lock_state"], "locked")
        self.assertIn("yellow book", selected["reason"])

    def test_tabletop_selection_holds_yellow_book_when_generic_object_reappears(self) -> None:
        state = ExtractorState(
            selected_track_id=17,
            last_selected_target={
                "track_id": 17,
                "target_class": "book",
                "target_subclass": "yellow_book",
                "target_mode": "tabletop_follow",
                "detector": "book_cover_color",
                "confidence": 0.92,
                "center_norm": {"x": 0.45, "y": 0.66},
                "bbox_norm": {"x": 0.31, "y": 0.48, "w": 0.28, "h": 0.22},
                "size_norm": 0.0616,
                "selection_score": 1.62,
            },
        )
        tracks = [
            {
                "track_id": 23,
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "detector": "tabletop_object",
                "confidence": 0.89,
                "center_norm": {"x": 0.50, "y": 0.56},
                "bbox_norm": {"x": 0.08, "y": 0.16, "w": 0.84, "h": 0.72},
                "size_norm": 0.60,
                "selection_score": 2.2,
            },
        ]

        selected = choose_selected_target(tracks, state, args=self.make_args())

        self.assertIsNotNone(selected)
        self.assertEqual(selected["detector"], "book_cover_color")
        self.assertEqual(selected["lock_state"], "held")
        self.assertIn("yellow book occlusion hold", selected["reason"])

    def test_book_control_hint_is_damped_for_smoother_tracking(self) -> None:
        hint = make_control_hint(
            0.75,
            0.50,
            "near",
            target_mode="tabletop_follow",
            target_class="book",
        )

        self.assertEqual(hint["feedback_profile"], "tabletop_book")
        self.assertEqual(hint["recommended_update_ms"], 160)
        self.assertLess(hint["yaw_error_norm"], 0.5)
        self.assertEqual(hint["deadband_norm"], {"yaw": 0.045, "pitch": 0.075})

    def test_choose_selected_target_recovers_previous_target_by_spatial_continuity(self) -> None:
        state = ExtractorState(
            last_selected_target={
                "track_id": 3,
                "lock_state": "locked",
                "reason": "previous selected target still visible",
                "target_class": "person",
                "detector": "haar_face",
                "confidence": 0.89,
                "bbox_norm": {"x": 0.42, "y": 0.18, "w": 0.16, "h": 0.28},
                "center_norm": {"x": 0.50, "y": 0.32},
                "horizontal_zone": "center",
                "vertical_zone": "upper",
                "size_norm": 0.052,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.08,
            },
        )
        tracks = [
            {
                "track_id": 11,
                "detector": "haar_face",
                "target_class": "person",
                "confidence": 0.91,
                "bbox_norm": {"x": 0.43, "y": 0.19, "w": 0.17, "h": 0.27},
                "center_norm": {"x": 0.515, "y": 0.325},
                "horizontal_zone": "center",
                "vertical_zone": "upper",
                "size_norm": 0.051,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.03,
            },
            {
                "track_id": 12,
                "detector": "haar_face",
                "target_class": "person",
                "confidence": 0.95,
                "bbox_norm": {"x": 0.70, "y": 0.22, "w": 0.18, "h": 0.28},
                "center_norm": {"x": 0.79, "y": 0.36},
                "horizontal_zone": "right",
                "vertical_zone": "middle",
                "size_norm": 0.056,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.15,
            },
        ]

        selected = choose_selected_target(
            tracks,
            state,
            args=self.make_args(),
            operator_state={},
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["track_id"], 11)
        self.assertEqual(selected["lock_state"], "locked")
        self.assertIn("spatial continuity", selected["reason"])
        self.assertAlmostEqual(float(selected["continuity_distance_norm"]), 0.0158, places=3)

    def test_choose_selected_target_keeps_visible_target_until_margin_is_decisive(self) -> None:
        state = ExtractorState(selected_track_id=3)
        tracks = [
            {
                "track_id": 3,
                "detector": "haar_face",
                "target_class": "person",
                "confidence": 0.88,
                "center_norm": {"x": 0.22, "y": 0.40},
                "selection_score": 1.00,
            },
            {
                "track_id": 8,
                "detector": "haar_face",
                "target_class": "person",
                "confidence": 0.91,
                "center_norm": {"x": 0.65, "y": 0.38},
                "selection_score": 1.14,
            },
        ]

        selected = choose_selected_target(
            tracks,
            state,
            args=self.make_args(),
            operator_state={},
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["track_id"], 3)
        self.assertEqual(selected["lock_state"], "locked")
        self.assertEqual(state.selected_track_id, 3)

    def test_choose_selected_target_keeps_locked_tabletop_target_until_margin_is_decisive(self) -> None:
        state = ExtractorState(selected_track_id=4)
        tracks = [
            {
                "track_id": 4,
                "detector": "tabletop_object",
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "confidence": 0.76,
                "center_norm": {"x": 0.49, "y": 0.70},
                "selection_score": 1.22,
                "edge_ratio": 0.16,
                "motion_ratio": 0.02,
                "aspect_ratio": 1.42,
            },
            {
                "track_id": 9,
                "detector": "tabletop_object",
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "confidence": 0.83,
                "center_norm": {"x": 0.62, "y": 0.73},
                "selection_score": 1.49,
                "edge_ratio": 0.18,
                "motion_ratio": 0.05,
                "aspect_ratio": 1.30,
            },
        ]

        selected = choose_selected_target(
            tracks,
            state,
            args=self.make_args(),
            operator_state={},
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["track_id"], 4)
        self.assertIn("tabletop", selected["reason"])

    def test_choose_selected_target_recovers_previous_tabletop_target_with_feature_continuity(self) -> None:
        state = ExtractorState(
            last_selected_target={
                "track_id": 14,
                "lock_state": "locked",
                "reason": "previous selected tabletop target still visible",
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "detector": "tabletop_object",
                "confidence": 0.81,
                "bbox_norm": {"x": 0.40, "y": 0.60, "w": 0.22, "h": 0.15},
                "center_norm": {"x": 0.51, "y": 0.675},
                "horizontal_zone": "center",
                "vertical_zone": "lower",
                "size_norm": 0.033,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.21,
                "edge_ratio": 0.17,
                "motion_ratio": 0.02,
                "aspect_ratio": 1.46,
            },
        )
        tracks = [
            {
                "track_id": 20,
                "detector": "tabletop_object",
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "confidence": 0.78,
                "bbox_norm": {"x": 0.41, "y": 0.61, "w": 0.22, "h": 0.15},
                "center_norm": {"x": 0.52, "y": 0.685},
                "horizontal_zone": "center",
                "vertical_zone": "lower",
                "size_norm": 0.034,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.18,
                "edge_ratio": 0.18,
                "motion_ratio": 0.03,
                "aspect_ratio": 1.44,
            },
            {
                "track_id": 21,
                "detector": "tabletop_object",
                "target_class": "object",
                "target_mode": "tabletop_follow",
                "confidence": 0.88,
                "bbox_norm": {"x": 0.68, "y": 0.61, "w": 0.18, "h": 0.16},
                "center_norm": {"x": 0.77, "y": 0.69},
                "horizontal_zone": "right",
                "vertical_zone": "lower",
                "size_norm": 0.029,
                "distance_band": "mid",
                "approach_state": "stable",
                "selection_score": 1.36,
                "edge_ratio": 0.10,
                "motion_ratio": 0.08,
                "aspect_ratio": 1.05,
            },
        ]

        selected = choose_selected_target(
            tracks,
            state,
            args=self.make_args(),
            operator_state={},
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["track_id"], 20)
        self.assertIn("tabletop target", selected["reason"])
        self.assertIn("continuity_aspect_delta", selected)

    def test_detect_tabletop_object_candidates_finds_book_like_target_in_table_roi(self) -> None:
        frame = np.full((160, 240, 3), 242, dtype=np.uint8)
        frame[96:138, 84:156] = (52, 78, 130)
        cv2.rectangle(frame, (84, 96), (156, 138), (245, 245, 245), 2)
        fg_mask = np.zeros((160, 240), dtype=np.uint8)
        fg_mask[94:140, 82:158] = 255

        candidates = detect_tabletop_object_candidates(
            frame,
            fg_mask,
            args=self.make_args(),
            previous_size_norm=None,
        )

        self.assertTrue(candidates)
        top = sorted(candidates, key=lambda item: item["selection_score"], reverse=True)[0]
        self.assertEqual(top["target_class"], "object")
        self.assertEqual(top["target_mode"], "tabletop_follow")
        self.assertEqual(top["detector"], "tabletop_object")
        self.assertGreater(float(top["confidence"]), 0.6)
        self.assertIn("object_lock_strength", top)

    def test_detect_tabletop_object_candidates_uses_yellow_book_cover_color_without_motion(self) -> None:
        frame = np.full((240, 320, 3), (194, 205, 214), dtype=np.uint8)
        frame[44:204, 36:286] = (24, 174, 226)
        cv2.circle(frame, (160, 118), 46, (245, 245, 245), -1)
        cv2.rectangle(frame, (144, 122), (176, 178), (20, 20, 20), -1)
        fg_mask = np.zeros((240, 320), dtype=np.uint8)

        candidates = detect_tabletop_object_candidates(
            frame,
            fg_mask,
            args=self.make_args(),
            previous_size_norm=None,
        )

        self.assertTrue(candidates)
        top = sorted(candidates, key=lambda item: item["selection_score"], reverse=True)[0]
        self.assertEqual(top["target_class"], "book")
        self.assertEqual(top["target_subclass"], "yellow_book")
        self.assertEqual(top["detector"], "book_cover_color")
        self.assertGreater(float(top["book_color_ratio"]), 0.5)
        self.assertGreater(float(top["book_match_strength"]), 1.0)
        self.assertGreater(float(top["book_rectangularity"]), 0.46)
        self.assertGreater(float(top["book_solidity"]), 0.72)
        self.assertGreater(float(top["book_inner_edge_ratio"]), 0.012)

    def test_yellow_plain_block_is_not_promoted_to_yellow_book(self) -> None:
        frame = np.full((240, 320, 3), (194, 205, 214), dtype=np.uint8)
        frame[44:204, 36:286] = (24, 174, 226)
        fg_mask = np.zeros((240, 320), dtype=np.uint8)

        candidates = detect_tabletop_object_candidates(
            frame,
            fg_mask,
            args=self.make_args(),
            previous_size_norm=None,
        )

        self.assertFalse(any(item.get("detector") == "book_cover_color" for item in candidates))

    def test_wide_perspective_yellow_cover_can_be_promoted_to_yellow_book(self) -> None:
        frame = np.full((240, 420, 3), (194, 205, 214), dtype=np.uint8)
        cv2.rectangle(frame, (42, 96), (354, 180), (24, 174, 226), -1)
        cv2.line(frame, (70, 120), (330, 120), (40, 40, 40), 3)
        cv2.putText(frame, "TASCHEN", (116, 158), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (35, 35, 35), 2)
        fg_mask = np.zeros((240, 420), dtype=np.uint8)

        candidates = detect_tabletop_object_candidates(
            frame,
            fg_mask,
            args=self.make_args(),
            previous_size_norm=None,
        )

        books = [item for item in candidates if item.get("detector") == "book_cover_color"]
        self.assertTrue(books)
        self.assertGreater(float(books[0]["aspect_ratio"]), 3.0)

    def test_yellow_blob_is_not_promoted_to_yellow_book(self) -> None:
        frame = np.full((240, 320, 3), (194, 205, 214), dtype=np.uint8)
        cv2.circle(frame, (160, 120), 70, (24, 174, 226), -1)
        cv2.line(frame, (125, 120), (195, 120), (20, 20, 20), 4)
        fg_mask = np.zeros((240, 320), dtype=np.uint8)

        candidates = detect_tabletop_object_candidates(
            frame,
            fg_mask,
            args=self.make_args(),
            previous_size_norm=None,
        )

        self.assertFalse(any(item.get("detector") == "book_cover_color" for item in candidates))

    def test_build_event_carries_target_mode_for_tabletop_target(self) -> None:
        selected_target = {
            "track_id": 5,
            "lock_state": "locked",
            "reason": "tabletop object selected",
            "target_class": "object",
            "target_mode": "tabletop_follow",
            "detector": "tabletop_object",
            "confidence": 0.79,
            "bbox_norm": {"x": 0.4, "y": 0.58, "w": 0.22, "h": 0.18},
            "center_norm": {"x": 0.51, "y": 0.67},
            "horizontal_zone": "center",
            "vertical_zone": "lower",
            "size_norm": 0.041,
            "distance_band": "mid",
            "approach_state": "stable",
            "selection_score": 1.07,
            "roi_mode": "tabletop",
            "edge_ratio": 0.16,
            "motion_ratio": 0.03,
            "aspect_ratio": 1.22,
            "fill_ratio": 0.66,
            "object_lock_strength": 1.15,
        }

        event = build_event(
            path=ROOT / "fixtures" / "vision_events" / "multi_person_left_right.json",
            frame=DummyFrame(),
            bbox=(80, 70, 44, 22),
            detector="tabletop_object",
            target_class="object",
            confidence=0.79,
            state=ExtractorState(last_target_present=True),
            args=self.make_args(),
            target_mode="tabletop_follow",
            target_count=1,
            selected_target=selected_target,
        )

        self.assertEqual(event["tracking"]["target_mode"], "tabletop_follow")
        self.assertEqual(event["tracking"]["roi_mode"], "tabletop")
        self.assertEqual(event["tracking"]["object_lock_strength"], 1.15)
        self.assertEqual(event["selected_target"]["target_mode"], "tabletop_follow")
        self.assertEqual(event["selected_target"]["edge_ratio"], 0.16)
        self.assertEqual(event["scene_hint"]["name"], "track_target")

    def test_detect_hand_arm_cue_finds_moving_skin_blob_in_lower_region(self) -> None:
        frame = np.zeros((120, 200, 3), dtype=np.uint8)
        frame[60:96, 126:166] = (80, 120, 180)
        fg_mask = np.zeros((120, 200), dtype=np.uint8)
        fg_mask[58:100, 122:170] = 255

        cue = detect_hand_arm_cue(
            frame,
            fg_mask,
            selected_target=None,
            warmup_count=10,
            warmup_frames=3,
            args=self.make_args(),
        )

        self.assertIsNotNone(cue)
        self.assertTrue(cue["hand_arm_present"])
        self.assertEqual(cue["detector"], "skin_motion_hand")
        self.assertEqual(cue["horizontal_zone"], "right")

    def test_detect_hand_arm_cue_rejects_static_skin_blob_without_motion(self) -> None:
        frame = np.zeros((120, 200, 3), dtype=np.uint8)
        frame[60:96, 126:166] = (80, 120, 180)
        fg_mask = np.zeros((120, 200), dtype=np.uint8)

        cue = detect_hand_arm_cue(
            frame,
            fg_mask,
            selected_target=None,
            warmup_count=10,
            warmup_frames=3,
            args=self.make_args(),
        )

        self.assertIsNone(cue)

    def test_detect_hand_arm_cue_rejects_upper_right_skin_blob_when_no_target(self) -> None:
        frame = np.zeros((120, 200, 3), dtype=np.uint8)
        frame[36:72, 164:194] = (80, 120, 180)
        fg_mask = np.zeros((120, 200), dtype=np.uint8)
        fg_mask[34:76, 160:198] = 255

        cue = detect_hand_arm_cue(
            frame,
            fg_mask,
            selected_target=None,
            warmup_count=10,
            warmup_frames=3,
            args=self.make_args(),
        )

        self.assertIsNone(cue)


if __name__ == "__main__":
    unittest.main()
