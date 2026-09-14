#!/usr/bin/env python3
"""Mira Light Shenzhen Console Windows 兼容性诊断脚本"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    print("=" * 60)
    print("1. Python 环境检查")
    print("=" * 60)
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ⚠️  建议使用 Python 3.8+")
    else:
        print("  ✓ 版本符合要求")
    print()

def check_ssh_tools():
    """检查 SSH 工具"""
    print("=" * 60)
    print("2. SSH 工具检查")
    print("=" * 60)

    # 检查 OpenSSH
    ssh_bin = shutil.which("ssh")
    print(f"{'✓' if ssh_bin else '✗'} OpenSSH (ssh): {ssh_bin or '未找到'}")

    # 检查 plink (Windows)
    plink_bin = shutil.which("plink") or shutil.which("plink.exe")
    print(f"{'✓' if plink_bin else '✗'} PuTTY plink: {plink_bin or '未找到'}")

    # 检查 Git Bash
    git_bash = shutil.which("bash")
    print(f"{'✓' if git_bash else '✗'} Git Bash (bash): {git_bash or '未找到'}")

    if not plink_bin and not ssh_bin:
        print("\n❌ 错误：未找到 SSH 工具！")
        print("   Windows 上需要安装：")
        print("   1. PuTTY: https://www.putty.org/ (推荐)")
        print("   2. 或 Git for Windows: https://gitforwindows.org/")
        print("   3. 或 OpenSSH: https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse")
        return False

    if os.name == "nt" and not plink_bin:
        print("\n⚠️  Windows 上推荐使用 plink (PuTTY)")
        print("   因为 pty 模块在 Windows 上不可用")

    if os.name == "nt" and plink_bin:
        print("\n✓ Windows + plink 配置正确")

    print()
    return True

def check_scripts():
    """检查必要的脚本文件"""
    print("=" * 60)
    print("3. 脚本文件检查")
    print("=" * 60)

    repo_root = Path(__file__).parent
    scripts = [
        "scripts/run_mira_light_vision_stack.sh",
        "scripts/mira_stepfun_realtime_voice_actions.py",
        "mira-light-unified-director-console/shenzhen_console.py",
    ]

    all_exist = True
    for script in scripts:
        path = repo_root / script
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {script}")
        if not exists:
            all_exist = False

    print()

    # 特别检查 bash 脚本的可执行性
    bash_script = repo_root / "scripts/run_mira_light_vision_stack.sh"
    if bash_script.exists():
        print(f"  脚本大小: {bash_script.stat().st_size} 字节")
        if os.name == "nt":
            print("  ⚠️  Windows 上 bash 脚本需要 Git Bash 或 WSL 环境")
        else:
            print("  ✓ Linux/Mac 环境可以直接执行")

    print()
    return all_exist

def check_board_connection():
    """检查开发板连接"""
    print("=" * 60)
    print("4. 开发板连接检查")
    print("=" * 60)

    host = os.environ.get("MIRA_BOARD_HOST", "192.168.0.183")
    port = int(os.environ.get("MIRA_BOARD_PORT", "22"))
    user = os.environ.get("MIRA_BOARD_USER", "root")

    print(f"  目标: {user}@{host}:{port}")

    # 检查网络连通性
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"  ✓ 网络可达 ({host}:{port})")
        else:
            print(f"  ✗ 网络不可达 (错误码: {result})")
            print(f"     请检查：")
            print(f"     1. 开发板电源是否开启")
            print(f"     2. 网络连接是否正常")
            print(f"     3. IP 地址是否正确")
    except Exception as e:
        print(f"  ✗ 网络检查失败: {e}")

    print()

def check_printer_bridge():
    """检查打印机桥接"""
    print("=" * 60)
    print("5. 打印机桥接检查")
    print("=" * 60)

    bridge_url = os.environ.get("OPENCLAW_PRINTER_BRIDGE_URL", "http://127.0.0.1:9771")
    bridge_token = os.environ.get("OPENCLAW_PRINTER_BRIDGE_TOKEN", "")

    print(f"  桥接地址: {bridge_url}")
    print(f"  令牌配置: {'✓ 已配置' if bridge_token else '✗ 未配置'}")

    if not bridge_token:
        print("\n  ⚠️  打印机桥接令牌未配置")
        print("  如需使用打印机功能，请设置环境变量：")
        print("  $env:OPENCLAW_PRINTER_BRIDGE_TOKEN = 'your-token-here'")

    print()

def check_windows_specific():
    """Windows 特定检查"""
    if os.name != "nt":
        return

    print("=" * 60)
    print("6. Windows 特定检查")
    print("=" * 60)

    # 检查 WSL
    try:
        result = subprocess.run(["wsl", "--status"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            print("  ✓ WSL 可用")
            print("    可以用于执行 bash 脚本")
        else:
            print("  ✗ WSL 不可用或未配置")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  ✗ WSL 未安装")
        print("    Windows 上需要 WSL 或 Git Bash 来执行 bash 脚本")

    # 检查 Git Bash
    git_bash_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        Path.home() / "AppData/Local/Programs/Git/bin/bash.exe",
    ]
    git_bash_found = any(p.exists() for p in git_bash_paths)
    print(f"  {'✓' if git_bash_found else '✗'} Git Bash: {'已安装' if git_bash_found else '未找到'}")
    print("    安装地址: https://gitforwindows.org/")

    print()

def print_summary():
    """打印总结和建议"""
    print("=" * 60)
    print("📋 修复建议")
    print("=" * 60)
    print()
    print("立即执行：")
    print()
    print("1️⃣  安装 PuTTY（解决 SSH 问题）")
    print("   → 下载：https://www.putty.org/")
    print("   → 或使用 Chocolatey: choco install putty")
    print()
    print("2️⃣  配置 SSH 密钥认证（推荐）")
    print("   → ssh-keygen -t ed25519 -C 'mira-board'")
    print("   → 复制公钥到开发板（见下方命令）")
    print()
    print("3️⃣  Windows 上使用追书功能")
    print("   → 需要安装 WSL 或 Git Bash")
    print("   → 或在 WSL/Linux 环境中运行控制台")
    print()
    print("4️⃣  （可选）配置打印机桥接令牌")
    print("   → 设置环境变量 OPENCLAW_PRINTER_BRIDGE_TOKEN")
    print()
    print("=" * 60)

def main():
    os.chdir(Path(__file__).parent)

    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Mira Light Shenzhen Console 诊断工具" + " " * 9 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    check_python_version()
    has_ssh = check_ssh_tools()
    check_scripts()
    check_board_connection()
    check_printer_bridge()
    check_windows_specific()
    print_summary()

    print("\n按 Enter 键退出...")
    input()

if __name__ == "__main__":
    main()
