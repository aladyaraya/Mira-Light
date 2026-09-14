#!/usr/bin/env python3
"""Live StepAudio realtime voice session with Mira Light action routing."""

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

from mira_config_env import prompt_file_status
from mira_runtime_memory import MiraRuntimeMemory

from mira_realtime_action_orchestrator import (
    DEFAULT_BRIDGE_URL,
    RealtimeActionConfig,
    RealtimeActionOrchestrator,
    extract_final_transcript,
    phase_for_realtime_event,
)
from stepfun_llm_planner import plan_from_text
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
DEFAULT_RUNTIME_DIR = ROOT / "runtime" / "stepfun-realtime-voice-actions"
DEFAULT_RUNTIME_MEMORY_FILE = ROOT / "runtime" / "mira-live-memory.json"
DEFAULT_INPUT_SAMPLE_RATE = 24000
DEFAULT_CHUNK_MS = 40
DEFAULT_SESSION_SECONDS = 0.0
DEFAULT_WEBSOCKET_PING_INTERVAL = 30.0
DEFAULT_WEBSOCKET_PING_TIMEOUT = 30.0
DEFAULT_WS_MAX_RETRIES = 3
DEFAULT_WS_RETRY_DELAY = 5.0


def realtime_playback_enabled(args: argparse.Namespace) -> bool:
    return not (
        bool(args.no_play)
        or bool(getattr(args, "no_realtime_playback", False))
        or bool(getattr(args, "planner_owns_reply", False))
    )


def planner_playback_enabled(args: argparse.Namespace) -> bool:
    return not (bool(args.no_play) or bool(getattr(args, "no_planner_playback", False)))


def validate_audio_routing(args: argparse.Namespace) -> None:
    """Prevent two independent TTS/playback paths from speaking at once."""
    if (
        bool(getattr(args, "speak_planner_reply", False))
        and planner_playback_enabled(args)
        and realtime_playback_enabled(args)
        and not bool(getattr(args, "planner_owns_reply", False))
    ):
        raise RuntimeError(
            "Audio routing conflict: realtime playback and planner playback are both enabled. "
            "Use --planner-owns-reply or --no-realtime-playback, or disable planner playback."
        )


def should_speak_planner_reply_action(action: dict[str, Any] | None) -> bool:
    """Return true when a semantic planner result should own Mira's spoken reply."""
    if not isinstance(action, dict):
        return False
    if not planner_reply_text_from_action(action):
        return False
    kind = str(action.get("kind") or "")
    if kind in {"semantic-action", "semantic-confirm", "semantic-override"}:
        return True
    if kind == "semantic-skip":
        return str(action.get("reason") or "") in {
            "none-action",
            "llm-generic-action-low-info",
            "llm-generic-action-low-confidence",
        }
    return False


def should_run_phase2_refinement(action: dict[str, Any] | None, *, llm_actions_for_ambiguous: bool = True) -> bool:
    """Only send unmatched Phase 1 transcripts into the slow LLM action brain."""
    if not isinstance(action, dict):
        return False
    if action.get("kind") != "semantic-skip":
        return False
    if action.get("reason") != "needs-llm-refinement":
        return False
    return bool(llm_actions_for_ambiguous)


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")


