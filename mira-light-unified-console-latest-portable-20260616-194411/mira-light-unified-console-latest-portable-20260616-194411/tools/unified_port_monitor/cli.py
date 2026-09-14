#!/usr/bin/env python3
"""
统一端口监控命令行工具

提供CLI界面查看端口状态，支持：
- 一次性扫描并输出
- 持续监控模式
- JSON/表格格式输出
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# 添加项目路径
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from .port_monitor import UnifiedPortMonitor, PortStatus, PortInfo


def format_status(status: PortStatus) -> str:
    """格式化状态显示"""
    colors = {
        PortStatus.ONLINE: "\033[92m",      # 绿色
        PortStatus.OFFLINE: "\033[91m",     # 红色
        PortStatus.ERROR: "\033[91m",       # 红色
        PortStatus.WARNING: "\033[93m",     # 黄色
        PortStatus.CHECKING: "\033[96m",    # 青色
        PortStatus.UNKNOWN: "\033[90m",     # 灰色
        PortStatus.NOT_CONFIGURED: "\033[90m",  # 灰色
    }
    reset = "\033[0m"
    color = colors.get(status, "")
    return f"{color}{status.value.upper()}{reset}"


def print_table(ports: List[PortInfo]) -> None:
    """打印表格格式的端口信息"""
    # 表头
    print("\n" + "=" * 120)
    print(f"{'名称':<30} {'类别':<12} {'状态':<12} {'类型':<10} {'地址':<25} {'延迟':<10} {'描述'}")
    print("-" * 120)
    
    # 按类别分组
    categories = {}
    for port in ports:
        cat = port.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(port)
    
    for category, cat_ports in sorted(categories.items()):
        print(f"\n[{category.upper()}]")
        for port in cat_ports:
            status_str = format_status(port.status)
            latency_str = f"{port.latency_ms:.1f}ms" if port.latency_ms else "-"
            address = f"{port.address}:{port.port}" if port.port else port.address
            address = address[:24] if len(address) > 24 else address
            
            print(f"{port.name:<30} {port.category:<12} {status_str:<20} {port.type:<10} {address:<25} {latency_str:<10} {port.description}")
            
            if port.error_message:
                print(f"  └─ 错误: {port.error_message}")
    
    print("=" * 120)


def print_summary(summary: Dict[str, Any]) -> None:
    """打印摘要统计"""
    s = summary["summary"]
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "端口状态摘要" + " " * 31 + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  总计:     {s['total']:<4}                              ║")
    print(f"║  在线:     {s['online']:<4}  ✓                          ║")
    print(f"║  离线:     {s['offline']:<4}  ✗                          ║")
    print(f"║  警告:     {s['warning']:<4}  ⚠                          ║")
    print(f"║  错误:     {s['error']:<4}  ✗                          ║")
    print(f"║  健康度:   {s['healthPercentage']}%{' ' * (35 - len(str(s['healthPercentage'])))}║")
    print("╚" + "═" * 58 + "╝")
    
    print("\n各类别状态:")
    for cat, info in summary["categories"].items():
        status_icon = "✓" if info["online"] == info["total"] else "✗" if info["error"] > 0 else "⚠"
        print(f"  {status_icon} {cat:<15} {info['online']}/{info['total']} 在线")


def print_json_output(data: Dict[str, Any]) -> None:
    """打印JSON格式输出"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def watch_mode(monitor: UnifiedPortMonitor, interval: float = 5.0) -> None:
    """持续监控模式"""
    print("\n进入持续监控模式 (按 Ctrl+C 退出)...")
    print(f"刷新间隔: {interval}秒\n")
    
    try:
        while True:
            # 清屏
            print("\033[2J\033[H", end="")
            
            ports = monitor.scan_all_ports()
            summary = monitor.get_port_summary()
            
            print(f"\n[监控时间: {summary['timestamp']}]")
            print_summary(summary)
            print_table(ports)
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n退出监控模式。")


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="Mira Light Unified Port Monitor CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 一次性扫描并显示表格
  %(prog)s --json                   # 输出JSON格式
  %(prog)s --watch                  # 持续监控模式
  %(prog)s --watch --interval 10    # 每10秒刷新
  %(prog)s --category servo         # 只显示舵机类别
  %(prog)s --category network,ssh   # 显示网络和SSH类别
        """
    )
    
    parser.add_argument("--project-root", type=str, help="项目根目录路径")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--watch", action="store_true", help="持续监控模式")
    parser.add_argument("--interval", type=float, default=5.0, help="刷新间隔(秒)")
    parser.add_argument("--category", type=str, help="筛选类别，逗号分隔")
    parser.add_argument("--summary-only", action="store_true", help="仅显示摘要")
    
    args = parser.parse_args()
    
    # 初始化监控器
    project_root = Path(args.project_root) if args.project_root else None
    monitor = UnifiedPortMonitor(project_root=project_root)
    
    # 持续监控模式
    if args.watch:
        watch_mode(monitor, interval=args.interval)
        return 0
    
    # 一次性扫描
    ports = monitor.scan_all_ports()
    summary = monitor.get_port_summary()
    
    # 类别筛选
    if args.category:
        categories = [c.strip() for c in args.category.split(",")]
        ports = [p for p in ports if p.category in categories]
        summary["ports"] = [p.to_dict() for p in ports]
    
    # JSON输出
    if args.json:
        print_json_output(summary)
        return 0
    
    # 表格输出
    print_summary(summary)
    
    if not args.summary_only:
        print_table(ports)
    
    # 如果有错误，返回非零退出码
    if summary["summary"]["error"] > 0:
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
