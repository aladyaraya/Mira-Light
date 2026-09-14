#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import sys
import time


DEFAULT_BOARD_DIR = "/home/sunrise/Desktop/mira-book-follow-camera"
DEFAULT_SERVO_DEVICE = "/dev/ttyS1"
DEFAULT_SERVO_PORT = 9527


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover Mira Light board-side servo bridge and camera ownership.")
    parser.add_argument("--host", default=os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", "22")))
    parser.add_argument("--user", default=os.environ.get("MIRA_SHENZHEN_BOARD_USER", "root"))
    parser.add_argument("--board-dir", default=os.environ.get("MIRA_BOOK_FOLLOW_BOARD_DIR", DEFAULT_BOARD_DIR))
    parser.add_argument("--servo-port", type=int, default=int(os.environ.get("MIRA_BOOK_FOLLOW_SERVO_PORT", str(DEFAULT_SERVO_PORT))))
    parser.add_argument("--servo-device", default=os.environ.get("MIRA_BOOK_FOLLOW_SERVO_DEVICE", DEFAULT_SERVO_DEVICE))
    parser.add_argument("--ssh-timeout", type=float, default=4.0)
    parser.add_argument("--verify-timeout", type=float, default=8.0)
    return parser.parse_args()


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "scripts" / "rdk_bus_servo_tcp_bridge.py").is_file():
            return parent
    raise RuntimeError("Could not locate repo root containing scripts/rdk_bus_servo_tcp_bridge.py")


def check_tcp(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def ssh_prefix(args: argparse.Namespace) -> list[str]:
    base = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/tmp/mira-board-recover-known-hosts",
        "-o",
        f"ConnectTimeout={max(1, int(args.ssh_timeout))}",
        "-p",
        str(args.port),
        f"{args.user}@{args.host}",
    ]
    password = os.environ.get("DIGUA_SSH_PASSWORD") or os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD") or ""
    if password and shutil.which("sshpass"):
        os.environ["SSHPASS"] = password
        return ["sshpass", "-e", *base]
    return base


def scp_prefix(args: argparse.Namespace) -> list[str]:
    base = [
        "scp",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/tmp/mira-board-recover-known-hosts",
        "-o",
        f"ConnectTimeout={max(1, int(args.ssh_timeout))}",
        "-P",
        str(args.port),
    ]
    password = os.environ.get("DIGUA_SSH_PASSWORD") or os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD") or ""
    if password and shutil.which("sshpass"):
        os.environ["SSHPASS"] = password
        return ["sshpass", "-e", *base]
    return base


def run(command: list[str], *, input_text: str | None = None, timeout: float = 30.0, check: bool = True) -> subprocess.CompletedProcess[str]:
    printable = " ".join(shlex.quote(part) for part in command)
    print(f"$ {printable}")
    result = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {printable}")
    return result


def remote_recovery_script(*, board_dir: str, servo_port: int, servo_device: str) -> str:
    return f"""set -euo pipefail
BOARD_DIR={shlex.quote(board_dir)}
SERVO_PORT={servo_port}
SERVO_DEVICE={shlex.quote(servo_device)}

echo "== board identity =="
hostname || true
date || true

echo "== clean old camera users for /dev/video0 =="
if command -v lsof >/dev/null 2>&1; then
  lsof /dev/video0 2>/dev/null || true
fi
if command -v fuser >/dev/null 2>&1; then
  fuser -v /dev/video0 2>/dev/null || true
fi
pkill -f '[c]am_sender.py' 2>/dev/null || true
pkill -f '[f]fmpeg.*(/dev/video0|-i[[:space:]]+/dev/video0)' 2>/dev/null || true
sleep 0.25
if command -v lsof >/dev/null 2>&1; then
  lsof /dev/video0 2>/dev/null || true
fi

echo "== restart servo bridge =="
mkdir -p "$BOARD_DIR"
old_bridge="$(cat "$BOARD_DIR/rdk_bus_servo_tcp_bridge.pid" 2>/dev/null || true)"
if [ -n "$old_bridge" ]; then
  kill "$old_bridge" 2>/dev/null || true
fi
pkill -f "rdk_bus_servo_tcp_bridge.py .*--port $SERVO_PORT" 2>/dev/null || true
pkill -f '[r]dk_bus_servo_tcp_bridge.py' 2>/dev/null || true
sleep 0.25
nohup python3 "$BOARD_DIR/rdk_bus_servo_tcp_bridge.py" \\
  --host 0.0.0.0 \\
  --port "$SERVO_PORT" \\
  --device "$SERVO_DEVICE" \\
  > "$BOARD_DIR/rdk_bus_servo_tcp_bridge.log" 2>&1 < /dev/null &
echo $! > "$BOARD_DIR/rdk_bus_servo_tcp_bridge.pid"
sleep 1

echo "== verify servo bridge on board =="
if command -v ss >/dev/null 2>&1; then
  ss -lntp | grep ":$SERVO_PORT " || true
elif command -v netstat >/dev/null 2>&1; then
  netstat -lntp 2>/dev/null | grep ":$SERVO_PORT " || true
fi
ps -ef | grep -E '[r]dk_bus_servo_tcp_bridge.py|[c]am_sender.py|[f]fmpeg' || true
echo "== servo bridge log tail =="
tail -40 "$BOARD_DIR/rdk_bus_servo_tcp_bridge.log" 2>/dev/null || true
"""


def wait_for_port(host: str, port: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() <= deadline:
        if check_tcp(host, port, timeout=1.0):
            return True
        time.sleep(0.3)
    return False


def main() -> int:
    args = parse_args()
    bridge_src = repo_root() / "scripts" / "rdk_bus_servo_tcp_bridge.py"
    remote_bridge = f"{args.user}@{args.host}:{args.board_dir.rstrip('/')}/rdk_bus_servo_tcp_bridge.py"

    print("== Mira Light board recovery ==")
    print(f"Board: {args.user}@{args.host}:{args.port}")
    print(f"Servo bridge: {args.host}:{args.servo_port} -> {args.servo_device}")
    print(f"Board dir: {args.board_dir}")

    print("== check SSH 22 ==")
    if not check_tcp(args.host, args.port, timeout=args.ssh_timeout):
        print(f"ERROR: SSH port is not reachable: {args.host}:{args.port}", file=sys.stderr)
        return 2
    print(f"OK: SSH port reachable: {args.host}:{args.port}")

    print("== check servo bridge 9527 before recovery ==")
    if check_tcp(args.host, args.servo_port, timeout=1.5):
        print(f"OK: servo bridge already reachable: {args.host}:{args.servo_port}")
    else:
        print(f"WARN: servo bridge not reachable before recovery: {args.host}:{args.servo_port}")

    run([*ssh_prefix(args), f"mkdir -p {shlex.quote(args.board_dir)}"], timeout=15.0)
    run([*scp_prefix(args), str(bridge_src), remote_bridge], timeout=25.0)
    run(
        [*ssh_prefix(args), "bash -s"],
        input_text=remote_recovery_script(
            board_dir=args.board_dir,
            servo_port=args.servo_port,
            servo_device=args.servo_device,
        ),
        timeout=45.0,
    )

    print("== check servo bridge 9527 after recovery ==")
    if not wait_for_port(args.host, args.servo_port, timeout_seconds=args.verify_timeout):
        print(f"ERROR: servo bridge is still not reachable: {args.host}:{args.servo_port}", file=sys.stderr)
        return 3
    print(f"OK: servo bridge reachable: {args.host}:{args.servo_port}")
    print("Board recovery complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
