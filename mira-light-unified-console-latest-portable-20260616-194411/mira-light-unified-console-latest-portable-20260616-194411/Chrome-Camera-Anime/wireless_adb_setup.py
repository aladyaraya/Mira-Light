#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import rokid_watch_daemon


ROKID_WATCH_LABEL = "com.javis.chrome-camera-anime.rokid-watch"


def run_command(command: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=input_text,
        check=check,
        capture_output=True,
        text=True,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pair and connect wireless ADB, then update the Rokid watch config on macOS.",
    )
    parser.add_argument("--adb-path", default=shutil.which("adb") or "adb")
    parser.add_argument("--pair-host")
    parser.add_argument("--pair-port", type=int)
    parser.add_argument("--pair-code")
    parser.add_argument("--connect-host", required=True)
    parser.add_argument("--connect-port", type=int, required=True)
    parser.add_argument("--config-path", type=Path, default=rokid_watch_daemon.DEFAULT_CONFIG_PATH)
    parser.add_argument("--kickstart-label", default=ROKID_WATCH_LABEL)
    parser.add_argument("--skip-pair", action="store_true")
    parser.add_argument("--skip-kickstart", action="store_true")
    return parser.parse_args(argv)


def ensure_pairing(args: argparse.Namespace) -> dict[str, object]:
    if args.skip_pair:
        return {"skipped": True}
    if not args.pair_host or not args.pair_port or not args.pair_code:
        raise SystemExit("pair info missing: --pair-host, --pair-port, and --pair-code are required unless --skip-pair is used")
    endpoint = f"{args.pair_host}:{args.pair_port}"
    result = run_command([args.adb_path, "pair", endpoint], input_text=f"{args.pair_code}\n", check=False)
    payload = {
        "endpoint": endpoint,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    if result.returncode != 0:
        note = ""
        stderr_text = payload["stderr"]
        if isinstance(stderr_text, str) and "protocol fault" in stderr_text:
            note = (
                "phone pairing session likely expired; reopen Wireless debugging > Pair device with pairing code "
                "and use the newly shown host, port, and code"
            )
        raise RuntimeError(json.dumps({"pair_failed": payload, "note": note}, ensure_ascii=False))
    return payload


def connect_device(args: argparse.Namespace) -> dict[str, object]:
    endpoint = f"{args.connect_host}:{args.connect_port}"
    result = run_command([args.adb_path, "connect", endpoint], check=False)
    payload = {
        "endpoint": endpoint,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    if result.returncode != 0:
        note = ""
        stdout_text = payload["stdout"]
        if isinstance(stdout_text, str) and "Connection refused" in stdout_text:
            note = "phone connect endpoint is not listening; refresh the wireless debugging screen and use the latest connect port"
        raise RuntimeError(json.dumps({"connect_failed": payload, "note": note}, ensure_ascii=False))
    return payload


def list_connected_serials(adb_path: str) -> list[str]:
    result = run_command([adb_path, "devices"], check=True)
    serials: list[str] = []
    for line in result.stdout.splitlines():
        if "\tdevice" not in line:
            continue
        serials.append(line.split("\t", 1)[0].strip())
    return serials


def update_rokid_config(*, config_path: Path, adb_path: str, adb_serial: str) -> dict[str, object]:
    config = rokid_watch_daemon.ensure_config(config_path)
    config["enabled"] = True
    config["adb_path"] = adb_path
    config["adb_serial"] = adb_serial
    rokid_watch_daemon.write_json(config_path, config)
    return config


def kickstart_service(label: str) -> dict[str, object]:
    uid = os.getuid()
    target = f"gui/{uid}/{label}"
    result = run_command(["launchctl", "kickstart", "-k", target], check=False)
    return {
        "target": target,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_command([args.adb_path, "start-server"], check=False)

        pair_result = ensure_pairing(args)
        connect_result = connect_device(args)

        expected_serial = f"{args.connect_host}:{args.connect_port}"
        serials = list_connected_serials(args.adb_path)
        if expected_serial in serials:
            adb_serial = expected_serial
        elif serials:
            adb_serial = serials[0]
        else:
            raise RuntimeError("wireless adb connect reported success, but no device is listed in `adb devices`")

        config = update_rokid_config(config_path=args.config_path, adb_path=args.adb_path, adb_serial=adb_serial)
        kickstart_result = {"skipped": True}
        if not args.skip_kickstart:
            kickstart_result = kickstart_service(args.kickstart_label)

        print(
            json.dumps(
                {
                    "pair": pair_result,
                    "connect": connect_result,
                    "adb_serial": adb_serial,
                    "config_path": str(args.config_path),
                    "enabled": bool(config.get("enabled")),
                    "kickstart": kickstart_result,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