def pcm16_bytes_from_float32(samples: Iterable[float]) -> bytes:
    try:
        import numpy as np
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing numpy. Run Setup-Mira-Light-Windows-Voice.ps1 first.") from exc

    array = np.asarray(list(samples), dtype=np.float32)
    if array.ndim > 1:
        array = array.reshape(-1)
    clipped = np.clip(array, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def decode_audio_delta(event: dict[str, Any]) -> bytes:
    if str(event.get("type") or "") != "response.audio.delta":
        return b""
    delta = str(event.get("delta") or "")
    return base64.b64decode(delta) if delta else b""


def _clean_display_text(value: Any) -> str:
    return str(value or "").strip()


def _first_content_text(content: Any) -> str:
    if not isinstance(content, list):
        return ""
    for item in content:
        if not isinstance(item, dict):
            continue
        text = _clean_display_text(item.get("transcript") or item.get("text"))
        if text:
            return text
    return ""


def display_update_for_event(event: dict[str, Any]) -> dict[str, str] | None:
    """Extract a console-friendly text update from noisy realtime events."""

    event_type = str(event.get("type") or "")
    if event_type == "conversation.item.input_audio_transcription.completed":
        text = _clean_display_text(event.get("transcript"))
        return {"role": "user", "text": text} if text else None

    if event_type == "response.audio_transcript.done":
        text = _clean_display_text(event.get("transcript"))
        return {"role": "assistant", "text": text} if text else None

    if event_type in {"response.text.done", "response.output_text.done"}:
        text = _clean_display_text(event.get("text"))
        return {"role": "assistant", "text": text} if text else None

    if event_type == "response.content_part.done":
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        text = _clean_display_text(part.get("transcript") or part.get("text"))
        return {"role": "assistant", "text": text} if text else None

    if event_type == "response.output_item.done":
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        text = _first_content_text(item.get("content"))
        return {"role": "assistant", "text": text} if text else None

    if event_type == "error" or "error" in event:
        text = _clean_display_text(event.get("error") or event)
        return {"role": "error", "text": text} if text else None

    return None


def write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def build_live_session_preview(args: argparse.Namespace) -> dict[str, Any]:
    voice_state_enabled = voice_state_actions_enabled(args)
    return {
        "ok": True,
        "dryRun": True,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "provider": "stepfun",
        "model": args.model,
        "connection": {
            "url": build_realtime_url(args.endpoint, args.model),
            "headers": build_auth_headers(placeholder=True),
            "proxy": args.proxy_url,
            "websocket": {
                "pingInterval": keepalive_seconds_or_none(args.websocket_ping_interval),
                "pingTimeout": keepalive_seconds_or_none(args.websocket_ping_timeout),
            },
        },
        "audio": {
            "inputDevice": args.input_device,
            "inputSampleRate": int(args.input_sample_rate),
            "outputSampleRate": int(args.output_sample_rate),
            "chunkMs": int(args.chunk_ms),
            "playback": realtime_playback_enabled(args),
            "realtimePlayback": realtime_playback_enabled(args),
            "plannerPlayback": planner_playback_enabled(args),
            "plannerOwnsReply": bool(getattr(args, "planner_owns_reply", False)),
            "seconds": float(args.seconds),
        },
        "actions": {
            "voiceStateActions": voice_state_enabled,
            "semanticActions": not bool(args.no_semantic_actions),
            "directorUrl": args.director_url,
            "bridgeUrl": args.bridge_url,
            "assistantTextActions": bool(args.assistant_text_actions),
            "twoPhaseRefinement": bool(getattr(args, "two_phase_refinement", False)),
            "llmActionsForAmbiguous": bool(getattr(args, "llm_actions_for_ambiguous", True)),
            "requireModelPlanning": bool(getattr(args, "require_model_planning", False)),
            "plannerProvider": str(getattr(args, "planner_provider", "deepseek")),
            "plannerModel": str(getattr(args, "planner_model", "")),
            "plannerReply": {
                "enabled": bool(args.speak_planner_reply),
                "voice": args.planner_reply_voice,
                "wait": bool(args.planner_reply_wait),
                "playback": planner_playback_enabled(args),
                "ownsReply": bool(getattr(args, "planner_owns_reply", False)),
            },
        },
        "config": {
            "runtimeMemory": {
                "turns": int(getattr(args, "runtime_memory_turns", 12)),
                "sessionFile": "memory.json",
                "file": str(getattr(args, "runtime_memory_file", DEFAULT_RUNTIME_MEMORY_FILE)),
                "longTermWrites": "candidate-only",
            },
            "promptFiles": prompt_file_status(
                "MIRA_LIGHT_LLM_SYSTEM_PROMPT_FILE",
                "MIRA_LIGHT_REALTIME_SYSTEM_PROMPT_FILE",
                "MIRA_LIGHT_PLANNER_SYSTEM_PROMPT_FILE",
                "MIRA_LIGHT_STT_INITIAL_PROMPT_FILE",
            ),
            "micEnv": {
                "MIRA_LIGHT_INPUT_DEVICE": os.environ.get("MIRA_LIGHT_INPUT_DEVICE", ""),
                "MIRA_LIGHT_WINDOWS_MIC_DEVICE": os.environ.get("MIRA_LIGHT_WINDOWS_MIC_DEVICE", ""),
            },
        },
        "events": [
            build_session_update_event(voice=args.voice),
            {"type": "input_audio_buffer.append", "audio": "<microphone pcm16 chunks>"},
            {"type": "server_vad", "note": "speech_started/speech_stopped events drive listening/thinking actions"},
            {"type": "response.audio.delta", "note": "audio deltas are played and also drive answer action"},
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "note": "final transcript is routed through the configured semantic planner and local action whitelist before any action dispatch",
            },
        ],
    }


def voice_state_actions_enabled(args: argparse.Namespace) -> bool:
    return (not bool(args.no_voice_state_actions)) and bool(str(args.director_url or "").strip())


def build_semantic_planner(
    args: argparse.Namespace,
    *,
    plan_func: Any = plan_from_text,
    runtime_memory: MiraRuntimeMemory | None = None,
) -> Any:
    # Resolve planner API key: explicit arg -> stepfun_api_key_manager fallback
    _planner_key = getattr(args, "planner_api_key", "") or ""
    if not _planner_key.strip():
        try:
            _planner_key = stepfun_api_key_manager.get_stepfun_api_key(raise_on_missing=False)
        except Exception:
            _planner_key = ""

    def planner(transcript: str, runtime_state: dict[str, Any] | None = None) -> dict[str, Any]:
        resolved_runtime_state = runtime_state or {}
        if runtime_memory is not None:
            resolved_runtime_state = runtime_memory.build_runtime_state(
                voice_phase=str(resolved_runtime_state.get("voicePhase") or ""),
                extra=resolved_runtime_state,
            )
        return plan_func(
            transcript,
            api_key=_planner_key or None,
            endpoint=getattr(args, "planner_endpoint", ""),
            model=getattr(args, "planner_model", ""),
            provider=getattr(args, "planner_provider", "deepseek"),
            timeout_seconds=int(getattr(args, "planner_timeout_seconds", 90)),
            runtime_state=resolved_runtime_state,
            proxy_url=args.proxy_url,
        )

    return planner


