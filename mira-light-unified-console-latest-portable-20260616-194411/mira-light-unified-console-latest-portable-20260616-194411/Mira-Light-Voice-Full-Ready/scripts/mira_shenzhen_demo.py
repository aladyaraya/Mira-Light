#!/usr/bin/env python3
"""Shenzhen booth demo cue runner for Mira Light.

Default path:
local cue text -> bridge /voice-lab/plan(useStepFun=false) -> scene/trigger.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

from mira_light_audio import AudioCuePlayer
from mira_realtime_action_orchestrator import DEFAULT_BRIDGE_URL, post_json_request


ROOT = Path(__file__).resolve().parents[1]

SHENZHEN_DEMO_CUES: dict[str, dict[str, Any]] = {
    "wake": {
        "title": "Wake up",
        "transcript": "醒一醒，Mira",
        "audio": "shenzhen_demo/wake.wav",
        "expectedAction": {"type": "scene", "name": "wake_up"},
    },
    "tired": {
        "title": "I am tired",
        "transcript": "我好累啊",
        "audio": "shenzhen_demo/tired.wav",
        "expectedAction": {"type": "trigger", "name": "voice_tired"},
    },
    "praise": {
        "title": "Praise",
        "transcript": "你好可爱",
        "audio": "shenzhen_demo/praise.wav",
        "expectedAction": {"type": "trigger", "name": "praise_detected"},
    },
    "celebrate": {
        "title": "Celebrate",
        "transcript": "可以跳个舞吗",
        "audio": "shenzhen_demo/celebrate.wav",
        "expectedAction": {"type": "scene", "name": "celebrate"},
    },
    "farewell": {
        "title": "Farewell",
        "transcript": "我先走了，再见",
        "audio": "shenzhen_demo/farewell.wav",
        "expectedAction": {"type": "trigger", "name": "farewell_detected"},
    },
    "sleep": {
        "title": "Sleep",
        "transcript": "休息一下",
        "audio": "shenzhen_demo/sleep.wav",
        "expectedAction": {"type": "scene", "name": "sleep"},
    },
}


def cue_or_raise(name: str) -> dict[str, Any]:
    cue = SHENZHEN_DEMO_CUES.get(name)
    if cue is None:
        choices = ", ".join(sorted(SHENZHEN_DEMO_CUES))
        raise ValueError(f"Unknown cue: {name}. Available: {choices}")
    return cue


def build_cue_plan_request(
    cue_name: str,
    *,
    bridge_url: str,
    use_stepfun: bool = False,
    dispatch: bool = True,
) -> dict[str, Any]:
    cue = cue_or_raise(cue_name)
    url = f"{bridge_url.rstrip('/')}/v1/mira-light/voice-lab/plan"
    payload = {
        "transcript": cue["transcript"],
        "useStepFun": bool(use_stepfun),
        "dispatch": bool(dispatch),
        "context": {
            "source": "shenzhen-demo",
            "cue": cue_name,
            "cueMode": "local-demo",
            "createdAt": datetime.now().isoformat(timespec="seconds"),
        },
    }
    return {
        "method": "POST",
        "url": url,
        "payload": payload,
        "expectedAction": dict(cue["expectedAction"]),
    }


def build_audio_preview(cue_name: str, *, no_audio: bool, wait: bool, voice: str) -> dict[str, Any]:
    cue = cue_or_raise(cue_name)
    return {
        "enabled": not bool(no_audio),
        "asset": cue["audio"],
        "wait": bool(wait),
        "voice": voice,
        "allowMissing": True,
    }


def build_dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "ok": True,
        "dryRun": True,
        "mode": "shenzhen-local-demo",
        "cue": args.cue,
        "title": cue_or_raise(args.cue)["title"],
        "bridgeUrl": args.bridge_url,
        "audio": build_audio_preview(
            args.cue,
            no_audio=bool(args.no_audio),
            wait=bool(args.audio_wait),
            voice=args.audio_voice,
        ),
        "request": build_cue_plan_request(
            args.cue,
            bridge_url=args.bridge_url,
            use_stepfun=bool(args.use_stepfun),
            dispatch=bool(args.dispatch),
        ),
        "cloudDependency": bool(args.use_stepfun),
    }


def run_cue(args: argparse.Namespace) -> dict[str, Any]:
    cue = cue_or_raise(args.cue)
    audio_result: dict[str, Any] | None = None
    if not args.no_audio:
        player = AudioCuePlayer(dry_run=False)
        audio_result = player.play_asset(cue["audio"], wait=bool(args.audio_wait), allow_missing=True)

    request = build_cue_plan_request(
        args.cue,
        bridge_url=args.bridge_url,
        use_stepfun=bool(args.use_stepfun),
        dispatch=bool(args.dispatch),
    )
    response = post_json_request(
        request["url"],
        request["payload"],
        token=args.bridge_token,
        timeout_seconds=int(args.timeout_seconds),
    )
    return {
        "ok": bool(response.get("ok")),
        "mode": "shenzhen-local-demo",
        "cue": args.cue,
        "title": cue["title"],
        "audio": audio_result,
        "request": request,
        "response": response,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Shenzhen Mira Light demo cue.")
    parser.add_argument("--cue", choices=sorted(SHENZHEN_DEMO_CUES), default="tired")
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--bridge-token", default="")
    parser.add_argument("--use-stepfun", action="store_true")
    parser.add_argument("--dispatch", action="store_true", default=True)
    parser.add_argument("--no-dispatch", dest="dispatch", action="store_false")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--audio-wait", action="store_true")
    parser.add_argument("--audio-voice", default="tts")
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--list-cues", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list_cues:
        payload = {
            "ok": True,
            "cues": [
                {"name": name, **cue}
                for name, cue in sorted(SHENZHEN_DEMO_CUES.items())
            ],
        }
    elif args.dry_run:
        payload = build_dry_run_payload(args)
    else:
        payload = run_cue(args)

    if args.json or args.dry_run or args.list_cues:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Ran cue={payload['cue']} ok={payload['ok']}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
