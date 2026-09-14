#!/usr/bin/env python3
"""End-to-end text simulation test for the Mira Light voice→action pipeline.

This script tests the FULL pipeline WITHOUT a microphone, using text input
to simulate voice transcripts. It verifies each layer:

  Layer 1: Local intent classification (keyword matching)
  Layer 2: StepFun LLM Planner (step-3.7-flash API call)
  Layer 3: Action Orchestrator → Bridge HTTP dispatch
  Layer 4: Bridge health + scene execution

Usage:
  python test_voice_pipeline_e2e.py --test all
  python test_voice_pipeline_e2e.py --test local-intents
  python test_voice_pipeline_e2e.py --test api-key
  python test_voice_pipeline_e2e.py --test llm-planner
  python test_voice_pipeline_e2e.py --test bridge-health
  python test_voice_pipeline_e2e.py --test e2e
  python test_voice_pipeline_e2e.py --test dispatch --text "跳舞"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure scripts dir is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ─── Helpers ───────────────────────────────────────────────────────────────

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
SKIP = "\033[93m⊘ SKIP\033[0m"
INFO = "\033[94mℹ INFO\033[0m"

def _print_result(label: str, passed: bool, detail: str = "") -> None:
    status = PASS if passed else FAIL
    msg = f"  {status}  {label}"
    if detail:
        msg += f"  →  {detail}"
    print(msg)

def _print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def _load_env_file(path: Path) -> dict[str, str]:
    """Load KEY=VALUE pairs from an env file (ignoring comments/exports)."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


# ─── Test: Local Intent Classification ─────────────────────────────────────

def test_local_intents() -> bool:
    """Test keyword-based intent classification without any API calls."""
    _print_section("Layer 1: Local Intent Classification")
    from mira_voice_intents import classify_intent, action_for_intent, scene_for_command

    test_cases = [
        ("跳舞", "scene:celebrate", {"type": "scene", "name": "celebrate"}),
        ("跳个舞", "scene:celebrate", {"type": "scene", "name": "celebrate"}),
        ("庆祝一下", "scene:celebrate", {"type": "scene", "name": "celebrate"}),
        ("好累", "comfort", {"type": "trigger", "name": "voice_tired"}),
        ("今天好累", "comfort", {"type": "trigger", "name": "voice_tired"}),
        ("拜拜", "farewell", {"type": "trigger", "name": "farewell_detected"}),
        ("再见", "farewell", {"type": "trigger", "name": "farewell_detected"}),
        ("好可爱", "praise", {"type": "trigger", "name": "praise_detected"}),
        ("起床", "scene:wake_up", {"type": "scene", "name": "wake_up"}),
        ("睡觉", "scene:sleep", {"type": "scene", "name": "sleep"}),
        ("你好", "chat", None),
        ("今天天气怎么样", "chat", None),
    ]

    all_passed = True
    for transcript, expected_intent, expected_action in test_cases:
        intent = classify_intent(transcript)
        action = action_for_intent(intent)
        intent_ok = intent == expected_intent
        if expected_action is None:
            action_ok = action is None or action.get("type") == "none"
        else:
            action_ok = action == expected_action

        passed = intent_ok and action_ok
        detail = f"intent={intent}"
        if action:
            detail += f"  action={action.get('type')}:{action.get('name')}"
        else:
            detail += "  action=none"

        _print_result(f'"{transcript}"', passed, detail)
        if not passed:
            all_passed = False
            if not intent_ok:
                print(f"         expected intent={expected_intent}, got={intent}")
            if not action_ok:
                print(f"         expected action={expected_action}, got={action}")

    return all_passed


# ─── Test: API Key Validation ──────────────────────────────────────────────

