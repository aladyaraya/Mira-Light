#!/usr/bin/env python
"""Edge-TTS playback helper for Mira Light on Windows.
Uses Microsoft Edge's free neural TTS (much more natural than System.Speech).
Usage: python speaker-edge-tts-play.py "你好吗"
"""
import asyncio
import sys
import tempfile
import os
import subprocess
import time


async def speak(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        await communicate.save(path)
        # Play via Windows default media player (non-blocking)
        os.startfile(path)
        # Brief wait for playback to start, then file will be cleaned later
        time.sleep(2)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass  # still playing, cleanup next time


def main() -> None:
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not text.strip():
        print("Usage: python speaker-edge-tts-play.py <text>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(speak(text))


if __name__ == "__main__":
    main()
