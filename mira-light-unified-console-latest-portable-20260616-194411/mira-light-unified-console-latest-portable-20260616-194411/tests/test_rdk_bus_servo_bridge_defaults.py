from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_tcp_bridge_defaults_to_uart1_servo_bus(monkeypatch):
    module = _load_module(ROOT / "scripts" / "rdk_bus_servo_tcp_bridge.py", "rdk_bus_servo_tcp_bridge")

    monkeypatch.setattr(sys, "argv", ["rdk_bus_servo_tcp_bridge.py"])

    args = module.parse_args()

    assert args.device == "/dev/ttyS1"
    assert args.center_positions == "2048,2150,2048,2130"
    assert args.four_servo_control == "/home/sunrise/Desktop/four_servo_control.py"


def test_tcp_bridge_maps_neutral_pwm_to_verified_legacy_centers():
    module = _load_module(ROOT / "scripts" / "rdk_bus_servo_tcp_bridge.py", "rdk_bus_servo_tcp_bridge_centers")
    config = module.BridgeConfig(
        device="/dev/ttyS1",
        baudrate=1_000_000,
        timeout=0.2,
        center_positions={0: 2048, 1: 2150, 2: 2048, 3: 2130},
        neutral_pwm=1500,
        steps_per_1000p=1536,
        speed=1000,
        four_servo_control="/home/sunrise/Desktop/four_servo_control.py",
    )

    assert module.pwm_to_position(1500, servo_id=0, config=config) == 2048
    assert module.pwm_to_position(1500, servo_id=1, config=config) == 2150
    assert module.pwm_to_position(1500, servo_id=3, config=config) == 2130


def test_recovery_script_defaults_to_uart1_servo_bus(monkeypatch):
    module = _load_module(
        ROOT / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts" / "recover_board_services.py",
        "recover_board_services",
    )
    monkeypatch.delenv("MIRA_BOOK_FOLLOW_SERVO_DEVICE", raising=False)
    monkeypatch.setattr(sys, "argv", ["recover_board_services.py"])

    args = module.parse_args()

    assert module.DEFAULT_SERVO_DEVICE == "/dev/ttyS1"
    assert args.servo_device == "/dev/ttyS1"
