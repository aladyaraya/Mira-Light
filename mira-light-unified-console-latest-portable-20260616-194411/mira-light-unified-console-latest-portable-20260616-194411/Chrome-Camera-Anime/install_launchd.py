#!/usr/bin/env python3
import argparse
import base64
import json
import os
import plistlib
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATE_DIR = Path.home() / ".openclaw-chrome-camera-anime"
WATCHER_LABEL = "com.javis.chrome-camera-anime.watcher"
WORKER_LABEL = "com.javis.chrome-camera-anime.worker"
PRINT_STATUS_LABEL = "com.javis.chrome-camera-anime.print-status"
MIRA_SYNC_LABEL = "com.javis.chrome-camera-anime.mira-sync"
OPENCLAW_GATEWAY_LABEL = "com.javis.chrome-camera-anime.openclaw-gateway"
ROKID_WATCH_LABEL = "com.javis.chrome-camera-anime.rokid-watch"
LOOPBACK_OPENCLAW_CONFIG_NAME = "openclaw.loopback.json"
HOOK_GATEWAY_CONFIG_NAME = "openclaw.hook-gateway.json"
OPENCLAW_HOOK_GATEWAY_PORT = 18791
OPENAI_CODEX_PROVIDER = "openai-codex"
OPENAI_CODEX_DEFAULT_MODEL = "openai-codex/gpt-5.3-codex"
LOOPBACK_GATEWAY_URL = f"ws://127.0.0.1:{OPENCLAW_HOOK_GATEWAY_PORT}"
DEFAULT_HOOK_URL = f"http://127.0.0.1:{OPENCLAW_HOOK_GATEWAY_PORT}/hooks/agent"
DEFAULT_HOOK_SESSION_KEY = "hook:chrome-camera-anime"
PRINT_STATUS_INTERVAL_SECONDS = 15
DEFAULT_PATH = os.environ.get(
    "PATH",
    "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
)
OPENCLAW_CLI = shutil.which("openclaw") or str(Path.home() / ".local" / "bin" / "openclaw")
RUNTIME_COPY_ITEMS = (
    "README.md",
    "chrome_watch_daemon.py",
    "detect_faces.swift",
    "digua_remote_render_pipeline.py",
    "expression_monitor.swift",
    "expression_monitor_control.py",
    "install_launchd.py",
    "job_store.py",
    "manual_insta_capture.py",
    "macos-camera",
    "mac_camera_render_pipeline.py",
    "mira_sync.py",
    "mira_sync_daemon.py",
    "pipeline.py",
    "print_client.py",
    "print_status_poller.py",
    "rokid_render_pipeline.py",
    "rokid_watch_control.py",
    "rokid_watch_daemon.py",
    "worker_daemon.py",
    "xiaomi_home_print.py",
    "landscapes",
)
FACE_DETECTOR_SWIFT = "detect_faces.swift"
FACE_DETECTOR_BINARY = "detect_faces"
EXPRESSION_MONITOR_SWIFT = "expression_monitor.swift"
EXPRESSION_MONITOR_BINARY = "expression_monitor"
ARK_API_KEY_FILENAME = "ark_api_key.txt"


def default_launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def runtime_dir(state_dir: Path) -> Path:
    return state_dir / "runtime"


def ark_api_key_path(state_dir: Path | None = None) -> Path:
    return (state_dir or STATE_DIR) / ARK_API_KEY_FILENAME


def watcher_takeover_command() -> list[str]:
    return ["pkill", "-f", "chrome_watch_daemon.py"]


def worker_takeover_command() -> list[str]:
    return ["pkill", "-f", "worker_daemon.py"]


def print_status_takeover_command() -> list[str]:
    return ["pkill", "-f", "print_status_poller.py"]


def mira_sync_takeover_command() -> list[str]:
    return ["pkill", "-f", "mira_sync_daemon.py"]


