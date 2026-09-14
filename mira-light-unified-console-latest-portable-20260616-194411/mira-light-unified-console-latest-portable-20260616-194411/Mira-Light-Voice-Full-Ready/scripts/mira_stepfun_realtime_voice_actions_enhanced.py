#!/usr/bin/env python3
"""Enhanced live StepAudio realtime voice session with noise suppression.

增强版实时语音会话 —— 集成降噪、智能设备选择和低延迟处理

主要改进：
  1. 智能选择真实麦克风（排除虚拟/模拟设备）
  2. 实时深度降噪（DeepFilterNet）
  3. 增强型VAD（Silero VAD）
  4. 自动增益控制（AGC）
  5. 低延迟音频处理管道
  6. 音频质量实时监控

使用方法：
  python mira_stepfun_realtime_voice_actions_enhanced.py [原有参数] [新增参数]

新增参数：
  --enhanced-audio          启用增强音频处理（默认开启）
  --no-enhanced-audio       禁用增强音频处理，回退到原始模式
  --denoise-model           降噪模型选择（deepfilternet2/deepfilternet）
  --no-denoise              禁用降噪
  --no-vad-enhance          禁用增强VAD
  --no-agc                  禁用自动增益控制
  --audio-metrics           显示音频质量指标

作者: AI Assistant
日期: 2026-06-18
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

# 导入原有功能
from mira_stepfun_realtime_voice_actions import (
    DEFAULT_BRIDGE_URL,
    DEFAULT_CHUNK_MS,
    DEFAULT_INPUT_SAMPLE_RATE,
    DEFAULT_OUTPUT_SAMPLE_RATE,
    DEFAULT_PROXY_URL,
    DEFAULT_REALTIME_ENDPOINT,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_SESSION_SECONDS,
    DEFAULT_VOICE,
    DEFAULT_WEBSOCKET_PING_INTERVAL,
    DEFAULT_WEBSOCKET_PING_TIMEOUT,
    RealtimeActionConfig,
    RealtimeActionOrchestrator,
    build_action_orchestrator,
    build_live_session_preview,
    build_semantic_planner,
    build_session_update_event,
    build_websocket_connect_kwargs,
    decode_audio_delta,
    display_update_for_event,
    env_flag,
    extract_final_transcript,
    keepalive_seconds_or_none,
    parse_args as original_parse_args,
    phase_for_realtime_event,
    planner_reply_text_from_action,
    resolve_api_key,
    run_live_session,
    timestamp_slug,
    voice_state_actions_enabled,
    write_jsonl,
)
from stepfun_llm_planner import plan_from_text
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

# 导入增强音频模块
sys.path.insert(0, str(Path(__file__).parent))
from audio_enhanced_capture import (
    AudioConfig,
    EnhancedAudioCapture,
    InputDevice,
    MicrophoneDetector,
    RealtimeAudioStream,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 增强版实时会话
# ═══════════════════════════════════════════════════════════════════════════════

async def run_enhanced_live_session_async(args: argparse.Namespace) -> dict[str, Any]:
    """运行增强版实时语音会话"""
    
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
    audio_metrics_path = session_dir / "audio_metrics.jsonl"

    api_key = resolve_api_key(args.api_key)
    url = build_realtime_url(args.endpoint, args.model)
    headers = build_auth_headers(api_key)
    orchestrator = build_action_orchestrator(args)
    planner_speech_player = None
    if args.speak_planner_reply:
        from mira_light_audio import AudioCuePlayer
        planner_speech_player = AudioCuePlayer(dry_run=bool(args.no_play))

    # 初始化增强音频处理
    enhanced_audio_enabled = not args.no_enhanced_audio
    audio_stream = None
    audio_config = None
    
    if enhanced_audio_enabled:
        audio_config = AudioConfig(
            sample_rate=int(args.input_sample_rate),
            channels=1,
            chunk_ms=int(args.chunk_ms),
            device_hint=args.input_device if args.input_device != "default" else "",
            enable_denoise=not args.no_denoise,
            denoise_model=args.denoise_model,
            enable_vad=not args.no_vad_enhance,
            vad_threshold=args.vad_threshold,
            enable_agc=not args.no_agc,
            target_rms=args.target_rms,
            low_latency_mode=True,
        )
        audio_stream = RealtimeAudioStream(audio_config)
        print("[enhanced-audio] 增强音频处理已启用")
        print(f"[enhanced-audio] 降噪: {'开启' if audio_config.enable_denoise else '关闭'}")
        print(f"[enhanced-audio] VAD: {'开启' if audio_config.enable_vad else '关闭'}")
        print(f"[enhanced-audio] AGC: {'开启' if audio_config.enable_agc else '关闭'}")
    else:
        print("[enhanced-audio] 使用原始音频模式")

    # 音频队列和事件
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
    stop_event = asyncio.Event()
    semantic_tasks: set[asyncio.Task] = set()
    counters = {
        "events": 0,
        "audioChunksSent": 0,
        "audioChunksDropped": 0,
        "audioChunksPlayed": 0,
        "actions": 0,
        "audioChunksProcessed": 0,
        "speechChunksDetected": 0,
    }
    last_display_text = {"user": "", "assistant": "", "error": ""}
    last_planner_reply = {"text": ""}

    connect_kwargs = build_websocket_connect_kwargs(args)
    try:
        connection = websockets.connect(url, additional_headers=headers, **connect_kwargs)
    except TypeError:
        connect_kwargs_basic: dict[str, Any] = dict(connect_kwargs)
        connect_kwargs_basic.pop("ping_interval", None)
        connect_kwargs_basic.pop("ping_timeout", None)
        try:
            connection = websockets.connect(url, additional_headers=headers, **connect_kwargs_basic)
        except TypeError:
            connection = websockets.connect(url, extra_headers=headers, **connect_kwargs_basic)

    loop = asyncio.get_running_loop()

    # 音频处理回调
    def enqueue_audio(pcm: bytes) -> None:
        if stop_event.is_set():
            return
        try:
            audio_queue.put_nowait(pcm)
        except asyncio.QueueFull:
            counters["audioChunksDropped"] += 1

    def on_enhanced_audio(audio: np.ndarray, metrics) -> None:
        """增强音频处理回调"""
        if stop_event.is_set():
            return
        
        # 转换为 PCM16
        clipped = np.clip(audio, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype("<i2").tobytes()
        
        loop.call_soon_threadsafe(enqueue_audio, pcm)
        counters["audioChunksProcessed"] += 1
        if metrics.is_speech:
            counters["speechChunksDetected"] += 1
        
        # 记录音频指标
        if args.audio_metrics:
            write_jsonl(audio_metrics_path, {
                "timestamp": datetime.now().isoformat(),
                **metrics.to_dict(),
            })

    # 原始音频回调（未启用增强模式时使用）
    def input_callback(indata: bytes, frames: int, time_info: Any, status: Any) -> None:
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        loop.call_soon_threadsafe(enqueue_audio, bytes(indata))

    # 设置输入流
    input_blocksize = max(160, int(int(args.input_sample_rate) * int(args.chunk_ms) / 1000))
    
    if enhanced_audio_enabled and audio_stream:
        # 使用增强音频流
        device = await audio_stream.start(
            args.input_device if args.input_device != "default" else ""
        )
        print(f"[enhanced-audio] 已选择设备: {device.name}")
        if device.is_real_microphone:
            print(f"[enhanced-audio] 设备类型: 真实麦克风 (置信度: {device.confidence_score:.2f})")
        else:
            print(f"[enhanced-audio] 警告: 可能选择了虚拟设备")
        
        # 设置回调
        audio_stream.capture.on_audio_ready = on_enhanced_audio
        input_stream = None  # 由 EnhancedAudioCapture 管理
    else:
        # 使用原始音频流
        input_stream = sd.RawInputStream(
            samplerate=int(args.input_sample_rate),
            blocksize=input_blocksize,
            device=None if args.input_device == "default" else args.input_device,
            channels=1,
            dtype="int16",
            callback=input_callback,
        )

    # 输出流
    output_stream = None
    if not args.no_play:
        output_stream = sd.RawOutputStream(
            samplerate=int(args.output_sample_rate),
            channels=1,
            dtype="int16",
        )

    async with connection as websocket:
        await websocket.send(json.dumps(build_session_update_event(voice=args.voice), ensure_ascii=False))
        print("Mira StepAudio realtime voice/actions session is running.")
        print(f"Session: {session_dir}")
        print(f"Bridge: {args.bridge_url} semantic-actions={not args.no_semantic_actions}")
        print(f"Bridge health: {args.bridge_url.rstrip('/')}/health")
        print(f"Director: {args.director_url or '-'} voice-state-actions={voice_state_actions_enabled(args)}")
        print(f"Assistant text actions: enabled={bool(args.assistant_text_actions)}")
        print(
            "Planner speech: "
            f"enabled={bool(args.speak_planner_reply)} voice={args.planner_reply_voice} "
            f"playback={not bool(args.no_play)}"
        )
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
                    if text != last_display_text.get(role):
                        last_display_text[role] = text
                        label = {"assistant": "Mary"}.get(role, role)
                        print(f"[{label}] {text}", flush=True)

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
                        )
                    )
                    semantic_tasks.add(task)
                    task.add_done_callback(semantic_tasks.discard)

                if str(event.get("type") or "") == "input_audio_buffer.speech_stopped":
                    await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    if args.manual_response_create_on_speech_stop:
                        await websocket.send(json.dumps({"type": "response.create", "response": {"modalities": ["text", "audio"]}}))

                pcm = decode_audio_delta(event)
                if pcm and output_stream is not None:
                    await asyncio.to_thread(output_stream.write, pcm)
                    counters["audioChunksPlayed"] += 1

        # 运行会话
        if enhanced_audio_enabled and audio_stream:
            # 增强模式：不需要额外的 input_stream
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
                audio_stream.stop()
        else:
            # 原始模式
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

    # 生成会话摘要
    summary = {
        "ok": True,
        "savedAt": datetime.now().isoformat(timespec="seconds"),
        "sessionDir": str(session_dir.resolve()),
        "eventsPath": str(events_path.resolve()),
        "actionsPath": str(actions_path.resolve()),
        "model": args.model,
        "counters": counters,
    }
    
    # 添加音频处理统计
    if enhanced_audio_enabled and audio_stream:
        audio_stats = audio_stream.get_stats()
        summary["audioProcessing"] = audio_stats
        print(f"\n[enhanced-audio] 音频处理统计:")
        print(f"  处理块数: {audio_stats['processedChunks']}")
        print(f"  语音块数: {audio_stats['speechChunks']}")
        print(f"  语音比例: {audio_stats['speechRatio']:.1%}")
        if audio_stats.get('metricsSummary'):
            metrics = audio_stats['metricsSummary']
            print(f"  平均SNR: {metrics.get('avgSnrDb', 0):.1f} dB")
            print(f"  平均增益: {metrics.get('avgGainDb', 0):.1f} dB")
    
    session_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


# 导入需要的函数
from mira_stepfun_realtime_voice_actions import _dispatch_transcript_async, _speak_planner_reply_async
import numpy as np


def parse_enhanced_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析增强版参数"""
    # 先调用原始参数解析
    parser = argparse.ArgumentParser(
        description="Enhanced live StepAudio realtime voice session with noise suppression.",
        parents=[],  # 不使用父解析器，手动添加所有参数
    )
    
    # 原始参数
    parser.add_argument("--api-key", default="")
    parser.add_argument("--endpoint", default=os.environ.get("STEPFUN_REALTIME_ENDPOINT", DEFAULT_REALTIME_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("STEPFUN_REALTIME_MODEL", DEFAULT_REALTIME_MODEL))
    parser.add_argument("--voice", default=os.environ.get("STEPFUN_REALTIME_VOICE", DEFAULT_VOICE))
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--websocket-ping-interval", type=float, default=float(os.environ.get("STEPFUN_REALTIME_WEBSOCKET_PING_INTERVAL", DEFAULT_WEBSOCKET_PING_INTERVAL)))
    parser.add_argument("--websocket-ping-timeout", type=float, default=float(os.environ.get("STEPFUN_REALTIME_WEBSOCKET_PING_TIMEOUT", DEFAULT_WEBSOCKET_PING_TIMEOUT)))
    parser.add_argument("--input-device", default=os.environ.get("MIRA_LIGHT_INPUT_DEVICE", "default"))
    parser.add_argument("--device", dest="input_device", help=argparse.SUPPRESS)
    parser.add_argument("--input-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_INPUT_SAMPLE_RATE", DEFAULT_INPUT_SAMPLE_RATE)))
    parser.add_argument("--output-sample-rate", type=int, default=int(os.environ.get("STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE", DEFAULT_OUTPUT_SAMPLE_RATE)))
    parser.add_argument("--chunk-ms", type=int, default=int(os.environ.get("STEPFUN_REALTIME_MIC_CHUNK_MS", DEFAULT_CHUNK_MS)))
    parser.add_argument("--seconds", type=float, default=float(os.environ.get("STEPFUN_REALTIME_SESSION_SECONDS", DEFAULT_SESSION_SECONDS)))
    parser.add_argument("--runtime-dir", default=str(Path(__file__).parent.parent / "runtime" / "stepfun-realtime-voice-actions"))
    parser.add_argument("--bridge-url", default=os.environ.get("MIRA_LIGHT_BRIDGE_URL", DEFAULT_BRIDGE_URL))
    parser.add_argument("--bridge-token", default=os.environ.get("MIRA_LIGHT_BRIDGE_TOKEN", ""))
    parser.add_argument("--director-url", default=os.environ.get("MIRA_LIGHT_DIRECTOR_URL", ""))
    parser.add_argument("--director-token", default=os.environ.get("MIRA_LIGHT_DIRECTOR_TOKEN", ""))
    parser.add_argument("--action-timeout-seconds", type=int, default=int(os.environ.get("MIRA_LIGHT_ACTION_TIMEOUT_SECONDS", "5")))
    parser.add_argument("--no-voice-state-actions", action="store_true")
    parser.add_argument("--no-semantic-actions", action="store_true")
    parser.add_argument("--no-trigger", dest="no_semantic_actions", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--assistant-text-actions", action="store_true", default=env_flag("MIRA_LIGHT_ASSISTANT_TEXT_ACTIONS", False))
    parser.add_argument("--no-assistant-text-actions", dest="assistant_text_actions", action="store_false")
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--dry-run-audio", dest="no_play", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--speak-planner-reply", action="store_true", default=env_flag("MIRA_LIGHT_SPEAK_PLANNER_REPLY", False))
    parser.add_argument("--no-speak-planner-reply", dest="speak_planner_reply", action="store_false")
    parser.add_argument("--planner-reply-voice", default=os.environ.get("MIRA_LIGHT_PLANNER_REPLY_VOICE", "tts"))
    parser.add_argument("--planner-reply-wait", action="store_true", default=env_flag("MIRA_LIGHT_PLANNER_REPLY_WAIT", False))
    parser.add_argument("--no-planner-reply-wait", dest="planner_reply_wait", action="store_false")
    parser.add_argument("--manual-response-create-on-speech-stop", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
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
    
    # ═════════════════════════════════════════════════════════════════════════
    # 增强音频参数（新增）
    # ═════════════════════════════════════════════════════════════════════════
    parser.add_argument(
        "--enhanced-audio",
        action="store_true",
        default=env_flag("MIRA_LIGHT_ENHANCED_AUDIO", True),
        help="启用增强音频处理（降噪+VAD+AGC）",
    )
    parser.add_argument(
        "--no-enhanced-audio",
        dest="enhanced_audio",
        action="store_false",
        help="禁用增强音频处理，回退到原始模式",
    )
    parser.add_argument(
        "--denoise-model",
        default=os.environ.get("MIRA_LIGHT_DENOISE_MODEL", "deepfilternet2"),
        choices=["deepfilternet2", "deepfilternet"],
        help="降噪模型选择",
    )
    parser.add_argument(
        "--no-denoise",
        action="store_true",
        help="禁用降噪",
    )
    parser.add_argument(
        "--no-vad-enhance",
        action="store_true",
        help="禁用增强VAD",
    )
    parser.add_argument(
        "--no-agc",
        action="store_true",
        help="禁用自动增益控制",
    )
    parser.add_argument(
        "--audio-metrics",
        action="store_true",
        default=env_flag("MIRA_LIGHT_AUDIO_METRICS", False),
        help="显示音频质量指标",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=float(os.environ.get("MIRA_LIGHT_VAD_THRESHOLD", "0.5")),
        help="VAD检测阈值 (0.0-1.0)",
    )
    parser.add_argument(
        "--target-rms",
        type=float,
        default=float(os.environ.get("MIRA_LIGHT_TARGET_RMS", "0.1")),
        help="目标RMS电平",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="列出可用音频设备并退出",
    )
    
    return parser.parse_args(argv)


def cmd_list_devices():
    """列出音频设备"""
    capture = EnhancedAudioCapture()
    devices = capture.list_devices()
    
    print("\n" + "=" * 70)
    print("音频输入设备列表")
    print("=" * 70)
    
    if not devices:
        print("未找到输入设备")
        return 1
    
    for i, device in enumerate(devices):
        real_marker = "✓ 真实麦克风" if device.is_real_microphone else "  虚拟设备"
        print(f"\n[{i}] 设备索引: {device.index}")
        print(f"    名称: {device.name}")
        print(f"    输入通道: {device.inputs}")
        print(f"    默认采样率: {int(device.default_sample_rate)} Hz")
        print(f"    类型: {real_marker} (置信度: {device.confidence_score:.2f})")
    
    print("\n" + "=" * 70)
    print(f"总计: {len(devices)} 个设备")
    print("=" * 70 + "\n")
    
    return 0


def main() -> int:
    args = parse_enhanced_args()
    
    # 如果请求列出设备
    if args.list_devices:
        return cmd_list_devices()
    
    try:
        if args.dry_run:
            result = build_live_session_preview(args)
        else:
            result = asyncio.run(run_enhanced_live_session_async(args))
        
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
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[realtime-voice-actions-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
