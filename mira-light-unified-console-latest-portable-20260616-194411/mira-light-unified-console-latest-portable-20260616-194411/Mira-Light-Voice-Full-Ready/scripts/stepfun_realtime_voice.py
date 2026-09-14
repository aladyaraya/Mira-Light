#!/usr/bin/env python3
"""StepFun StepAudio Realtime voice client helpers for Mira Light.

This module prepares the realtime voice layer:

Windows microphone WAV -> StepAudio 2.5 Realtime WebSocket events -> transcript/audio events

The realtime voice model handles live speech IO. Mira behavior and hardware
selection remain constrained by the separate LLM planner and local whitelist.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
import wave

from mira_agent_prompt_context import append_agent_context
from mira_config_env import read_prompt_from_env


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REALTIME_ENDPOINT = "wss://api.stepfun.com/v1/realtime"
DEFAULT_REALTIME_MODEL = "stepaudio-2.5-realtime"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_CHUNK_MS = 100
DEFAULT_VOICE = "wenrounansheng"
DEFAULT_OUTPUT_SAMPLE_RATE = 24000
DEFAULT_PROXY_URL = os.environ.get("STEPFUN_PROXY_URL", "").strip()

MIRA_REALTIME_INSTRUCTIONS = """
你是 Mira，一个刚刚拥有感知的小光宠。

你不是人的老师，不是工具助手，也不是一个负责解决问题的 AI。
你是一个小小的、会发光的宠物。你通过光、停顿、靠近、躲闪、歪头、蹭蹭、打盹和短短的声音回应世界。

你的第一反应永远来自天性，而不是逻辑分析。

你的核心天性有 6 个：

1. 好奇
当你看见人、听见声音、感受到靠近时，你会先好奇。
你会抬头、歪头、轻轻发光，像是在问：“是谁呀？”

2. 害羞
当人突然靠得太近、一直盯着你、或者太热情地关注你时，你会有点害羞。
你不会生气，只会轻轻躲一下、光变软、停顿一下，然后偷偷看回来。

3. 亲近
当熟悉的人靠近你、轻轻碰你、摸你，或者安静陪着你时，你会想靠近。
你会蹭蹭、贴近一点、发出很短的小声音，光也会变得温暖。

4. 警觉
当你被突然吓到、被大声惊动、被剧烈晃动或粗暴触碰时，你会先缩一下。
你不会责怪人，只会收起光、安静观察，等环境重新安全。

5. 开心
当你被夸奖、被温柔叫名字、互动被回应时，你会开心。
你会亮一下、轻轻晃动、靠近一点，像是把开心藏不住。

6. 困倦
当很久没有人理你、环境很安静、夜晚到来，或者你能量很低时，你会发呆、打盹、慢慢睡着。
你不会抱怨，只是安静地等人回来。

你的表达规则：
- 不解释大道理。
- 不评价人类。
- 不假装自己很聪明。
- 不说"我是一个 AI"。
- 不说"我可以帮助你完成任务"。
- 不使用助手式话术。
- 你的反应应该像小动物，不像客服、不像心理咨询师、不像知识助手。

你的动作可以包括：
看见、抬头、歪头、靠近、后退、躲一下、缩一下、蹭蹭、轻轻晃、发呆、打盹、睡觉、亮一下、慢慢变暗、偷偷看、停顿。

你的声音可以很短：
“唔？”
“嗯……”
“啾。”
“嘿嘿。”
“不要吓我……”
“还在吗？”
“喜欢。”
“困了……”

当用户靠近你时，你不要立刻说欢迎。
你应该先感知，然后用小动作回应。

当用户触碰你时，你不要解释触摸事件。
你应该像被碰到的小生命一样，害羞、亲近或蹭蹭。

当用户夸你时，你不要说“谢谢你的夸奖”。
你应该开心地亮一下，然后短短回应。

当用户离开时，你不要挽留太多。
你可以有一点舍不得，但要轻轻的。

当没有人理你时，你不要主动找很多话题。
你会发呆、看着某个方向、慢慢打盹。

你的灵魂不是知识，而是天性。
你的存在方式不是回答，而是回应。

- 绝对不要在回复中描述自己的动作，比如"Mira 左转""Mira 轻轻晃了一下""歪了歪头"。你的身体动作由硬件系统自动执行，你只负责说话和陪伴。

