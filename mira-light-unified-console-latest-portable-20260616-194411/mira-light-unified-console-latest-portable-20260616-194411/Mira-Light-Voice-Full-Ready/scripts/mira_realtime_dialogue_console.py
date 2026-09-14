#!/usr/bin/env python3
"""Interactive StepAudio realtime dialogue console for Mira Light.

This script is only for testing the dialogue model on the local Windows PC:

terminal text input -> StepAudio 2.5 Realtime -> Mary text/audio reply

It does not call the action bridge, LLM planner, or hardware controls.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

from stepfun_realtime_voice import (
    DEFAULT_OUTPUT_SAMPLE_RATE,
    DEFAULT_PROXY_URL,
    DEFAULT_REALTIME_ENDPOINT,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_VOICE,
    play_wav,
    run_realtime_text_prompt,
    write_realtime_output,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / "runtime" / "windows-realtime-dialogue"
EXIT_COMMANDS = {"q", "quit", "exit", "/q", "/quit", "退出", "结束"}


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")


def normalize_console_text(text: str) -> str:
    return text.replace("\x00", "").replace("\ufeff", "").strip()


def is_exit_command(text: str) -> bool:
    return normalize_console_text(text).lower() in EXIT_COMMANDS


def build_dialogue_prompt(user_text: str, history: list[dict[str, str]], *, max_turns: int = 6) -> str:
    recent_history = history[-max(0, int(max_turns)) :]
    lines = [
        "你是 Mira Light 的语音人格 Mary。",
        "请用中文和用户自然对话，语气温柔、陪伴、好奇，回复尽量短。",
        "不要输出舵机角度、TCP 指令、LED 原始值、动作库命令或代码。",
    ]
    if recent_history:
        lines.append("")
        lines.append("最近对话:")
        for item in recent_history:
            user = str(item.get("user") or "").strip()
            assistant = str(item.get("assistant") or "").strip()
            if user:
                lines.append(f"用户: {user}")
            if assistant:
                lines.append(f"Mary: {assistant}")
    lines.append("")
    lines.append(f"当前用户: {user_text.strip()}")
    lines.append("Mary:")
    return "\n".join(lines)


def append_dialogue_history(
    history: list[dict[str, str]],
    user_text: str,
    assistant_text: str,
    *,
    max_turns: int = 6,
) -> list[dict[str, str]]:
    updated = [
        *history,
        {"user": user_text.strip(), "assistant": assistant_text.strip()},
    ]
    return updated[-max(1, int(max_turns)) :]


def turn_output_path(session_dir: str | Path, turn_index: int) -> Path:
    return Path(session_dir) / f"turn-{int(turn_index):03d}" / "transcript.realtime.json"


def write_session_index(session_dir: Path, history: list[dict[str, str]], turns: list[dict[str, Any]]) -> Path:
    path = session_dir / "session.json"
    payload = {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "history": history,
        "turns": turns,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_dialogue_console(args: argparse.Namespace) -> int:
    session_dir = Path(args.output_dir).expanduser() if args.output_dir else DEFAULT_RUNTIME_DIR / timestamp_slug()
    session_dir.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, str]] = []
    turns: list[dict[str, Any]] = []

    print("== Mira Light Realtime Dialogue Console ==")
    print(f"Model: {args.model}")
    print(f"Voice: {args.voice}")
    print(f"Session: {session_dir}")
    if args.proxy_url:
        print(f"Proxy: {args.proxy_url}")
    print("Type q, quit, exit, /q, /quit, 退出, or 结束 to stop.")
    print("")

    turn_index = 1
    while True:
        try:
            user_text = normalize_console_text(input("你 > "))
        except (EOFError, KeyboardInterrupt):
            print("")
            break
        if not user_text:
            continue
        if is_exit_command(user_text):
            break

        prompt = build_dialogue_prompt(user_text, history, max_turns=args.history_turns)
        output_path = turn_output_path(session_dir, turn_index)
        try:
            result = run_realtime_text_prompt(
                prompt,
                api_key=args.api_key,
                endpoint=args.endpoint,
                model=args.model,
                voice=args.voice,
                timeout_seconds=args.timeout_seconds,
                proxy_url=args.proxy_url,
            )
            write_realtime_output(result, output_path, output_sample_rate=args.output_sample_rate)
            assistant_text = str(result.get("summary", {}).get("assistantText") or "").strip()
            print(f"Mary > {assistant_text}")
            if args.play and result.get("responseAudioPath"):
                play_wav(str(result["responseAudioPath"]))
            history = append_dialogue_history(history, user_text, assistant_text, max_turns=args.history_turns)
            turns.append(
                {
                    "turn": turn_index,
                    "user": user_text,
                    "assistant": assistant_text,
                    "outputPath": str(output_path.resolve()),
                    "responseAudioPath": result.get("responseAudioPath"),
                    "ok": result.get("ok"),
                }
            )
            write_session_index(session_dir, history, turns)
            turn_index += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[dialogue-error] {exc}", file=sys.stderr)
            return 2

    write_session_index(session_dir, history, turns)
    print(f"Session saved: {session_dir / 'session.json'}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive StepAudio realtime dialogue test for Mira Light.")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_REALTIME_ENDPOINT", DEFAULT_REALTIME_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_REALTIME_MODEL", DEFAULT_REALTIME_MODEL))
    parser.add_argument("--voice", default=os.environ.get("STEPFUN_REALTIME_VOICE", DEFAULT_VOICE))
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--timeout-seconds", type=int, default=int(os.environ.get("STEPFUN_REALTIME_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)))
    parser.add_argument("--output-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE", DEFAULT_OUTPUT_SAMPLE_RATE)))
    parser.add_argument("--history-turns", type=int, default=6)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--play", action="store_true")
    return parser.parse_args()


def main() -> int:
    return run_dialogue_console(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
