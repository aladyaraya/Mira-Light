from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mira_hardware_motion_acceptance import diagnose_route_risk, parse_positions  # noqa: E402


def test_parse_positions_accepts_four_servo_control_output() -> None:
    raw = """
    OK,read-pos-all
    servo 0 position 2048
    servo 1 position 2150
    servo 2 position 2048
    servo 3 position 2130
    """

    assert parse_positions(raw) == {"0": 2048, "1": 2150, "2": 2048, "3": 2130}


def test_parse_positions_accepts_compact_output() -> None:
    assert parse_positions("0:2048 1:1880 2:2912 3:2130") == {
        "0": 2048,
        "1": 1880,
        "2": 2912,
        "3": 2130,
    }


def test_diagnose_route_risk_flags_vpn_intercept_for_old_board_ip() -> None:
    diagnosis = diagnose_route_risk(
        board_host="192.168.0.183",
        route_rows=[
            {
                "DestinationPrefix": "0.0.0.0/0",
                "NextHop": "198.18.0.2",
                "InterfaceAlias": "Meta",
                "RouteMetric": 0,
                "InterfaceMetric": "",
            },
            {
                "DestinationPrefix": "0.0.0.0/0",
                "NextHop": "192.168.123.254",
                "InterfaceAlias": "WLAN",
                "RouteMetric": 0,
                "InterfaceMetric": 35,
            },
            {
                "DestinationPrefix": "192.168.120.0/22",
                "NextHop": "0.0.0.0",
                "InterfaceAlias": "WLAN",
                "RouteMetric": 256,
                "InterfaceMetric": 35,
            },
        ],
        ip_configs=[
            {"InterfaceAlias": "WLAN", "IPv4Address": "192.168.120.245"},
            {"InterfaceAlias": "Meta", "IPv4Address": "198.18.0.1"},
        ],
    )

    assert diagnosis["risk"] == "vpn-route-risk"
    assert diagnosis["selectedRoute"]["InterfaceAlias"] == "Meta"
    assert diagnosis["boardIsOnLocalSubnet"] is False
    assert "refresh-board-ip" in diagnosis["suggestedActions"]
    assert "add-lan-host-route" in diagnosis["suggestedActions"]