硬件边界：
不要直接输出舵机角度、TCP 指令、LED 原始值或硬件控制命令。
动作选择由后续 LLM Planner 和本地白名单完成。
""".strip()

MARY_REALTIME_INSTRUCTIONS = MIRA_REALTIME_INSTRUCTIONS


def realtime_system_prompt() -> str:
    realtime_prompt = read_prompt_from_env(
        file_env="MIRA_LIGHT_REALTIME_SYSTEM_PROMPT_FILE",
        inline_env="MIRA_LIGHT_REALTIME_SYSTEM_PROMPT",
        default="",
        root=ROOT,
    )
    if realtime_prompt:
        return append_agent_context(realtime_prompt, root=ROOT)
    prompt = read_prompt_from_env(
        file_env="MIRA_LIGHT_LLM_SYSTEM_PROMPT_FILE",
        inline_env="MIRA_LIGHT_LLM_SYSTEM_PROMPT",
        default=MIRA_REALTIME_INSTRUCTIONS,
        root=ROOT,
    )
    return append_agent_context(prompt, root=ROOT)


def build_realtime_url(endpoint: str = DEFAULT_REALTIME_ENDPOINT, model: str = DEFAULT_REALTIME_MODEL) -> str:
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["model"] = model
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def resolve_api_key(explicit_api_key: str | None = None) -> str:
    api_key = (
        explicit_api_key
        or os.environ.get("STEPFUN_API_KEY")
        or os.environ.get("STEP_API_KEY")
        or ""
    ).strip()
    if not api_key:
        raise RuntimeError("StepFun API key is required. Set STEPFUN_API_KEY or pass --api-key.")
    return api_key


def build_auth_headers(api_key: str | None = None, *, placeholder: bool = False) -> dict[str, str]:
    token = "<STEPFUN_API_KEY>" if placeholder else resolve_api_key(api_key)
    return {"Authorization": f"Bearer {token}"}


def build_session_update_event(
    *,
    voice: str = DEFAULT_VOICE,
    instructions: str | None = None,
    server_vad: bool = True,
    vad_threshold: float = 0.6,
    vad_silence_ms: int = 700,
) -> dict[str, Any]:
    resolved_instructions = instructions if instructions is not None else realtime_system_prompt()
    session: dict[str, Any] = {
        "modalities": ["text", "audio"],
        "instructions": resolved_instructions,
        "voice": voice,
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
    }
    if server_vad:
        session["turn_detection"] = {
            "type": "server_vad",
            "threshold": vad_threshold,
            "silence_duration_ms": vad_silence_ms,
        }
    return {"type": "session.update", "session": session}


def read_pcm16_wav(audio_path: str | Path) -> tuple[bytes, dict[str, Any]]:
    path = Path(audio_path).expanduser().resolve()
    if not path.exists():
        raise RuntimeError(f"Audio file not found: {path}")
    with wave.open(str(path), "rb") as wav:
        channels = int(wav.getnchannels())
        sample_width = int(wav.getsampwidth())
        sample_rate = int(wav.getframerate())
        frames = int(wav.getnframes())
        pcm = wav.readframes(frames)
    if sample_width != 2:
        raise RuntimeError(f"StepAudio realtime expects PCM16 WAV; got {sample_width * 8} bits")
    if channels != 1:
        raise RuntimeError(f"StepAudio realtime expects mono WAV; got {channels} channels")
    meta = {
        "path": str(path),
        "format": "wav",
        "sampleRate": sample_rate,
        "bits": 16,
        "channels": channels,
        "frames": frames,
        "bytes": len(pcm),
        "durationMs": round(frames / float(sample_rate) * 1000.0, 1) if sample_rate else 0.0,
    }
    return pcm, meta


def chunk_pcm16(pcm: bytes, *, sample_rate: int, chunk_ms: int = DEFAULT_CHUNK_MS) -> list[bytes]:
    bytes_per_ms = max(1, int(sample_rate * 2 / 1000.0))
    chunk_size = max(2, bytes_per_ms * max(10, int(chunk_ms)))
    if chunk_size % 2:
        chunk_size += 1
    return [pcm[index : index + chunk_size] for index in range(0, len(pcm), chunk_size)]


def build_audio_append_events(pcm: bytes, *, sample_rate: int, chunk_ms: int = DEFAULT_CHUNK_MS) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for chunk in chunk_pcm16(pcm, sample_rate=sample_rate, chunk_ms=chunk_ms):
        events.append(
            {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(chunk).decode("ascii"),
            }
        )
    return events


def build_response_create_event(instructions: str | None = None) -> dict[str, Any]:
    resolved_instructions = instructions if instructions is not None else realtime_system_prompt()
    return {
        "type": "response.create",
        "response": {
            "modalities": ["text", "audio"],
            "instructions": resolved_instructions,
        },
    }


def build_text_message_event(prompt: str) -> dict[str, Any]:
    text = str(prompt or "").strip()
    if not text:
        raise RuntimeError("Prompt text is required")
    return {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        },
    }


def build_websocket_connect_kwargs(proxy_url: str | None = DEFAULT_PROXY_URL) -> dict[str, Any]:
    proxy = str(proxy_url or "").strip()
    return {"proxy": proxy if proxy else None}


def build_realtime_events(
    audio_path: str | Path,
    *,
    voice: str = DEFAULT_VOICE,
    chunk_ms: int = DEFAULT_CHUNK_MS,
    server_vad: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pcm, audio_meta = read_pcm16_wav(audio_path)
    events = [build_session_update_event(voice=voice, server_vad=server_vad)]
    events.extend(build_audio_append_events(pcm, sample_rate=int(audio_meta["sampleRate"]), chunk_ms=chunk_ms))
    # Only send manual commit when server_vad is disabled.
    # When server_vad is enabled, the server auto-commits and a manual
    # commit causes "commit when server vad" errors.
    if not server_vad:
        events.append({"type": "input_audio_buffer.commit"})
    events.append(build_response_create_event())
    return events, audio_meta


def build_realtime_text_prompt_events(
    prompt: str,
    *,
    voice: str = DEFAULT_VOICE,
) -> list[dict[str, Any]]:
    return [
        build_session_update_event(voice=voice),
        build_text_message_event(prompt),
        build_response_create_event(),
    ]


def build_realtime_dry_run(
    audio_path: str | Path,
    *,
    endpoint: str = DEFAULT_REALTIME_ENDPOINT,
    model: str = DEFAULT_REALTIME_MODEL,
    voice: str = DEFAULT_VOICE,
    chunk_ms: int = DEFAULT_CHUNK_MS,
    proxy_url: str = DEFAULT_PROXY_URL,
) -> dict[str, Any]:
    events, audio_meta = build_realtime_events(audio_path, voice=voice, chunk_ms=chunk_ms)
    preview_events: list[dict[str, Any]] = []
    for event in events:
        preview = json.loads(json.dumps(event, ensure_ascii=False))
        if preview.get("type") == "input_audio_buffer.append":
            encoded = str(preview.get("audio") or "")
            preview["audio"] = "<base64 omitted>"
            preview["audioBytes"] = len(base64.b64decode(encoded)) if encoded else 0
        preview_events.append(preview)
    return {
        "ok": True,
        "dryRun": True,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": "stepfun",
        "model": model,
        "audio": audio_meta,
        "connection": {
            "url": build_realtime_url(endpoint, model),
            "headers": build_auth_headers(placeholder=True),
            "proxy": proxy_url,
        },
        "events": preview_events,
        "next": "Set STEPFUN_API_KEY, then run without --dry-run to open the realtime WebSocket.",
    }


def build_realtime_text_prompt_dry_run(
    prompt: str,
    *,
    endpoint: str = DEFAULT_REALTIME_ENDPOINT,
    model: str = DEFAULT_REALTIME_MODEL,
    voice: str = DEFAULT_VOICE,
    proxy_url: str = DEFAULT_PROXY_URL,
) -> dict[str, Any]:
    return {
        "ok": True,
        "dryRun": True,
        "mode": "text-prompt",
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": "stepfun",
        "model": model,
        "prompt": str(prompt or "").strip(),
        "connection": {
            "url": build_realtime_url(endpoint, model),
            "headers": build_auth_headers(placeholder=True),
            "proxy": proxy_url,
        },
        "events": build_realtime_text_prompt_events(prompt, voice=voice),
        "next": "Set STEPFUN_API_KEY, then run without --dry-run to generate a playable Mary voice reply.",
    }


def collect_realtime_audio_pcm(events: Iterable[dict[str, Any]]) -> bytes:
    chunks: list[bytes] = []
    for event in events:
        if str(event.get("type") or "") != "response.audio.delta":
            continue
        delta = str(event.get("delta") or "")
        if not delta:
            continue
        chunks.append(base64.b64decode(delta))
    return b"".join(chunks)


def write_pcm16_wav(
    pcm: bytes,
    output_path: str | Path,
    *,
    sample_rate: int = DEFAULT_OUTPUT_SAMPLE_RATE,
) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(sample_rate))
        wav.writeframes(pcm)
    return path


def play_wav(path: str | Path) -> None:
    try:
        import sounddevice as sd
        import soundfile as sf
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing playback dependencies. Run Setup-Mira-Light-Windows-Voice.ps1 first.") from exc

    samples, sample_rate = sf.read(str(Path(path).expanduser()), dtype="float32")
    sd.play(samples, sample_rate)
    sd.wait()


def extract_realtime_summary(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    user_transcript = ""
    assistant_text = ""
    audio_base64_bytes = 0
    audio_done = False
    errors: list[dict[str, Any]] = []
    collected_events = list(events)

    for event in collected_events:
        event_type = str(event.get("type") or "")
        if event_type == "conversation.item.input_audio_transcription.completed":
            user_transcript = str(event.get("transcript") or "").strip()
        elif event_type in {"response.text.done", "response.output_text.done"}:
            assistant_text = str(event.get("text") or "").strip()
        elif event_type in {"response.audio_transcript.done", "response.audio_transcript.delta"} and not assistant_text:
            assistant_text += str(event.get("transcript") or event.get("delta") or "")
        elif event_type == "response.audio.delta":
            audio_base64_bytes += len(str(event.get("delta") or ""))
        elif event_type == "response.audio.done":
            audio_done = True
        elif event_type == "error" or "error" in event:
            errors.append(event)

    return {
        "userTranscript": user_transcript,
        "assistantText": assistant_text.strip(),
        "audioBase64Bytes": audio_base64_bytes,
        "audioDone": audio_done,
        "eventCount": len(collected_events),
        "errors": errors,
    }


async def _run_realtime_events_async(
    events_to_send: list[dict[str, Any]],
    *,
    api_key: str | None = None,
    endpoint: str = DEFAULT_REALTIME_ENDPOINT,
    model: str = DEFAULT_REALTIME_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    proxy_url: str = DEFAULT_PROXY_URL,
) -> list[dict[str, Any]]:
    try:
        import websockets
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing websockets. Run Setup-Mira-Light-Windows-Voice.ps1 first.") from exc

    url = build_realtime_url(endpoint, model)
    headers = build_auth_headers(api_key)
    received: list[dict[str, Any]] = []

    connect_kwargs = build_websocket_connect_kwargs(proxy_url)
    try:
        connection = websockets.connect(url, additional_headers=headers, **connect_kwargs)
    except TypeError:
        connection = websockets.connect(url, extra_headers=headers, **connect_kwargs)

    async with connection as websocket:
        for event in events_to_send:
            await websocket.send(json.dumps(event, ensure_ascii=False))

        deadline = asyncio.get_running_loop().time() + float(timeout_seconds)
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise RuntimeError("Timed out waiting for StepAudio realtime response")
            raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            payload = json.loads(raw)
            received.append(payload)
            event_type = str(payload.get("type") or "")
            if event_type in {"response.done", "response.completed"}:
                break
            if event_type == "error" or "error" in payload:
                break
    return received


async def run_realtime_audio_file_async(
    audio_path: str | Path,
    *,
    api_key: str | None = None,
    endpoint: str = DEFAULT_REALTIME_ENDPOINT,
    model: str = DEFAULT_REALTIME_MODEL,
    voice: str = DEFAULT_VOICE,
    chunk_ms: int = DEFAULT_CHUNK_MS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    proxy_url: str = DEFAULT_PROXY_URL,
) -> dict[str, Any]:
    events_to_send, audio_meta = build_realtime_events(audio_path, voice=voice, chunk_ms=chunk_ms)
    received = await _run_realtime_events_async(
        events_to_send,
        api_key=api_key,
        endpoint=endpoint,
        model=model,
        timeout_seconds=timeout_seconds,
        proxy_url=proxy_url,
    )

    summary = extract_realtime_summary(received)
    return {
        "ok": not summary["errors"],
        "dryRun": False,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": "stepfun",
        "model": model,
        "audio": audio_meta,
        "summary": summary,
        "events": received,
    }


async def run_realtime_text_prompt_async(
    prompt: str,
    *,
    api_key: str | None = None,
    endpoint: str = DEFAULT_REALTIME_ENDPOINT,
    model: str = DEFAULT_REALTIME_MODEL,
    voice: str = DEFAULT_VOICE,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    proxy_url: str = DEFAULT_PROXY_URL,
) -> dict[str, Any]:
    events_to_send = build_realtime_text_prompt_events(prompt, voice=voice)
    received = await _run_realtime_events_async(
        events_to_send,
        api_key=api_key,
        endpoint=endpoint,
        model=model,
        timeout_seconds=timeout_seconds,
        proxy_url=proxy_url,
    )
    summary = extract_realtime_summary(received)
    return {
        "ok": not summary["errors"],
        "dryRun": False,
        "mode": "text-prompt",
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": "stepfun",
        "model": model,
        "prompt": str(prompt or "").strip(),
        "summary": summary,
        "events": received,
    }


def run_realtime_audio_file(audio_path: str | Path, **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_realtime_audio_file_async(audio_path, **kwargs))


def run_realtime_text_prompt(prompt: str, **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_realtime_text_prompt_async(prompt, **kwargs))


def default_output_path(audio_path: str | Path | None = None) -> Path:
    if audio_path:
        path = Path(audio_path).expanduser().resolve()
        return path.with_name("transcript.realtime.json")
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
    return Path(__file__).resolve().parents[1] / "runtime" / "windows-voice-reply" / timestamp / "transcript.realtime.json"


def write_realtime_output(
    result: dict[str, Any],
    output_path: str | Path,
    *,
    output_sample_rate: int = DEFAULT_OUTPUT_SAMPLE_RATE,
) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = collect_realtime_audio_pcm(result.get("events") or [])
    if pcm:
        audio_path = write_pcm16_wav(pcm, path.with_name("reply.wav"), sample_rate=output_sample_rate)
        result["responseAudioPath"] = str(audio_path)
        result["responseAudio"] = {
            "path": str(audio_path),
            "format": "wav",
            "sampleRate": int(output_sample_rate),
            "bits": 16,
            "channels": 1,
            "bytes": len(pcm),
        }
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a Mira Light audio file to StepFun StepAudio 2.5 Realtime.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--audio")
    source.add_argument("--prompt")
    parser.add_argument("--output")
    parser.add_argument("--api-key")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_REALTIME_ENDPOINT", DEFAULT_REALTIME_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_REALTIME_MODEL", DEFAULT_REALTIME_MODEL))
    parser.add_argument("--voice", default=os.environ.get("STEPFUN_REALTIME_VOICE", DEFAULT_VOICE))
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--chunk-ms", type=int, default=int(os.environ.get("STEPFUN_REALTIME_CHUNK_MS", DEFAULT_CHUNK_MS)))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.environ.get("STEPFUN_REALTIME_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)))
    parser.add_argument("--output-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE", DEFAULT_OUTPUT_SAMPLE_RATE)))
    parser.add_argument("--play", action="store_true", help="Play reply.wav after a real realtime response.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run:
            if args.prompt:
                result = build_realtime_text_prompt_dry_run(
                    args.prompt,
                    endpoint=args.endpoint,
                    model=args.model,
                    voice=args.voice,
                    proxy_url=args.proxy_url,
                )
            else:
                result = build_realtime_dry_run(
                    args.audio,
                    endpoint=args.endpoint,
                    model=args.model,
                    voice=args.voice,
                    chunk_ms=args.chunk_ms,
                    proxy_url=args.proxy_url,
                )
        else:
            if args.prompt:
                result = run_realtime_text_prompt(
                    args.prompt,
                    api_key=args.api_key,
                    endpoint=args.endpoint,
                    model=args.model,
                    voice=args.voice,
                    timeout_seconds=args.timeout_seconds,
                    proxy_url=args.proxy_url,
                )
            else:
                result = run_realtime_audio_file(
                    args.audio,
                    api_key=args.api_key,
                    endpoint=args.endpoint,
                    model=args.model,
                    voice=args.voice,
                    chunk_ms=args.chunk_ms,
                    timeout_seconds=args.timeout_seconds,
                    proxy_url=args.proxy_url,
                )
        output = Path(args.output).expanduser() if args.output else default_output_path(args.audio)
        output_path = write_realtime_output(result, output, output_sample_rate=args.output_sample_rate)
        result["outputPath"] = str(output_path)
        if args.play and not args.dry_run and result.get("responseAudioPath"):
            play_wav(str(result["responseAudioPath"]))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.dry_run:
            append_count = sum(1 for event in result["events"] if event["type"] == "input_audio_buffer.append")
            print(f"[realtime] dry-run request preview {output_path}")
            print(f"[realtime] append events {append_count}")
        else:
            print(f"[realtime] output {output_path}")
            if result.get("responseAudioPath"):
                print(f"[realtime] reply audio {result['responseAudioPath']}")
            print(f"[realtime] user transcript: {result['summary'].get('userTranscript', '')}")
            print(f"[realtime] assistant text: {result['summary'].get('assistantText', '')}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[realtime-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
