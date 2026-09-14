#!/usr/bin/env python3
"""Windows-friendly microphone capture utility for Mira Light voice work.

This is the first local loop in the Windows voice stack:

Windows microphone -> WAV file -> metadata JSON

It intentionally avoids macOS-only tools and does not import mlx-whisper.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import json
import math
import os
from pathlib import Path
import queue
import sys
import threading
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / "runtime" / "windows-voice-capture"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_MODE = "vad"
DEFAULT_SECONDS = 5.0
DEFAULT_CHUNK_MS = 50
DEFAULT_VAD_START_MS = 120
DEFAULT_VAD_END_MS = 900
DEFAULT_VAD_MIN_RMS = 0.003
DEFAULT_VAD_SPEECH_RATIO = 1.5
DEFAULT_MIN_UTTERANCE_MS = 400
DEFAULT_MAX_UTTERANCE_SECONDS = 8.0
DEFAULT_MAX_WAIT_SECONDS = 30.0
DEFAULT_PREROLL_MS = 250

np = None
sd = None
sf = None


def require_audio_deps() -> None:
    global np, sd, sf
    if np is not None and sd is not None and sf is not None:
        return
    try:
        import numpy as numpy_module
        import sounddevice as sounddevice_module
        import soundfile as soundfile_module
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing Windows audio dependency. Run: "
            "python -m pip install -r Mira-Light-Voice-Full-Ready\\requirements-windows-voice.txt"
        ) from exc
    np = numpy_module
    sd = sounddevice_module
    sf = soundfile_module


@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str
    inputs: int
    default_sample_rate: float


@dataclass(frozen=True)
class CaptureResult:
    samples: np.ndarray
    sample_rate: int
    mode: str
    device: InputDevice
    meta: dict[str, Any]


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")


def list_input_devices() -> list[InputDevice]:
    require_audio_deps()
    devices: list[InputDevice] = []
    for index, device in enumerate(sd.query_devices()):
        inputs = int(device.get("max_input_channels") or 0)
        if inputs <= 0:
            continue
        devices.append(
            InputDevice(
                index=index,
                name=str(device.get("name") or ""),
                inputs=inputs,
                default_sample_rate=float(device.get("default_samplerate") or 0.0),
            )
        )
    return devices


def print_input_devices() -> int:
    devices = list_input_devices()
    if not devices:
        print("No input devices found.")
        return 1
    print("Input devices:")
    for device in devices:
        print(
            f"{device.index:>2}  {device.name}  "
            f"(inputs={device.inputs}, default_sr={int(device.default_sample_rate)})"
        )
    return 0


def resolve_input_device(device_hint: str | None) -> InputDevice:
    """解析输入设备，优先选择真实麦克风（排除虚拟/模拟设备）。"""
    devices = list_input_devices()
    if not devices:
        raise RuntimeError("No input devices available")

    resolved_hint = (
        device_hint
        or os.environ.get("MIRA_LIGHT_INPUT_DEVICE")
        or os.environ.get("MIRA_LIGHT_WINDOWS_MIC_DEVICE")
        or os.environ.get("MIRA_LIGHT_MIC_DEVICE")
        or ""
    ).strip()

    if resolved_hint and resolved_hint.lower() != "default":
        lowered = resolved_hint.lower()
        if lowered.isdigit():
            requested_index = int(lowered)
            for device in devices:
                if device.index == requested_index:
                    return device
        for device in devices:
            if lowered in device.name.lower():
                return device
        available = ", ".join(f"{item.index}:{item.name}" for item in devices)
        raise RuntimeError(f"Input device not found: {resolved_hint}. Available: {available}")

    # --- 智能选择：优先真实麦克风，排除虚拟设备 ---
    try:
        from audio_noise_suppressor import score_real_microphone, is_virtual_device
        scored = []
        for device in devices:
            if is_virtual_device(device.name):
                continue
            s = score_real_microphone(device.name)
            if s > 0:
                scored.append((device, s))
        if scored:
            scored.sort(key=lambda x: -x[1])
            chosen = scored[0][0]
            print(f"[mic] auto-selected real microphone: [{chosen.index}] {chosen.name} (score={scored[0][1]:.2f})")
            return chosen
    except ImportError:
        pass  # 回退到原始逻辑

    default_index: int | None = None
    try:
        default_device = sd.default.device
        if isinstance(default_device, (list, tuple)) and default_device:
            if default_device[0] is not None and int(default_device[0]) >= 0:
                default_index = int(default_device[0])
        elif default_device is not None and int(default_device) >= 0:
            default_index = int(default_device)
    except Exception:
        default_index = None

    if default_index is not None:
        for device in devices:
            if device.index == default_index:
                return device

    for preferred in ("microphone", "mic", "array", "realtek", "usb"):
        for device in devices:
            if preferred in device.name.lower():
                return device

    return devices[0]


def ensure_mono_float32(samples: np.ndarray) -> np.ndarray:
    require_audio_deps()
    array = np.asarray(samples, dtype=np.float32)
    if array.ndim == 1:
        return array
    return array.mean(axis=1, dtype=np.float32)


def audio_metrics(samples: np.ndarray, sample_rate: int) -> dict[str, float]:
    mono = ensure_mono_float32(samples)
    if mono.size == 0:
        return {"durationMs": 0.0, "rms": 0.0, "peak": 0.0}
    rms = float(np.sqrt(np.mean(np.square(mono), dtype=np.float64)))
    peak = float(np.max(np.abs(mono)))
    duration_ms = float(mono.size / float(sample_rate) * 1000.0)
    return {"durationMs": round(duration_ms, 1), "rms": rms, "peak": peak}


def save_wav(samples: np.ndarray, *, sample_rate: int, path: Path) -> Path:
    require_audio_deps()
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, ensure_mono_float32(samples), sample_rate, subtype="PCM_16")
    return path


def capture_fixed(args: argparse.Namespace, device: InputDevice) -> CaptureResult:
    require_audio_deps()
    seconds = max(0.1, float(args.seconds))
    frame_count = max(1, int(args.sample_rate * seconds))
    print(f"[capture] fixed {seconds:.1f}s from device {device.index}: {device.name}")
    samples = sd.rec(
        frame_count,
        samplerate=args.sample_rate,
        channels=args.channels,
        dtype="float32",
        device=device.index,
    )
    sd.wait()
    mono = ensure_mono_float32(samples)
    return CaptureResult(
        samples=mono,
        sample_rate=args.sample_rate,
        mode="fixed",
        device=device,
        meta={"seconds": seconds, "frames": int(mono.size)},
    )


def capture_ptt(args: argparse.Namespace, device: InputDevice) -> CaptureResult:
    require_audio_deps()
    print(f"[capture] push-to-talk from device {device.index}: {device.name}")
    print("Press Enter to start recording.")
    input()
    print("Recording. Press Enter again to stop.")

    chunks: list[np.ndarray] = []
    stop_event = threading.Event()

    def callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        del frames, time_info
        if status:
            print(f"[audio-status] {status}", file=sys.stderr)
        chunks.append(indata.copy())
        if stop_event.is_set():
            raise sd.CallbackStop

    with sd.InputStream(
        samplerate=args.sample_rate,
        channels=args.channels,
        dtype="float32",
        callback=callback,
        device=device.index,
    ):
        input()
        stop_event.set()

    if not chunks:
        raise RuntimeError("No audio captured")
    mono = ensure_mono_float32(np.concatenate(chunks, axis=0))
    return CaptureResult(
        samples=mono,
        sample_rate=args.sample_rate,
        mode="ptt",
        device=device,
        meta={"frames": int(mono.size)},
    )


def capture_vad(args: argparse.Namespace, device: InputDevice) -> CaptureResult:
    require_audio_deps()
    sample_rate = int(args.sample_rate)
    chunk_ms = max(10, int(args.chunk_ms))
    chunk_frames = max(1, int(sample_rate * chunk_ms / 1000.0))
    start_chunks = max(1, math.ceil(args.vad_start_ms / chunk_ms))
    end_chunks = max(1, math.ceil(args.vad_end_ms / chunk_ms))
    min_chunks = max(1, math.ceil(args.min_utterance_ms / chunk_ms))
    max_chunks = max(1, math.ceil(args.max_utterance_seconds * 1000.0 / chunk_ms))
    max_wait_chunks = max(1, math.ceil(args.max_wait_seconds * 1000.0 / chunk_ms))
    preroll_chunks = max(0, math.ceil(args.preroll_ms / chunk_ms))

    print(f"[capture] vad from device {device.index}: {device.name}")
    print(
        "[capture] waiting for speech "
        f"(threshold=max({args.vad_min_rms}, noise*{args.vad_speech_ratio}))"
    )

    chunk_queue: queue.Queue[np.ndarray] = queue.Queue()
    errors: list[str] = []

    def callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        del frames, time_info
        if status:
            errors.append(str(status))
        chunk_queue.put(indata.copy())

    noise_floor = float(args.vad_min_rms)
    speech_run = 0
    silence_run = 0
    observed_chunks = 0
    started = False
    started_at_chunk = 0
    preroll: deque[np.ndarray] = deque(maxlen=preroll_chunks)
    captured: list[np.ndarray] = []

    with sd.InputStream(
        samplerate=sample_rate,
        channels=args.channels,
        dtype="float32",
        blocksize=chunk_frames,
        callback=callback,
        device=device.index,
    ):
        while True:
            if observed_chunks > max_wait_chunks and not started:
                raise RuntimeError("Timed out waiting for speech")
            try:
                chunk = chunk_queue.get(timeout=1.0)
            except queue.Empty as exc:
                raise RuntimeError("No microphone data received") from exc

            observed_chunks += 1
            mono_chunk = ensure_mono_float32(chunk)
            rms = float(np.sqrt(np.mean(np.square(mono_chunk), dtype=np.float64))) if mono_chunk.size else 0.0
            threshold = max(float(args.vad_min_rms), noise_floor * float(args.vad_speech_ratio))
            is_speech = rms >= threshold

            if not started:
                if not is_speech:
                    noise_floor = (noise_floor * 0.96) + (max(rms, 1e-6) * 0.04)
                if preroll_chunks:
                    preroll.append(mono_chunk)
                speech_run = speech_run + 1 if is_speech else 0
                if speech_run >= start_chunks:
                    started = True
                    started_at_chunk = observed_chunks
                    captured.extend(list(preroll))
                    print(f"[capture] speech started rms={rms:.5f} threshold={threshold:.5f}")
                continue

            captured.append(mono_chunk)
            captured_chunks = observed_chunks - started_at_chunk + len(preroll)
            if is_speech:
                silence_run = 0
            else:
                silence_run += 1

            enough_audio = captured_chunks >= min_chunks
            reached_silence = enough_audio and silence_run >= end_chunks
            reached_max = captured_chunks >= max_chunks
            if reached_silence or reached_max:
                reason = "silence" if reached_silence else "max-duration"
                print(f"[capture] speech ended reason={reason}")
                break

    if errors:
        print(f"[audio-status] {'; '.join(errors[-3:])}", file=sys.stderr)
    if not captured:
        raise RuntimeError("No speech captured")

    mono = ensure_mono_float32(np.concatenate(captured, axis=0))
    return CaptureResult(
        samples=mono,
        sample_rate=sample_rate,
        mode="vad",
        device=device,
        meta={
            "chunkMs": chunk_ms,
            "vadStartMs": int(args.vad_start_ms),
            "vadEndMs": int(args.vad_end_ms),
            "vadMinRms": float(args.vad_min_rms),
            "vadSpeechRatio": float(args.vad_speech_ratio),
            "noiseFloor": noise_floor,
            "observedChunks": observed_chunks,
            "frames": int(mono.size),
        },
    )


def default_output_path(runtime_dir: Path) -> Path:
    return runtime_dir / timestamp_slug() / "input.wav"


def write_metadata(path: Path, payload: dict[str, Any]) -> Path:
    metadata_path = path.with_suffix(".json")
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Windows microphone audio for Mira Light.")
    parser.add_argument("--list-devices", action="store_true", help="List input devices and exit.")
    parser.add_argument("--device", help="Input device index or name substring.")
    parser.add_argument("--mode", choices=["fixed", "vad", "ptt"], default=os.environ.get("MIRA_LIGHT_CAPTURE_MODE", DEFAULT_MODE))
    parser.add_argument("--seconds", type=float, default=DEFAULT_SECONDS, help="Fixed capture duration.")
    parser.add_argument("--sample-rate", type=int, default=int(os.environ.get("MIRA_LIGHT_SAMPLE_RATE", DEFAULT_SAMPLE_RATE)))
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS)
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--output", help="Output WAV path. Defaults to runtime/windows-voice-capture/<timestamp>/input.wav.")
    parser.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    parser.add_argument("--vad-start-ms", type=int, default=DEFAULT_VAD_START_MS)
    parser.add_argument("--vad-end-ms", type=int, default=DEFAULT_VAD_END_MS)
    parser.add_argument("--vad-min-rms", type=float, default=DEFAULT_VAD_MIN_RMS)
    parser.add_argument("--vad-speech-ratio", type=float, default=DEFAULT_VAD_SPEECH_RATIO)
    parser.add_argument("--min-utterance-ms", type=int, default=DEFAULT_MIN_UTTERANCE_MS)
    parser.add_argument("--max-utterance-seconds", type=float, default=DEFAULT_MAX_UTTERANCE_SECONDS)
    parser.add_argument("--max-wait-seconds", type=float, default=DEFAULT_MAX_WAIT_SECONDS)
    parser.add_argument("--preroll-ms", type=int, default=DEFAULT_PREROLL_MS)
    parser.add_argument("--json", action="store_true", help="Print only JSON result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.list_devices:
            return print_input_devices()

        device = resolve_input_device(args.device)
        if args.mode == "fixed":
            result = capture_fixed(args, device)
        elif args.mode == "ptt":
            result = capture_ptt(args, device)
        else:
            result = capture_vad(args, device)

        output = Path(args.output).expanduser() if args.output else default_output_path(Path(args.runtime_dir).expanduser())
        wav_path = save_wav(result.samples, sample_rate=result.sample_rate, path=output)
        metrics = audio_metrics(result.samples, result.sample_rate)
        payload = {
            "ok": True,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "mode": result.mode,
            "path": str(wav_path),
            "sampleRate": result.sample_rate,
            "channels": 1,
            "device": {
                "index": result.device.index,
                "name": result.device.name,
                "inputs": result.device.inputs,
                "defaultSampleRate": result.device.default_sample_rate,
            },
            "audioMetrics": metrics,
            "capture": result.meta,
        }
        metadata_path = write_metadata(wav_path, payload)
        payload["metadataPath"] = str(metadata_path)

        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"[capture] saved {wav_path}")
            print(f"[capture] metadata {metadata_path}")
            print(
                "[capture] metrics "
                f"durationMs={metrics['durationMs']:.1f} "
                f"rms={metrics['rms']:.5f} peak={metrics['peak']:.5f}"
            )
        return 0
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"[capture-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