def openclaw_gateway_takeover_command() -> list[str]:
    return ["pkill", "-f", f"openclaw gateway --port {OPENCLAW_HOOK_GATEWAY_PORT}"]


def rokid_watch_takeover_command() -> list[str]:
    return ["pkill", "-f", "rokid_watch_daemon.py"]


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True)


def default_openclaw_config_path() -> Path:
    return Path.home() / ".openclaw" / "openclaw.json"


def default_codex_auth_path() -> Path:
    return Path.home() / ".codex" / "auth.json"


def default_openclaw_agent_dir() -> Path:
    return Path.home() / ".openclaw" / "agents" / "main" / "agent"


def decode_jwt_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2:
        return {}

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def load_codex_auth_profile(
    *,
    codex_auth_path: Path | None = None,
) -> dict | None:
    codex_auth_path = codex_auth_path or default_codex_auth_path()
    if not codex_auth_path.is_file():
        return None

    try:
        payload = json.loads(codex_auth_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    tokens = payload.get("tokens", {})
    access_token = str(tokens.get("access_token") or "").strip()
    refresh_token = str(tokens.get("refresh_token") or "").strip()
    account_id = str(tokens.get("account_id") or "").strip()
    id_token = str(tokens.get("id_token") or "").strip()
    if not access_token or not refresh_token:
        return None

    jwt_payload = decode_jwt_payload(id_token) if id_token else {}
    email = str(jwt_payload.get("email") or "").strip()
    exp = jwt_payload.get("exp")
    expires = int(exp * 1000) if isinstance(exp, (int, float)) else int(
        (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000
    )
    profile_id = f"{OPENAI_CODEX_PROVIDER}:{email}" if email else f"{OPENAI_CODEX_PROVIDER}:default"
    credential = {
        "type": "oauth",
        "provider": OPENAI_CODEX_PROVIDER,
        "access": access_token,
        "refresh": refresh_token,
        "expires": expires,
    }
    if email:
        credential["email"] = email
    if account_id:
        credential["accountId"] = account_id
    return {
        "profile_id": profile_id,
        "email": email or None,
        "credential": credential,
    }


def update_auth_store_with_profile(path: Path, *, profile_id: str, credential: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = {}

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        payload["profiles"] = {}
    payload["profiles"][profile_id] = credential
    payload.setdefault(
        "meta",
        {
            "version": 1,
            "createdAt": "2026-02-10T12:00:00.000Z",
            "comment": "Auth profiles - add credentials via 'openclaw models auth add'",
        },
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_openclaw_codex_auth(
    *,
    agent_dir: Path | None = None,
    codex_auth_path: Path | None = None,
) -> str | None:
    profile = load_codex_auth_profile(codex_auth_path=codex_auth_path)
    if not profile:
        return None

    agent_dir = agent_dir or default_openclaw_agent_dir()
    update_auth_store_with_profile(
        agent_dir / "auth-profiles.json",
        profile_id=profile["profile_id"],
        credential=profile["credential"],
    )
    update_auth_store_with_profile(
        agent_dir / "auth.json",
        profile_id=profile["profile_id"],
        credential=profile["credential"],
    )
    return str(profile["profile_id"])


def apply_openai_codex_defaults(payload: dict, *, codex_profile: dict | None) -> None:
    agents = payload.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    existing_model = defaults.get("model")

    primary = ""
    fallbacks = None
    if isinstance(existing_model, str):
        primary = existing_model.strip()
    elif isinstance(existing_model, dict):
        primary = str(existing_model.get("primary") or "").strip()
        fallbacks = existing_model.get("fallbacks")
    if not primary:
        primary = OPENAI_CODEX_DEFAULT_MODEL

    next_model = {"primary": primary}
    if fallbacks:
        next_model["fallbacks"] = fallbacks
    defaults["model"] = next_model

    models = defaults.get("models")
    if not isinstance(models, dict):
        defaults["models"] = {}
    defaults["models"].setdefault(primary, {})

    if not codex_profile:
        return

    auth = payload.setdefault("auth", {})
    profiles = auth.get("profiles")
    if not isinstance(profiles, dict):
        auth["profiles"] = {}
    auth["profiles"][codex_profile["profile_id"]] = {
        "provider": OPENAI_CODEX_PROVIDER,
        "mode": "oauth",
        **({"email": codex_profile["email"]} if codex_profile.get("email") else {}),
    }

    order = auth.get("order")
    if not isinstance(order, dict):
        auth["order"] = {}
    existing_order = auth["order"].get(OPENAI_CODEX_PROVIDER)
    if isinstance(existing_order, list):
        deduped = [codex_profile["profile_id"]]
        deduped.extend(profile_id for profile_id in existing_order if profile_id != codex_profile["profile_id"])
        auth["order"][OPENAI_CODEX_PROVIDER] = deduped
    else:
        auth["order"][OPENAI_CODEX_PROVIDER] = [codex_profile["profile_id"]]


def write_loopback_openclaw_config(
    target_path: Path,
    *,
    source_path: Path | None = None,
) -> Path | None:
    source_path = source_path or default_openclaw_config_path()
    if not source_path.is_file():
        return None

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    gateway = payload.setdefault("gateway", {})
    auth = gateway.setdefault("auth", {})
    remote = gateway.setdefault("remote", {})
    remote["url"] = LOOPBACK_GATEWAY_URL
    token = str(auth.get("token") or remote.get("token") or "").strip()
    if token:
        remote["token"] = token
    target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_path


def write_hook_gateway_config(
    target_path: Path,
    *,
    source_path: Path | None = None,
    codex_auth_path: Path | None = None,
) -> Path | None:
    source_path = source_path or default_openclaw_config_path()
    if not source_path.is_file():
        return None

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    codex_profile = load_codex_auth_profile(codex_auth_path=codex_auth_path)
    apply_openai_codex_defaults(payload, codex_profile=codex_profile)
    gateway = payload.setdefault("gateway", {})
    auth = gateway.setdefault("auth", {})
    gateway_token = str(auth.get("token") or gateway.get("remote", {}).get("token") or "").strip()
    if not gateway_token:
        gateway_token = secrets.token_hex(24)
    hooks_token = str(payload.get("hooks", {}).get("token") or "").strip()
    if not hooks_token or hooks_token == gateway_token:
        hooks_token = secrets.token_hex(24)

    gateway["mode"] = "local"
    gateway["bind"] = "loopback"
    gateway["port"] = OPENCLAW_HOOK_GATEWAY_PORT
    auth["mode"] = "token"
    auth["token"] = gateway_token

    payload["hooks"] = {
        "enabled": True,
        "token": hooks_token,
        "path": "/hooks",
        "allowedAgentIds": ["main"],
        "defaultSessionKey": DEFAULT_HOOK_SESSION_KEY,
    }
    target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_path


def compile_face_detector_binary(target_dir: Path) -> Path | None:
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return None

    source = target_dir / FACE_DETECTOR_SWIFT
    if not source.is_file():
        return None

    binary = target_dir / FACE_DETECTOR_BINARY
    try:
        subprocess.run(
            [swiftc, "-O", str(source), "-o", str(binary)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None
    return binary


def compile_expression_monitor_binary(target_dir: Path) -> Path | None:
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return None

    source = target_dir / EXPRESSION_MONITOR_SWIFT
    if not source.is_file():
        return None

    binary = target_dir / EXPRESSION_MONITOR_BINARY
    try:
        subprocess.run(
            [swiftc, "-O", str(source), "-o", str(binary)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None
    return binary


def materialize_runtime_tree(target_dir: Path) -> Path:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for name in RUNTIME_COPY_ITEMS:
        source = ROOT / name
        destination = target_dir / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)

    write_loopback_openclaw_config(target_dir / LOOPBACK_OPENCLAW_CONFIG_NAME)
    write_hook_gateway_config(target_dir / HOOK_GATEWAY_CONFIG_NAME)
    sync_openclaw_codex_auth()
    compile_face_detector_binary(target_dir)
    compile_expression_monitor_binary(target_dir)
    return target_dir


def read_persisted_ark_api_key(*, state_dir: Path | None = None) -> str:
    path = ark_api_key_path(state_dir)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def persist_ark_api_key_from_environment(*, state_dir: Path | None = None) -> str | None:
    ark_api_key = os.environ.get("ARK_API_KEY", "").strip()
    if not ark_api_key:
        return None
    path = ark_api_key_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{ark_api_key}\n", encoding="utf-8")
    return ark_api_key


def read_hook_gateway_token(script_dir: Path) -> str:
    payload = json.loads((script_dir / HOOK_GATEWAY_CONFIG_NAME).read_text(encoding="utf-8"))
    return str(payload.get("hooks", {}).get("token") or payload.get("gateway", {}).get("auth", {}).get("token") or "").strip()


def resolve_ssl_cert_file() -> str:
    override = os.environ.get("SSL_CERT_FILE", "").strip()
    if override:
        return override
    try:
        import certifi  # type: ignore
    except Exception:
        return ""
    return str(certifi.where())


def common_environment(script_dir: Path) -> dict[str, str]:
    env = {
        "PATH": DEFAULT_PATH,
        "PYTHONPATH": str(script_dir),
        "OPENCLAW_CONFIG_PATH": str(script_dir / LOOPBACK_OPENCLAW_CONFIG_NAME),
        "OPENCLAW_HOOK_URL": DEFAULT_HOOK_URL,
    }
    ssl_cert_file = resolve_ssl_cert_file()
    if ssl_cert_file:
        env["SSL_CERT_FILE"] = ssl_cert_file
    hook_token = read_hook_gateway_token(script_dir) if (script_dir / HOOK_GATEWAY_CONFIG_NAME).is_file() else ""
    if hook_token:
        env["OPENCLAW_HOOK_TOKEN"] = hook_token
    ark_api_key = os.environ.get("ARK_API_KEY", "").strip() or read_persisted_ark_api_key()
    if ark_api_key:
        env["ARK_API_KEY"] = ark_api_key
    for key in (
        "OPENCLAW_HOOK_URL",
        "OPENCLAW_HOOK_TOKEN",
        "OPENCLAW_HOOK_AGENT_ID",
        "OPENCLAW_HOOK_NAME",
        "OPENCLAW_HOOK_WAKE_MODE",
    ):
        value = os.environ.get(key, "").strip()
        if value:
            env[key] = value
    return env


def build_watcher_plist(script_dir: Path, state_dir: Path) -> dict:
    python_executable = os.environ.get("PYTHON3_BIN", sys.executable)
    return {
        "Label": WATCHER_LABEL,
        "ProgramArguments": [python_executable, str(script_dir / "chrome_watch_daemon.py")],
        "RunAtLoad": True,
        "KeepAlive": True,
        "WorkingDirectory": str(script_dir),
        "EnvironmentVariables": common_environment(script_dir),
        "StandardOutPath": str(state_dir / "launchd-watcher.stdout.log"),
        "StandardErrorPath": str(state_dir / "launchd-watcher.stderr.log"),
    }


def build_worker_plist(script_dir: Path, state_dir: Path) -> dict:
    python_executable = os.environ.get("PYTHON3_BIN", sys.executable)
    return {
        "Label": WORKER_LABEL,
        "ProgramArguments": [python_executable, str(script_dir / "worker_daemon.py")],
        "RunAtLoad": True,
        "KeepAlive": True,
        "WorkingDirectory": str(script_dir),
        "EnvironmentVariables": common_environment(script_dir),
        "StandardOutPath": str(state_dir / "launchd-worker.stdout.log"),
        "StandardErrorPath": str(state_dir / "launchd-worker.stderr.log"),
    }


def build_print_status_poller_plist(script_dir: Path, state_dir: Path) -> dict:
    python_executable = os.environ.get("PYTHON3_BIN", sys.executable)
    return {
        "Label": PRINT_STATUS_LABEL,
        "ProgramArguments": [python_executable, str(script_dir / "print_status_poller.py")],
        "RunAtLoad": True,
        "StartInterval": PRINT_STATUS_INTERVAL_SECONDS,
        "WorkingDirectory": str(script_dir),
        "EnvironmentVariables": common_environment(script_dir),
        "StandardOutPath": str(state_dir / "launchd-print-status.stdout.log"),
        "StandardErrorPath": str(state_dir / "launchd-print-status.stderr.log"),
    }


def build_mira_sync_plist(script_dir: Path, state_dir: Path) -> dict:
    python_executable = os.environ.get("PYTHON3_BIN", sys.executable)
    return {
        "Label": MIRA_SYNC_LABEL,
        "ProgramArguments": [python_executable, str(script_dir / "mira_sync_daemon.py")],
        "RunAtLoad": True,
        "KeepAlive": True,
        "WorkingDirectory": str(script_dir),
        "EnvironmentVariables": common_environment(script_dir),
        "StandardOutPath": str(state_dir / "launchd-mira-sync.stdout.log"),
        "StandardErrorPath": str(state_dir / "launchd-mira-sync.stderr.log"),
    }


def build_openclaw_gateway_plist(script_dir: Path, state_dir: Path) -> dict:
    return {
        "Label": OPENCLAW_GATEWAY_LABEL,
        "ProgramArguments": [
            OPENCLAW_CLI,
            "gateway",
            "--port",
            str(OPENCLAW_HOOK_GATEWAY_PORT),
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "WorkingDirectory": str(script_dir),
        "EnvironmentVariables": {
            "HOME": str(Path.home()),
            "PATH": DEFAULT_PATH,
            "OPENCLAW_CONFIG_PATH": str(script_dir / HOOK_GATEWAY_CONFIG_NAME),
        },
        "StandardOutPath": str(state_dir / "launchd-openclaw-gateway.stdout.log"),
        "StandardErrorPath": str(state_dir / "launchd-openclaw-gateway.stderr.log"),
    }


def build_rokid_watch_plist(script_dir: Path, state_dir: Path) -> dict:
    python_executable = os.environ.get("PYTHON3_BIN", sys.executable)
    return {
        "Label": ROKID_WATCH_LABEL,
        "ProgramArguments": [python_executable, str(script_dir / "rokid_watch_daemon.py")],
        "RunAtLoad": True,
        "KeepAlive": True,
        "WorkingDirectory": str(script_dir),
        "EnvironmentVariables": common_environment(script_dir),
        "StandardOutPath": str(state_dir / "launchd-rokid-watch.stdout.log"),
        "StandardErrorPath": str(state_dir / "launchd-rokid-watch.stderr.log"),
    }


def write_plist(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)


def bootout(label_path: Path) -> None:
    domain = f"gui/{os.getuid()}"
    run(["launchctl", "bootout", domain, str(label_path)], check=False)


def bootstrap_and_kickstart(label: str, label_path: Path) -> None:
    domain = f"gui/{os.getuid()}"
    run(["launchctl", "bootstrap", domain, str(label_path)])
    run(["launchctl", "enable", f"{domain}/{label}"], check=False)
    run(["launchctl", "kickstart", "-k", f"{domain}/{label}"], check=False)


def install_launch_agents(launch_agents_dir: Path | None = None, load: bool = True) -> list[Path]:
    launch_agents_dir = launch_agents_dir or default_launch_agents_dir()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    persist_ark_api_key_from_environment()
    script_dir = materialize_runtime_tree(runtime_dir(STATE_DIR))
    watcher_path = launch_agents_dir / f"{WATCHER_LABEL}.plist"
    worker_path = launch_agents_dir / f"{WORKER_LABEL}.plist"
    print_status_path = launch_agents_dir / f"{PRINT_STATUS_LABEL}.plist"
    mira_sync_path = launch_agents_dir / f"{MIRA_SYNC_LABEL}.plist"
    openclaw_gateway_path = launch_agents_dir / f"{OPENCLAW_GATEWAY_LABEL}.plist"
    rokid_watch_path = launch_agents_dir / f"{ROKID_WATCH_LABEL}.plist"
    write_plist(watcher_path, build_watcher_plist(script_dir, STATE_DIR))
    write_plist(worker_path, build_worker_plist(script_dir, STATE_DIR))
    write_plist(print_status_path, build_print_status_poller_plist(script_dir, STATE_DIR))
    write_plist(mira_sync_path, build_mira_sync_plist(script_dir, STATE_DIR))
    write_plist(openclaw_gateway_path, build_openclaw_gateway_plist(script_dir, STATE_DIR))
    write_plist(rokid_watch_path, build_rokid_watch_plist(script_dir, STATE_DIR))

    if load:
        bootout(openclaw_gateway_path)
        run(openclaw_gateway_takeover_command(), check=False)
        bootstrap_and_kickstart(OPENCLAW_GATEWAY_LABEL, openclaw_gateway_path)

        bootout(watcher_path)
        run(watcher_takeover_command(), check=False)
        bootstrap_and_kickstart(WATCHER_LABEL, watcher_path)

        bootout(worker_path)
        run(worker_takeover_command(), check=False)
        bootstrap_and_kickstart(WORKER_LABEL, worker_path)

        bootout(print_status_path)
        run(print_status_takeover_command(), check=False)
        bootstrap_and_kickstart(PRINT_STATUS_LABEL, print_status_path)

        bootout(mira_sync_path)
        run(mira_sync_takeover_command(), check=False)
        bootstrap_and_kickstart(MIRA_SYNC_LABEL, mira_sync_path)

        bootout(rokid_watch_path)
        run(rokid_watch_takeover_command(), check=False)
        bootstrap_and_kickstart(ROKID_WATCH_LABEL, rokid_watch_path)
    return [openclaw_gateway_path, watcher_path, worker_path, print_status_path, mira_sync_path, rokid_watch_path]


def uninstall_launch_agents(launch_agents_dir: Path | None = None) -> list[Path]:
    launch_agents_dir = launch_agents_dir or default_launch_agents_dir()
    paths = [
        launch_agents_dir / f"{WATCHER_LABEL}.plist",
        launch_agents_dir / f"{WORKER_LABEL}.plist",
        launch_agents_dir / f"{PRINT_STATUS_LABEL}.plist",
        launch_agents_dir / f"{MIRA_SYNC_LABEL}.plist",
        launch_agents_dir / f"{OPENCLAW_GATEWAY_LABEL}.plist",
        launch_agents_dir / f"{ROKID_WATCH_LABEL}.plist",
    ]
    for path in paths:
        if path.exists():
            bootout(path)
            path.unlink()
    run(watcher_takeover_command(), check=False)
    run(worker_takeover_command(), check=False)
    run(print_status_takeover_command(), check=False)
    run(mira_sync_takeover_command(), check=False)
    run(openclaw_gateway_takeover_command(), check=False)
    run(rokid_watch_takeover_command(), check=False)
    shutil.rmtree(runtime_dir(STATE_DIR), ignore_errors=True)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Chrome camera anime launchd agent for the current user.")
    parser.add_argument("--write-only", action="store_true", help="Write plist files without loading them through launchctl")
    parser.add_argument("--uninstall", action="store_true", help="Unload and remove the launch agent plist files")
    args = parser.parse_args()

    if args.uninstall:
        removed = uninstall_launch_agents()
        print("removed")
        for path in removed:
            print(path)
        return

    installed = install_launch_agents(load=not args.write_only)
    print("installed")
    for path in installed:
        print(path)


if __name__ == "__main__":
    main()
