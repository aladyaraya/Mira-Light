#!/usr/bin/env python3
"""Mira Light Console Voice - Realtime voice control for Unified Director Console.

This script integrates StepFun realtime voice ASR with the Unified Director Console,
routing voice commands to console APIs instead of the hardware bridge.

It reuses the existing realtime voice infrastructure from Mira-Light-Voice-Full-Ready
and plugs in ConsoleVoiceOrchestrator from voice_console_adapter.py.

Usage:
    python mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790
    python mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790 --no-tts-feedback
    python mira_stepfun_console_voice.py --list-commands
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
from typing import Any

# ── Add voice system scripts to path ──
VOICE_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "Mira-Light-Voice-Full-Ready" / "scripts"
if str(VOICE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(VOICE_SCRIPTS_DIR))

# ── Add console dir to path for adapter ──
CONSOLE_DIR = Path(__file__).resolve().parent
if str(CONSOLE_DIR) not in sys.path:
    sys.path.insert(0, str(CONSOLE_DIR))

# Reuse existing voice infrastructure
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
from mira_stepfun_realtime_voice_actions import (
    timestamp_slug,
    pcm16_bytes_from_float32,
    decode_audio_delta,
    _clean_display_text,
    _first_content_text,
    display_update_for_event,
    write_jsonl,
    build_live_session_preview,
    voice_state_actions_enabled,
    build_websocket_connect_kwargs,
    env_flag,
    default_input_device,
    keepalive_seconds_or_none,
    planner_reply_text_from_action,
    _speak_planner_reply_async,
)

# phase_for_realtime_event and extract_final_transcript are in mira_realtime_action_orchestrator
from mira_realtime_action_orchestrator import phase_for_realtime_event, extract_final_transcript

# Import console adapter
from voice_console_adapter import (
    ConsoleVoiceOrchestrator,
    ConsoleActionConfig,
    DEFAULT_CONSOLE_URL,
    DEFAULT_BRIDGE_URL,
    DEFAULT_ACTION_TIMEOUT_SECONDS,
    build_console_action_orchestrator,
    CONSOLE_COMMAND_ALIASES,
    SCENE_COMMAND_ALIASES,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / "runtime" / "voice-console"
DEFAULT_INPUT_SAMPLE_RATE = 24000
DEFAULT_CHUNK_MS = 40
DEFAULT_SESSION_SECONDS = 0.0
DEFAULT_WEBSOCKET_PING_INTERVAL = 20.0
DEFAULT_WEBSOCKET_PING_TIMEOUT = 10.0


# ── Console-specific transcript dispatch ──

async def _dispatch_console_transcript_async(
    orchestrator: ConsoleVoiceOrchestrator,
    transcript: str,
    *,
    actions_path: Path,
    planner_speech_player: Any | None = None,
    speak_planner_reply: bool = False,
    planner_reply_voice: str = "tts",
    planner_reply_wait: bool = False,
    last_planner_reply: dict[str, str] | None = None,
) -> None:
    """Dispatch transcript to console orchestrator and optionally speak reply."""
    try:
        action = await asyncio.to_thread(orchestrator.dispatch_transcript, transcript)
    except Exception as exc:  # noqa: BLE001
        action = {"kind": "console-error", "transcript": transcript, "error": str(exc)}
    if action:
        write_jsonl(actions_path, action)
        kind = action.get("kind", "")
        if kind == "console-action":
            cmd = action.get("command", "")
            print(f"[console-action] {cmd} transcript='{transcript}'")
        elif kind == "console-skip":
            print(f"[console-skip] {action.get('reason', '')} transcript='{transcript}'")
        elif kind == "console-error":
            print(f"[console-error] {action.get('error', '')} transcript='{transcript}'", file=sys.stderr)
        else:
            print(f"[action] {kind} transcript='{transcript}'")

        if speak_planner_reply and planner_speech_player is not None:
            await _speak_planner_reply_async(
                action,
                transcript,
                actions_path=actions_path,
                audio_player=planner_speech_player,
                voice=planner_reply_voice,
                wait=planner_reply_wait,
                last_reply_text=last_planner_reply if last_planner_reply is not None else {},
            )


# ── Live session with console routing ──

async def run_console_voice_session_async(args: argparse.Namespace) -> dict[str, Any]:
    """Run a live voice session that routes commands to the console API."""
    try:
        import sounddevice as sd
        import websockets
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing realtime audio dependencies. Run Setup-Mira-Light-Windows-Voice.ps1 first."
        ) from exc

    session_dir = Path(args.runtime_dir).expanduser() / timestamp_slug()
    session_dir.mkdir(parents=True, exist_ok=True)
    events_path = session_dir / "events.jsonl"
    actions_path = session_dir / "actions.jsonl"
    session_path = session_dir / "session.json"

    api_key = resolve_api_key(args.api_key)
    url = build_realtime_url(args.endpoint, args.model)
    headers = build_auth_headers(api_key)

    # Build console orchestrator instead of bridge orchestrator
    orchestrator = build_console_action_orchestrator(
        console_url=args.console_url,
        bridge_url=args.bridge_url,
        voice_state_enabled=not args.no_voice_state_actions,
        semantic_actions_enabled=not args.no_semantic_actions,
        tts_feedback_enabled=not args.no_tts_feedback,
        action_timeout_seconds=args.action_timeout_seconds,
    )

    planner_speech_player = None
    if args.speak_planner_reply:
        from mira_light_audio import AudioCuePlayer
        planner_speech_player = AudioCuePlayer(dry_run=bool(args.no_play))

    # Noise suppressor
    noise_suppressor = None
    denoise_enabled = not args.no_denoise
    if denoise_enabled:
        try:
            from audio_noise_suppressor import NoiseSuppressor
            noise_suppressor = NoiseSuppressor(
                sample_rate=int(args.input_sample_rate),
                highpass_cutoff=80.0,
                spectral_gate_strength=1.5,
                spectral_gate_floor_db=-40.0,
                agc_target_rms=0.04,
                agc_max_gain_db=12.0,
            )
            print("[denoise] noise suppression enabled")
        except ImportError:
            print("[denoise] not available, skipping", file=sys.stderr)

    # Mic device selection
    input_device = None if args.input_device == "default" else args.input_device
    if input_device is None and denoise_enabled:
        try:
            from audio_noise_suppressor import resolve_best_mic_index
            best_idx = resolve_best_mic_index(prefer_real=True)
            if best_idx is not None:
                import sounddevice as _sd
                dev_name = _sd.query_devices(best_idx).get("name", "?")
                print(f"[mic] auto-selected: [{best_idx}] {dev_name}")
                input_device = best_idx
        except Exception as exc:
            print(f"[mic] auto-select failed: {exc}", file=sys.stderr)

    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
    stop_event = asyncio.Event()
    semantic_tasks: set[asyncio.Task] = set()
    counters = {"events": 0, "audioChunksSent": 0, "audioChunksDropped": 0, "audioChunksPlayed": 0, "actions": 0}
    last_display_text = {"user": "", "assistant": "", "error": ""}
    last_planner_reply = {"text": ""}

    connect_kwargs = build_websocket_connect_kwargs(args)
    try:
        connection = websockets.connect(url, additional_headers=headers, **connect_kwargs)
    except TypeError:
        connect_kwargs_basic: dict[str, Any] = dict(connect_kwargs)
        connect_kwargs_basic.pop("ping_interval", None)
        try:
            connection = websockets.connect(url, additional_headers=headers, **connect_kwargs_basic)
        except TypeError:
            connection = websockets.connect(url, extra_headers=headers, **connect_kwargs_basic)

    loop = asyncio.get_running_loop()

    def enqueue_audio(pcm: bytes) -> None:
        if stop_event.is_set():
            return
        try:
            audio_queue.put_nowait(pcm)
        except asyncio.QueueFull:
            counters["audioChunksDropped"] += 1

    def input_callback(indata: bytes, frames: int, time_info: Any, status: Any) -> None:  # noqa: ARG001
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        raw = bytes(indata)
        if noise_suppressor is not None:
            try:
                raw = noise_suppressor.process(raw)
            except Exception:
                pass
        loop.call_soon_threadsafe(enqueue_audio, raw)

    input_blocksize = max(160, int(int(args.input_sample_rate) * int(args.chunk_ms) / 1000))
    input_stream = sd.RawInputStream(
        samplerate=int(args.input_sample_rate),
        blocksize=input_blocksize,
        device=input_device,
        channels=1,
        dtype="int16",
        callback=input_callback,
    )
    output_stream = None
    if not args.no_play:
        output_stream = sd.RawOutputStream(
            samplerate=int(args.output_sample_rate),
            channels=1,
            dtype="int16",
        )

    async with connection as websocket:
        await websocket.send(json.dumps(build_session_update_event(voice=args.voice), ensure_ascii=False))
        print("")
        print("=" * 50)
        print("  Mira Light Voice Console")
        print("  Voice Control for Unified Director")
        print("=" * 50)
        print("")
        print(f"Session:  {session_dir}")
        print(f"Console:  {args.console_url}")
        print(f"Bridge:   {args.bridge_url} (TTS feedback)")
        print(f"Semantic: {not args.no_semantic_actions}")
        print(f"Voice states: {not args.no_voice_state_actions}")
        print(f"TTS feedback: {not args.no_tts_feedback}")
        print(f"Planner speech: {bool(args.speak_planner_reply)}")
        print("")
        print("Speak naturally to control the console.")
        print("Examples: '起床', '拍照', '开始示教', '紧急停止'")
        print("Press Ctrl+C to stop.")
        print("")

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

                display_update = display_update_for_event(event)
                if display_update:
                    role = display_update["role"]
                    text = display_update["text"]
                    if text != last_display_text.get(role):
                        last_display_text[role] = text
                        label = {"assistant": "Mira"}.get(role, role)
                        print(f"[{label}] {text}", flush=True)

                # Voice phase actions (listening/thinking/answer) -> director quick actions
                phase = phase_for_realtime_event(event)
                if phase:
                    action = orchestrator.dispatch_voice_phase(phase)
                    if action:
                        counters["actions"] += 1
                        write_jsonl(actions_path, action)
                        print(f"[voice-state] {action.get('kind')} phase={phase}", flush=True)

                # Transcript -> console semantic actions
                transcript = extract_final_transcript(event)
                if transcript and not args.no_semantic_actions:
                    task = asyncio.create_task(
                        _dispatch_console_transcript_async(
                            orchestrator,
                            transcript,
                            actions_path=actions_path,
                            planner_speech_player=planner_speech_player,
                            speak_planner_reply=bool(args.speak_planner_reply),
                            planner_reply_voice=args.planner_reply_voice,
                            planner_reply_wait=bool(args.planner_reply_wait),
                            last_planner_reply=last_planner_reply,
                        )
                    )
                    semantic_tasks.add(task)
                    task.add_done_callback(semantic_tasks.discard)

                if str(event.get("type") or "") == "input_audio_buffer.speech_stopped":
                    await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    if args.manual_response_create_on_speech_stop:
                        await websocket.send(
                            json.dumps({"type": "response.create", "response": {"modalities": ["text", "audio"]}})
                        )

                pcm = decode_audio_delta(event)
                if pcm and output_stream is not None:
                    await asyncio.to_thread(output_stream.write, pcm)
                    counters["audioChunksPlayed"] += 1

        with input_stream:
            if output_stream is None:
                send_task = asyncio.create_task(send_audio_loop())
                recv_task = asyncio.create_task(receive_loop())
                try:
                    if args.seconds and float(args.seconds) > 0:
                        await asyncio.sleep(float(args.seconds))
                        stop_event.set()
                    else:
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
                        if args.seconds and float(args.seconds) > 0:
                            await asyncio.sleep(float(args.seconds))
                            stop_event.set()
                        else:
                            await asyncio.gather(send_task, recv_task)
                    finally:
                        stop_event.set()
                        send_task.cancel()
                        recv_task.cancel()

        if semantic_tasks:
            await asyncio.gather(*semantic_tasks, return_exceptions=True)

    summary = {
        "ok": True,
        "savedAt": datetime.now().isoformat(timespec="seconds"),
        "sessionDir": str(session_dir.resolve()),
        "eventsPath": str(events_path.resolve()),
        "actionsPath": str(actions_path.resolve()),
        "model": args.model,
        "consoleUrl": args.console_url,
        "bridgeUrl": args.bridge_url,
        "counters": counters,
    }
    session_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def run_console_voice_session(args: argparse.Namespace) -> dict[str, Any]:
    return asyncio.run(run_console_voice_session_async(args))


# ── CLI ──

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mira Light Console Voice - Realtime voice control for Unified Director Console"
    )
    # StepFun API
    parser.add_argument("--api-key", default="")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_REALTIME_ENDPOINT", DEFAULT_REALTIME_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_REALTIME_MODEL", DEFAULT_REALTIME_MODEL))
    parser.add_argument("--voice", default=os.environ.get("STEPFUN_REALTIME_VOICE", DEFAULT_VOICE))
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--websocket-ping-interval", type=float, default=DEFAULT_WEBSOCKET_PING_INTERVAL)
    parser.add_argument("--websocket-ping-timeout", type=float, default=DEFAULT_WEBSOCKET_PING_TIMEOUT)

    # Audio
    parser.add_argument("--input-device", default=default_input_device())
    parser.add_argument("--input-sample-rate", type=int, default=DEFAULT_INPUT_SAMPLE_RATE)
    parser.add_argument("--output-sample-rate", type=int, default=DEFAULT_OUTPUT_SAMPLE_RATE)
    parser.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    parser.add_argument("--seconds", type=float, default=DEFAULT_SESSION_SECONDS)
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--no-denoise", action="store_true")

    # Console / Bridge
    parser.add_argument("--console-url", default=os.environ.get("MIRA_LIGHT_CONSOLE_URL", DEFAULT_CONSOLE_URL))
    parser.add_argument("--bridge-url", default=os.environ.get("MIRA_LIGHT_BRIDGE_URL", DEFAULT_BRIDGE_URL))
    parser.add_argument("--action-timeout-seconds", type=int, default=DEFAULT_ACTION_TIMEOUT_SECONDS)

    # Actions
    parser.add_argument("--no-voice-state-actions", action="store_true")
    parser.add_argument("--no-semantic-actions", action="store_true")
    parser.add_argument("--no-tts-feedback", action="store_true")
    parser.add_argument("--speak-planner-reply", action="store_true", default=env_flag("MIRA_LIGHT_SPEAK_PLANNER_REPLY", False))
    parser.add_argument("--no-speak-planner-reply", dest="speak_planner_reply", action="store_false")
    parser.add_argument("--planner-reply-voice", default=os.environ.get("MIRA_LIGHT_PLANNER_REPLY_VOICE", "tts"))
    parser.add_argument("--planner-reply-wait", action="store_true", default=env_flag("MIRA_LIGHT_PLANNER_REPLY_WAIT", False))
    parser.add_argument("--no-planner-reply-wait", dest="planner_reply_wait", action="store_false")
    parser.add_argument("--manual-response-create-on-speech-stop", action="store_true")

    # Runtime
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR))

    # Utility
    parser.add_argument("--list-commands", action="store_true", help="List all available voice commands")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")

    return parser.parse_args(argv)


def list_commands() -> None:
    print("=== Mira Light Voice Console Commands ===\n")
    print("--- Scene Commands ---")
    for name, aliases in sorted(SCENE_COMMAND_ALIASES.items()):
        print(f"  {name}: {', '.join(aliases)}")
    print("\n--- Console Feature Commands ---")
    for name, aliases in sorted(CONSOLE_COMMAND_ALIASES.items()):
        print(f"  {name}: {', '.join(aliases)}")
    print("\n--- Voice State Actions ---")
    print("  listening  -> quick-action/voice_motion_listening")
    print("  thinking   -> quick-action/voice_motion_thinking")
    print("  answer     -> quick-action/voice_motion_answer")
    print("\nTip: Speak naturally in Chinese. Local keyword matching provides")
    print("     zero-latency response; LLM handles ambiguous commands.")


def main() -> int:
    args = parse_args()

    if args.list_commands:
        list_commands()
        return 0

    try:
        if args.dry_run:
            # Build a preview without running
            preview = {
                "ok": True,
                "dryRun": True,
                "consoleUrl": args.console_url,
                "bridgeUrl": args.bridge_url,
                "model": args.model,
                "semanticActions": not args.no_semantic_actions,
                "voiceStateActions": not args.no_voice_state_actions,
                "ttsFeedback": not args.no_tts_feedback,
            }
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return 0

        result = run_console_voice_session(args)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\nSession saved: {result['sessionDir']}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        return 130
    except Exception as exc:  # noqa: BLE001
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[console-voice-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
