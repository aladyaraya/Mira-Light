#!/usr/bin/env python3
"""StepFun StepAudio ASR client for the Mira Light Windows voice loop.

This is the second local loop in the Windows voice stack:

WAV file -> StepFun ASR/STT -> transcript JSON

The ASR layer only turns audio into text. Mary/Mira personality is carried as
metadata for the next LLM semantic layer, not injected into recognition logic.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Iterable
import wave


DEFAULT_ASR_ENDPOINT = "https://api.stepfun.com/v1/audio/asr/sse"
DEFAULT_MODEL = "stepaudio-2.5-asr"
DEFAULT_LANGUAGE = "zh"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_HOTWORDS = [
    "Mira",
    "Mira Light",
    "米拉",
    "Mary",
    "麦瑞",
    "Mira-Light",
    "场景音频",
    "语音交互",
    "动作库",
    "唤醒",
    "陪伴",
]
MARY_PERSONA_CONTEXT = {
    "assistantName": "Mary",
    "deviceName": "Mira Light",
    "voiceRole": "warm companion, curious desk light, gentle emotional presence",
    "styleHints": ["warm", "soft", "curious", "brief", "companion-like"],
    "note": "ASR only returns text; Mary personality should be applied by the LLM semantic layer after transcription.",
}

SsePoster = Callable[[str, Any], Iterable[str | bytes]]


def normalize_hotwords(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        raw_items: Iterable[str] = []
    elif isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = value

    items: list[str] = []
    for raw in raw_items:
        text = str(raw).strip()
        if text and text not in items:
            items.append(text)
    return items


def merge_hotwords(extra_hotwords: str | Iterable[str] | None = None) -> list[str]:
    return normalize_hotwords([*DEFAULT_HOTWORDS, *normalize_hotwords(extra_hotwords)])


def _wav_format(audio_path: Path) -> dict[str, Any]:
    with wave.open(str(audio_path), "rb") as wav:
        return {
            "type": "wav",
            "rate": int(wav.getframerate()),
            "bits": int(wav.getsampwidth() * 8),
            "channel": int(wav.getnchannels()),
        }


def detect_audio_format(audio_path: Path) -> dict[str, Any]:
    suffix = audio_path.suffix.lower().lstrip(".")
    if suffix == "wav":
        return _wav_format(audio_path)
    if suffix in {"mp3", "ogg", "opus", "aac", "flac", "m4a"}:
        return {"type": suffix}
    if suffix == "pcm":
        return {"type": "pcm", "codec": "pcm_s16le", "rate": 16000, "bits": 16, "channel": 1}
    raise RuntimeError(f"Unsupported audio format: {audio_path.suffix or '<none>'}")


def build_asr_payload(
    audio_path: str | Path,
    *,
    model: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
    hotwords: str | Iterable[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(audio_path).expanduser().resolve()
    if not path.exists():
        raise RuntimeError(f"Audio file not found: {path}")
    if not path.is_file():
        raise RuntimeError(f"Audio path is not a file: {path}")

    encoded_audio = base64.b64encode(path.read_bytes()).decode("ascii")
    audio_format = detect_audio_format(path)
    audio_meta = {
        "path": str(path),
        "format": audio_format["type"],
        "bytes": path.stat().st_size,
        "sampleRate": audio_format.get("rate"),
        "bits": audio_format.get("bits"),
        "channels": audio_format.get("channel"),
    }
    payload = {
        "audio": {
            "data": encoded_audio,
            "input": {
                "format": audio_format,
                "transcription": {
                    "model": model,
                    "language": language,
                    "response_format": "json",
                    "hotwords": merge_hotwords(hotwords),
                },
            },
        }
    }
    return payload, audio_meta


def _flush_sse_event(event_name: str | None, data_lines: list[str]) -> dict[str, Any] | None:
    if not data_lines:
        return None
    raw_data = "\n".join(data_lines).strip()
    if not raw_data or raw_data == "[DONE]":
        return None
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError:
        payload = {"data": raw_data}
    if not isinstance(payload, dict):
        payload = {"data": payload}
    if event_name and "event" not in payload:
        payload["event"] = event_name
    return payload


def _extract_text(events: list[dict[str, Any]]) -> str:
    done_text = ""
    text_parts: list[str] = []
    for event in events:
        event_type = str(event.get("type") or event.get("event") or "")
        if event_type.endswith(".done") and isinstance(event.get("text"), str):
            done_text = event["text"].strip()
        elif isinstance(event.get("delta"), str):
            text_parts.append(event["delta"])
        elif isinstance(event.get("text"), str):
            text_parts.append(event["text"])
    return done_text or "".join(text_parts).strip()


def parse_sse_events(lines: Iterable[str | bytes]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    event_name: str | None = None
    data_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else str(raw_line)
        line = line.rstrip("\r\n")
        if line == "":
            payload = _flush_sse_event(event_name, data_lines)
            if payload is not None:
                events.append(payload)
            event_name = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if not separator:
            continue
        value = value[1:] if value.startswith(" ") else value
        if field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)

    payload = _flush_sse_event(event_name, data_lines)
    if payload is not None:
        events.append(payload)

    for event in events:
        event_type = str(event.get("type") or event.get("event") or "")
        if event_type == "error" or "error" in event:
            raise RuntimeError(f"StepFun ASR error event: {json.dumps(event, ensure_ascii=False)}")

    return {
        "text": _extract_text(events),
        "eventCount": len(events),
        "events": events,
    }


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


def post_sse_request(
    url: str,
    *,
    headers: dict[str, str],
    json_payload: dict[str, Any],
    timeout_seconds: int,
) -> Iterable[str | bytes]:
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing requests. Run Setup-Mira-Light-Windows-Voice.ps1 first.") from exc

    proxy_url = os.environ.get("STEPFUN_PROXY_URL", "").strip()
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    response = requests.post(
        url,
        headers=headers,
        json=json_payload,
        stream=True,
        timeout=timeout_seconds,
        proxies=proxies,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"StepFun ASR HTTP {response.status_code}: {response.text}")
    return response.iter_lines(decode_unicode=True)


def transcribe_audio_file(
    audio_path: str | Path,
    *,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ASR_ENDPOINT,
    model: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
    hotwords: str | Iterable[str] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    post_sse: Callable[..., Iterable[str | bytes]] = post_sse_request,
) -> dict[str, Any]:
    resolved_api_key = resolve_api_key(api_key)
    payload, audio_meta = build_asr_payload(
        audio_path,
        model=model,
        language=language,
        hotwords=hotwords,
    )
    headers = {
        "Authorization": f"Bearer {resolved_api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    lines = post_sse(
        endpoint,
        headers=headers,
        json_payload=payload,
        timeout_seconds=int(timeout_seconds),
    )
    parsed = parse_sse_events(lines)
    return {
        "ok": True,
        "dryRun": False,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": "stepfun",
        "endpoint": endpoint,
        "model": model,
        "language": language,
        "audio": audio_meta,
        "text": parsed["text"],
        "eventCount": parsed["eventCount"],
        "events": parsed["events"],
        "hotwords": payload["audio"]["input"]["transcription"]["hotwords"],
        "personaContext": MARY_PERSONA_CONTEXT,
    }


def build_dry_run_result(
    audio_path: str | Path,
    *,
    endpoint: str = DEFAULT_ASR_ENDPOINT,
    model: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
    hotwords: str | Iterable[str] | None = None,
) -> dict[str, Any]:
    payload, audio_meta = build_asr_payload(
        audio_path,
        model=model,
        language=language,
        hotwords=hotwords,
    )
    body_preview = json.loads(json.dumps(payload, ensure_ascii=False))
    data = body_preview["audio"].get("data") or ""
    body_preview["audio"]["data"] = "<base64 omitted>"
    body_preview["audio"]["dataLength"] = len(data)
    return {
        "ok": True,
        "dryRun": True,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": "stepfun",
        "endpoint": endpoint,
        "model": model,
        "language": language,
        "audio": audio_meta,
        "text": "",
        "eventCount": 0,
        "events": [],
        "hotwords": payload["audio"]["input"]["transcription"]["hotwords"],
        "personaContext": MARY_PERSONA_CONTEXT,
        "request": {
            "method": "POST",
            "endpoint": endpoint,
            "headers": {
                "Authorization": "Bearer <STEPFUN_API_KEY>",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            "body": body_preview,
        },
        "next": "Set STEPFUN_API_KEY, then run without --dry-run to call StepFun ASR.",
    }


def default_output_path(audio_path: str | Path) -> Path:
    path = Path(audio_path).expanduser().resolve()
    return path.with_name("transcript.stepfun.json")


def write_transcript_outputs(result: dict[str, Any], output_path: str | Path) -> tuple[Path, Path]:
    json_path = Path(output_path).expanduser().resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    txt_path = json_path.with_suffix(".txt")
    txt_path.write_text(str(result.get("text") or "") + "\n", encoding="utf-8")
    return json_path, txt_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a Mira Light audio file to StepFun StepAudio ASR.")
    parser.add_argument("--audio", required=True, help="Input audio path, normally runtime/.../input.wav.")
    parser.add_argument("--output", help="Output transcript JSON path. Defaults to transcript.stepfun.json next to audio.")
    parser.add_argument("--api-key", help="StepFun API key. Defaults to STEPFUN_API_KEY or STEP_API_KEY.")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_ASR_ENDPOINT", DEFAULT_ASR_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_ASR_MODEL", DEFAULT_MODEL))
    parser.add_argument("--language", default=os.environ.get("STEPFUN_ASR_LANGUAGE", DEFAULT_LANGUAGE))
    parser.add_argument("--hotwords", default=os.environ.get("MIRA_LIGHT_ASR_HOTWORDS", ""))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.environ.get("STEPFUN_ASR_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)))
    parser.add_argument("--dry-run", action="store_true", help="Build and save a request preview without requiring an API key.")
    parser.add_argument("--json", action="store_true", help="Print only JSON result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run:
            result = build_dry_run_result(
                args.audio,
                endpoint=args.endpoint,
                model=args.model,
                language=args.language,
                hotwords=args.hotwords,
            )
        else:
            result = transcribe_audio_file(
                args.audio,
                api_key=args.api_key,
                endpoint=args.endpoint,
                model=args.model,
                language=args.language,
                hotwords=args.hotwords,
                timeout_seconds=args.timeout_seconds,
            )
        output = Path(args.output).expanduser() if args.output else default_output_path(args.audio)
        json_path, txt_path = write_transcript_outputs(result, output)
        result["outputPath"] = str(json_path)
        result["textPath"] = str(txt_path)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.dry_run:
            print(f"[asr] dry-run request preview {json_path}")
            print(f"[asr] audio base64 length {result['request']['body']['audio']['dataLength']}")
        else:
            print(f"[asr] text: {result['text']}")
            print(f"[asr] transcript {json_path}")
            print(f"[asr] text file {txt_path}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[asr-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
