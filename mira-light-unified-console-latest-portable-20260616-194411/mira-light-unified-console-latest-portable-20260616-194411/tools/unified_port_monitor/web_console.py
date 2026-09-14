#!/usr/bin/env python3
"""
统一端口监控 Web 控制台

提供美观的Web界面展示所有端口状态：
- 实时状态面板
- 分类展示
- 详细信息查看
- 自动刷新
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# 添加项目路径
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from .port_monitor import UnifiedPortMonitor, PortStatus


# HTML 模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mira Light 统一端口监控</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }
        
        header h1 {
            font-size: 2.5em;
            font-weight: 300;
            letter-spacing: 2px;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        header .subtitle {
            color: #888;
            font-size: 1.1em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        
        .stat-card .number {
            font-size: 3em;
            font-weight: 700;
            margin: 10px 0;
        }
        
        .stat-card .label {
            color: #888;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-card.online { border-top: 3px solid #00d4ff; }
        .stat-card.online .number { color: #00d4ff; }
        
        .stat-card.offline { border-top: 3px solid #ff6b6b; }
        .stat-card.offline .number { color: #ff6b6b; }
        
        .stat-card.warning { border-top: 3px solid #ffd93d; }
        .stat-card.warning .number { color: #ffd93d; }
        
        .stat-card.error { border-top: 3px solid #ff4757; }
        .stat-card.error .number { color: #ff4757; }
        
        .category-section {
            margin-bottom: 30px;
        }
        
        .category-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding: 0 10px;
        }
        
        .category-header h2 {
            font-size: 1.5em;
            font-weight: 500;
            color: #fff;
        }
        
        .category-badge {
            background: rgba(255,255,255,0.1);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            color: #888;
        }
        
        .ports-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 16px;
        }
        
        .port-card {
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.05);
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .port-card:hover {
            background: rgba(255,255,255,0.06);
            border-color: rgba(255,255,255,0.15);
        }
        
        .port-card.online { border-left: 4px solid #00d4ff; }
        .port-card.offline { border-left: 4px solid #ff6b6b; }
        .port-card.error { border-left: 4px solid #ff4757; }
        .port-card.warning { border-left: 4px solid #ffd93d; }
        .port-card.checking { border-left: 4px solid #888; }
        
        .port-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .port-name {
            font-weight: 600;
            font-size: 1.1em;
            color: #fff;
        }
        
        .port-status {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .port-status.online { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }
        .port-status.offline { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
        .port-status.error { background: rgba(255, 71, 87, 0.2); color: #ff4757; }
        .port-status.warning { background: rgba(255, 217, 61, 0.2); color: #ffd93d; }
        .port-status.checking { background: rgba(136, 136, 136, 0.2); color: #888; }
        
        .port-address {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #00d4ff;
            margin-bottom: 8px;
        }
        
        .port-description {
            color: #888;
            font-size: 0.85em;
            margin-bottom: 12px;
        }
        
        .port-details {
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 12px;
            font-size: 0.8em;
            color: #aaa;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .port-details summary {
            cursor: pointer;
            color: #ccc;
            font-weight: 500;
        }
        
        .port-details pre {
            margin-top: 10px;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .latency-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75em;
            margin-left: 8px;
        }
        
        .latency-good { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }
        .latency-medium { background: rgba(255, 217, 61, 0.2); color: #ffd93d; }
        .latency-bad { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
        
        .refresh-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(10px);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .refresh-bar button {
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            border: none;
            color: white;
            padding: 8px 24px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9em;
            transition: opacity 0.3s;
        }
        
        .refresh-bar button:hover {
            opacity: 0.8;
        }
        
        .last-updated {
            color: #888;
            font-size: 0.85em;
        }
        
        .error-message {
            color: #ff6b6b;
            font-size: 0.8em;
            margin-top: 8px;
            padding: 8px;
            background: rgba(255, 107, 107, 0.1);
            border-radius: 6px;
        }
        
        @media (max-width: 768px) {
            .ports-grid {
                grid-template-columns: 1fr;
            }
            header h1 {
                font-size: 1.8em;
            }
        }
        
        /* 动画 */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .checking .port-status {
            animation: pulse 1.5s infinite;
        }
        
        /* 滚动条样式 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(0,0,0,0.1);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.2);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255,255,255,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Mira Light 统一端口监控</h1>
            <p class="subtitle">Unified Port Monitor - 实时工程端口状态面板</p>
        </header>
        
        <div class="stats-grid" id="statsGrid">
            <!-- 统计卡片将通过JS动态生成 -->
        </div>
        
        <div id="categoriesContainer">
            <!-- 分类区域将通过JS动态生成 -->
        </div>
    </div>
    
    <div class="refresh-bar">
        <span class="last-updated" id="lastUpdated">最后更新: --</span>
        <button onclick="refreshData()">立即刷新</button>
    </div>
    
    <script>
        let autoRefreshInterval;
        
        function getStatusClass(status) {
            const map = {
                'online': 'online',
                'offline': 'offline',
                'error': 'error',
                'warning': 'warning',
                'checking': 'checking',
                'unknown': 'checking',
                'not_configured': 'warning'
            };
            return map[status] || 'checking';
        }
        
        function getLatencyClass(ms) {
            if (!ms) return '';
            if (ms < 50) return 'latency-good';
            if (ms < 200) return 'latency-medium';
            return 'latency-bad';
        }
        
        function formatLatency(ms) {
            if (!ms) return '';
            return `<span class="latency-badge ${getLatencyClass(ms)}">${ms.toFixed(1)}ms</span>`;
        }
        
        function renderStats(summary) {
            const statsGrid = document.getElementById('statsGrid');
            statsGrid.innerHTML = `
                <div class="stat-card online">
                    <div class="label">在线</div>
                    <div class="number">${summary.online}</div>
                </div>
                <div class="stat-card offline">
                    <div class="label">离线</div>
                    <div class="number">${summary.offline}</div>
                </div>
                <div class="stat-card warning">
                    <div class="label">警告</div>
                    <div class="number">${summary.warning}</div>
                </div>
                <div class="stat-card error">
                    <div class="label">错误</div>
                    <div class="number">${summary.error}</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #7b2cbf;">
                    <div class="label">健康度</div>
                    <div class="number" style="color: #7b2cbf;">${summary.healthPercentage}%</div>
                </div>
                <div class="stat-card" style="border-top: 3px solid #00d4ff;">
                    <div class="label">总计</div>
                    <div class="number" style="color: #00d4ff;">${summary.total}</div>
                </div>
            `;
        }
        
        function renderCategories(ports, categories) {
            const container = document.getElementById('categoriesContainer');
            const categoryNames = {
                'servo': '舵机系统',
                'audio': '音频系统',
                'network': '网络连接',
                'ssh': 'SSH 隧道',
                'model': '模型服务',
                'bridge': '桥接服务',
                'module': '项目模块',
                'voice': '语音系统'
            };
            
            let html = '';
            
            // 按类别分组
            const grouped = {};
            ports.forEach(port => {
                if (!grouped[port.category]) {
                    grouped[port.category] = [];
                }
                grouped[port.category].push(port);
            });
            
            for (const [category, catPorts] of Object.entries(grouped)) {
                const catInfo = categories[category] || {total: catPorts.length, online: 0};
                const displayName = categoryNames[category] || category;
                
                html += `
                    <div class="category-section">
                        <div class="category-header">
                            <h2>${displayName}</h2>
                            <span class="category-badge">
                                ${catInfo.online}/${catInfo.total} 在线
                            </span>
                        </div>
                        <div class="ports-grid">
                            ${catPorts.map(port => `
                                <div class="port-card ${getStatusClass(port.status)}">
                                    <div class="port-header">
                                        <span class="port-name">${port.name}</span>
                                        <span class="port-status ${getStatusClass(port.status)}">
                                            ${port.status}
                                        </span>
                                    </div>
                                    <div class="port-address">
                                        ${port.address}${port.port ? ':' + port.port : ''}
                                        ${formatLatency(port.latencyMs)}
                                    </div>
                                    <div class="port-description">${port.description}</div>
                                    ${port.errorMessage ? `<div class="error-message">${port.errorMessage}</div>` : ''}
                                    <details class="port-details">
                                        <summary>详细信息</summary>
                                        <pre>${JSON.stringify(port.details, null, 2)}</pre>
                                    </details>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        async function refreshData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                renderStats(data.summary);
                renderCategories(data.ports, data.categories);
                
                document.getElementById('lastUpdated').textContent = 
                    '最后更新: ' + new Date(data.timestamp).toLocaleString('zh-CN');
            } catch (error) {
                console.error('刷新失败:', error);
                document.getElementById('lastUpdated').textContent = 
                    '更新失败: ' + error.message;
            }
        }
        
        function startAutoRefresh() {
            autoRefreshInterval = setInterval(refreshData, 5000);
        }
        
        // 初始加载
        refreshData();
        startAutoRefresh();
        
        // 页面可见性变化时控制刷新
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                clearInterval(autoRefreshInterval);
            } else {
                refreshData();
                startAutoRefresh();
            }
        });
    </script>
</body>
</html>
"""


class MonitorHTTPHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    monitor: UnifiedPortMonitor = None
    
    def log_message(self, format: str, *args) -> None:
        # 简化日志输出
        pass
    
    def _send_json(self, status_code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    
    def _send_html(self, status_code: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/" or path == "/index.html":
            self._send_html(200, HTML_TEMPLATE)
            return
        
        if path == "/api/status":
            summary = self.monitor.get_port_summary()
            self._send_json(200, summary)
            return
        
        if path == "/api/environment":
            env = self.monitor.get_environment_summary()
            self._send_json(200, env)
            return
        
        if path.startswith("/api/category/"):
            category = path.split("/")[-1]
            ports = self.monitor.get_ports_by_category(category)
            self._send_json(200, {
                "category": category,
                "ports": [p.to_dict() for p in ports]
            })
            return
        
        if path == "/api/refresh":
            ports = self.monitor.scan_all_ports()
            self._send_json(200, {
                "ok": True,
                "message": "Refresh triggered",
                "portCount": len(ports)
            })
            return
        
        self._send_json(404, {"ok": False, "error": "Not found"})
    
    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class MonitorHTTPServer(ThreadingHTTPServer):
    """监控HTTP服务器"""
    
    def __init__(self, server_address, handler_class, monitor: UnifiedPortMonitor):
        super().__init__(server_address, handler_class)
        self.monitor = monitor


def start_monitor_server(
    port: int = 9876,
    project_root: Path = None,
    auto_refresh: bool = True
) -> MonitorHTTPServer:
    """
    启动监控Web服务器
    
    Args:
        port: 服务器端口，默认9876
        project_root: 项目根目录
        auto_refresh: 是否自动刷新
    
    Returns:
        HTTP服务器实例
    """
    monitor = UnifiedPortMonitor(project_root=project_root)
    
    # 初始扫描
    monitor.scan_all_ports()
    
    # 启动自动监控
    if auto_refresh:
        monitor.start_monitoring(interval_seconds=10.0)
    
    # 设置处理器类
    MonitorHTTPHandler.monitor = monitor
    
    server = MonitorHTTPServer(("0.0.0.0", port), MonitorHTTPHandler, monitor)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     Mira Light 统一端口监控控制台已启动                      ║
╠══════════════════════════════════════════════════════════════╣
║  Web界面: http://localhost:{port:<5}                         ║
║  API状态: http://localhost:{port}/api/status                 ║
║  环境信息: http://localhost:{port}/api/environment           ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    return server


def main() -> int:
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mira Light Unified Port Monitor")
    parser.add_argument("--port", type=int, default=9876, help="Web服务器端口")
    parser.add_argument("--project-root", type=str, help="项目根目录路径")
    parser.add_argument("--no-auto-refresh", action="store_true", help="禁用自动刷新")
    args = parser.parse_args()
    
    project_root = Path(args.project_root) if args.project_root else None
    
    server = start_monitor_server(
        port=args.port,
        project_root=project_root,
        auto_refresh=not args.no_auto_refresh
    )
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[monitor] 关闭服务器...")
        server.monitor.stop_monitoring()
        server.server_close()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
