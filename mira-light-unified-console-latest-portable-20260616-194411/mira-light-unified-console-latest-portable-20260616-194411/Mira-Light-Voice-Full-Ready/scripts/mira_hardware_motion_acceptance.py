#!/usr/bin/env python3
"""Hardware acceptance probe for Mira voice motion.

This script intentionally fails if the board-side 9527 endpoint only accepts a
TCP connection but does not acknowledge the servo frame. A visible motion claim
is not valid until this probe can prove the low-level motion transport.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import ipaddress
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from typing import Any

from bus_servo_transport import BusServoTransportError, TcpBusServoTransport
from mira_local_voice_loop import dispatch_transcript_once


DEFAULT_BOARD_HOST = "192.168.0.183"
DEFAULT_BOARD_PORT = 9527
DEFAULT_BRIDGE_URL = "http://127.0.0.1:19783"
DEFAULT_PROBE_COMMANDS = [
    "{#000P1367T0500!#001P1500T0500!#002P1500T0500!#003P1500T0500!}",
    "{#000P1648T0500!#001P1500T0500!#002P1500T0500!#003P1500T0500!}",
    "{#000P1500T0500!#001P1500T0500!#002P1500T0500!#003P1500T0500!}",
]
POSITION_RE = re.compile(r"(?P<id>[0-3])\D+(?P<position>[0-9]{3,4})")
VPN_INTERFACE_MARKERS = ("meta", "vpn", "tun", "tap", "openvpn", "radmin")


def tired_transcript() -> str:
    return "".join(chr(code) for code in [0x6211, 0x597D, 0x7D2F, 0x554A])


def default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
    return Path(__file__).resolve().parents[1] / "runtime" / "hardware-motion-acceptance" / timestamp / "result.json"


def write_result(payload: dict[str, Any], output: str | Path | None) -> Path:
    path = Path(output).expanduser() if output else default_output_path()
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_ack_probe(*, board_host: str, board_port: int, timeout_seconds: float) -> list[dict[str, Any]]:
    transport = TcpBusServoTransport(
        board_host,
        board_port,
        timeout_seconds=timeout_seconds,
        require_ack=True,
    )
    results = []
    for command in DEFAULT_PROBE_COMMANDS:
        results.append(transport.send(command))
    return results


def send_raw_tcp(host: str, port: int, payload: str, *, timeout_seconds: float) -> str:
    with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
        sock.settimeout(timeout_seconds)
        sock.sendall((payload.rstrip("\n") + "\n").encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def parse_positions(raw: str) -> dict[str, int]:
    positions: dict[str, int] = {}
    for match in POSITION_RE.finditer(raw.replace("\r", "\n")):
        positions[match.group("id")] = int(match.group("position"))
    return positions


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _prefix_network(prefix: Any) -> ipaddress.IPv4Network | None:
    try:
        return ipaddress.ip_network(str(prefix), strict=False)
    except ValueError:
        return None


def _row_interface(row: dict[str, Any]) -> str:
    return str(row.get("InterfaceAlias") or row.get("ifAlias") or "")


def _select_route(board_host: str, route_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        board_ip = ipaddress.ip_address(board_host)
    except ValueError:
        return None
    candidates: list[tuple[int, int, int, dict[str, Any]]] = []
    for row in route_rows:
        network = _prefix_network(row.get("DestinationPrefix"))
        if network is None or board_ip not in network:
            continue
        total_metric = _as_int(row.get("RouteMetric")) + _as_int(row.get("InterfaceMetric"))
        candidates.append((-int(network.prefixlen), total_metric, len(candidates), row))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][3]


def _board_is_on_connected_subnet(board_host: str, route_rows: list[dict[str, Any]]) -> bool:
    try:
        board_ip = ipaddress.ip_address(board_host)
    except ValueError:
        return False
    for row in route_rows:
        if str(row.get("NextHop") or "") not in {"", "0.0.0.0"}:
            continue
        network = _prefix_network(row.get("DestinationPrefix"))
        if network is None or network.prefixlen >= 32:
            continue
        if board_ip in network:
            return True
    return False


def diagnose_route_risk(
    *,
    board_host: str,
    route_rows: list[dict[str, Any]],
    ip_configs: list[dict[str, Any]],
) -> dict[str, Any]:
    selected = _select_route(board_host, route_rows)
    board_is_local = _board_is_on_connected_subnet(board_host, route_rows)
    interface = _row_interface(selected or {}).lower()
    next_hop = str((selected or {}).get("NextHop") or "")
    selected_is_vpn = any(marker in interface for marker in VPN_INTERFACE_MARKERS) or next_hop.startswith("198.18.")
    risk = "none"
    if selected is None:
        risk = "no-route"
    elif selected_is_vpn and not board_is_local:
        risk = "vpn-route-risk"
    suggested_actions: list[str] = []
    if risk == "vpn-route-risk":
        suggested_actions = [
            "refresh-board-ip",
            "add-lan-host-route",
            "disable-vpn-route-for-board",
        ]
    elif risk == "no-route":
        suggested_actions = ["refresh-board-ip", "join-board-lan"]
    return {
        "risk": risk,
        "boardHost": board_host,
        "selectedRoute": selected,
        "boardIsOnLocalSubnet": board_is_local,
        "ipConfigs": ip_configs,
        "suggestedActions": suggested_actions,
    }


def _run_powershell_json(command: str, timeout_seconds: float = 5.0) -> Any:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    text = completed.stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return []
    return json.loads(text)


def _listify_json(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def collect_windows_route_diagnosis(board_host: str) -> dict[str, Any]:
    try:
        route_rows = _listify_json(
            _run_powershell_json(
                "Get-NetRoute -AddressFamily IPv4 | "
                "Select-Object DestinationPrefix,NextHop,InterfaceAlias,RouteMetric,InterfaceMetric | "
                "ConvertTo-Json -Depth 4"
            )
        )
        ip_configs = _listify_json(
            _run_powershell_json(
                "Get-NetIPAddress -AddressFamily IPv4 | "
                "Select-Object InterfaceAlias,IPAddress | "
                "ConvertTo-Json -Depth 4",
                timeout_seconds=10.0,
            )
        )
        return diagnose_route_risk(board_host=board_host, route_rows=route_rows, ip_configs=ip_configs)
    except Exception as exc:
        return {"risk": "diagnosis-error", "boardHost": board_host, "error": str(exc)}


def read_positions(*, board_host: str, board_port: int, timeout_seconds: float) -> dict[str, Any]:
    raw = send_raw_tcp(board_host, board_port, "READ", timeout_seconds=timeout_seconds)
    positions = parse_positions(raw)
    return {"ok": bool(raw.startswith("OK") and positions), "raw": raw, "positions": positions}


def run_position_change_probe(*, board_host: str, board_port: int, timeout_seconds: float, threshold: int) -> dict[str, Any]:
    before = read_positions(board_host=board_host, board_port=board_port, timeout_seconds=timeout_seconds)
    if not before["ok"]:
        return {"ok": False, "reason": "read-before-failed", "before": before}

    transport = TcpBusServoTransport(board_host, board_port, timeout_seconds=timeout_seconds, require_ack=True)
    move_a = transport.send(DEFAULT_PROBE_COMMANDS[0])
    time.sleep(0.8)
    after_a = read_positions(board_host=board_host, board_port=board_port, timeout_seconds=timeout_seconds)
    move_b = transport.send(DEFAULT_PROBE_COMMANDS[-1])
    time.sleep(0.8)
    after_b = read_positions(board_host=board_host, board_port=board_port, timeout_seconds=timeout_seconds)

    deltas = {}
    before_positions = before["positions"]
    for key, value in after_a.get("positions", {}).items():
        if key in before_positions:
            deltas[key] = abs(int(value) - int(before_positions[key]))
    moved = any(delta >= int(threshold) for delta in deltas.values())
    return {
        "ok": moved,
        "threshold": int(threshold),
        "before": before,
        "moveA": move_a,
        "afterA": after_a,
        "moveB": move_b,
        "afterB": after_b,
        "deltas": deltas,
        "reason": "" if moved else "no-servo-position-change-detected",
    }


def run_acceptance(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "board": {"host": args.board_host, "port": args.board_port},
        "bridgeUrl": args.bridge_url,
        "checks": {},
    }

    try:
        result["checks"]["ackProbe"] = {
            "ok": True,
            "commands": run_ack_probe(
                board_host=args.board_host,
                board_port=int(args.board_port),
                timeout_seconds=float(args.timeout_seconds),
            ),
        }
    except (BusServoTransportError, OSError) as exc:
        result["checks"]["ackProbe"] = {"ok": False, "error": str(exc)}
        result["checks"]["networkRoute"] = collect_windows_route_diagnosis(args.board_host)
        result["error"] = "board servo endpoint did not prove motion transport"
        return result

    if not args.skip_position_change_check:
        result["checks"]["positionChange"] = run_position_change_probe(
            board_host=args.board_host,
            board_port=int(args.board_port),
            timeout_seconds=float(args.timeout_seconds),
            threshold=int(args.position_delta_threshold),
        )
        if not result["checks"]["positionChange"].get("ok"):
            result["error"] = "board servo endpoint did not prove physical position change"
            return result

    voice_result = dispatch_transcript_once(
        args.transcript,
        bridge_url=args.bridge_url,
        action_timeout_seconds=int(args.action_timeout_seconds),
        speak_reply=bool(args.speak_reply),
    )
    result["checks"]["voiceLoop"] = voice_result
    result["ok"] = bool(voice_result.get("ok"))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Mira hardware motion before claiming voice control works.")
    parser.add_argument("--board-host", default=DEFAULT_BOARD_HOST)
    parser.add_argument("--board-port", type=int, default=DEFAULT_BOARD_PORT)
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--transcript", default=tired_transcript())
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--action-timeout-seconds", type=int, default=8)
    parser.add_argument("--position-delta-threshold", type=int, default=20)
    parser.add_argument("--skip-position-change-check", action="store_true")
    parser.add_argument("--speak-reply", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_acceptance(args)
    output_path = write_result(result, args.output)
    result["outputPath"] = str(output_path)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[mira-hardware-acceptance] ok={result['ok']}")
        print(f"[mira-hardware-acceptance] output={output_path}")
        if not result["ok"]:
            print(f"[mira-hardware-acceptance-error] {result.get('error')}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
