#!/usr/bin/env python3
"""Play a local Mac celebration sound for the iPad-triggered celebration page."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave


SAMPLE_RATE = 44100
MAX_AMPLITUDE = 32767
CELEBRATION_DURATION_SECONDS = 10.20


def envelope(age: float, duration: float, attack: float = 0.018, release: float = 0.055) -> float:
    if age < 0 or age > duration:
        return 0.0
    if age < attack:
        return age / attack
    if age > duration - release:
        return max(0.0, (duration - age) / release)
    return 1.0


def tone_sample(age: float, frequency: float, wave_type: str) -> float:
    phase = 2 * math.pi * frequency * age
    if wave_type == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    if wave_type == "saw":
        cycle = (frequency * age) % 1.0
        return 2.0 * cycle - 1.0
    return math.sin(phase)


def add_tone(
    left: list[float],
    right: list[float],
    *,
    start: float,
    duration: float,
    frequency: float,
    gain: float,
    pan: float = 0.0,
    wave_type: str = "sine",
) -> None:
    start_index = max(0, int(start * SAMPLE_RATE))
    end_index = min(len(left), int((start + duration) * SAMPLE_RATE))
    left_gain = gain * (1.0 - max(0.0, pan) * 0.55)
    right_gain = gain * (1.0 + min(0.0, pan) * 0.55)
    for index in range(start_index, end_index):
        age = index / SAMPLE_RATE - start
        value = tone_sample(age, frequency, wave_type) * envelope(age, duration)
        left[index] += value * left_gain
        right[index] += value * right_gain


def build_celebration_audio(path: Path, profile: str) -> None:
    if profile == "silence":
        duration = 30.0
    elif profile == "click":
        duration = 0.22
    else:
        duration = CELEBRATION_DURATION_SECONDS
    total_samples = int(duration * SAMPLE_RATE)
    left = [0.0] * total_samples
    right = [0.0] * total_samples

    if profile == "silence":
        pass
    elif profile == "click":
        add_tone(left, right, start=0.01, duration=0.1, frequency=880.0, gain=0.22, wave_type="sine")
        add_tone(left, right, start=0.08, duration=0.11, frequency=1318.51, gain=0.16, wave_type="sine")
    else:
        add_tone(left, right, start=0.01, duration=0.1, frequency=880.0, gain=0.22, wave_type="sine")
        fanfare = [
            (0.00, 523.25, 0.28, -0.7),
            (0.16, 659.25, 0.28, 0.72),
            (0.32, 783.99, 0.30, -0.45),
            (0.52, 1046.50, 0.42, 0.45),
            (0.98, 880.00, 0.24, -0.6),
            (1.14, 987.77, 0.24, 0.62),
            (1.30, 1318.51, 0.40, 0.0),
        ]
        for start, frequency, note_duration, pan in fanfare:
            add_tone(left, right, start=start + 0.04, duration=note_duration, frequency=frequency, gain=0.18, pan=pan, wave_type="saw")
            add_tone(
                left,
                right,
                start=start + 0.04,
                duration=note_duration + 0.04,
                frequency=frequency * 0.5,
                gain=0.08,
                pan=pan * 0.7,
                wave_type="sine",
            )

        bass_pattern = [
            (0.00, 130.81, -0.7),
            (0.26, 130.81, 0.7),
            (0.52, 164.81, -0.5),
            (0.78, 174.61, 0.5),
            (1.04, 196.00, -0.7),
            (1.30, 220.00, 0.72),
            (1.56, 246.94, -0.45),
            (1.82, 261.63, 0.45),
        ]
        loop_start = 1.74
        loop_length = 2.08
        while loop_start < duration - 0.25:
            for offset, frequency, pan in bass_pattern:
                start = loop_start + offset
                if start > duration - 0.22:
                    continue
                add_tone(left, right, start=start, duration=0.20, frequency=frequency, gain=0.13, pan=pan, wave_type="square")
                add_tone(left, right, start=start, duration=0.16, frequency=frequency * 2, gain=0.07, pan=-pan * 0.75)
            loop_start += loop_length

        add_tone(left, right, start=9.55, duration=0.24, frequency=783.99, gain=0.12, pan=-0.35, wave_type="saw")
        add_tone(left, right, start=9.73, duration=0.30, frequency=1046.50, gain=0.14, pan=0.35, wave_type="saw")
        add_tone(left, right, start=9.96, duration=0.20, frequency=1318.51, gain=0.12, pan=0.0, wave_type="sine")

    peak = max(0.001, max(max(abs(value) for value in left), max(abs(value) for value in right)))
    normalizer = min(1.0, 0.92 / peak)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for left_value, right_value in zip(left, right):
            for value in (left_value, right_value):
                sample = int(max(-1.0, min(1.0, value * normalizer)) * MAX_AMPLITUDE)
                frames.extend(sample.to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(frames))


def main() -> int:
    parser = argparse.ArgumentParser(description="Play the Mira celebration sound on this Mac.")
    parser.add_argument("--profile", choices=["celebrate", "click", "silence"], default="celebrate")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    output = args.output or Path(tempfile.gettempdir()) / f"mira-light-{args.profile}-audio.wav"
    build_celebration_audio(output, args.profile)
    if args.build_only:
        print(output)
        return 0

    afplay = shutil.which("afplay")
    if not afplay:
        raise SystemExit("afplay is not available on this machine")
    subprocess.run([afplay, str(output)], check=False, timeout=max(8, int(CELEBRATION_DURATION_SECONDS + 2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
