#!/usr/bin/env python3
"""Mira Light Windows Full-Duplex Voice Conversation (对话专用入口).

This is a streamlined entry point optimized for Windows portable deployments
with a strict < 600ms latency target. It uses StepFun StepAudio 2.5 Realtime
via WebSocket for true full-duplex voice conversation.

Key differences from mira_stepfun_realtime_voice_actions.py:
- No hardware action routing (pure conversation focus)
- Aggressive low-latency audio parameters
- Simplified startup with automatic Bridge detection
- Built-in latency measurement and reporting

Usage:
    python -m scripts.mira_windows_full_duplex_voice
    python -m scripts.mira_windows_full_duplex_voice --voice wenrounansheng
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
import time
from typing import Any

# Auto-activate global StepFun API key fallback (env -> hardcoded).
# Must import BEFORE stepfun_realtime_voice so the monkey-patch applies.
import stepfun_api_key_manager  # noqa: F401

from stepfun_realtime_voice import (
    DEFAULT_OUTPUT_SAMPLE_RATE,
    DEFAULT_PROXY_URL,
    DEFAULT_REALTIME_ENDPOINT,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_VOICE,
    build_auth_headers,
    build_realtime_url,
    build_session_update_event,
    resolve_api_key,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / "runtime" / "windows-full-duplex-voice"
DEFAULT_INPUT_SAMPLE_RATE = 24000
DEFAULT_CHUNK_MS = 20
DEFAULT_WEBSOCKET_PING_INTERVAL = 10.0
DEFAULT_WEBSOCKET_PING_TIMEOUT = 5.0


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")


def write_jsonl(path: Path, obj: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def decode_audio_delta(event: dict[str, Any]) -> bytes | None:
    if str(event.get("type") or "") != "response.audio.delta":
        return None
    delta = event.get("delta") or event.get("audio") or ""
    if not delta:
        return None
    try:
        return base64.b64decode(delta)
    except Exception:
        return None


def display_update_for_event(event: dict[str, Any]) -> dict[str, str] | None:
    """Extract console-friendly text update from realtime events."""
    event_type = str(event.get("type") or "")

    if event_type == "conversation.item.input_audio_transcription.completed":
        text = _clean_text(event.get("transcript"))
        return {"role": "user", "text": text} if text else None

    if event_type == "response.audio_transcript.done":
        text = _clean_text(event.get("transcript"))
        return {"role": "assistant", "text": text} if text else None

    if event_type in {"response.text.done", "response.output_text.done"}:
        text = _clean_text(event.get("text"))
        return {"role": "assistant", "text": text} if text else None

    if event_type == "error" or "error" in event:
        text = _clean_text(event.get("error") or event)
        return {"role": "error", "text": text} if text else None

    return None


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def keepalive_seconds_or_none(value: Any) -> float | None:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return seconds


def default_input_device() -> str:
    return (
        os.environ.get("MIRA_LIGHT_INPUT_DEVICE")
        or os.environ.get("MIRA_LIGHT_WINDOWS_MIC_DEVICE")
        or os.environ.get("MIRA_LIGHT_MIC_DEVICE")
        or "default"
    )


def _resolve_best_mic() -> int | None:
    """Auto-select the best real microphone on Windows."""
    try:
        from audio_noise_suppressor import resolve_best_mic_index
        return resolve_best_mic_index(prefer_real=True)
    except Exception:
        return None


async def run_conversation_async(args: argparse.Namespace) -> dict[str, Any]:
    """Run a full-duplex voice conversation session."""
    try:
        import sounddevice as sd
        import websockets
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing realtime audio dependencies. "
            "Run: pip install sounddevice websockets"
        ) from exc

    # --- Vision understanding engine (optional, graceful if unavailable) ---
    vision_engine = None
    tracker = None
    if not getattr(args, "no_vision", False):
        try:
            from mira_vision_context import start_vision_engine, stop_vision_engine
            from person_tracker import PersonTracker

            tracker = PersonTracker(camera_index=getattr(args, "camera_index", 0), profile="low")
            tracker.start()
            from mira_vision_context import set_frame_provider
            set_frame_provider(tracker.get_latest_frame)
            vision_engine = start_vision_engine()
            if vision_engine:
                print(f"[vision] multimodal understanding active: {vision_engine.model}")
            else:
                print("[vision] disabled (no API key or MIRA_VISION_ENABLED=0)")
        except Exception as exc:
            print(f"[vision] unavailable: {exc}")
            vision_engine = None

    session_dir = Path(args.runtime_dir).expanduser() / timestamp_slug()
    session_dir.mkdir(parents=True, exist_ok=True)
    events_path = session_dir / "events.jsonl"
    session_path = session_dir / "session.json"

    api_key = resolve_api_key(args.api_key)
    url = build_realtime_url(args.endpoint, args.model)
    headers = build_auth_headers(api_key)

    # --- Latency measurement state ---
    latency_stats = {
        "firstUserSpeechStart": None,
        "firstAssistantResponseStart": None,
        "firstAudioDeltaReceived": None,
        "turnAroundMs": None,
        "audioToAudioMs": None,
    }

    # --- Audio queue and control ---
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
    stop_event = asyncio.Event()
    counters = {"events": 0, "audioChunksSent": 0, "audioChunksPlayed": 0}
    last_display_text = {"user": "", "assistant": "", "error": ""}

    # --- WebSocket connection kwargs ---
    connect_kwargs: dict[str, Any] = {
        "ping_interval": keepalive_seconds_or_none(args.websocket_ping_interval),
        "ping_timeout": keepalive_seconds_or_none(args.websocket_ping_timeout),
    }
    if args.proxy_url:
        connect_kwargs["proxy"] = args.proxy_url

    # --- Resolve input device ---
    input_device = None if args.input_device == "default" else args.input_device
    if input_device is None:
        best_idx = _resolve_best_mic()
        if best_idx is not None:
            try:
                dev_name = sd.query_devices(best_idx).get("name", "?")
                print(f"[mic] auto-selected: [{best_idx}] {dev_name}")
                input_device = best_idx
            except Exception:
                pass

    # --- Audio streams ---
    input_blocksize = max(160, int(int(args.input_sample_rate) * int(args.chunk_ms) / 1000))
    output_stream = None
    if not args.no_play:
        output_stream = sd.RawOutputStream(
            samplerate=int(args.output_sample_rate),
            channels=1,
            dtype="int16",
        )

    loop = asyncio.get_running_loop()

    def enqueue_audio(pcm: bytes) -> None:
        if stop_event.is_set():
            return
        try:
            audio_queue.put_nowait(pcm)
        except asyncio.QueueFull:
            pass

    def input_callback(indata: bytes, frames: int, time_info: Any, status: Any) -> None:  # noqa: ARG001
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        loop.call_soon_threadsafe(enqueue_audio, bytes(indata))

    # callback must be passed in constructor, not assigned afterwards
    input_stream = sd.RawInputStream(
        samplerate=int(args.input_sample_rate),
        blocksize=input_blocksize,
        device=input_device,
        channels=1,
        dtype="int16",
        callback=input_callback,
    )

    # --- WebSocket connection with fallback ---
    try:
        connection = websockets.connect(url, additional_headers=headers, **connect_kwargs)
    except TypeError:
        connect_kwargs_basic = dict(connect_kwargs)
        connect_kwargs_basic.pop("ping_interval", None)
        connect_kwargs_basic.pop("ping_timeout", None)
        try:
            connection = websockets.connect(url, additional_headers=headers, **connect_kwargs_basic)
        except TypeError:
            connection = websockets.connect(url, extra_headers=headers, **connect_kwargs_basic)

    async with connection as websocket:
        await websocket.send(
            json.dumps(build_session_update_event(voice=args.voice), ensure_ascii=False)
        )

        print("=" * 50)
        print("  Mira Light - Full-Duplex Voice Conversation")
        print("=" * 50)
        print(f"Session:  {session_dir}")
        print(f"Model:    {args.model}")
        print(f"Voice:    {args.voice}")
        print(f"Chunk:    {args.chunk_ms}ms")
        print(f"Latency:  target < 600ms")
        print(f"Mode:     {'playback ON' if not args.no_play else 'playback OFF'}")
        print("-" * 50)
        print("Speak naturally. Mary will respond in real time.")
        print("Press Ctrl+C to stop.")
        print()

        async def send_audio_loop() -> None:
            while not stop_event.is_set():
                pcm = await audio_queue.get()
                await websocket.send(
                    json.dumps(
                        {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(pcm).decode("ascii"),
                        }
                    )
                )
                counters["audioChunksSent"] += 1

        async def receive_loop() -> None:
            while not stop_event.is_set():
                raw = await websocket.recv()
                event = json.loads(raw)
                counters["events"] += 1
                write_jsonl(events_path, event)

                # Latency tracking
                event_type = str(event.get("type") or "")
                if event_type == "input_audio_buffer.speech_started":
                    if latency_stats["firstUserSpeechStart"] is None:
                        latency_stats["firstUserSpeechStart"] = time.perf_counter()
                elif event_type == "response.audio_transcript.delta":
                    if latency_stats["firstAssistantResponseStart"] is None:
                        latency_stats["firstAssistantResponseStart"] = time.perf_counter()
                        if latency_stats["firstUserSpeechStart"] is not None:
                            latency_stats["turnAroundMs"] = round(
                                (latency_stats["firstAssistantResponseStart"] - latency_stats["firstUserSpeechStart"]) * 1000, 1
                            )
                elif event_type == "response.audio.delta":
                    if latency_stats["firstAudioDeltaReceived"] is None:
                        latency_stats["firstAudioDeltaReceived"] = time.perf_counter()
                        if latency_stats["firstUserSpeechStart"] is not None:
                            latency_stats["audioToAudioMs"] = round(
                                (latency_stats["firstAudioDeltaReceived"] - latency_stats["firstUserSpeechStart"]) * 1000, 1
                            )

                # Display updates
                display_update = display_update_for_event(event)
                if display_update:
                    role = display_update["role"]
                    text = display_update["text"]
                    if text != last_display_text.get(role):
                        last_display_text[role] = text
                        label = {"assistant": "Mary"}.get(role, role)
                        # Print latency on first assistant response
                        extra = ""
                        if role == "assistant" and latency_stats["turnAroundMs"] is not None:
                            extra = f" [TTFB: {latency_stats['turnAroundMs']}ms]"
                        print(f"[{label}] {text}{extra}", flush=True)

                # NOTE: Do NOT send input_audio_buffer.commit when server_vad is enabled.
                # The server auto-commits on speech_stopped. Manual commit causes
                # "commit when server vad" errors.

                # Play audio delta
                pcm = decode_audio_delta(event)
                if pcm and output_stream is not None:
                    await asyncio.to_thread(output_stream.write, pcm)
                    counters["audioChunksPlayed"] += 1

        with input_stream:
            if output_stream is None:
                send_task = asyncio.create_task(send_audio_loop())
                recv_task = asyncio.create_task(receive_loop())
                try:
                    await asyncio.gather(send_task, recv_task)
                finally:
                    stop_event.set()
                    send_task.cancel()
                    recv_task.cancel()
            else:
                with output_stream:
                    send_task = asyncio.create_task(send_audio_loop())
                    recv_task = asyncio.create_task(receive_loop())
                    try:
                        await asyncio.gather(send_task, recv_task)
                    finally:
                        stop_event.set()
                        send_task.cancel()
                        recv_task.cancel()

    summary = {
        "ok": True,
        "savedAt": datetime.now().isoformat(timespec="seconds"),
        "sessionDir": str(session_dir.resolve()),
        "eventsPath": str(events_path.resolve()),
        "model": args.model,
        "voice": args.voice,
        "latencyStats": {k: v for k, v in latency_stats.items() if v is not None},
        "counters": counters,
    }
    session_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def run_conversation(args: argparse.Namespace) -> dict[str, Any]:
    return asyncio.run(run_conversation_async(args))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mira Light Windows Full-Duplex Voice Conversation (对话专用)"
    )
    parser.add_argument("--api-key", default="")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_REALTIME_ENDPOINT", DEFAULT_REALTIME_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_REALTIME_MODEL", DEFAULT_REALTIME_MODEL))
    parser.add_argument("--voice", default=os.environ.get("STEPFUN_REALTIME_VOICE", DEFAULT_VOICE))
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument(
        "--websocket-ping-interval",
        type=float,
        default=float(os.environ.get("STEPFUN_REALTIME_WEBSOCKET_PING_INTERVAL", DEFAULT_WEBSOCKET_PING_INTERVAL)),
    )
    parser.add_argument(
        "--websocket-ping-timeout",
        type=float,
        default=float(os.environ.get("STEPFUN_REALTIME_WEBSOCKET_PING_TIMEOUT", DEFAULT_WEBSOCKET_PING_TIMEOUT)),
    )
    parser.add_argument("--input-device", default=default_input_device())
    parser.add_argument("--input-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_INPUT_SAMPLE_RATE", DEFAULT_INPUT_SAMPLE_RATE)))
    parser.add_argument("--output-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE", DEFAULT_OUTPUT_SAMPLE_RATE)))
    parser.add_argument("--chunk-ms", type=int, default=int(os.environ.get("STEPFUN_REALTIME_MIC_CHUNK_MS", DEFAULT_CHUNK_MS)))
    parser.add_argument("--seconds", type=float, default=0.0)
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-vision", action="store_true", help="Disable multimodal vision understanding")
    parser.add_argument("--camera-index", type=int, default=0, help="Camera index for vision (default: 0)")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run:
            print("[dry-run] Configuration:")
            print(f"  endpoint: {args.endpoint}")
            print(f"  model:    {args.model}")
            print(f"  voice:    {args.voice}")
            print(f"  chunk:    {args.chunk_ms}ms")
            print(f"  device:   {args.input_device}")
            print(f"  api-key:  {'set' if resolve_api_key(args.api_key) else 'missing'}")
            return 0

        result = run_conversation(args)
        print(f"\nSession saved: {result['sessionDir']}")
        if result.get("latencyStats"):
            print(f"Latency stats: {json.dumps(result['latencyStats'], ensure_ascii=False)}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye.")
        return 130
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    finally:
        # Clean up vision engine and camera tracker if they were started
        try:
            from mira_vision_context import stop_vision_engine
            stop_vision_engine()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
