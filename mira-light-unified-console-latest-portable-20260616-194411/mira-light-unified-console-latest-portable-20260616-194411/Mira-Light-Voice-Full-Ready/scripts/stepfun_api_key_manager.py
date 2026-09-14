#!/usr/bin/env python3
"""Global StepFun API Key manager for Mira Light Windows voice stack.

This module provides a single source of truth for the StepFun API key across
all voice scripts. It supports:

1. Environment variable (STEPFUN_API_KEY / STEP_API_KEY) — highest priority
2. Hard-coded fallback key — for portable deployments
3. Explicit override via code

Usage:
    from stepfun_api_key_manager import get_stepfun_api_key, set_stepfun_api_key

    # Get key (auto-resolves env -> hardcoded -> error)
    api_key = get_stepfun_api_key()

    # Override globally for this process
    set_stepfun_api_key("sk-...")

    # Pass to any StepFun client
    from stepfun_realtime_voice import build_auth_headers
    headers = build_auth_headers(api_key)
"""

from __future__ import annotations

import os
from typing import Final


# ---------------------------------------------------------------------------
# Optional hard-coded fallback key for portable Windows deployments.
# Public repositories MUST leave this empty. Fill it in only on trusted
# private machines, or set STEPFUN_API_KEY in the environment instead.
# ---------------------------------------------------------------------------
_FALLBACK_API_KEY: Final[str] = ""

# Process-level override (set via set_stepfun_api_key)
_override_key: str | None = None


def get_stepfun_api_key(
    *,
    explicit: str | None = None,
    allow_fallback: bool = True,
    raise_on_missing: bool = True,
) -> str:
    """Resolve the StepFun API key from explicit -> override -> env -> fallback.

    Resolution order:
        1. explicit argument (if provided)
        2. process override via set_stepfun_api_key()
        3. STEPFUN_API_KEY env var
        4. STEP_API_KEY env var (legacy alias)
        5. _FALLBACK_API_KEY (if allow_fallback=True)
        6. raise RuntimeError (if raise_on_missing=True) or return ""
    """
    # 1. Explicit argument
    if explicit is not None:
        key = explicit.strip()
        if key:
            return key

    # 2. Process override
    global _override_key
    if _override_key is not None:
        key = _override_key.strip()
        if key:
            return key

    # 3. Environment variables
    for env_name in ("STEPFUN_API_KEY", "STEP_API_KEY"):
        key = os.environ.get(env_name, "").strip()
        if key:
            return key

    # 4. Hard-coded fallback
    if allow_fallback:
        key = _FALLBACK_API_KEY.strip()
        if key:
            return key

    # 5. Nothing found
    if raise_on_missing:
        raise RuntimeError(
            "StepFun API key is required. "
            "Set STEPFUN_API_KEY environment variable, "
            "or call set_stepfun_api_key() before use."
        )
    return ""


def set_stepfun_api_key(key: str | None) -> None:
    """Set a process-level override for the StepFun API key.

    This affects all subsequent calls to get_stepfun_api_key() in this process.
    Pass None to clear the override.
    """
    global _override_key
    _override_key = key.strip() if key else None


def has_stepfun_api_key() -> bool:
    """Return True if a usable StepFun API key is available."""
    try:
        get_stepfun_api_key(raise_on_missing=False)
        return True
    except Exception:
        return False


def resolve_api_key_with_fallback(explicit_api_key: str | None = None) -> str:
    """Drop-in replacement for stepfun_realtime_voice.resolve_api_key().

    Maintains backward compatibility with existing callers while adding
    the hard-coded fallback.
    """
    return get_stepfun_api_key(explicit=explicit_api_key, allow_fallback=True)


# ---------------------------------------------------------------------------
# Monkey-patch stepfun_realtime_voice.resolve_api_key at import time
# so all existing scripts automatically get the fallback behavior.
# ---------------------------------------------------------------------------
def _patch_stepfun_realtime_voice() -> None:
    try:
        import stepfun_realtime_voice as _sfrv
        _sfrv.resolve_api_key = resolve_api_key_with_fallback  # type: ignore[attr-defined]
    except Exception:
        pass  # Module not imported yet; will be patched when it is


_patch_stepfun_realtime_voice()
