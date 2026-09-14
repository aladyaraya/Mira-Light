#!/usr/bin/env python3
"""Lingzhu SDK usage examples and integration demos.

This script demonstrates the four SDK capabilities:
1. Basic text chat (backward compatible with existing client)
2. Multimodal: send camera frames to the cloud brain
3. Streaming: token-by-token response for lower latency
4. Session management with embodied + vision memory binding

Run:
    # Set environment variables first
    set MIRA_LIGHT_LINGZHU_BASE_URL=http://127.0.0.1:31879
    set MIRA_LIGHT_LINGZHU_AUTH_AK=your_ak

    # Run all demos
    python mira_lingzhu_sdk_demo.py

    # Run specific demo
    python mira_lingzhu_sdk_demo.py --demo basic
    python mira_lingzhu_sdk_demo.py --demo multimodal
    python mira_lingzhu_sdk_demo.py --demo streaming
    python mira_lingzhu_sdk_demo.py --demo session
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any


def demo_basic_chat() -> None:
    """Demo 1: Basic text chat (backward compatible)."""
    from mira_lingzhu_sdk import LingzhuSDK

    sdk = LingzhuSDK()
    if not sdk.is_healthy:
        print("[demo] WARNING: Lingzhu adapter not reachable. Running in degraded mode.")

    print("\n=== Demo 1: Basic Chat ===")
    response = sdk.chat("你好呀，Mira 在吗？")
    print(f"Reply: {response.text}")
    print(f"Model: {response.model}")
    print(f"Latency: {response.latency_ms}ms")


def demo_multimodal() -> None:
    """Demo 2: Send a camera frame to the cloud brain."""
    from mira_lingzhu_sdk import LingzhuSDK
    from mira_vision_context import get_latest_scene

    sdk = LingzhuSDK()

    print("\n=== Demo 2: Multimodal Chat ===")

    # Try to get a frame from the vision engine
    frame = None
    try:
        from mira_vision_context import get_vision_engine
        engine = get_vision_engine()
        if engine and engine.is_running():
            # Access the frame provider
            frame = engine.frame_provider()
    except Exception:
        pass

    if frame is None:
        print("[demo] No camera frame available. Use a test image instead.")
        # Create a dummy frame for testing
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (100, 150, 200)  # blue-ish
        print("[demo] Using a dummy blue frame for testing.")

    # Get current vision context if available
    scene = get_latest_scene()
    vision_ctx = scene.to_tracking_context() if scene else None

    response = sdk.chat_with_image(
        "看看你现在看到了什么？",
        frame=frame,
        vision_context=vision_ctx,
    )
    print(f"Reply: {response.text}")
    print(f"Model: {response.model}")


def demo_streaming() -> None:
    """Demo 3: Stream a response token by token."""
    from mira_lingzhu_sdk import LingzhuSDK

    sdk = LingzhuSDK()

    print("\n=== Demo 3: Streaming Chat ===")
    print("Streaming: ", end="", flush=True)
    full_text = ""
    started = time.perf_counter()
    first_token_time = None

    for token in sdk.chat_stream("给我讲一个关于小灯宠物的短故事"):
        if first_token_time is None:
            first_token_time = time.perf_counter() - started
        print(token, end="", flush=True)
        full_text += token

    total_time = time.perf_counter() - started
    print(f"\n\n[metrics] first-token: {first_token_time:.2f}s  total: {total_time:.2f}s  chars: {len(full_text)}")


def demo_session() -> None:
    """Demo 4: Session management with memory binding."""
    from mira_lingzhu_sdk import LingzhuSDK

    sdk = LingzhuSDK()

    print("\n=== Demo 4: Session & Memory ===")

    # Create a session
    session = sdk.create_session(user_id="demo-user")
    print(f"Session: {session.session_id}")

    # Bind embodied memory (mira-light-bridge context)
    sdk.bind_embodied_memory(session)
    print(f"Memory contexts: {session.additional_user_ids}")

    # Bind vision memory
    sdk.bind_vision_memory(session)
    print(f"Memory contexts after vision binding: {session.additional_user_ids}")

    # Multi-turn conversation
    turns = [
        "你好，我是第一次和你聊天",
        "你还记得我刚说了什么吗？",
        "我现在在看着一个蓝色的杯子",
    ]

    for turn in turns:
        print(f"\n[user] {turn}")
        response = sdk.chat_in_session(session, turn)
        print(f"[mira] {response.text}")

    # Show session info
    info = sdk.get_session_info(session.session_id)
    print(f"\n[session] {info}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lingzhu SDK demo")
    parser.add_argument(
        "--demo",
        choices=["basic", "multimodal", "streaming", "session", "all"],
        default="all",
        help="Which demo to run (default: all)",
    )
    args = parser.parse_args()

    if args.demo in ("basic", "all"):
        try:
            demo_basic_chat()
        except Exception as exc:
            print(f"[demo-basic] error: {exc}")

    if args.demo in ("multimodal", "all"):
        try:
            demo_multimodal()
        except Exception as exc:
            print(f"[demo-multimodal] error: {exc}")

    if args.demo in ("streaming", "all"):
        try:
            demo_streaming()
        except Exception as exc:
            print(f"[demo-streaming] error: {exc}")

    if args.demo in ("session", "all"):
        try:
            demo_session()
        except Exception as exc:
            print(f"[demo-session] error: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
