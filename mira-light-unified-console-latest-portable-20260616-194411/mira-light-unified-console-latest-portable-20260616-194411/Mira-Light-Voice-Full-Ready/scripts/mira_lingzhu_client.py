#!/usr/bin/env python3
"""HTTP client helpers for the remote Mira Lingzhu live adapter."""

from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any
import urllib.error
import urllib.request


def normalize_string_list(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = list(value)

    items: list[str] = []
    for raw in raw_items:
        text = str(raw).strip()
        if text and text not in items:
            items.append(text)
    return items


def _extract_text(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("text", "content", "reply", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            return _extract_text(choices[0])
        delta = payload.get("delta")
        if isinstance(delta, dict):
            return _extract_text(delta)
        upstream = payload.get("upstream")
        if isinstance(upstream, dict):
            return _extract_text(upstream)
    return ""


def _parse_response_body(raw: str) -> dict[str, Any]:
    stripped = raw.strip()
    if not stripped:
        return {"ok": True}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    event_payloads: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            text_parts.append(data)
            continue
        event_payloads.append(payload)
        text = _extract_text(payload)
        if text:
            text_parts.append(text)
    if event_payloads or text_parts:
        return {"ok": True, "events": event_payloads, "text": "".join(text_parts)}
    return {"ok": True, "raw": stripped}


def _post_json(base_url: str, path: str, payload: dict[str, Any], *, auth_ak: str, timeout_seconds: int) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            **({"Authorization": f"Bearer {auth_ak}"} if auth_ak else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8").strip()
            return _parse_response_body(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Lingzhu HTTP {exc.code} calling {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Lingzhu request failed: {exc}") from exc


def _message_items(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role") or "user").strip() or "user"
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        items.append({"role": role, "type": "text", "text": content})
    return items


def _metis_message_text(messages: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for message in messages:
        role = str(message.get("role") or "user").strip() or "user"
        content = str(message.get("content") or "").strip()
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def _send_v1_chat(
    messages: list[dict[str, str]],
    *,
    base_url: str,
    auth_ak: str,
    agent_id: str,
    user_id: str,
    session_id: str,
    additional_user_ids: list[str],
    timeout_seconds: int,
) -> tuple[str, dict[str, Any]]:
    payload = _post_json(
        base_url,
        "/v1/chat",
        {
            "agent_id": agent_id,
            "user_id": user_id,
            "session_id": session_id,
            "message_id": f"mira-light-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "additional_user_ids": additional_user_ids,
            "disable_default_additional_user_ids": len(additional_user_ids) == 0,
            "message": _message_items(messages),
        },
        auth_ak=auth_ak,
        timeout_seconds=timeout_seconds,
    )
    text = str(payload.get("text") or "").strip()
    upstream = payload.get("upstream") if isinstance(payload.get("upstream"), dict) else {}
    return text, {
        "provider": "lingzhu-live-adapter",
        "protocol": "v1",
        "model": str(upstream.get("model") or ""),
        "payload": payload,
    }


def _send_metis_sse(
    messages: list[dict[str, str]],
    *,
    base_url: str,
    auth_ak: str,
    agent_id: str,
    user_id: str,
    session_id: str,
    additional_user_ids: list[str],
    timeout_seconds: int,
) -> tuple[str, dict[str, Any]]:
    payload = _post_json(
        base_url,
        "/metis/agent/api/sse",
        {
            "agent_id": agent_id,
            "user_id": user_id,
            "session_id": session_id,
            "message_id": f"mira-light-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "additional_user_ids": additional_user_ids,
            "message": _message_items(messages),
            "query": _metis_message_text(messages),
        },
        auth_ak=auth_ak,
        timeout_seconds=timeout_seconds,
    )
    return _extract_text(payload), {
        "provider": "lingzhu-live-adapter",
        "protocol": "metis-sse",
        "model": "",
        "payload": payload,
    }


def send_via_lingzhu_messages(
    messages: list[dict[str, str]],
    *,
    base_url: str,
    auth_ak: str,
    agent_id: str,
    user_id: str,
    session_id: str,
    additional_user_ids: str | list[str] | tuple[str, ...] | None,
    timeout_seconds: int,
) -> tuple[str, dict[str, Any]]:
    if not base_url.strip():
        raise RuntimeError("Lingzhu base URL is required")
    if not auth_ak.strip():
        raise RuntimeError("Lingzhu auth AK is required")

    normalized_additional_user_ids = normalize_string_list(additional_user_ids)
    protocol = os.environ.get("MIRA_LIGHT_LINGZHU_PROTOCOL", "auto").strip().lower() or "auto"
    senders = {
        "v1": [_send_v1_chat],
        "metis-sse": [_send_metis_sse],
        "auto": [_send_v1_chat, _send_metis_sse],
    }.get(protocol)
    if senders is None:
        raise RuntimeError(f"Unsupported Lingzhu protocol: {protocol}")

    errors: list[str] = []
    for sender in senders:
        try:
            text, meta = sender(
                messages,
                base_url=base_url,
                auth_ak=auth_ak,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
                additional_user_ids=normalized_additional_user_ids,
                timeout_seconds=timeout_seconds,
            )
            meta.update({"agent": agent_id, "userId": user_id, "sessionId": session_id, "additionalUserIds": normalized_additional_user_ids})
            return text, meta
        except RuntimeError as exc:
            error = str(exc)
            errors.append(error)
            if "HTTP 401" in error:
                break
            if protocol != "auto":
                break
    raise RuntimeError("Lingzhu route failed: " + " | ".join(errors))
