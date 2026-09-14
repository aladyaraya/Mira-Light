#!/usr/bin/env python3
"""Manual show orchestration primitives for the Mira Light unified console."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any


RESOURCES = {
    "servo_motion",
    "camera_stream",
    "camera_capture",
    "touch_service",
    "render_print",
    "audio_output",
}
SHARED_RESOURCES = {"camera_stream"}


class ResourceConflict(RuntimeError):
    def __init__(self, resource: str, owner: str, holders: list[dict[str, Any]]) -> None:
        self.resource = resource
        self.owner = owner
        self.holders = holders
        super().__init__(f"{resource} is held by {', '.join(item['owner'] for item in holders)}")

    def as_payload(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "owner": self.owner,
            "holders": self.holders,
            "message": str(self),
        }


@dataclass
class ResourceLease:
    resource: str
    owner: str
    mode: str
    acquired_at: float
    ttl_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expires_at(self) -> float:
        return self.acquired_at + self.ttl_seconds

    def expired(self, now: float | None = None) -> bool:
        return (now or time.time()) >= self.expires_at

    def view(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "owner": self.owner,
            "mode": self.mode,
            "acquiredAt": self.acquired_at,
            "expiresAt": self.expires_at,
            "metadata": dict(self.metadata),
        }


class ResourceManager:
    def __init__(self, *, default_ttl_seconds: float = 180.0) -> None:
        self.default_ttl_seconds = float(default_ttl_seconds)
        self._lock = RLock()
        self._leases: list[ResourceLease] = []

    def acquire(
        self,
        owner: str,
        requirements: list[dict[str, Any] | tuple[str, str] | str],
        *,
        ttl_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[ResourceLease]:
        ttl = float(ttl_seconds or self.default_ttl_seconds)
        normalized = [self._normalize_requirement(item) for item in requirements]
        now = time.time()
        with self._lock:
            self._prune_expired_locked(now)
            for requirement in normalized:
                conflict = self._find_conflict_locked(owner, requirement)
                if conflict:
                    raise ResourceConflict(requirement["resource"], owner, [item.view() for item in conflict])

            acquired: list[ResourceLease] = []
            for requirement in normalized:
                self._leases = [
                    item
                    for item in self._leases
                    if not (item.owner == owner and item.resource == requirement["resource"])
                ]
                lease = ResourceLease(
                    resource=requirement["resource"],
                    owner=owner,
                    mode=requirement["mode"],
                    acquired_at=now,
                    ttl_seconds=ttl,
                    metadata=dict(metadata or {}),
                )
                self._leases.append(lease)
                acquired.append(lease)
            return acquired

    def release_owner(self, owner: str, resources: list[str] | None = None) -> None:
        selected = set(resources or [])
        with self._lock:
            self._leases = [
                item
                for item in self._leases
                if item.owner != owner or (selected and item.resource not in selected)
            ]

    def clear(self) -> None:
        with self._lock:
            self._leases.clear()

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            self._prune_expired_locked(now)
            resources: dict[str, Any] = {}
            for resource in sorted(RESOURCES):
                leases = [item.view() for item in self._leases if item.resource == resource]
                resources[resource] = {
                    "mode": "free" if not leases else ("shared" if all(item["mode"] == "read" for item in leases) else "exclusive"),
                    "owners": [item["owner"] for item in leases],
                    "leases": leases,
                }
            return {"ok": True, "resources": resources, "updatedAt": now}

    def owner_map(self) -> dict[str, str]:
        snapshot = self.snapshot()
        result: dict[str, str] = {}
        for resource, payload in snapshot["resources"].items():
            owners = payload.get("owners") or []
            if not owners:
                continue
            result[resource] = "shared" if payload.get("mode") == "shared" else str(owners[0])
        return result

    def _normalize_requirement(self, item: dict[str, Any] | tuple[str, str] | str) -> dict[str, str]:
        if isinstance(item, str):
            resource, mode = item, "exclusive"
        elif isinstance(item, tuple):
            resource, mode = item
        else:
            resource = str(item.get("resource") or "")
            mode = str(item.get("mode") or "exclusive")
        if resource not in RESOURCES:
            raise ValueError(f"Unknown resource: {resource}")
        if mode not in {"read", "exclusive"}:
            raise ValueError(f"Unknown lock mode for {resource}: {mode}")
        if mode == "read" and resource not in SHARED_RESOURCES:
            raise ValueError(f"{resource} does not support shared read locks")
        return {"resource": resource, "mode": mode}

    def _find_conflict_locked(self, owner: str, requirement: dict[str, str]) -> list[ResourceLease]:
        leases = [item for item in self._leases if item.resource == requirement["resource"] and item.owner != owner]
        if not leases:
            return []
        if requirement["mode"] == "read" and requirement["resource"] in SHARED_RESOURCES:
            return [item for item in leases if item.mode != "read"]
        return leases

    def _prune_expired_locked(self, now: float) -> None:
        self._leases = [item for item in self._leases if not item.expired(now)]


BOOK_PROFILES = {
    "yellow_book": {
        "id": "yellow_book",
        "title": "Big meets Little",
        "author": "Yang Liu",
        "summary": (
            "这本书用极简图形讲大和小的相遇。它不是靠很多文字，而是用对比、位置和形状，"
            "让小朋友直观看到关系、尺度和陪伴。Mira 会把它当成一位黄色封面的朋友来追随。"
        ),
    }
}


SHOW_STATES_BY_STEP = {
    "wake_up": "wake_ready",
    "touch": "touch_ready",
    "book_follow": "book_following",
    "book_summary": "book_explained",
    "answer_demo": "book_explained",
    "offer_celebrate": "offer_celebrated",
    "photo_pose": "photo_ready",
    "photo_snapshot": "photo_done",
    "photo_highres": "photo_done",
    "sleep": "sleeping",
}


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