def build_action_orchestrator(
    args: argparse.Namespace,
    *,
    runtime_memory: MiraRuntimeMemory | None = None,
) -> RealtimeActionOrchestrator:
    return RealtimeActionOrchestrator(
        RealtimeActionConfig(
            bridge_url=args.bridge_url,
            director_url=args.director_url,
            bridge_token=args.bridge_token,
            director_token=args.director_token,
            voice_state_enabled=voice_state_actions_enabled(args),
            semantic_actions_enabled=not bool(args.no_semantic_actions),
            request_timeout_seconds=int(args.action_timeout_seconds),
            assistant_action_enabled=bool(args.assistant_text_actions),
            two_phase_refinement_enabled=bool(getattr(args, "two_phase_refinement", False)),
            require_model_planning=bool(getattr(args, "require_model_planning", False)),
        ),
        planner=build_semantic_planner(args, runtime_memory=runtime_memory),
    )


def keepalive_seconds_or_none(value: Any) -> float | None:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return seconds


def build_websocket_connect_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    proxy_url = str(args.proxy_url or "").strip()
    kwargs: dict[str, Any] = {
        "ping_interval": keepalive_seconds_or_none(args.websocket_ping_interval),
        "ping_timeout": keepalive_seconds_or_none(args.websocket_ping_timeout),
        "proxy": proxy_url if proxy_url else None,
    }
    return kwargs


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def default_input_device() -> str:
    return (
        os.environ.get("MIRA_LIGHT_INPUT_DEVICE")
        or os.environ.get("MIRA_LIGHT_WINDOWS_MIC_DEVICE")
        or os.environ.get("MIRA_LIGHT_MIC_DEVICE")
        or "default"
    )


def planner_reply_text_from_action(action: dict[str, Any] | None) -> str:
    """Return the short local speech text produced by the semantic planner."""

    if not isinstance(action, dict):
        return ""

    plan = action.get("plan") if isinstance(action.get("plan"), dict) else {}
    if isinstance(plan.get("plan"), dict):
        plan = plan["plan"]
    speech = plan.get("speech") if isinstance(plan.get("speech"), dict) else {}
    if speech.get("shouldSpeak") is False:
        return ""

    candidates = [
        speech.get("text"),
        plan.get("reply"),
        action.get("reply"),
    ]
    action_speech = action.get("speech") if isinstance(action.get("speech"), dict) else {}
    candidates.append(action_speech.get("text"))

    for value in candidates:
        text = _clean_display_text(value)
        if text:
            return text
    return ""


def _action_from_plan_like(action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict):
        return {}
    plan = _plan_from_action_like(action)
    planned_action = plan.get("action") if isinstance(plan.get("action"), dict) else {}
    return planned_action


def _plan_from_action_like(action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict):
        return {}
    if isinstance(action.get("confirmed_action"), dict):
        return {"action": action["confirmed_action"]}
    if isinstance(action.get("new_action"), dict):
        return {"action": action["new_action"]}
    plan = action.get("plan") if isinstance(action.get("plan"), dict) else {}
    if isinstance(plan.get("plan"), dict):
        plan = plan["plan"]
    return plan


def _compact_console_value(value: Any, *, limit: int = 220) -> str:
    text = _clean_display_text(value)
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def action_console_summary(action: dict[str, Any] | None, transcript: str) -> str:
    """Build a high-signal console line for semantic action debugging."""

    if not isinstance(action, dict):
        return f"[action] none transcript={transcript}"

    kind = str(action.get("kind") or "")
    if kind == "semantic-skip" and action.get("reason") == "needs-llm-refinement":
        kind = "semantic-pending"
    parts = [f"[action] {kind}"]

    planned_action = _action_from_plan_like(action)
    action_type = str(planned_action.get("type") or "")
    action_name = str(planned_action.get("name") or "")
    if action_type and action_type != "none" and action_name:
        parts.append(f"{action_type}={action_name}")

    raw_plan = action.get("plan") if isinstance(action.get("plan"), dict) else {}
    plan = _plan_from_action_like(action)
    provider = _compact_console_value(action.get("provider") or raw_plan.get("provider") or plan.get("provider"))
    model = _compact_console_value(action.get("model") or raw_plan.get("model") or plan.get("model"), limit=80)
    if provider:
        parts.append(f"provider={provider}")
    if model:
        parts.append(f"model={model}")

    source = _compact_console_value(action.get("source"))
    if source:
        parts.append(f"source={source}")

    reason = _compact_console_value(action.get("reason") or plan.get("reason"), limit=160)
    if reason:
        parts.append(f"reason={reason}")

    response = action.get("response") if isinstance(action.get("response"), dict) else {}
    if response and response.get("ok") is False:
        error = _compact_console_value(response.get("error"))
        parts.append("ok=false")
        if error:
            parts.append(f"error={error}")

    direct_error = _compact_console_value(action.get("error"))
    if direct_error:
        parts.append(f"error={direct_error}")

    parts.append(f"transcript={transcript}")
    return " ".join(parts)


def write_runtime_memory_snapshots(
    runtime_memory: MiraRuntimeMemory,
    memory_paths: Iterable[Path | None] | None,
) -> None:
    for memory_path in memory_paths or []:
        if memory_path is not None:
            runtime_memory.write_json(memory_path)


