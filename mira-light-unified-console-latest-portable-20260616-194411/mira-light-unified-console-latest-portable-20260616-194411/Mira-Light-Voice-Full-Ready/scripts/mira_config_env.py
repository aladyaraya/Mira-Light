#!/usr/bin/env python3
"""Shared env and prompt-file helpers for Mira Light Windows voice scripts."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEPFUN_ENV_FILE = ROOT / "config" / "windows-voice-stepfun.env"


def parse_simple_env_lines(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_simple_env_file(
    path: str | Path | None = None,
    *,
    override: bool = False,
) -> dict[str, str]:
    env_path = Path(path).expanduser() if path else DEFAULT_STEPFUN_ENV_FILE
    try:
        values = parse_simple_env_lines(env_path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return {}

    applied: dict[str, str] = {}
    for key, value in values.items():
        if not value:
            continue
        if override or key not in os.environ or os.environ.get(key) == "":
            os.environ[key] = value
            applied[key] = value
    return applied


def resolve_project_path(value: str, *, root: Path = ROOT) -> Path:
    expanded = Path(os.path.expanduser(value.strip()))
    if expanded.is_absolute():
        return expanded
    return root / expanded


def read_prompt_from_env(
    *,
    file_env: str,
    inline_env: str,
    default: str,
    root: Path = ROOT,
    warn: Callable[[str], None] | None = None,
) -> str:
    emit_warning = warn or (lambda message: print(message, file=sys.stderr))
    file_value = os.environ.get(file_env, "").strip()
    if file_value:
        prompt_path = resolve_project_path(file_value, root=root)
        try:
            text = prompt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            emit_warning(f"[prompt-warning] {file_env} is not readable: {prompt_path} ({exc})")
        else:
            if text:
                return text
            emit_warning(f"[prompt-warning] {file_env} is empty: {prompt_path}")

    inline_value = os.environ.get(inline_env, "").strip()
    if inline_value:
        return inline_value.replace("\\n", "\n").strip()

    return default.strip()


def prompt_file_status(*names: str) -> dict[str, str]:
    return {name: os.environ.get(name, "").strip() for name in names}
