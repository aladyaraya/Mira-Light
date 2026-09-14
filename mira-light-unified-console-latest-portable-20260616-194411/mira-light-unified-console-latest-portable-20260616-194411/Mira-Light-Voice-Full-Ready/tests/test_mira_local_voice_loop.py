from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_local_voice_loop import dispatch_transcript_once  # noqa: E402


def test_dispatch_transcript_once_routes_tired_text_through_realtime_orchestrator() -> None:
    calls: list[dict] = []

    def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
        calls.append({"url": url, "payload": payload})
        return {"ok": True}

    transcript = "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])

    result = dispatch_transcript_once(
        transcript,
        bridge_url="http://127.0.0.1:19783",
        post_json=fake_post,
        speak_reply=False,
    )

    assert result["ok"] is True
    assert result["transcript"] == transcript
    assert result["actions"][0]["source"] == "local-intent"
    assert result["actions"][0]["plan"]["plan"]["action"] == {"type": "trigger", "name": "voice_tired"}
    assert calls[0]["url"] == "http://127.0.0.1:19783/v1/mira-light/trigger"
    assert calls[0]["payload"]["event"] == "voice_tired"
    assert result["reply"]


def test_dispatch_transcript_once_can_speak_local_reply_after_action() -> None:
    calls: list[dict] = []

    def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
        calls.append({"url": url, "payload": payload})
        return {"ok": True}

    transcript = "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])

    result = dispatch_transcript_once(
        transcript,
        bridge_url="http://127.0.0.1:19783",
        post_json=fake_post,
        speak_reply=True,
    )

    assert result["speak"]["ok"] is True
    assert calls[-1]["url"] == "http://127.0.0.1:19783/v1/mira-light/speak"
    assert calls[-1]["payload"]["text"] == result["reply"]


def test_dispatch_transcript_once_waits_for_running_scene_before_speaking() -> None:
    calls: list[dict] = []
    health_calls: list[str] = []

    def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
        calls.append({"url": url, "payload": payload})
        if url.endswith("/trigger"):
            return {"ok": True, "runtime": {"running": True, "runningScene": "voice_demo_tired"}}
        return {"ok": True}

    def fake_get(url: str, *, token: str = "", timeout_seconds: int = 5) -> dict:
        health_calls.append(url)
        return {"ok": True, "runtime": {"running": len(health_calls) == 1}}

    transcript = "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])

    result = dispatch_transcript_once(
        transcript,
        bridge_url="http://127.0.0.1:19783",
        post_json=fake_post,
        get_json=fake_get,
        speak_reply=True,
        idle_poll_interval_seconds=0,
    )

    assert result["speak"]["ok"] is True
    assert health_calls == [
        "http://127.0.0.1:19783/health",
        "http://127.0.0.1:19783/health",
    ]
    assert calls[-1]["url"] == "http://127.0.0.1:19783/v1/mira-light/speak"


def test_dispatch_transcript_once_reports_scene_completion_error_without_speech() -> None:
    calls: list[dict] = []
    health_calls: list[str] = []

    def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
        calls.append({"url": url, "payload": payload})
        return {"ok": True, "runtime": {"running": True, "runningScene": "voice_demo_tired"}}

    def fake_get(url: str, *, token: str = "", timeout_seconds: int = 5) -> dict:
        health_calls.append(url)
        return {
            "ok": True,
            "runtime": {
                "running": False,
                "lastError": "servo endpoint did not acknowledge command",
                "lastFinishedScene": "voice_demo_tired",
            },
        }

    transcript = "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])

    result = dispatch_transcript_once(
        transcript,
        bridge_url="http://127.0.0.1:19783",
        post_json=fake_post,
        get_json=fake_get,
        speak_reply=False,
        idle_poll_interval_seconds=0,
    )

    assert result["ok"] is False
    assert "did not acknowledge" in result["error"]
    assert result["completion"]["runtime"]["lastFinishedScene"] == "voice_demo_tired"
    assert health_calls == ["http://127.0.0.1:19783/health"]


def test_dispatch_transcript_once_reports_immediate_bridge_error() -> None:
    def fake_post(url: str, payload: dict, *, token: str = "", timeout_seconds: int = 5) -> dict:
        return {"ok": False, "error": "HTTP 500: servo endpoint did not acknowledge"}

    transcript = "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])

    result = dispatch_transcript_once(
        transcript,
        bridge_url="http://127.0.0.1:19783",
        post_json=fake_post,
        speak_reply=False,
    )

    assert result["ok"] is False
    assert "did not acknowledge" in result["error"]