async def _speak_planner_reply_async(
    action: dict[str, Any],
    transcript: str,
    *,
    actions_path: Path,
    audio_player: Any,
    voice: str,
    wait: bool,
    last_reply_text: dict[str, str],
) -> None:
    text = planner_reply_text_from_action(action)
    if not text:
        return
    if text == last_reply_text.get("text"):
        write_jsonl(
            actions_path,
            {
                "kind": "planner-speech-skip",
                "reason": "duplicate-reply",
                "transcript": transcript,
                "text": text,
            },
        )
        return

    last_reply_text["text"] = text
    try:
        audio_result = await asyncio.to_thread(audio_player.speak_text, text, voice=voice, wait=wait)
        speech_action = {
            "kind": "planner-speech",
            "transcript": transcript,
            "text": text,
            "voice": voice,
            "wait": wait,
            "audio": audio_result,
        }
        print(f"[speech] planner-reply voice={voice} text={text}", flush=True)
    except Exception as exc:  # noqa: BLE001
        speech_action = {
            "kind": "planner-speech-error",
            "transcript": transcript,
            "text": text,
            "voice": voice,
            "error": str(exc),
        }
        print(f"[speech-error] planner-reply: {exc}", file=sys.stderr, flush=True)
    write_jsonl(actions_path, speech_action)


async def _dispatch_transcript_async(
    orchestrator: RealtimeActionOrchestrator,
    transcript: str,
    *,
    actions_path: Path,
    planner_speech_player: Any | None = None,
    speak_planner_reply: bool = False,
    planner_reply_voice: str = "tts",
    planner_reply_wait: bool = False,
    last_planner_reply: dict[str, str] | None = None,
    llm_actions_for_ambiguous: bool = True,
    runtime_memory: MiraRuntimeMemory | None = None,
    memory_paths: Iterable[Path | None] | None = None,
) -> None:
    # ── Semantic dispatch: model-planned by default, optional local-fast mode ──
    try:
        action = await asyncio.to_thread(orchestrator.dispatch_transcript, transcript)
    except Exception as exc:  # noqa: BLE001
        action = {"kind": "semantic-error", "transcript": transcript, "error": str(exc)}
    if action:
        write_jsonl(actions_path, action)
        print(action_console_summary(action, transcript), flush=True)
        if runtime_memory is not None:
            runtime_memory.record_planner_result(transcript, action)
            write_runtime_memory_snapshots(runtime_memory, memory_paths)
        if (
            speak_planner_reply
            and planner_speech_player is not None
            and should_speak_planner_reply_action(action)
        ):
            await _speak_planner_reply_async(
                action,
                transcript,
                actions_path=actions_path,
                audio_player=planner_speech_player,
                voice=planner_reply_voice,
                wait=planner_reply_wait,
                last_reply_text=last_planner_reply if last_planner_reply is not None else {},
            )

    # ── Phase 2: LLM refinement (slow, only in two-phase mode) ──
    if orchestrator.config.two_phase_refinement_enabled:
        if (
            isinstance(action, dict)
            and action.get("kind") == "semantic-skip"
            and action.get("reason") == "needs-llm-refinement"
            and not llm_actions_for_ambiguous
        ):
            skipped = {
                "kind": "semantic-skip",
                "reason": "ambiguous-no-local-action",
                "transcript": transcript,
                "phase": 2,
            }
            write_jsonl(actions_path, skipped)
            print(action_console_summary(skipped, transcript), flush=True)
            return
        if not should_run_phase2_refinement(action, llm_actions_for_ambiguous=llm_actions_for_ambiguous):
            return
        try:
            refinement = await asyncio.to_thread(orchestrator.refine_transcript, transcript)
        except Exception as exc:  # noqa: BLE001
            refinement = {"kind": "semantic-refinement-error", "transcript": transcript, "error": str(exc)}
        if refinement:
            write_jsonl(actions_path, refinement)
            kind = refinement.get("kind", "")
            print(action_console_summary(refinement, transcript), flush=True)
            if runtime_memory is not None:
                runtime_memory.record_planner_result(transcript, refinement)
                write_runtime_memory_snapshots(runtime_memory, memory_paths)
            # Speak planner reply when the LLM produced usable speech.  Confirm
            # matters because Phase 1 may have moved locally while the realtime
            # voice replied with a generic short phrase.
            if (
                speak_planner_reply
                and planner_speech_player is not None
                and should_speak_planner_reply_action(refinement)
            ):
                await _speak_planner_reply_async(
                    refinement,
                    transcript,
                    actions_path=actions_path,
                    audio_player=planner_speech_player,
                    voice=planner_reply_voice,
                    wait=planner_reply_wait,
                    last_reply_text=last_planner_reply if last_planner_reply is not None else {},
                )


