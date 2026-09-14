#!/usr/bin/env python3
"""Deploy four_servo_control.py and send_uart3_led_cmd.py to the RDK X5 board.

Usage:
    python deploy_board_scripts.py [--host 192.168.0.183] [--user lckfb] [--remote-dir /home/sunrise/Desktop]

This script:
1. SCPs four_servo_control.py and send_uart3_led_cmd.py to the board
2. Installs pyserial on the board if not present
3. Verifies the scripts are executable
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_TO_DEPLOY = [
    "four_servo_control.py",
    "send_uart3_led_cmd.py",
    "servo_3_shake_2100_2000.py",
    "servo_2_nod_1900_2200.py",
]


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def deploy(host: str, user: str, remote_dir: str, install_deps: bool) -> int:
    remote_target = f"{user}@{host}"
    remote_path = f"{remote_target}:{remote_dir}/"

    # Ensure remote directory exists
    print(f"\n[1/4] Ensuring remote directory {remote_dir} exists...")
    run(["ssh", remote_target, f"mkdir -p {remote_dir}"])

    # Install pyserial on the board
    if install_deps:
        print(f"\n[2/4] Installing pyserial on the board...")
        result = run(["ssh", remote_target, "pip3 install pyserial 2>&1 || pip install pyserial 2>&1"], check=False)
        if result.returncode != 0:
            print(f"  WARNING: pyserial install may have failed (board may already have it)")
        else:
            print(f"  pyserial installed successfully")

    # SCP scripts
    print(f"\n[3/4] Deploying scripts to {remote_path}...")
    for script_name in SCRIPTS_TO_DEPLOY:
        local_path = SCRIPT_DIR / script_name
        if not local_path.exists():
            print(f"  ERROR: {local_path} not found", file=sys.stderr)
            return 1
        run(["scp", str(local_path), remote_path])
        print(f"  Deployed: {script_name}")

    # Make executable and verify
    print(f"\n[4/4] Setting permissions and verifying...")
    for script_name in SCRIPTS_TO_DEPLOY:
        run(["ssh", remote_target, f"chmod +x {remote_dir}/{script_name}"])

    # Quick verification
    print("\n[verify] Testing four_servo_control.py ping-all...")
    result = run(
        ["ssh", remote_target, f"python3 {remote_dir}/four_servo_control.py ping-all"],
        check=False
    )
    print(f"  stdout: {result.stdout.strip()}")
    if result.stderr.strip():
        print(f"  stderr: {result.stderr.strip()}")

    print("\n✓ Deployment complete!")
    print(f"  Board: {remote_target}")
    print(f"  Remote dir: {remote_dir}")
    print(f"  Scripts: {', '.join(SCRIPTS_TO_DEPLOY)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy servo/LED scripts to RDK X5 board.")
    parser.add_argument("--host", default="192.168.0.183", help="Board IP address")
    parser.add_argument("--user", default="lckfb", help="Board SSH user")
    parser.add_argument("--remote-dir", default="/home/sunrise/Desktop", help="Remote directory")
    parser.add_argument("--no-install-deps", action="store_true", help="Skip pyserial installation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Check SSH availability
    if not shutil.which("ssh"):
        print("ERROR: ssh not found. Please install OpenSSH client.", file=sys.stderr)
        return 1
    if not shutil.which("scp"):
        print("ERROR: scp not found. Please install OpenSSH client.", file=sys.stderr)
        return 1

    print(f"Deploying to {args.user}@{args.host}:{args.remote_dir}")
    return deploy(args.host, args.user, args.remote_dir, not args.no_install_deps)


if __name__ == "__main__":
    raise SystemExit(main())
