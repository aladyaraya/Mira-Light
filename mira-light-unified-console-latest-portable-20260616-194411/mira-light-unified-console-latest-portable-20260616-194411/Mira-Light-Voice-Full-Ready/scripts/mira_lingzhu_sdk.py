#!/usr/bin/env python3
"""Enhanced Lingzhu SDK for Mira Light.

This module extends the existing mira_lingzhu_client.py into a fuller SDK
with four capabilities the project needs:

1. Multimodal messages  — send images (camera frames, vision results) to
   the cloud brain, so Mira can "show" the Lingzhu adapter what it sees.
2. Streaming responses   — true SSE token-by-token streaming for lower
   first-token latency in voice conversations.
3. Session & memory      — session persistence, layered memory prompt-pack
   read/write, and context window management.
4. Connection resilience — health checks, auto-reconnect, structured errors,
   and async support (asyncio).

Design principles:
- Drop-in compatible: the existing send_via_lingzhu_messages() API is
  preserved. The SDK wraps it and adds new capabilities.
- Cross-platform: pure Python stdlib + optional cv2/numpy for image encoding.
  No platform-specific dependencies.
- Graceful degradation: if streaming is not supported by the server, falls
  back to batch mode automatically.

Usage:

    from mira_lingzhu_sdk import LingzhuSDK, LingzhuConfig

    config = LingzhuConfig.from_env()
    sdk = LingzhuSDK(config)

    # Basic text chat (backward compatible)
    reply = sdk.chat("你好呀")

    # Multimodal: send a camera frame
    reply = sdk.chat_with_image("看看这是什么", frame_bgr)

    # Streaming: get tokens as they arrive
    for token in sdk.chat_stream("给我讲个故事"):
        print(token, end="", flush=True)

    # Session management
    session = sdk.create_session(user_id="user-1")
    sdk.bind_memory_context(session, additional_user_ids=["mira-light-bridge"])

Environment variables (all optional, extends existing MIRA_LIGHT_LINGZHU_*):
    MIRA_LIGHT_LINGZHU_BASE_URL          Base URL (default: http://127.0.0.1:31879)
    MIRA_LIGHT_LINGZHU_AUTH_AK           Auth AK
    MIRA_LIGHT_LINGZHU_AGENT_ID          Agent ID (default: main)
    MIRA_LIGHT_LINGZHU_PROTOCOL          v1 | metis-sse | auto (default: auto)
    MIRA_LIGHT_LINGZHU_TIMEOUT_SECONDS   Request timeout (default: 45)
    MIRA_LIGHT_LINGZHU_STREAM_ENABLED    Enable streaming (default: 1)
    MIRA_LIGHT_LINGZHU_HEALTH_CHECK      Enable health check on startup (default: 1)
    MIRA_LIGHT_LINGZHU_AUTO_RECONNECT    Enable auto-reconnect (default: 1)
    MIRA_LIGHT_LINGZHU_MAX_RETRIES       Max retry attempts (default: 3)
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Generator, Iterator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://127.0.0.1:31879"
DEFAULT_AGENT_ID = "main"
DEFAULT_TIMEOUT = 45
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_HEALTH_TIMEOUT = 5


@dataclass
class LingzhuConfig:
    """Configuration for the Lingzhu SDK."""

    base_url: str = DEFAULT_BASE_URL
    auth_ak: str = ""
    agent_id: str = DEFAULT_AGENT_ID
    protocol: str = "auto"  # v1 | metis-sse | auto
    timeout_seconds: int = DEFAULT_TIMEOUT
    stream_enabled: bool = True
    health_check_enabled: bool = True
    auto_reconnect: bool = True
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY

    @classmethod
    def from_env(cls) -> "LingzhuConfig":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.environ.get("MIRA_LIGHT_LINGZHU_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            auth_ak=os.environ.get("MIRA_LIGHT_LINGZHU_AUTH_AK", ""),
            agent_id=os.environ.get("MIRA_LIGHT_LINGZHU_AGENT_ID", DEFAULT_AGENT_ID),
            protocol=os.environ.get("MIRA_LIGHT_LINGZHU_PROTOCOL", "auto").strip().lower(),
            timeout_seconds=int(os.environ.get("MIRA_LIGHT_LINGZHU_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT))),
            stream_enabled=os.environ.get("MIRA_LIGHT_LINGZHU_STREAM_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"},
            health_check_enabled=os.environ.get("MIRA_LIGHT_LINGZHU_HEALTH_CHECK", "1").strip().lower() not in {"0", "false", "no", "off"},
            auto_reconnect=os.environ.get("MIRA_LIGHT_LINGZHU_AUTO_RECONNECT", "1").strip().lower() not in {"0", "false", "no", "off"},
            max_retries=int(os.environ.get("MIRA_LIGHT_LINGZHU_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))),
            retry_delay=float(os.environ.get("MIRA_LIGHT_LINGZHU_RETRY_DELAY", str(DEFAULT_RETRY_DELAY))),
        )


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class LingzhuError(Exception):
    """Base error for all Lingzhu SDK failures."""


class LingzhuConnectionError(LingzhuError):
    """Cannot reach the Lingzhu adapter (network/tunnel issue)."""


class LingzhuAuthError(LingzhuError):
    """Authentication failed (HTTP 401/403)."""


class LingzhuServerError(LingzhuError):
    """Lingzhu adapter returned a server error (HTTP 5xx)."""


class LingzhuProtocolError(LingzhuError):
    """Unexpected response format from the adapter."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LingzhuMessage:
    """A single message in a Lingzhu conversation."""
    role: str = "user"  # system | user | assistant
    text: str = ""
    images: list[str] = field(default_factory=list)  # data URIs

    def to_dict(self) -> dict[str, Any]:
        item: dict[str, Any] = {"role": self.role, "type": "text", "text": self.text}
        if self.images:
            item["images"] = self.images
        return item


