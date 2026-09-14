#!/usr/bin/env python3
"""
统一端口监控核心模块

负责检测和监控所有工程端口的状态：
- 舵机串口/TCP
- 音频设备
- 网络连接
- SSH隧道
- HTTP服务
- 模型API端点
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse


class PortStatus(Enum):
    """端口状态枚举"""
    UNKNOWN = "unknown"           # 未知状态
    ONLINE = "online"             # 在线/正常
    OFFLINE = "offline"           # 离线/断开
    ERROR = "error"               # 错误
    WARNING = "warning"           # 警告
    CHECKING = "checking"         # 检测中
    NOT_CONFIGURED = "not_configured"  # 未配置


@dataclass
class PortInfo:
    """端口信息数据类"""
    name: str                           # 端口名称
    category: str                       # 类别: servo/audio/network/ssh/model/bridge
    status: PortStatus                  # 状态
    type: str                           # 类型: serial/tcp/http/websocket/ssh
    address: str                        # 地址/路径
    port: Optional[int] = None          # 端口号
    description: str = ""               # 描述
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    last_checked: Optional[str] = None  # 最后检测时间
    latency_ms: Optional[float] = None  # 延迟(ms)
    error_message: Optional[str] = None # 错误信息

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status.value,
            "type": self.type,
            "address": self.address,
            "port": self.port,
            "description": self.description,
            "details": self.details,
            "lastChecked": self.last_checked,
            "latencyMs": self.latency_ms,
            "errorMessage": self.error_message,
        }


class UnifiedPortMonitor:
    """
    统一端口监控器
    
    自动检测和监控 Mira Light 项目中的所有端口和连接。
    """

    # 默认配置路径
    DEFAULT_CONFIG_PATHS = [
        Path("Mira-Light-Voice-Full-Ready/config/bus_servo_runtime.json"),
        Path("config/bus_servo_runtime.json"),
        Path("Mira-Light-Voice-Cloud-Ready/config/bus_servo_runtime.json"),
    ]

    DEFAULT_ENV_PATHS = [
        Path("portable/unified-console.env"),
        Path("Mira-Light-Voice-Full-Ready/config/mira-light-realtime.env"),
        Path("Mira-Light-Voice-Full-Ready/config/windows-voice-stepfun.env"),
    ]

    DEFAULT_BRIDGE_CONFIGS = [
        Path("Mira-Light-Voice-Full-Ready/tools/mira_light_bridge/bridge_config.json"),
        Path("tools/mira_light_bridge/bridge_config.json"),
    ]

    # RDK X5 板子默认配置
    DEFAULT_BOARD_HOST = "192.168.0.183"
    DEFAULT_BOARD_SSH_PORT = 22
    DEFAULT_BOARD_SSH_USER = "root"
    DEFAULT_SERVO_TCP_PORT = 9527

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.ports: List[PortInfo] = []
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[List[PortInfo]], None]] = []
        self._env_vars: Dict[str, str] = {}
        self._configs: Dict[str, Any] = {}
        
        # 加载配置
        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """加载所有配置文件"""
        # 加载环境变量
        for env_path in self.DEFAULT_ENV_PATHS:
            full_path = self.project_root / env_path
            if full_path.exists():
                self._load_env_file(full_path)
        
        # 加载JSON配置
        for config_path in self.DEFAULT_CONFIG_PATHS:
            full_path = self.project_root / config_path
            if full_path.exists():
                try:
                    if "bus_servo_runtime" not in self._configs:  # 只加载第一个找到的
                        self._configs["bus_servo_runtime"] = json.loads(full_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
        
        # 加载Bridge配置
        for bridge_path in self.DEFAULT_BRIDGE_CONFIGS:
            full_path = self.project_root / bridge_path
            if full_path.exists():
                try:
                    if "bridge" not in self._configs:  # 只加载第一个找到的
                        self._configs["bridge"] = json.loads(full_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

    def _load_env_file(self, path: Path) -> None:
        """加载环境变量文件"""
        try:
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:]
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    self._env_vars[key] = value
        except Exception:
            pass

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    def _check_tcp_port(self, host: str, port: int, timeout: float = 2.0) -> Tuple[PortStatus, Optional[float], Optional[str]]:
        """检测TCP端口是否开放"""
        start = time.time()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                latency = (time.time() - start) * 1000
                return PortStatus.ONLINE, latency, None
        except socket.timeout:
            return PortStatus.OFFLINE, None, "Connection timeout"
        except ConnectionRefusedError:
            return PortStatus.OFFLINE, None, "Connection refused"
        except OSError as e:
            return PortStatus.ERROR, None, str(e)

    def _check_http_endpoint(self, url: str, timeout: float = 3.0) -> Tuple[PortStatus, Optional[float], Optional[str], Optional[Dict]]:
        """检测HTTP端点"""
        start = time.time()
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "MiraLight-PortMonitor/1.0")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = (time.time() - start) * 1000
                status = PortStatus.ONLINE if resp.status < 400 else PortStatus.WARNING
                data = None
                try:
                    body = resp.read().decode("utf-8", errors="replace")
                    data = json.loads(body) if body else None
                except Exception:
                    pass
                return status, latency, None, data
        except urllib.error.HTTPError as e:
            latency = (time.time() - start) * 1000
            if e.code == 401:
                return PortStatus.ONLINE, latency, None, None  # 需要认证但服务在线
            return PortStatus.WARNING, latency, f"HTTP {e.code}", None
        except urllib.error.URLError as e:
            return PortStatus.OFFLINE, None, str(e.reason), None
        except socket.timeout:
            return PortStatus.OFFLINE, None, "Timeout", None
        except Exception as e:
            return PortStatus.ERROR, None, str(e), None

    def _check_websocket_endpoint(self, url: str, timeout: float = 3.0) -> Tuple[PortStatus, Optional[float], Optional[str]]:
        """检测WebSocket端点 (简化检测，只验证TCP连接)"""
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        if not host:
            return PortStatus.ERROR, None, "Invalid WebSocket URL"
        return self._check_tcp_port(host, port, timeout)

    def _check_serial_port(self, port_path: str) -> Tuple[PortStatus, Optional[str]]:
        """检测串口是否可用"""
        try:
            import serial
            try:
                with serial.Serial(port_path, baudrate=115200, timeout=1) as ser:
                    return PortStatus.ONLINE, f"Serial port accessible, baudrate={ser.baudrate}"
            except serial.SerialException as e:
                return PortStatus.OFFLINE, str(e)
        except ImportError:
            # 没有pyserial，尝试文件检测
            if sys.platform == "win32":
                # Windows COM端口检测
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM")
                    ports = []
                    i = 0
                    while True:
                        try:
                            _, value, _ = winreg.EnumValue(key, i)
                            ports.append(value)
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                    if port_path in ports:
                        return PortStatus.ONLINE, "COM port found in registry"
                    return PortStatus.OFFLINE, "COM port not found"
                except Exception as e:
                    return PortStatus.ERROR, str(e)
            else:
                # Unix-like系统
                path = Path(port_path)
                if path.exists():
                    return PortStatus.ONLINE, "Device file exists"
                return PortStatus.OFFLINE, "Device file not found"

    def _check_ssh_tunnel(self, local_port: int) -> Tuple[PortStatus, Optional[float], Optional[str]]:
        """检测SSH隧道是否建立"""
        # 首先检查本地端口是否监听
        status, latency, error = self._check_tcp_port("127.0.0.1", local_port)
        if status == PortStatus.ONLINE:
            return PortStatus.ONLINE, latency, "SSH tunnel active"
        return PortStatus.OFFLINE, None, error or "SSH tunnel not established"

    def _check_process_running(self, process_name: str) -> bool:
        """检查进程是否正在运行"""
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                    capture_output=True, text=True, timeout=5
                )
                return process_name.lower() in result.stdout.lower()
            else:
                result = subprocess.run(
                    ["pgrep", "-f", process_name],
                    capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0
        except Exception:
            return False

    def detect_servo_ports(self) -> List[PortInfo]:
        """检测舵机端口"""
        ports = []
        
        # 从配置获取（优先使用 bridge_config 中的 lampBaseUrl）
        bridge_config = self._configs.get("bridge", {})
        lamp_url = bridge_config.get("lampBaseUrl", "")
        servo_config = self._configs.get("bus_servo_runtime", {})
        
        # 解析 lampBaseUrl 中的 host:port
        if lamp_url and "tcp://" in lamp_url:
            parsed = urlparse(lamp_url)
            host = parsed.hostname or self.DEFAULT_BOARD_HOST
            port = parsed.port or self.DEFAULT_SERVO_TCP_PORT
        elif servo_config.get("transport") == "tcp":
            host = servo_config.get("tcpHost", self.DEFAULT_BOARD_HOST)
            port = servo_config.get("tcpPort", self.DEFAULT_SERVO_TCP_PORT)
        else:
            host = self.DEFAULT_BOARD_HOST
            port = self.DEFAULT_SERVO_TCP_PORT
        
        timeout = servo_config.get("timeoutSeconds", 2.0)
        
        status, latency, error = self._check_tcp_port(host, port, timeout)
        ports.append(PortInfo(
            name="Bus Servo TCP",
            category="servo",
            status=status,
            type="tcp",
            address=f"{host}:{port}",
            port=port,
            description="RDK X5 Bus Servo TCP Bridge",
            details={
                "transport": "tcp",
                "host": host,
                "timeoutSeconds": timeout,
                "defaultMoveMs": servo_config.get("defaultMoveMs", 220),
                "requireAck": servo_config.get("requireAck", True),
            },
            last_checked=self._now(),
            latency_ms=latency,
            error_message=error,
        ))
        
        # 关节映射信息
        joint_map_path = self.project_root / "config" / "bus_servo_joint_map.json"
        if joint_map_path.exists():
            try:
                joint_map = json.loads(joint_map_path.read_text(encoding="utf-8"))
                for port in ports:
                    if port.category == "servo":
                        port.details["jointMap"] = joint_map
            except Exception:
                pass
        
        return ports

    def detect_audio_ports(self) -> List[PortInfo]:
        """检测音频端口和设备"""
        ports = []
        
        # 麦克风设备
        mic_device = self._env_vars.get("MIRA_LIGHT_MIC_DEVICE", "")
        
        # 检测音频设备
        audio_devices = self._scan_audio_devices()
        
        ports.append(PortInfo(
            name="Audio Input (Microphone)",
            category="audio",
            status=PortStatus.ONLINE if audio_devices.get("inputs") else PortStatus.WARNING,
            type="audio",
            address=mic_device or "default",
            description="Microphone input device",
            details={
                "configuredDevice": mic_device,
                "availableInputs": audio_devices.get("inputs", []),
                "availableOutputs": audio_devices.get("outputs", []),
            },
            last_checked=self._now(),
        ))
        
        # 音频输出
        ports.append(PortInfo(
            name="Audio Output (Speaker)",
            category="audio",
            status=PortStatus.ONLINE if audio_devices.get("outputs") else PortStatus.WARNING,
            type="audio",
            address="default",
            description="Speaker output device",
            details={
                "availableOutputs": audio_devices.get("outputs", []),
                "prepareCommand": self._env_vars.get("MIRA_LIGHT_AUDIO_PREPARE_CMD", ""),
            },
            last_checked=self._now(),
        ))
        
        # Touch-Audio Bridge (精简音频桥，可选服务)
        # 注意：Touch-Audio Bridge 功能已集成到主 Bridge 的 /v1/mira-light/trigger 端点
        # 主 Bridge 端口从配置文件读取，env 变量作为备选
        bridge_cfg = self._configs.get("bridge", {})
        # 优先使用配置文件中的 listenPort，env 变量作为 fallback
        bridge_port_check = int(bridge_cfg.get("listenPort", 19783))
        bridge_host_check = self._env_vars.get("MIRA_LIGHT_BRIDGE_HOST", "127.0.0.1")
        _bridge_status, _bridge_latency, _ = self._check_tcp_port(bridge_host_check, bridge_port_check)
        
        if _bridge_status == PortStatus.ONLINE:
            ports.append(PortInfo(
                name="Touch-Audio Bridge",
                category="audio",
                status=PortStatus.ONLINE,
                type="http",
                address=f"{bridge_host_check}:{bridge_port_check}",
                port=bridge_port_check,
                description="Touch Audio (由主 Bridge 提供 /v1/mira-light/trigger)",
                details={"note": "触摸音频功能已集成到主 Bridge HTTP 中"},
                last_checked=self._now(),
                latency_ms=_bridge_latency,
            ))
        else:
            # 如果主 Bridge 没运行，尝试检测独立 Touch-Audio Bridge
            _status, _latency, _error = self._check_tcp_port("127.0.0.1", 5000)
            ports.append(PortInfo(
                name="Touch-Audio Bridge",
                category="audio",
                status=_status,
                type="http",
                address="127.0.0.1:5000",
                port=5000,
                description="Touch-Audio Bridge HTTP Server (standalone)",
                details={"endpoint": "http://127.0.0.1:5000/touch/event"},
                last_checked=self._now(),
                latency_ms=_latency,
                error_message=_error,
            ))
        
        return ports

    def _scan_audio_devices(self) -> Dict[str, List[Dict[str, str]]]:
        """扫描音频设备"""
        devices = {"inputs": [], "outputs": []}
        
        try:
            import sounddevice as sd
            all_devices = sd.query_devices()
            for i, device in enumerate(all_devices):
                dev_info = {
                    "index": str(i),
                    "name": device.get("name", "Unknown"),
                    "channels": str(device.get("max_input_channels" if device.get("max_input_channels", 0) > 0 else "max_output_channels", 0)),
                }
                if device.get("max_input_channels", 0) > 0:
                    devices["inputs"].append(dev_info)
                if device.get("max_output_channels", 0) > 0:
                    devices["outputs"].append(dev_info)
        except ImportError:
            pass
        
        # 尝试使用pyaudio
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                dev_info = {
                    "index": str(i),
                    "name": info.get("name", "Unknown"),
                    "channels": str(info.get("maxInputChannels" if info.get("maxInputChannels", 0) > 0 else "maxOutputChannels", 0)),
                }
                if info.get("maxInputChannels", 0) > 0:
                    if not any(d["name"] == dev_info["name"] for d in devices["inputs"]):
                        devices["inputs"].append(dev_info)
                if info.get("maxOutputChannels", 0) > 0:
                    if not any(d["name"] == dev_info["name"] for d in devices["outputs"]):
                        devices["outputs"].append(dev_info)
            p.terminate()
        except ImportError:
            pass
        
        return devices

    def detect_network_ports(self) -> List[PortInfo]:
        """检测网络端口和服务"""
        ports = []
        
        # RDK X5 板子 SSH
        board_host = self._env_vars.get("MIRA_SHENZHEN_BOARD_HOST", self.DEFAULT_BOARD_HOST)
        board_ssh_port = int(self._env_vars.get("MIRA_SHENZHEN_BOARD_PORT", str(self.DEFAULT_BOARD_SSH_PORT)))
        
        status, latency, error = self._check_tcp_port(board_host, board_ssh_port)
        ports.append(PortInfo(
            name="RDK X5 Board SSH",
            category="network",
            status=status,
            type="ssh",
            address=f"{board_host}:{board_ssh_port}",
            port=board_ssh_port,
            description="RDK X5 开发板 SSH 远程管理",
            details={
                "host": board_host,
                "os": "Ubuntu 22.04 (aarch64)",
                "user": self._env_vars.get("MIRA_SHENZHEN_BOARD_USER", self.DEFAULT_BOARD_SSH_USER),
                "serialDevices": ["/dev/ttyS1 (servo UART)"],
            },
            last_checked=self._now(),
            latency_ms=latency,
            error_message=error,
        ))
        
        # 主 Bridge HTTP 服务 (从配置读取端口)
        bridge_cfg = self._configs.get("bridge", {})
        bridge_host = self._env_vars.get("MIRA_LIGHT_BRIDGE_HOST", "127.0.0.1")
        # 优先使用配置文件中的 listenPort，默认 19783
        bridge_port = int(bridge_cfg.get("listenPort", 19783))
        
        bridge_status, bridge_latency, bridge_error, bridge_data = self._check_http_endpoint(
            f"http://{bridge_host}:{bridge_port}/health"
        )
        ports.append(PortInfo(
            name="Mira Light Bridge HTTP",
            category="bridge",
            status=bridge_status,
            type="http",
            address=f"{bridge_host}:{bridge_port}",
            port=bridge_port,
            description="Mira Light Bridge HTTP API (Action Bridge)",
            details={
                "healthEndpoint": f"http://{bridge_host}:{bridge_port}/health",
                "lampBaseUrl": bridge_cfg.get("lampBaseUrl", ""),
                "version": bridge_data.get("service") if bridge_data else None,
                "runtimeState": bridge_data.get("runtime") if bridge_data else None,
            },
            last_checked=self._now(),
            latency_ms=bridge_latency,
            error_message=bridge_error,
        ))
        
        # Director 服务 (19783)
        director_port = int(self._env_vars.get("MIRA_LIGHT_DIRECTOR_PORT", "19783"))
        director_status, director_latency, director_error, _ = self._check_http_endpoint(
            f"http://127.0.0.1:{director_port}/health"
        )
        ports.append(PortInfo(
            name="Mira Light Director",
            category="bridge",
            status=director_status,
            type="http",
            address=f"127.0.0.1:{director_port}",
            port=director_port,
            description="Unified Director Console HTTP API",
            details={"healthEndpoint": f"http://127.0.0.1:{director_port}/health"},
            last_checked=self._now(),
            latency_ms=director_latency,
            error_message=director_error,
        ))
        
        # 检查本地IP和网络接口
        network_info = self._get_network_info()
        ports.append(PortInfo(
            name="Local Network Interfaces",
            category="network",
            status=PortStatus.ONLINE,
            type="network",
            address="localhost",
            description="Local network interface information",
            details=network_info,
            last_checked=self._now(),
        ))
        
        return ports

    def _get_network_info(self) -> Dict[str, Any]:
        """获取网络接口信息"""
        info = {"interfaces": [], "hostname": socket.gethostname()}
        
        try:
            # 获取所有网络接口
            if sys.platform == "win32":
                result = subprocess.run(
                    ["ipconfig"],
                    capture_output=True, text=True, timeout=10
                )
                info["ipconfig"] = result.stdout
            else:
                result = subprocess.run(
                    ["ip", "addr"],
                    capture_output=True, text=True, timeout=10
                )
                info["ipAddr"] = result.stdout
                
                # 获取路由表
                route_result = subprocess.run(
                    ["ip", "route"],
                    capture_output=True, text=True, timeout=10
                )
                info["routes"] = route_result.stdout.splitlines()
        except Exception as e:
            info["error"] = str(e)
        
        # 获取本机IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            info["localIp"] = s.getsockname()[0]
            s.close()
        except Exception:
            info["localIp"] = "127.0.0.1"
        
        return info

    def detect_ssh_tunnels(self) -> List[PortInfo]:
        """检测SSH隧道"""
        ports = []
        
        # Lingzhu SSH Tunnel
        lingzhu_local_port = int(self._env_vars.get("MIRA_LIGHT_LINGZHU_TUNNEL_LOCAL_PORT", "31879"))
        lingzhu_remote_host = self._env_vars.get("MIRA_LIGHT_LINGZHU_REMOTE_HOST", "43.160.239.180")
        lingzhu_remote_port = int(self._env_vars.get("MIRA_LIGHT_LINGZHU_REMOTE_TARGET_PORT", "18789"))
        
        status, latency, error = self._check_ssh_tunnel(lingzhu_local_port)
        ports.append(PortInfo(
            name="Lingzhu SSH Tunnel",
            category="ssh",
            status=status,
            type="ssh_tunnel",
            address=f"127.0.0.1:{lingzhu_local_port} -> {lingzhu_remote_host}:{lingzhu_remote_port}",
            port=lingzhu_local_port,
            description="SSH tunnel to Lingzhu remote service",
            details={
                "localHost": "127.0.0.1",
                "localPort": lingzhu_local_port,
                "remoteHost": lingzhu_remote_host,
                "remotePort": lingzhu_remote_port,
                "remoteUser": self._env_vars.get("MIRA_LIGHT_LINGZHU_REMOTE_USER", "ubuntu"),
            },
            last_checked=self._now(),
            latency_ms=latency,
            error_message=error,
        ))
        
        # 检查SSH进程
        ssh_running = self._check_process_running("ssh.exe" if sys.platform == "win32" else "ssh")
        ports.append(PortInfo(
            name="SSH Process",
            category="ssh",
            status=PortStatus.ONLINE if ssh_running else PortStatus.OFFLINE,
            type="process",
            address="ssh",
            description="SSH client process",
            details={"running": ssh_running},
            last_checked=self._now(),
        ))
        
        return ports

    def detect_model_endpoints(self) -> List[PortInfo]:
        """检测模型API端点"""
        ports = []
        
        # StepFun Realtime WebSocket
        stepfun_ws_url = "wss://api.stepfun.com/v1/realtime"
        ws_status, ws_latency, ws_error = self._check_websocket_endpoint(stepfun_ws_url)
        ports.append(PortInfo(
            name="StepFun Realtime API",
            category="model",
            status=ws_status,
            type="websocket",
            address=stepfun_ws_url,
            port=443,
            description="StepFun StepAudio Realtime WebSocket API",
            details={
                "model": "stepaudio-2.5-realtime",
                "proxyUrl": self._env_vars.get("STEPFUN_PROXY_URL", ""),
            },
            last_checked=self._now(),
            latency_ms=ws_latency,
            error_message=ws_error,
        ))
        
        # OpenClaw Agent
        openclaw_url = self._env_vars.get("OPENCLAW_AGENT_BASE_URL", "")
        if openclaw_url:
            oc_status, oc_latency, oc_error, oc_data = self._check_http_endpoint(
                f"{openclaw_url}/health", timeout=5.0
            )
            ports.append(PortInfo(
                name="OpenClaw Agent",
                category="model",
                status=oc_status,
                type="http",
                address=openclaw_url,
                description="OpenClaw Agent API",
                details={"healthResponse": oc_data},
                last_checked=self._now(),
                latency_ms=oc_latency,
                error_message=oc_error,
            ))
        
        # Lingzhu HTTP API (通过隧道)
        lingzhu_base = self._env_vars.get("MIRA_LIGHT_LINGZHU_BASE_URL", "http://127.0.0.1:31879")
        if lingzhu_base:
            lz_status, lz_latency, lz_error, lz_data = self._check_http_endpoint(
                f"{lingzhu_base}/health", timeout=3.0
            )
            ports.append(PortInfo(
                name="Lingzhu API",
                category="model",
                status=lz_status,
                type="http",
                address=lingzhu_base,
                description="Lingzhu Remote Adapter HTTP API",
                details={
                    "agentId": self._env_vars.get("MIRA_LIGHT_LINGZHU_AGENT_ID", "main"),
                    "authConfigured": bool(self._env_vars.get("MIRA_LIGHT_LINGZHU_AUTH_AK", "")),
                },
                last_checked=self._now(),
                latency_ms=lz_latency,
                error_message=lz_error,
            ))
        
        # API Keys 状态
        api_keys = {
            "STEPFUN_API_KEY": bool(self._env_vars.get("STEPFUN_API_KEY", "")),
            "OPENCLAW_NEWAPI_API_KEY": bool(self._env_vars.get("OPENCLAW_NEWAPI_API_KEY", "")),
            "OPENCLAW_OAI1_API_KEY": bool(self._env_vars.get("OPENCLAW_OAI1_API_KEY", "")),
            "MIRA_LINGZHU_AUTH_AK": bool(self._env_vars.get("MIRA_LINGZHU_AUTH_AK", "")),
        }
        ports.append(PortInfo(
            name="API Keys Status",
            category="model",
            status=PortStatus.ONLINE if any(api_keys.values()) else PortStatus.WARNING,
            type="config",
            address="environment",
            description="API key configuration status",
            details=api_keys,
            last_checked=self._now(),
        ))
        
        return ports

    def detect_project_modules(self) -> List[PortInfo]:
        """检测本地项目模块状态"""
        ports = []
        
        modules = [
            ("Mira Light Runtime", "scripts/mira_light_runtime.py", "runtime"),
            ("Bus Servo Adapter", "scripts/bus_servo_adapter.py", "servo"),
            ("Bus Servo Protocol", "scripts/bus_servo_protocol.py", "servo"),
            ("Bus Servo Transport", "scripts/bus_servo_transport.py", "servo"),
            ("Mira Light Audio", "Mira-Light-Voice-Full-Ready/scripts/mira_light_audio.py", "audio"),
            ("Voice Interaction", "Mira-Light-Voice-Full-Ready/scripts/mira_realtime_voice_interaction.py", "voice"),
            ("StepFun Voice", "Mira-Light-Voice-Full-Ready/scripts/stepfun_realtime_voice.py", "voice"),
            ("Action Orchestrator", "Mira-Light-Voice-Full-Ready/scripts/mira_realtime_action_orchestrator.py", "runtime"),
            ("Bridge Server", "tools/mira_light_bridge/bridge_server.py", "bridge"),
            ("Scenes", "Mira-Light-Voice-Full-Ready/scripts/scenes.py", "runtime"),
        ]
        
        for name, rel_path, category in modules:
            full_path = self.project_root / rel_path
            exists = full_path.exists()
            
            # 检查文件大小和修改时间
            details = {"path": str(rel_path)}
            if exists:
                stat = full_path.stat()
                details["size"] = stat.st_size
                details["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            ports.append(PortInfo(
                name=name,
                category="module",
                status=PortStatus.ONLINE if exists else PortStatus.ERROR,
                type="file",
                address=str(rel_path),
                description=f"Project module: {name}",
                details=details,
                last_checked=self._now(),
                error_message=None if exists else "File not found",
            ))
        
        # 配置文件状态
        config_files = [
            ("Bus Servo Runtime Config", "config/bus_servo_runtime.json"),
            ("Bridge Config", "tools/mira_light_bridge/bridge_config.json"),
            ("Signal Delivery Schema", "Mira-Light-Voice-Full-Ready/config/mira_light_signal_delivery.schema.json"),
            ("Voice Env", "Mira-Light-Voice-Full-Ready/config/mira-light-realtime.env"),
        ]
        
        for name, rel_path in config_files:
            full_path = self.project_root / rel_path
            exists = full_path.exists()
            ports.append(PortInfo(
                name=name,
                category="module",
                status=PortStatus.ONLINE if exists else PortStatus.WARNING,
                type="config",
                address=str(rel_path),
                description=f"Configuration file: {name}",
                details={"exists": exists, "path": str(rel_path)},
                last_checked=self._now(),
                error_message=None if exists else "Config file not found",
            ))
        
        return ports

    def scan_all_ports(self) -> List[PortInfo]:
        """扫描所有端口并返回完整状态"""
        all_ports = []
        
        all_ports.extend(self.detect_servo_ports())
        all_ports.extend(self.detect_audio_ports())
        all_ports.extend(self.detect_network_ports())
        all_ports.extend(self.detect_ssh_tunnels())
        all_ports.extend(self.detect_model_endpoints())
        all_ports.extend(self.detect_project_modules())
        
        with self._lock:
            self.ports = all_ports
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(all_ports)
            except Exception:
                pass
        
        return all_ports

    def get_ports_by_category(self, category: str) -> List[PortInfo]:
        """按类别获取端口"""
        with self._lock:
            return [p for p in self.ports if p.category == category]

    def get_port_summary(self) -> Dict[str, Any]:
        """获取端口摘要统计"""
        with self._lock:
            ports = self.ports.copy()
        
        total = len(ports)
        online = sum(1 for p in ports if p.status == PortStatus.ONLINE)
        offline = sum(1 for p in ports if p.status == PortStatus.OFFLINE)
        error = sum(1 for p in ports if p.status == PortStatus.ERROR)
        warning = sum(1 for p in ports if p.status == PortStatus.WARNING)
        
        categories = {}
        for p in ports:
            cat = p.category
            if cat not in categories:
                categories[cat] = {"total": 0, "online": 0, "offline": 0, "error": 0}
            categories[cat]["total"] += 1
            if p.status == PortStatus.ONLINE:
                categories[cat]["online"] += 1
            elif p.status == PortStatus.OFFLINE:
                categories[cat]["offline"] += 1
            elif p.status == PortStatus.ERROR:
                categories[cat]["error"] += 1
        
        return {
            "timestamp": self._now(),
            "summary": {
                "total": total,
                "online": online,
                "offline": offline,
                "error": error,
                "warning": warning,
                "healthPercentage": round((online / total * 100), 1) if total > 0 else 0,
            },
            "categories": categories,
            "ports": [p.to_dict() for p in ports],
        }

    def start_monitoring(self, interval_seconds: float = 10.0) -> None:
        """启动持续监控"""
        if self._running:
            return
        
        self._running = True
        
        def monitor_loop():
            while self._running:
                self.scan_all_ports()
                time.sleep(interval_seconds)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)

    def on_update(self, callback: Callable[[List[PortInfo]], None]) -> None:
        """注册状态更新回调"""
        self._callbacks.append(callback)

    def get_environment_summary(self) -> Dict[str, Any]:
        """获取环境变量摘要"""
        return {
            "projectRoot": str(self.project_root),
            "platform": sys.platform,
            "pythonVersion": sys.version,
            "environmentVariables": {
                k: "***" if "KEY" in k or "PASSWORD" in k or "AUTH" in k or "TOKEN" in k else v
                for k, v in self._env_vars.items()
            },
            "loadedConfigs": list(self._configs.keys()),
        }
