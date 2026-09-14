#!/usr/bin/env python3
"""Windows voice interaction runtime for MIRA Light.

This script implements:
1. Microphone VAD capture -> local WAV file.
2. StepFun Realtime WebSocket file upload -> ASR + LLM reply + TTS audio file.
3. Intent/Keyword matching -> immediate bridge action dispatch (Sound & Picture Sync).
4. Audio cue playback of the TTS reply.
5. Windows PowerShell SAPI5 speech synthesis fallback (Downgrade/Fallback).
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error

# Add current directory to path so imports work correctly
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPTS_DIR))

try:
    # Auto-activate global StepFun API key fallback (env -> hardcoded).
    # Must import BEFORE stepfun_realtime_voice so the monkey-patch applies.
    import stepfun_api_key_manager  # noqa: F401

    from windows_mic_capture import (
        resolve_input_device,
        capture_vad,
        save_wav as save_capture_wav,
        audio_metrics,
    )
    from stepfun_realtime_voice import (
        run_realtime_audio_file,
        play_wav,
        write_realtime_output,
        resolve_api_key,
    )
    from mira_realtime_action_orchestrator import (
        RealtimeActionConfig,
        RealtimeActionOrchestrator,
        post_json_request,
    )
    from mira_voice_intents import classify_intent, action_for_intent
    # AudioCuePlayer intentionally NOT imported — all TTS via StepFun model
except ImportError as exc:
    print(f"Error importing modules: {exc}", file=sys.stderr)
    print("Please ensure this script is run from the 'Mira-Light-Voice-Full-Ready/scripts' context.", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / "runtime" / "windows-voice-sync"


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")


def get_fallback_reply(intent: str) -> str:
    """Return a cozy local fallback sentence when cloud generation fails."""
    if intent.startswith("scene:"):
        scene_name = intent.split(":", 1)[1].strip()
        replies = {
            "celebrate": "好，我们来跳个舞吧！",
            "sleep": "困了，我先睡觉啦。",
            "wake_up": "伸个懒腰，我醒来啦。",
            "curious_observe": "你在做什么呀？我看一下。",
            "touch_affection": "蹭蹭你，感觉好温暖。",
            "daydream": "放空一小会，发个呆。",
        }
        return replies.get(scene_name, "好，我动一下。")
    
    if intent == "comfort":
        return "辛苦啦，要不要休息一下？我陪着你。"
    if intent == "farewell":
        return "拜拜，下次再见啦。"
    if intent == "praise":
        return "嘿嘿，听到你夸我，我好开心呀！"
    
    return "网络出了一点状况，我先休息一下。"


def run_windows_voice_loop(args: argparse.Namespace) -> int:
    # 1. Resolve key components
    try:
        api_key = resolve_api_key(args.api_key)
    except Exception as exc:
        print(f"[config-error] {exc}")
        print("Running in DRY-RUN mode or using environment defaults.")
        api_key = os.environ.get("STEPFUN_API_KEY", "")

    # Configure session dirs
    runtime_dir = Path(args.runtime_dir).expanduser()
    session_dir = runtime_dir / timestamp_slug()
    session_dir.mkdir(parents=True, exist_ok=True)

    print("")
    print("###################################################")
    print("  MIRA Light Windows Voice Loop (Sync & Fallback)")
    print(f"  Session: {session_dir}")
    print(f"  Bridge URL: {args.bridge_url}")
    print(f"  Director URL: {args.director_url or '(None)'}")
    print("###################################################")
    print("")

    # Initialize orchestrators
    orchestrator = RealtimeActionOrchestrator(
        RealtimeActionConfig(
            bridge_url=args.bridge_url,
            director_url=args.director_url,
            bridge_token=args.bridge_token,
            director_token=args.director_token,
            voice_state_enabled=not bool(args.no_voice_state_actions),
            semantic_actions_enabled=not bool(args.no_semantic_actions),
            request_timeout_seconds=5,
        )
    )

    # audio_player (AudioCuePlayer / local TTS) intentionally NOT created.
    # All speech output is handled by the StepFun StepAudio 2.5 model.
    device = resolve_input_device(args.input_device)
    print(f"[mic] Using input device: index={device.index} name='{device.name}'")

    turn_index = 0
    try:
        while True:
            turn_index += 1
            turn_dir = session_dir / f"turn-{turn_index:03d}"
            turn_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n--- [Turn {turn_index:03d}] ---")
            
            # Action Cue: Listening start
            orchestrator.dispatch_voice_phase("listening")

            # A. Capture voice audio using local VAD
            wav_path = turn_dir / "input.wav"
            if args.file:
                import shutil
                source_file = Path(args.file).expanduser().resolve()
                if not source_file.is_file():
                    print(f"[config-error] Audio file not found: {source_file}")
                    break
                shutil.copy(str(source_file), str(wav_path))
                print(f"[file] Using input audio file: {source_file}")
            else:
                try:
                    print("[mic] Listening for speech (VAD active)...")
                    result = capture_vad(args, device)
                    save_capture_wav(result.samples, sample_rate=result.sample_rate, path=wav_path)
                    metrics = audio_metrics(result.samples, result.sample_rate)
                    
                    # Check for extremely quiet/low energy sounds to skip noise
                    if metrics["rms"] < args.vad_min_rms * 0.8:
                        print(f"[mic] Skipped: low energy utterance (rms={metrics['rms']:.5f})")
                        orchestrator.dispatch_voice_phase("idle")
                        continue
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    print(f"[mic-error] Failed to capture microphone: {exc}")
                    orchestrator.dispatch_voice_phase("idle")
                    time.sleep(1)
                    continue

            # Action Cue: Thinking start
            orchestrator.dispatch_voice_phase("thinking")

            # B. Upload WAV to StepFun Realtime API (Single request for STT+LLM+TTS)
            print("[cloud] Transcribing and generating Mary's reply...")
            output_json = turn_dir / "transcript.realtime.json"
            
            api_success = False
            user_transcript = ""
            assistant_text = ""
            reply_wav_path = ""

            try:
                result = run_realtime_audio_file(
                    wav_path,
                    api_key=api_key,
                    endpoint=args.endpoint,
                    model=args.model,
                    voice=args.voice,
                    chunk_ms=args.chunk_ms,
                    timeout_seconds=args.timeout_seconds,
                    proxy_url=args.proxy_url,
                )
                
                # Extract WAV reply audio and JSON metadata
                write_realtime_output(result, output_json, output_sample_rate=args.output_sample_rate)
                
                summary = result.get("summary", {})
                user_transcript = summary.get("userTranscript", "").strip()
                assistant_text = summary.get("assistantText", "").strip()
                reply_wav_path = result.get("responseAudioPath")
                
                if user_transcript or assistant_text:
                    api_success = True
                    print(f"User > '{user_transcript}'")
                    print(f"Mary > '{assistant_text}'")
                else:
                    if summary.get("errors"):
                        print(f"[api-warn] StepFun returned errors: {summary['errors']}")
            
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"[api-error] StepFun API request failed: {exc}")

            # C. Downgrade Fallback handling — StepFun only, NO local TTS
            if not api_success:
                print("[fallback] StepFun API request failed — skipping local TTS fallback.")
                print(f"Mary (fallback-text) > '{fallback_text}'")

                orchestrator.dispatch_voice_phase("answer")

                # Reset physical board to sleep scene
                try:
                    print("[action] Resetting board to sleep scene...")
                    post_json_request(
                        f"{args.bridge_url.rstrip('/')}/v1/mira-light/run-scene",
                        {"scene": "sleep", "cueMode": "voice-fallback"},
                        timeout_seconds=2
                    )
                except Exception:
                    pass

                # NO local TTS — StepFun handles all speech
                print(f"[tts-skip] Local TTS disabled; fallback text not spoken: {fallback_text}")
                orchestrator.dispatch_voice_phase("idle")
                continue

            # D. Action Dispatch (Sound & Picture Synchronization)
            # We trigger actions BEFORE playing the voice reply
            action_dispatched = False
            intent = "chat"
            
            if user_transcript:
                # 1. Local keyword intent mapping (highest priority)
                intent = classify_intent(user_transcript)
                local_action = action_for_intent(intent)
                if local_action and local_action.get("type") != "none":
                    print(f"[action] User text matched intent '{intent}' -> {local_action.get('type')}:{local_action.get('name')}")
                    orchestrator.dispatch_transcript(user_transcript)
                    action_dispatched = True

            if not action_dispatched and assistant_text:
                # 2. Assistant text keyword mapping (Mary's words drive actions)
                assistant_action = orchestrator.dispatch_assistant_text(assistant_text)
                if assistant_action and assistant_action.get("kind") == "assistant-action":
                    kw = assistant_action.get("keyword")
                    act = assistant_action.get("action", {})
                    print(f"[action] Assistant text matched keyword '{kw}' -> {act.get('type')}:{act.get('name')}")
                    action_dispatched = True

            # Action Cue: Answer phase
            orchestrator.dispatch_voice_phase("answer")

            # E. Playback voice response — StepFun only, NO local TTS fallback
            if reply_wav_path and os.path.exists(reply_wav_path) and not args.no_play:
                play_wav(reply_wav_path)
            else:
                # No wav from StepFun — print text only, do NOT use local TTS
                print(f"[tts-skip] No wav from StepFun; local TTS disabled. Text: {assistant_text}")

            # Turn complete, reset to idle
            orchestrator.dispatch_voice_phase("idle")
            
            # Brief cooldown after TTS to prevent self-looping
            if args.post_tts_cooldown_seconds > 0:
                time.sleep(args.post_tts_cooldown_seconds)

            if args.once:
                break

    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        orchestrator.dispatch_voice_phase("idle")
        return 130
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronized Windows Voice orchestrator for MIRA Light.")
    
    # StepFun API configs
    parser.add_argument("--api-key", default="")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_REALTIME_ENDPOINT", "wss://api.stepfun.com/v1/realtime"))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_REALTIME_MODEL", "stepaudio-2.5-realtime"))
    parser.add_argument("--voice", default=os.environ.get("STEPFUN_REALTIME_VOICE", "wenrounansheng"))
    parser.add_argument("--proxy-url", default=os.environ.get("STEPFUN_PROXY_URL", ""))
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--output-sample-rate", type=int, default=24000)

    # Capture/Mic configs
    parser.add_argument("--input-device", default=os.environ.get("MIRA_LIGHT_INPUT_DEVICE", "default"))
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--chunk-ms", type=int, default=100)
    parser.add_argument("--vad-start-ms", type=int, default=120)
    parser.add_argument("--vad-end-ms", type=int, default=900)
    parser.add_argument("--vad-min-rms", type=float, default=0.003)
    parser.add_argument("--vad-speech-ratio", type=float, default=1.5)
    parser.add_argument("--min-utterance-ms", type=int, default=400)
    parser.add_argument("--max-utterance-seconds", type=float, default=8.0)
    parser.add_argument("--max-wait-seconds", type=float, default=30.0)
    parser.add_argument("--preroll-ms", type=int, default=250)

    # Bridge & Director configs
    parser.add_argument("--bridge-url", default=os.environ.get("MIRA_LIGHT_BRIDGE_URL", "http://127.0.0.1:9783"))
    parser.add_argument("--bridge-token", default=os.environ.get("MIRA_LIGHT_BRIDGE_TOKEN", ""))
    parser.add_argument("--director-url", default=os.environ.get("MIRA_LIGHT_DIRECTOR_URL", ""))
    parser.add_argument("--director-token", default=os.environ.get("MIRA_LIGHT_DIRECTOR_TOKEN", ""))
    parser.add_argument("--no-voice-state-actions", action="store_true")
    parser.add_argument("--no-semantic-actions", action="store_true")
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--post-tts-cooldown-seconds", type=float, default=float(os.environ.get("MIRA_LIGHT_POST_TTS_COOLDOWN_SECONDS", "0.25")))
    
    # Loop control
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--file", help="Pre-recorded WAV file to use instead of live mic capture")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR))

    args = parser.parse_args()
    
    # If proxy-url is set, configure environment proxy
    if args.proxy_url:
        os.environ["HTTP_PROXY"] = args.proxy_url
        os.environ["HTTPS_PROXY"] = args.proxy_url
        os.environ["NO_PROXY"] = "127.0.0.1,localhost,192.168.0.183"

    return run_windows_voice_loop(args)


if __name__ == "__main__":
    sys.exit(main())
