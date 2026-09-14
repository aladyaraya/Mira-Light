"""Shared pytest configuration for Mira Light tests.

Injects lightweight stubs for optional hardware-only packages (sounddevice,
soundfile) that are not available in headless / CI test environments.  The
stubs are inserted into ``sys.modules`` **before** any test is collected so
that modules like ``mira_realtime_voice_interaction`` and
``openclaw_voice_to_claw`` can be imported without error.

The stubs expose just enough surface area to avoid ``ImportError`` during
module-level ``import``; actual audio I/O functions that depend on real
hardware are not exercised in unit tests anyway.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _install_stub(module_name: str) -> None:
    """Register a ``MagicMock`` as *module_name* if the real package is absent."""
    if module_name in sys.modules:
        return  # already loaded (real or previous stub)
    try:
        __import__(module_name)
    except (ImportError, ModuleNotFoundError, OSError):
        stub = types.ModuleType(module_name)
        # Make attribute access on the stub return further mocks so that
        # statements like ``sd.InputStream`` or ``sf.write`` don't raise.
        stub.__dict__.setdefault("__spec__", None)
        stub.__dict__.setdefault("__loader__", None)
        stub.__dict__.setdefault("__path__", [])
        stub.__dict__.setdefault("__package__", module_name)

        # Wrap the stub so arbitrary attribute lookups (e.g. sd.InputStream,
        # sd.CallbackStop, sf.read) return usable mock objects.
        mock = MagicMock()
        # Preserve the module identity while still delegating attribute access.
        mock.__name__ = module_name
        mock.__spec__ = None
        mock.__path__ = []
        mock.__package__ = module_name
        sys.modules[module_name] = mock


# --- Install stubs for hardware-only packages ---
_OPTIONAL_HW_PACKAGES = [
    "sounddevice",
    "soundfile",
]

for _pkg in _OPTIONAL_HW_PACKAGES:
    _install_stub(_pkg)
