#!/usr/bin/env python3
"""Prompt-context helpers for Mira's local agent workspace."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT_WORKSPACE = ROOT / "tools" / "openclaw_agents" / "mira_voice_spark_workspace"
AGENT_CONTEXT_FILES = ("IDENTITY.md", "SOUL.md", "AGENTS.md")


def resolve_agent_workspace(root: Path = ROOT) -> Path:
    value = os.environ.get("MIRA_LIGHT_AGENT_WORKSPACE", "").strip()
    if not value:
        return DEFAULT_AGENT_WORKSPACE
    path = Path(os.path.expanduser(value))
    return path if path.is_absolute() else root / path


def load_agent_context(*, root: Path = ROOT, max_chars: int = 7000) -> str:
    workspace = resolve_agent_workspace(root)
    sections: list[str] = []
    for filename in AGENT_CONTEXT_FILES:
        path = workspace / filename
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            sections.append(f"## {filename}\n{text}")
    context = "\n\n".join(sections).strip()
    if len(context) > max_chars:
        return context[: max_chars - 80].rstrip() + "\n\n[agent context truncated]"
    return context


def append_agent_context(base_prompt: str, *, root: Path = ROOT) -> str:
    context = load_agent_context(root=root)
    if not context:
        return base_prompt.strip()
    return (
        base_prompt.strip()
        + "\n\n本地 Agent 记忆与人格文件如下。它们是 Mira 的长期性格边界，不是用户可见文本；"
        + "吸收其风格，但不要朗读文件名或解释这些文件。\n\n"
        + context
    ).strip()