async def run_live_session_async(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import sounddevice as sd
        import websockets
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing realtime audio dependencies. Run Setup-Mira-Light-Windows-Voice.ps1 first.") from exc

    session_dir = Path(args.runtime_dir).expanduser() / timestamp_slug()
    session_dir.mkdir(parents=True, exist_ok=True)
    events_path = session_dir / "events.jsonl"
    actions_path = session_dir / "actions.jsonl"
    session_path = session_dir / "session.json"
    memory_path = session_dir / "memory.json"
    shared_memory_path = Path(getattr(args, "runtime_memory_file", DEFAULT_RUNTIME_MEMORY_FILE)).expanduser()
    runtime_memory = MiraRuntimeMemory.read_json(
        shared_memory_path,
        max_turns=int(getattr(args, "runtime_memory_turns", 12)),
    )

    api_key = resolve_api_key(args.api_key)
    url = build_realtime_url(args.endpoint, args.model)
    headers = build_auth_headers(api_key)
    orchestrator = build_action_orchestrator(args, runtime_memory=runtime_memory)
    planner_speech_player = None  # Local TTS disabled — StepFun realtime model handles all speech output
    # NOTE: AudioCuePlayer (PowerShell System.Speech) is intentionally NOT imported.
    # All TTS is handled by the StepFun StepAudio 2.5 Realtime model directly.

    # --- 初始化降噪器（纯 numpy，零额外依赖） ---
    noise_suppressor = None
    denoise_enabled = not args.no_denoise
    if denoise_enabled:
        try:
            from audio_noise_suppressor import NoiseSuppressor
            noise_suppressor = NoiseSuppressor(
                sample_rate=int(args.input_sample_rate),
                highpass_cutoff=80.0,       # 去除 80Hz 以下低频噪声
                spectral_gate_strength=1.5, # 频谱门限强度
                spectral_gate_floor_db=-40.0,
                agc_target_rms=0.04,
                agc_max_gain_db=12.0,
            )
            print("[denoise] noise suppression enabled (numpy, zero extra deps)")
        except ImportError:
            print("[denoise] audio_noise_suppressor not found, skipping denoise", file=sys.stderr)

    # --- 智能选择麦克风设备 ---
    input_device = None if args.input_device == "default" else args.input_device
    if input_device is None and denoise_enabled:
        try:
            from audio_noise_suppressor import resolve_best_mic_index
            best_idx = resolve_best_mic_index(
                prefer_real=True,
                samplerate=int(args.input_sample_rate),
                channels=1,
                dtype="int16",
            )
            if best_idx is not None:
                import sounddevice as _sd
                dev_name = _sd.query_devices(best_idx).get("name", "?")
                print(f"[mic] auto-selected real microphone: [{best_idx}] {dev_name}")
                input_device = best_idx
            else:
                print("[mic] no compatible device found for "
                      f"{args.input_sample_rate}Hz, using system default",
                      file=sys.stderr)
        except Exception as exc:
            print(f"[mic] auto-select failed: {exc}, using default", file=sys.stderr)

    # Use an unbounded queue so the microphone callback never drops samples
    # even if the network temporarily lags. The send_audio_loop consumes it.
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
    stop_event = asyncio.Event()
    semantic_tasks: set[asyncio.Task] = set()
    counters = {
        "events": 0,
        "audioChunksSent": 0,
        "audioChunksDropped": 0,
        "audioChunksPlayed": 0,
        "actions": 0,
        "semanticTasksCancelled": 0,
    }
    last_display_text = {"user": "", "assistant": "", "error": ""}
    last_planner_reply = {"text": ""}

    connect_kwargs = build_websocket_connect_kwargs(args)
    try:
        connection = websockets.connect(url, additional_headers=headers, **connect_kwargs)
    except TypeError:
        # Fallback for older websockets versions that don't support ping_interval
        connect_kwargs_basic: dict[str, Any] = dict(connect_kwargs)
        connect_kwargs_basic.pop("ping_interval", None)
        connect_kwargs_basic.pop("ping_timeout", None)
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
            # Defensive: should not happen with an unbounded queue, but keep count
            counters["audioChunksDropped"] += 1

    def input_callback(indata: bytes, frames: int, time_info: Any, status: Any) -> None:  # noqa: ARG001
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        raw = bytes(indata)
        # --- 实时降噪：在发送到 API 之前处理音频 ---
        if noise_suppressor is not None:
            try:
                raw = noise_suppressor.process(raw)
            except Exception:
                pass  # 降噪失败时使用原始音频
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
    if realtime_playback_enabled(args):
        output_stream = sd.RawOutputStream(
            samplerate=int(args.output_sample_rate),
            channels=1,
            dtype="int16",
        )

    async with connection as websocket:
        await websocket.send(json.dumps(build_session_update_event(voice=args.voice), ensure_ascii=False))
        print("Mira StepAudio realtime voice/actions session is running.")
        print(f"Session: {session_dir}")
        print(f"Runtime memory: {shared_memory_path}")
        print(f"Bridge: {args.bridge_url} semantic-actions={not args.no_semantic_actions}")
        print(f"Bridge health: {args.bridge_url.rstrip('/')}/health")
        print(f"Director: {args.director_url or '-'} voice-state-actions={voice_state_actions_enabled(args)}")
        print(f"Assistant text actions: enabled={bool(args.assistant_text_actions)}")
        print(f"Semantic model planning: required={bool(getattr(args, 'require_model_planning', False))}")
        print(
            "Planner speech: "
            f"enabled={bool(args.speak_planner_reply)} voice={args.planner_reply_voice} "
            f"playback={planner_playback_enabled(args)} "
            f"ownsReply={bool(getattr(args, 'planner_owns_reply', False))}"
        )
        print(f"Realtime playback: enabled={realtime_playback_enabled(args)}")
        print("Console text updates will appear as [user], [Mary], and [error].")
        print("Press Ctrl+C to stop.")

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
                    if role == "assistant" and bool(getattr(args, "planner_owns_reply", False)):
                        continue
                    if text != last_display_text.get(role):
                        last_display_text[role] = text
                        label = {"assistant": "Mary"}.get(role, role)
                        print(f"[{label}] {text}", flush=True)

                        # When Mary replies with action words, dispatch to board
                        if role == "assistant" and text:
                            try:
                                assistant_action = await asyncio.to_thread(
                                    orchestrator.dispatch_assistant_text, text
                                )
                                if assistant_action:
                                    kind = assistant_action.get("kind", "")
                                    write_jsonl(actions_path, assistant_action)
                                    if kind == "assistant-action":
                                        counters["actions"] += 1
                                        kw = assistant_action.get("keyword", "")
                                        act = assistant_action.get("action", {})
                                        print(f"[action] assistant-action keyword='{kw}' -> {act.get('type')}:{act.get('name')}", flush=True)
                            except Exception as exc:
                                print(f"[action-error] assistant dispatch: {exc}", file=sys.stderr)

                phase = phase_for_realtime_event(event)
                if phase:
                    action = orchestrator.dispatch_voice_phase(phase)
                    if action:
                        counters["actions"] += 1
                        write_jsonl(actions_path, action)
                        print(f"[action] {action.get('kind')} phase={phase}", flush=True)

                transcript = extract_final_transcript(event)
                if transcript and not args.no_semantic_actions:
                    for pending_task in list(semantic_tasks):
                        if not pending_task.done():
                            pending_task.cancel()
                            counters["semanticTasksCancelled"] += 1
                    task = asyncio.create_task(
                        _dispatch_transcript_async(
                            orchestrator,
                            transcript,
                            actions_path=actions_path,
                            planner_speech_player=planner_speech_player,
                            speak_planner_reply=bool(args.speak_planner_reply),
                            planner_reply_voice=args.planner_reply_voice,
                            planner_reply_wait=bool(args.planner_reply_wait),
                            last_planner_reply=last_planner_reply,
                            llm_actions_for_ambiguous=bool(args.llm_actions_for_ambiguous),
                            runtime_memory=runtime_memory,
                            memory_paths=[memory_path, shared_memory_path],
                        )
                    )
                    semantic_tasks.add(task)
                    task.add_done_callback(semantic_tasks.discard)

                if str(event.get("type") or "") == "input_audio_buffer.speech_stopped":
                    # NOTE: Do NOT send input_audio_buffer.commit when server_vad is enabled.
                    # The server auto-commits on speech_stopped. Manual commit causes
                    # "commit when server vad" errors.
                    if args.manual_response_create_on_speech_stop:
                        await websocket.send(json.dumps({"type": "response.create", "response": {"modalities": ["text", "audio"]}}))

                pcm = decode_audio_delta(event)
                if pcm and output_stream is not None:
                    # sounddevice.RawOutputStream.write() can block when the
                    # device buffer is full. Run it in a thread so the event loop
                    # (and the input audio queue) is not stalled.
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
        "memoryPath": str(memory_path.resolve()),
        "sharedMemoryPath": str(shared_memory_path.resolve()),
        "model": args.model,
        "counters": counters,
    }
    session_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def run_live_session(args: argparse.Namespace) -> dict[str, Any]:
    return asyncio.run(run_live_session_async(args))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live StepAudio realtime voice session with Mira Light action routing.")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_REALTIME_ENDPOINT", DEFAULT_REALTIME_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_REALTIME_MODEL", DEFAULT_REALTIME_MODEL))
    parser.add_argument("--voice", default=os.environ.get("STEPFUN_REALTIME_VOICE", DEFAULT_VOICE))
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument(
        "--websocket-ping-interval",
        type=float,
        default=float(os.environ.get("STEPFUN_REALTIME_WEBSOCKET_PING_INTERVAL", DEFAULT_WEBSOCKET_PING_INTERVAL)),
        help="Client WebSocket ping interval in seconds. Use 0 to disable client keepalive pings.",
    )
    parser.add_argument(
        "--websocket-ping-timeout",
        type=float,
        default=float(os.environ.get("STEPFUN_REALTIME_WEBSOCKET_PING_TIMEOUT", DEFAULT_WEBSOCKET_PING_TIMEOUT)),
        help="Client WebSocket ping timeout in seconds. Use 0 to disable client keepalive timeout.",
    )
    parser.add_argument("--input-device", default=default_input_device())
    parser.add_argument("--device", dest="input_device", help=argparse.SUPPRESS)
    parser.add_argument("--input-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_INPUT_SAMPLE_RATE", DEFAULT_INPUT_SAMPLE_RATE)))
    parser.add_argument("--output-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE", DEFAULT_OUTPUT_SAMPLE_RATE)))
    parser.add_argument("--chunk-ms", type=int, default=int(os.environ.get("STEPFUN_REALTIME_MIC_CHUNK_MS", DEFAULT_CHUNK_MS)))
    parser.add_argument("--seconds", type=float, default=float(os.environ.get("STEPFUN_REALTIME_SESSION_SECONDS", DEFAULT_SESSION_SECONDS)))
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR))
    parser.add_argument(
        "--runtime-memory-file",
        default=os.environ.get("MIRA_LIGHT_RUNTIME_MEMORY_FILE", str(DEFAULT_RUNTIME_MEMORY_FILE)),
        help="Persistent Mira runtime memory JSON file reused across reconnects and restarts.",
    )
    parser.add_argument(
        "--runtime-memory-turns",
        type=int,
        default=int(os.environ.get("MIRA_LIGHT_RUNTIME_MEMORY_TURNS", "12")),
        help="Number of recent user/Mira turns to pass into the semantic planner.",
    )
    parser.add_argument("--bridge-url", default=os.environ.get("MIRA_LIGHT_BRIDGE_URL", DEFAULT_BRIDGE_URL))
    parser.add_argument("--bridge-token", default=os.environ.get("MIRA_LIGHT_BRIDGE_TOKEN", ""))
    parser.add_argument("--director-url", default=os.environ.get("MIRA_LIGHT_DIRECTOR_URL", ""))
    parser.add_argument("--director-token", default=os.environ.get("MIRA_LIGHT_DIRECTOR_TOKEN", ""))
    parser.add_argument("--action-timeout-seconds", type=int, default=int(os.environ.get("MIRA_LIGHT_ACTION_TIMEOUT_SECONDS", "5")))
    parser.add_argument("--planner-provider", choices=["deepseek", "stepfun", "hermes"], default=os.environ.get("MIRA_LIGHT_PLANNER_PROVIDER", "stepfun"))
    parser.add_argument("--planner-api-key", default="")
    parser.add_argument("--planner-endpoint", default=os.environ.get("MIRA_LIGHT_PLANNER_ENDPOINT", os.environ.get("STEPFUN_LLM_ENDPOINT", "")))
    parser.add_argument("--planner-model", default=os.environ.get("MIRA_LIGHT_PLANNER_MODEL", os.environ.get("STEPFUN_LLM_MODEL", "")))
    parser.add_argument("--planner-timeout-seconds", type=int, default=int(os.environ.get("MIRA_LIGHT_PLANNER_TIMEOUT_SECONDS", "90")))
    parser.add_argument("--no-voice-state-actions", action="store_true")
    parser.add_argument("--no-semantic-actions", action="store_true")
    parser.add_argument("--no-trigger", dest="no_semantic_actions", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--assistant-text-actions",
        action="store_true",
        default=env_flag("MIRA_LIGHT_ASSISTANT_TEXT_ACTIONS", False),
        help="Let StepAudio/Mary reply text keywords directly trigger actions. Off by default; semantic planner is preferred.",
    )
    parser.add_argument("--no-assistant-text-actions", dest="assistant_text_actions", action="store_false")
    parser.add_argument(
        "--two-phase-refinement",
        action="store_true",
        default=env_flag("MIRA_LIGHT_TWO_PHASE_REFINEMENT", False),
        help="Enable two-phase state machine: Phase 1 fires local keyword action instantly, Phase 2 runs LLM and confirms/overrides/cancels.",
    )
    parser.add_argument(
        "--require-model-planning",
        action="store_true",
        default=env_flag("MIRA_LIGHT_REQUIRE_MODEL_PLANNING", False),
        help="Require the configured semantic planner before dispatching any final-transcript scene or trigger.",
    )
    parser.add_argument(
        "--allow-local-semantic-fallback",
        dest="require_model_planning",
        action="store_false",
        help="Allow local keyword intent mapping to dispatch semantic actions before planner refinement.",
    )
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--dry-run-audio", dest="no_play", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--no-realtime-playback",
        action="store_true",
        default=env_flag("MIRA_LIGHT_NO_REALTIME_PLAYBACK", False),
        help="Do not play StepAudio realtime audio deltas locally. Planner TTS can still speak.",
    )
    parser.add_argument(
        "--no-planner-playback",
        action="store_true",
        default=env_flag("MIRA_LIGHT_NO_PLANNER_PLAYBACK", False),
        help="Do not play the local planner reply TTS. StepAudio realtime playback can still be enabled.",
    )
    parser.add_argument(
        "--planner-playback",
        dest="no_planner_playback",
        action="store_false",
        help="Enable local planner reply TTS playback.",
    )
    parser.add_argument(
        "--speak-planner-reply",
        action="store_true",
        default=env_flag("MIRA_LIGHT_SPEAK_PLANNER_REPLY", False),
        help="Speak the semantic planner's short reply through the local speaker path.",
    )
    parser.add_argument("--no-speak-planner-reply", dest="speak_planner_reply", action="store_false")
    parser.add_argument(
        "--planner-owns-reply",
        action="store_true",
        default=env_flag("MIRA_LIGHT_PLANNER_OWNS_REPLY", False),
        help="Use planner/agent speech as Mira's final reply. StepAudio audio playback and free assistant console replies are muted.",
    )
    parser.add_argument("--no-planner-owns-reply", dest="planner_owns_reply", action="store_false")
    parser.add_argument("--planner-reply-voice", default=os.environ.get("MIRA_LIGHT_PLANNER_REPLY_VOICE", "tts"))
    parser.add_argument(
        "--planner-reply-wait",
        action="store_true",
        default=env_flag("MIRA_LIGHT_PLANNER_REPLY_WAIT", False),
        help="Wait for planner reply TTS playback before returning from the semantic action task.",
    )
    parser.add_argument("--no-planner-reply-wait", dest="planner_reply_wait", action="store_false")
    parser.add_argument(
        "--llm-actions-for-ambiguous",
        action="store_true",
        default=env_flag("MIRA_LIGHT_LLM_ACTIONS_FOR_AMBIGUOUS", True),
        help="Allow phase-2 LLM refinement to execute actions even when no local action intent matched.",
    )
    parser.add_argument(
        "--no-llm-actions-for-ambiguous",
        dest="llm_actions_for_ambiguous",
        action="store_false",
        help="Disable phase-2 LLM action execution for transcripts without a local action match.",
    )
    parser.add_argument("--manual-response-create-on-speech-stop", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")

    # Compatibility with the existing Full mode launcher. These flags are
    # meaningful for the legacy local-STT pipeline but not for StepAudio's
    # realtime WebSocket, so the realtime engine accepts and records them
    # without changing the hardware/action boundary.
    parser.add_argument("--mode", choices=["continuous", "enter-vad", "ptt", "fixed"], default=os.environ.get("MIRA_LIGHT_CAPTURE_MODE", "continuous"))
    parser.add_argument("--profile", default=os.environ.get("MIRA_LIGHT_STT_PROFILE", ""))
    parser.add_argument("--latency-preset", default=os.environ.get("MIRA_LIGHT_LATENCY_PRESET", ""))
    parser.add_argument("--voice-mode", default=os.environ.get("MIRA_LIGHT_TTS_MODE", ""))
    parser.add_argument("--vad-start-ms", type=int, default=0)
    parser.add_argument("--vad-end-ms", type=int, default=0)
    parser.add_argument("--vad-min-rms", type=float, default=0.0)
    parser.add_argument("--vad-speech-ratio", type=float, default=0.0)
    parser.add_argument("--startup-warmup", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-startup-warmup", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-denoise", action="store_true", help="Disable real-time noise suppression.")
    parser.add_argument(
        "--ws-max-retries",
        type=int,
        default=int(os.environ.get("MIRA_LIGHT_WS_MAX_RETRIES", DEFAULT_WS_MAX_RETRIES)),
        help="Max WebSocket reconnection attempts on keepalive timeout or connection error.",
    )
    parser.add_argument(
        "--ws-retry-delay",
        type=float,
        default=float(os.environ.get("MIRA_LIGHT_WS_RETRY_DELAY", DEFAULT_WS_RETRY_DELAY)),
        help="Seconds to wait between WebSocket reconnection attempts.",
    )
    parser.add_argument("--no-reconnect", action="store_true", help="Disable WebSocket auto-reconnection.")
    args = parser.parse_args(argv)
    if not str(args.planner_api_key or "").strip():
        explicit_planner_key = os.environ.get("MIRA_LIGHT_PLANNER_API_KEY", "")
        if explicit_planner_key:
            args.planner_api_key = explicit_planner_key
        elif str(args.planner_provider or "").strip().lower() == "stepfun":
            args.planner_api_key = os.environ.get("STEPFUN_API_KEY", "")
        elif str(args.planner_provider or "").strip().lower() == "deepseek":
            args.planner_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if str(args.planner_provider or "").strip().lower() == "hermes":
        if str(args.planner_endpoint or "").strip() in {
            "https://api.deepseek.com/chat/completions",
            "https://api.stepfun.com/v1/chat/completions",
            "",
        }:
            args.planner_endpoint = ""
        if str(args.planner_model or "").strip() in {"deepseek-v4-flash", "step-3.7-flash", ""}:
            args.planner_model = "hermes-agent"
    if not str(args.planner_endpoint or "").strip():
        if args.planner_provider == "stepfun":
            args.planner_endpoint = "https://api.stepfun.com/v1/chat/completions"
        elif args.planner_provider == "deepseek":
            args.planner_endpoint = "https://api.deepseek.com/chat/completions"
    if not str(args.planner_model or "").strip():
        if args.planner_provider == "stepfun":
            args.planner_model = "step-3.7-flash"
        elif args.planner_provider == "deepseek":
            args.planner_model = "deepseek-v4-flash"
    return args


def main() -> int:
    args = parse_args()
    try:
        validate_audio_routing(args)
        if args.dry_run:
            result = build_live_session_preview(args)
        else:
            # ── WebSocket auto-reconnection loop ──
            # The StepFun realtime WebSocket can drop on keepalive ping
            # timeout. Instead of killing the entire session, we retry.
            max_retries = 0 if args.no_reconnect else max(0, int(args.ws_max_retries))
            retry_delay = max(1.0, float(args.ws_retry_delay))
            result = None
            for attempt in range(max_retries + 1):
                try:
                    result = run_live_session(args)
                    break
                except KeyboardInterrupt:
                    raise
                except SystemExit:
                    raise
                except Exception as exc:
                    if attempt < max_retries:
                        print(
                            f"[reconnect] WebSocket session error (attempt {attempt + 1}/{max_retries + 1}): {exc}",
                            file=sys.stderr,
                        )
                        print(f"[reconnect] Retrying in {retry_delay:.0f}s...", file=sys.stderr)
                        import time as _time
                        _time.sleep(retry_delay)
                    else:
                        raise
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.dry_run:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Saved session: {result['sessionDir']}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        return 130
    except Exception as exc:  # noqa: BLE001
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[realtime-voice-actions-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    raise SystemExit(main())