def test_api_key() -> bool:
    """Verify the StepFun API key is set and reachable."""
    _print_section("Layer 2: StepFun API Key Validation")

    api_key = os.environ.get("STEPFUN_API_KEY") or os.environ.get("STEP_API_KEY") or ""
    if not api_key:
        _print_result("STEPFUN_API_KEY env var set", False, "Not found in environment")
        return False
    _print_result("STEPFUN_API_KEY env var set", True, f"...{api_key[-8:]}")

    # Quick connectivity test: send a minimal chat completion request
    try:
        import requests
        endpoint = os.environ.get("STEPFUN_LLM_ENDPOINT", "https://api.stepfun.com/v1/chat/completions")
        proxy_url = os.environ.get("STEPFUN_PROXY_URL", "").strip()
        proxies = {"https": proxy_url, "http": proxy_url} if proxy_url else None

        # Also set env vars so other libraries (urllib, websockets) can find the proxy
        if proxy_url:
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["HTTP_PROXY"] = proxy_url
            _print_result("Proxy configured", True, proxy_url)

        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.environ.get("STEPFUN_LLM_MODEL", "step-3.7-flash"),
                "messages": [{"role": "user", "content": "回复OK"}],
                "max_tokens": 5,
                "temperature": 0.0,
            },
            timeout=30,
            proxies=proxies,
        )
        if resp.status_code == 200:
            body = resp.json()
            content = ""
            try:
                content = body["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                content = str(body)[:80]
            _print_result("StepFun API reachable", True, f"HTTP 200, response: {content[:40]}")
            return True
        else:
            _print_result("StepFun API reachable", False, f"HTTP {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as exc:
        _print_result("StepFun API reachable", False, str(exc)[:120])
        return False


# ─── Test: LLM Planner ────────────────────────────────────────────────────

def test_llm_planner() -> bool:
    """Test the step-3.7-flash LLM planner with a sample transcript."""
    _print_section("Layer 3: StepFun LLM Planner (step-3.7-flash)")

    from stepfun_llm_planner import plan_from_text, validate_plan

    test_cases = [
        ("我今天好累啊", "comfort/trigger"),
        ("跳个舞吧", "scene:celebrate"),
        ("你好呀", "chat/none"),
    ]

    all_passed = True
    for transcript, expected_hint in test_cases:
        print(f"\n  Testing: \"{transcript}\" (expect ~{expected_hint})")
        try:
            t0 = time.time()
            result = plan_from_text(transcript)
            elapsed = time.time() - t0

            plan = result.get("plan", {})
            validation = result.get("validation", {})
            action = plan.get("action", {})
            action_type = action.get("type", "?")
            action_name = action.get("name", "")
            speech = plan.get("speech", {})
            speech_text = speech.get("text", "")

            valid = validation.get("ok", False)
            _print_result(
                f"plan_from_text",
                valid,
                f"action={action_type}:{action_name}  speech=\"{speech_text[:30]}\"  ({elapsed:.1f}s)"
            )
            if not valid:
                all_passed = False
                print(f"         validation error: {validation.get('error')}")
        except Exception as exc:
            _print_result(f"plan_from_text", False, str(exc)[:120])
            all_passed = False

    return all_passed


# ─── Test: Bridge Health ──────────────────────────────────────────────────

def test_bridge_health(bridge_url: str = "http://127.0.0.1:19783") -> bool:
    """Check if the Action Bridge is running and healthy."""
    _print_section("Layer 4: Action Bridge Health")

    try:
        import requests
        resp = requests.get(f"{bridge_url}/health", timeout=3)
        if resp.status_code == 200:
            body = resp.json()
            is_healthy = body.get("ok") and body.get("service") == "mira-light-bridge"
            runtime = body.get("runtime", {})
            base_url = runtime.get("baseUrl", "?")
            dry_run = runtime.get("dryRun", "?")
            _print_result(
                "Bridge /health",
                is_healthy,
                f"service={body.get('service')}  baseUrl={base_url}  dryRun={dry_run}"
            )
            return is_healthy
        else:
            _print_result("Bridge /health", False, f"HTTP {resp.status_code}")
            return False
    except Exception as exc:
        _print_result("Bridge /health", False, f"连接失败: {exc}")
        print(f"         请先启动 Action Bridge:")
        print(f"         powershell Start-Mira-Light-Windows-Action-Bridge.ps1")
        return False


# ─── Test: End-to-End Dispatch ────────────────────────────────────────────

def test_e2e_dispatch(bridge_url: str = "http://127.0.0.1:19783", text: str = "") -> bool:
    """Full end-to-end: text → intent → planner → bridge POST → board action."""
    _print_section("Layer 5: End-to-End Dispatch")

    import requests
    from mira_voice_intents import classify_intent, action_for_intent
    from mira_realtime_action_orchestrator import (
        RealtimeActionConfig,
        RealtimeActionOrchestrator,
        build_local_fallback_plan,
        build_plan_action_request,
    )

    transcripts = [text] if text else ["跳舞", "好累", "起床"]

    # First check bridge
    try:
        resp = requests.get(f"{bridge_url}/health", timeout=3)
        if resp.status_code != 200 or not resp.json().get("ok"):
            _print_result("Bridge reachable", False, "Bridge not healthy")
            return False
        _print_result("Bridge reachable", True, bridge_url)
    except Exception as exc:
        _print_result("Bridge reachable", False, str(exc))
        return False

    all_passed = True
    for transcript in transcripts:
        print(f"\n  --- Dispatching: \"{transcript}\" ---")

        # Stop any running scene first
        try:
            requests.post(f"{bridge_url}/v1/mira-light/stop", json={}, timeout=3)
            time.sleep(0.5)
        except Exception:
            pass

        # Step 1: Local intent
        intent = classify_intent(transcript)
        action = action_for_intent(intent)
        _print_result(f"Local intent", True, f"intent={intent}  action={action}")

        # Step 2: Build action request using local fallback (fast, no LLM call)
        if action and action.get("type") != "none":
            plan = build_local_fallback_plan(transcript)
            plan_data = plan.get("plan", {})
            request = build_plan_action_request(
                plan_data,
                bridge_url=bridge_url,
                transcript=transcript,
            )
            if request:
                _print_result(
                    "Action request built",
                    True,
                    f"POST {request['url']}"
                )

                # Step 3: Actually POST to bridge
                try:
                    resp = requests.post(
                        request["url"],
                        json=request["payload"],
                        timeout=5,
                    )
                    body = resp.json()
                    ok = body.get("ok", False)
                    runtime = body.get("runtime", {})
                    running_scene = runtime.get("runningScene", "")
                    _print_result(
                        "Bridge POST",
                        ok,
                        f"HTTP {resp.status_code}  runningScene={running_scene}"
                    )
                    if not ok:
                        all_passed = False
                        print(f"         error: {body.get('error', 'unknown')}")
                    else:
                        print(f"         🎉 板端动作已触发: {request['payload'].get('scene') or request['payload'].get('event')}")

                    # Wait a moment then stop scene to avoid blocking next test
                    time.sleep(1)
                    try:
                        requests.post(f"{bridge_url}/v1/mira-light/stop", json={}, timeout=3)
                    except Exception:
                        pass

                except Exception as exc:
                    _print_result("Bridge POST", False, str(exc)[:100])
                    all_passed = False
            else:
                _print_result("Action request", False, "No request built (action type=none)")
        else:
            _print_result("No action needed", True, f"intent={intent} → chat, skipped")

    return all_passed


def test_single_dispatch(bridge_url: str, text: str) -> bool:
    """Dispatch a single text command through the full pipeline."""
    _print_section(f"Single Dispatch: \"{text}\"")

    from mira_voice_intents import classify_intent, action_for_intent

    intent = classify_intent(text)
    action = action_for_intent(intent)
    print(f"  {INFO}  intent={intent}  action={action}")

    if not action or action.get("type") == "none":
        # Try LLM planner for semantic understanding
        print(f"  {INFO}  No local keyword match, trying LLM planner...")
        try:
            from stepfun_llm_planner import plan_from_text
            result = plan_from_text(text)
            plan = result.get("plan", {})
            action = plan.get("action", {})
            print(f"  {INFO}  LLM plan: action={action}")
        except Exception as exc:
            _print_result("LLM Planner", False, str(exc)[:100])
            return False

    if action and action.get("type") not in ("none", ""):
        return test_e2e_dispatch(bridge_url, text)
    else:
        print(f"  {INFO}  This is a chat intent, no board action needed.")
        return True


# ─── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Mira Light voice pipeline end-to-end test")
    parser.add_argument("--test", default="all",
                        choices=["all", "local-intents", "api-key", "llm-planner", "bridge-health", "e2e", "dispatch"],
                        help="Which test layer to run")
    parser.add_argument("--text", default="", help="Text to dispatch (for --test dispatch)")
    parser.add_argument("--bridge-url", default="http://127.0.0.1:19783")
    parser.add_argument("--env-file", default="",
                        help="Path to .env file to load before running tests")
    args = parser.parse_args()

    # Load env file if specified
    if args.env_file:
        env_path = Path(args.env_file).resolve()
    else:
        env_path = Path(__file__).resolve().parents[1] / "config" / "windows-voice-stepfun.env"
    if env_path.exists():
        env = _load_env_file(env_path)
        for key, value in env.items():
            if value and key not in os.environ:
                os.environ[key] = value
        print(f"  {INFO}  Loaded env from: {env_path}")
        print(f"  {INFO}  STEPFUN_API_KEY: ...{os.environ.get('STEPFUN_API_KEY', '')[-8:]}")
        # Propagate proxy for requests/urllib/websockets
        proxy_url = os.environ.get("STEPFUN_PROXY_URL", "").strip()
        if proxy_url:
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["HTTP_PROXY"] = proxy_url
            print(f"  {INFO}  Proxy: {proxy_url}")
    else:
        print(f"  {SKIP}  No env file found at {env_path}")

    print(f"\n{'#'*60}")
    print(f"  Mira Light Voice Pipeline E2E Test")
    print(f"  Time: {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Test: {args.test}")
    print(f"  Bridge: {args.bridge_url}")
    print(f"{'#'*60}")

    results = {}

    if args.test in ("all", "local-intents"):
        results["local-intents"] = test_local_intents()

    if args.test in ("all", "api-key"):
        results["api-key"] = test_api_key()

    if args.test in ("all", "llm-planner"):
        results["llm-planner"] = test_llm_planner()

    if args.test in ("all", "bridge-health"):
        results["bridge-health"] = test_bridge_health(args.bridge_url)

    if args.test in ("all", "e2e"):
        results["e2e"] = test_e2e_dispatch(args.bridge_url)

    if args.test == "dispatch":
        if not args.text:
            print(f"\n  {FAIL}  --text is required for dispatch test")
            return 1
        results["dispatch"] = test_single_dispatch(args.bridge_url, args.text)

    # Summary
    _print_section("Summary")
    total_passed = 0
    total_failed = 0
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {name}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1

    print(f"\n  Total: {total_passed} passed, {total_failed} failed")
    if total_failed > 0:
        print(f"\n  Some tests failed. Check the output above for details.")
        return 1
    else:
        print(f"\n  🎉 All tests passed!")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