@dataclass
class LingzhuSession:
    """A conversation session with the Lingzhu adapter."""
    session_id: str
    user_id: str = ""
    agent_id: str = "main"
    additional_user_ids: list[str] = field(default_factory=list)
    history: list[LingzhuMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)

    def add_message(self, msg: LingzhuMessage) -> None:
        self.history.append(msg)
        self.last_active_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "additional_user_ids": self.additional_user_ids,
            "message_count": len(self.history),
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(timespec="seconds"),
            "last_active_at": datetime.fromtimestamp(self.last_active_at).isoformat(timespec="seconds"),
        }


@dataclass
class LingzhuResponse:
    """A response from the Lingzhu adapter."""
    text: str = ""
    model: str = ""
    provider: str = "lingzhu-live-adapter"
    protocol: str = "v1"
    raw: dict[str, Any] | None = None
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# Multimodal message builder
# ---------------------------------------------------------------------------

class MultimodalMessageBuilder:
    """Build multimodal messages for the Lingzhu adapter.

    Supports encoding OpenCV frames (BGR numpy arrays) and image files
    as base64 data URIs that can be sent alongside text.
    """

    @staticmethod
    def encode_frame(frame: Any, *, max_width: int = 768, jpeg_quality: int = 75) -> str:
        """Encode an OpenCV BGR frame as a JPEG data URI."""
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise LingzhuError("OpenCV and numpy required for image encoding") from exc

        if not isinstance(frame, np.ndarray):
            raise LingzhuError("Frame must be a numpy array (BGR format)")

        h, w = frame.shape[:2]
        if w > max_width:
            scale = max_width / w
            frame = cv2.resize(frame, (max_width, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)

        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        if not ok:
            raise LingzhuError("Failed to encode frame as JPEG")
        encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    @staticmethod
    def encode_file(path: str) -> str:
        """Encode an image file as a data URI."""
        import mimetypes
        from pathlib import Path

        p = Path(path)
        if not p.is_file():
            raise LingzhuError(f"Image file not found: {path}")
        mime_type, _ = mimetypes.guess_type(p.name)
        if not mime_type:
            mime_type = "image/jpeg"
        encoded = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @classmethod
    def build_vision_message(
        cls,
        text: str,
        *,
        frame: Any = None,
        image_path: str | None = None,
        vision_context: dict[str, Any] | None = None,
    ) -> LingzhuMessage:
        """Build a multimodal message with optional image and vision context.

        Args:
            text: The text content of the message.
            frame: Optional OpenCV BGR frame to attach.
            image_path: Optional path to an image file to attach.
            vision_context: Optional vision understanding context dict
                           (from mira_vision_understanding.SceneUnderstanding).
        """
        images: list[str] = []
        if frame is not None:
            images.append(cls.encode_frame(frame))
        if image_path is not None:
            images.append(cls.encode_file(image_path))

        # If vision context is provided, prepend it to the text
        full_text = text
        if vision_context:
            ctx = vision_context.get("vision_context", vision_context)
            summary = ctx.get("scene_summary", "")
            if summary:
                full_text = f"[视觉感知: {summary}] {text}"

        return LingzhuMessage(role="user", text=full_text, images=images)


# ---------------------------------------------------------------------------
# Streaming response handler
# ---------------------------------------------------------------------------

class StreamingResponseHandler:
    """Parse SSE (Server-Sent Events) streams from the Lingzhu adapter.

    The Lingzhu adapter's /metis/agent/api/sse endpoint returns SSE-formatted
    data. This handler yields text tokens as they arrive, enabling real-time
    TTS and lower perceived latency.
    """

    @staticmethod
    def stream_sse(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: int,
    ) -> Generator[str, None, None]:
        """Open an SSE connection and yield text tokens as they arrive.

        Yields:
            Text fragments (tokens) as they are received from the server.
        """
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={**headers, "Accept": "text/event-stream"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                buffer = ""
                for chunk in response:
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            yield data
                            continue
                        text = StreamingResponseHandler._extract_text(event)
                        if text:
                            yield text
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401:
                raise LingzhuAuthError(f"Authentication failed: {body}") from exc
            if exc.code >= 500:
                raise LingzhuServerError(f"Server error {exc.code}: {body}") from exc
            raise LingzhuError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise LingzhuConnectionError(f"Cannot reach Lingzhu adapter: {exc}") from exc

    @staticmethod
    def _extract_text(payload: Any) -> str:
        """Extract text from an SSE event payload."""
        if isinstance(payload, dict):
            for key in ("text", "content", "reply", "delta", "message"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            choices = payload.get("choices")
            if isinstance(choices, list) and choices:
                return StreamingResponseHandler._extract_text(choices[0])
            delta = payload.get("delta")
            if isinstance(delta, dict):
                return StreamingResponseHandler._extract_text(delta)
        return ""


# ---------------------------------------------------------------------------
# Session & memory manager
# ---------------------------------------------------------------------------

class SessionManager:
    """Manage Lingzhu conversation sessions and memory context.

    The Lingzhu adapter supports layered memory through 'additional_user_ids'.
    Each ID represents a memory context (e.g., 'mira-light-bridge' for
    embodied memory). This manager tracks active sessions and their
    memory bindings.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, LingzhuSession] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        *,
        user_id: str = "",
        agent_id: str = "main",
        additional_user_ids: list[str] | None = None,
    ) -> LingzhuSession:
        """Create a new conversation session."""
        session_id = f"mira-session-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        session = LingzhuSession(
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            additional_user_ids=additional_user_ids or [],
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> LingzhuSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> LingzhuSession | None:
        with self._lock:
            return self._sessions.pop(session_id, None)

    def bind_memory_context(
        self,
        session: LingzhuSession,
        additional_user_ids: list[str],
    ) -> None:
        """Bind memory contexts (additional_user_ids) to a session."""
        for uid in additional_user_ids:
            if uid not in session.additional_user_ids:
                session.additional_user_ids.append(uid)

    def unbind_memory_context(
        self,
        session: LingzhuSession,
        additional_user_ids: list[str],
    ) -> None:
        """Remove memory contexts from a session."""
        session.additional_user_ids = [
            uid for uid in session.additional_user_ids if uid not in additional_user_ids
        ]

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._sessions.values()]

    def get_history(self, session_id: str, max_turns: int = 10) -> list[LingzhuMessage]:
        """Get recent conversation history for a session."""
        session = self.get_session(session_id)
        if session is None:
            return []
        return session.history[-max_turns:] if max_turns > 0 else list(session.history)


# ---------------------------------------------------------------------------
# Main SDK class
# ---------------------------------------------------------------------------

class LingzhuSDK:
    """Enhanced Lingzhu SDK for Mira Light.

    Wraps the existing mira_lingzhu_client.send_via_lingzhu_messages()
    and adds multimodal, streaming, session management, and resilience.
    """

    def __init__(self, config: LingzhuConfig | None = None) -> None:
        self.config = config or LingzhuConfig.from_env()
        self.sessions = SessionManager()
        self._healthy: bool = False
        self._last_health_check: float = 0.0
        self._lock = threading.Lock()

        # Import the legacy client for backward compatibility
        try:
            from mira_lingzhu_client import send_via_lingzhu_messages
            self._legacy_send = send_via_lingzhu_messages
        except ImportError:
            self._legacy_send = None

        # Run health check on startup if enabled
        if self.config.health_check_enabled:
            self.check_health()

    # -----------------------------------------------------------------------
    # Health check & connection management
    # -----------------------------------------------------------------------

    def check_health(self) -> bool:
        """Check if the Lingzhu adapter is reachable.

        Tries both /v1/health and /metis/agent/api/health endpoints.
        Updates the internal health state.
        """
        for path in ["/v1/health", "/metis/agent/api/health"]:
            url = f"{self.config.base_url}{path}"
            try:
                request = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(request, timeout=DEFAULT_HEALTH_TIMEOUT) as response:
                    if response.status == 200:
                        with self._lock:
                            self._healthy = True
                            self._last_health_check = time.time()
                        return True
            except Exception:
                continue
        with self._lock:
            self._healthy = False
        return False

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    def ensure_connected(self) -> None:
        """Ensure the adapter is reachable. Raises on failure."""
        if not self._healthy or (time.time() - self._last_health_check > 30):
            if not self.check_health():
                raise LingzhuConnectionError(
                    f"Lingzhu adapter not reachable at {self.config.base_url}. "
                    "Check SSH tunnel or network connection."
                )

    # -----------------------------------------------------------------------
    # Basic chat (backward compatible)
    # -----------------------------------------------------------------------

    def chat(
        self,
        text: str,
        *,
        session: LingzhuSession | None = None,
        system_prompt: str = "",
        timeout: int | None = None,
    ) -> LingzhuResponse:
        """Send a text message and get a reply.

        Args:
            text: User message text.
            session: Optional session for context. If None, a one-shot session is used.
            system_prompt: Optional system prompt.
            timeout: Override default timeout.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if session:
            # Include recent history for context
            for msg in session.history[-6:]:
                messages.append({"role": msg.role, "content": msg.text})
        messages.append({"role": "user", "content": text})

        return self._send_messages(messages, session=session, timeout=timeout)

    def chat_with_image(
        self,
        text: str,
        frame: Any = None,
        *,
        image_path: str | None = None,
        vision_context: dict[str, Any] | None = None,
        session: LingzhuSession | None = None,
        system_prompt: str = "",
        timeout: int | None = None,
    ) -> LingzhuResponse:
        """Send a multimodal message with an image.

        Args:
            text: User message text.
            frame: OpenCV BGR frame (numpy array).
            image_path: Path to an image file (alternative to frame).
            vision_context: Optional vision understanding context.
            session: Optional session for context.
            system_prompt: Optional system prompt.
            timeout: Override default timeout.
        """
        msg = MultimodalMessageBuilder.build_vision_message(
            text, frame=frame, image_path=image_path, vision_context=vision_context
        )

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if session:
            for m in session.history[-6:]:
                messages.append({"role": m.role, "content": m.text})

        # Add the multimodal message as text (images are sent as a separate field)
        # The Lingzhu adapter's v1/chat accepts message items with optional images
        messages.append({"role": msg.role, "content": msg.text, "images": msg.images})

        return self._send_messages(messages, session=session, timeout=timeout)

    # -----------------------------------------------------------------------
    # Streaming chat
    # -----------------------------------------------------------------------

    def chat_stream(
        self,
        text: str,
        *,
        session: LingzhuSession | None = None,
        system_prompt: str = "",
        timeout: int | None = None,
    ) -> Generator[str, None, None]:
        """Stream a chat response token by token.

        Falls back to batch mode (yielding the full text at once) if
        streaming is disabled or the server doesn't support SSE.

        Yields:
            Text tokens as they arrive from the server.
        """
        if not self.config.stream_enabled:
            response = self.chat(text, session=session, system_prompt=system_prompt, timeout=timeout)
            yield response.text
            return

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if session:
            for msg in session.history[-6:]:
                messages.append({"role": msg.role, "content": msg.text})
        messages.append({"role": "user", "content": text})

        payload = self._build_payload(messages, session=session)
        headers = self._build_headers()

        url = f"{self.config.base_url}/metis/agent/api/sse"
        try:
            full_text = ""
            for token in StreamingResponseHandler.stream_sse(
                url, payload, headers, timeout or self.config.timeout_seconds
            ):
                full_text += token
                yield token

            # Update session history
            if session:
                session.add_message(LingzhuMessage(role="user", text=text))
                session.add_message(LingzhuMessage(role="assistant", text=full_text))

        except LingzhuError:
            # Fall back to batch mode
            if self.config.auto_reconnect:
                response = self.chat(text, session=session, system_prompt=system_prompt, timeout=timeout)
                yield response.text
            else:
                raise

    # -----------------------------------------------------------------------
    # Session management
    # -----------------------------------------------------------------------

    def create_session(
        self,
        *,
        user_id: str = "",
        additional_user_ids: list[str] | None = None,
    ) -> LingzhuSession:
        """Create a new conversation session."""
        return self.sessions.create_session(
            user_id=user_id,
            agent_id=self.config.agent_id,
            additional_user_ids=additional_user_ids,
        )

    def chat_in_session(
        self,
        session: LingzhuSession,
        text: str,
        *,
        system_prompt: str = "",
        timeout: int | None = None,
    ) -> LingzhuResponse:
        """Send a message within an existing session (with history context)."""
        response = self.chat(text, session=session, system_prompt=system_prompt, timeout=timeout)
        session.add_message(LingzhuMessage(role="user", text=text))
        session.add_message(LingzhuMessage(role="assistant", text=response.text))
        return response

    # -----------------------------------------------------------------------
    # Memory / context management
    # -----------------------------------------------------------------------

    def bind_embodied_memory(self, session: LingzhuSession) -> None:
        """Bind the mira-light-bridge embodied memory context to a session."""
        self.sessions.bind_memory_context(session, ["mira-light-bridge"])

    def bind_vision_memory(self, session: LingzhuSession) -> None:
        """Bind a vision memory context to a session.

        This allows the Lingzhu adapter to accumulate vision observations
        across turns, so the cloud brain remembers what Mira has seen.
        """
        self.sessions.bind_memory_context(session, ["mira-vision-context"])

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get information about a session."""
        session = self.sessions.get_session(session_id)
        return session.to_dict() if session else None

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _send_messages(
        self,
        messages: list[dict[str, str]],
        *,
        session: LingzhuSession | None = None,
        timeout: int | None = None,
    ) -> LingzhuResponse:
        """Send messages via the Lingzhu adapter with retry logic."""
        effective_timeout = timeout or self.config.timeout_seconds
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                if self.config.auto_reconnect and not self._healthy:
                    self.check_health()

                # Try the legacy client first (most compatible)
                if self._legacy_send is not None:
                    text, meta = self._legacy_send(
                        messages,
                        base_url=self.config.base_url,
                        auth_ak=self.config.auth_ak,
                        agent_id=session.agent_id if session else self.config.agent_id,
                        user_id=session.user_id if session else "",
                        session_id=session.session_id if session else f"oneshot-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        additional_user_ids=session.additional_user_ids if session else [],
                        timeout_seconds=effective_timeout,
                    )
                    return LingzhuResponse(
                        text=text,
                        model=meta.get("model", ""),
                        provider=meta.get("provider", "lingzhu-live-adapter"),
                        protocol=meta.get("protocol", "v1"),
                        raw=meta.get("payload"),
                        latency_ms=0,
                    )

                # Fallback: direct HTTP call
                return self._send_direct(messages, session=session, timeout=effective_timeout)

            except LingzhuAuthError:
                raise  # Don't retry auth errors
            except (LingzhuConnectionError, LingzhuServerError, RuntimeError) as exc:
                last_error = exc
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * attempt
                    time.sleep(delay)
                    if self.config.auto_reconnect:
                        self.check_health()
                continue

        raise LingzhuError(f"Failed after {self.config.max_retries} attempts: {last_error}") from last_error

    def _send_direct(
        self,
        messages: list[dict[str, str]],
        *,
        session: LingzhuSession | None = None,
        timeout: int,
    ) -> LingzhuResponse:
        """Direct HTTP call to the Lingzhu adapter (fallback when legacy client unavailable)."""
        payload = self._build_payload(messages, session=session)
        headers = self._build_headers()
        url = f"{self.config.base_url}/v1/chat"

        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8").strip()
                latency_ms = int((time.perf_counter() - started) * 1000)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401:
                raise LingzhuAuthError(f"Auth failed: {body}") from exc
            if exc.code >= 500:
                raise LingzhuServerError(f"Server error {exc.code}: {body}") from exc
            raise LingzhuError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise LingzhuConnectionError(f"Cannot reach adapter: {exc}") from exc

        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"ok": True, "raw": raw}

        text = str(data.get("text") or "")
        upstream = data.get("upstream") if isinstance(data.get("upstream"), dict) else {}

        return LingzhuResponse(
            text=text,
            model=str(upstream.get("model") or ""),
            provider="lingzhu-live-adapter",
            protocol="v1",
            raw=data,
            latency_ms=latency_ms,
        )

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        *,
        session: LingzhuSession | None = None,
    ) -> dict[str, Any]:
        """Build the request payload for the Lingzhu adapter."""
        # Convert messages to the Lingzhu message item format
        items: list[dict[str, Any]] = []
        for msg in messages:
            role = str(msg.get("role") or "user").strip() or "user"
            content = str(msg.get("content") or "").strip()
            if not content and not msg.get("images"):
                continue
            item: dict[str, Any] = {"role": role, "type": "text", "text": content}
            if msg.get("images"):
                item["images"] = msg["images"]
            items.append(item)

        return {
            "agent_id": session.agent_id if session else self.config.agent_id,
            "user_id": session.user_id if session else "",
            "session_id": session.session_id if session else f"oneshot-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message_id": f"mira-light-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "additional_user_ids": session.additional_user_ids if session else [],
            "disable_default_additional_user_ids": not (session and session.additional_user_ids),
            "message": items,
        }

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self.config.auth_ak:
            headers["Authorization"] = f"Bearer {self.config.auth_ak}"
        return headers


# ---------------------------------------------------------------------------
# Convenience: module-level singleton
# ---------------------------------------------------------------------------

_sdk_instance: LingzhuSDK | None = None
_sdk_lock = threading.Lock()


def get_sdk() -> LingzhuSDK:
    """Get the process-wide Lingzhu SDK singleton."""
    global _sdk_instance
    with _sdk_lock:
        if _sdk_instance is None:
            _sdk_instance = LingzhuSDK()
        return _sdk_instance


def reset_sdk() -> None:
    """Reset the singleton (useful for testing)."""
    global _sdk_instance
    with _sdk_lock:
        _sdk_instance = None
