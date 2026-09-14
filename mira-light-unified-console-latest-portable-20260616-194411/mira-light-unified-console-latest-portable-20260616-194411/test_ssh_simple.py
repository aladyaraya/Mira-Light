#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试：验证 SSH 命令构建
"""

import os
import sys
import subprocess
from pathlib import Path

# 设置路径
REPO_ROOT = Path(__file__).parent
CHROME_CAMERA_DIR = REPO_ROOT / "Chrome-Camera-Anime"
sys.path.insert(0, str(CHROME_CAMERA_DIR))

import digua_remote_render_pipeline

def test_ssh_command_building():
    """测试 SSH 命令构建"""

    host = "192.168.0.183"
    user = "root"
    port = 22
    password = ""  # 空密码 - 应该使用 SSH 密钥

    print("=" * 60)
    print("SSH 命令构建测试")
    print("=" * 60)
    print(f"主机: {user}@{host}:{port}")
    print(f"密码: {'[空 - 应使用 SSH 密钥]' if not password else '[已配置]'}")
    print()

    # 测试 1: build_ssh_command
    print("[测试 1] 构建 SSH 命令")
    print("-" * 60)

    try:
        command = digua_remote_render_pipeline.build_ssh_command(
            host=host,
            user=user,
            port=port,
            bind_address="",
            known_hosts_path=Path.home() / ".ssh" / "known_hosts",
            connect_timeout=10,
            remote_script="echo 'SSH_TEST_OK'",
            batch_mode=not password,  # password 为空 → batch_mode=True
        )

        print(f"命令: {' '.join(command)}")
        print()

        # 检查是否包含 BatchMode
        if "-o" in command and "BatchMode=yes" in command:
            print("[OK] 包含 BatchMode=yes - 将不会提示密码")
        else:
            print("[警告] 缺少 BatchMode=yes")

        # 检查是否包含 ssh（而不是 plink）
        if command[0] == "ssh":
            print("[OK] 使用 OpenSSH (ssh)")
        else:
            print(f"[错误] 未预期的命令: {command[0]}")

    except Exception as e:
        print(f"[错误] 构建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # 测试 2: 执行 SSH 命令
    print("[测试 2] 执行 SSH 命令")
    print("-" * 60)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=15,
            text=True,
            cwd=str(REPO_ROOT)
        )

        print(f"返回码: {result.returncode}")
        print(f"stdout: {result.stdout[:300]}")
        if result.stderr:
            print(f"stderr: {result.stderr[:300]}")

        if result.returncode == 0 and "SSH_TEST_OK" in result.stdout:
            print()
            print("[成功] SSH 密钥认证工作正常！")
            return True
        else:
            print()
            print("[失败] SSH 连接失败")
            return False

    except subprocess.TimeoutExpired:
        print("[错误] SSH 超时")
        return False
    except Exception as e:
        print(f"[错误] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_plink_command_building():
    """测试 plink 命令构建（应该失败）"""

    host = "192.168.0.183"
    user = "root"
    password = "dummy_password"  # 假设有密码

    print()
    print("=" * 60)
    print("Plink 命令构建测试（应该失败）")
    print("=" * 60)
    print(f"主机: {user}@{host}")
    print(f"密码: [假设密码='{password}']")
    print()

    try:
        command = digua_remote_render_pipeline._build_plink_command(
            host=host,
            port=22,
            user=user,
            password=password,
            remote_script="echo 'test'",
        )
        print(f"[错误] 不应该成功构建 plink 命令！")
        return False

    except RuntimeError as e:
        if "plink is required" in str(e):
            print(f"[预期内错误] {e}")
            print()
            print("[OK] 代码正确检测到缺少 plink")
            return True
        else:
            print(f"[错误] 意外的 RuntimeError: {e}")
            return False
    except Exception as e:
        print(f"[错误] 意外异常: {e}")
        return False

def main():
    print()

    success1 = test_ssh_command_building()
    success2 = test_plink_command_building()

    print()
    print("=" * 60)
    print("总结")
    print("=" * 60)
    print(f"SSH 命令构建: {'[OK]' if success1 else '[失败]'}")
    print(f"Plink 检测: {'[OK]' if success2 else '[失败]'}")

    if success1:
        print()
        print("结论: SSH 密钥认证应该能正常工作")
        print("如果控制台仍然报错，可能是：")
        print("1. 控制台使用了不同的密码配置")
        print("2. 控制台缓存了旧的状态")
        print("3. 控制台在另一个进程中运行")

    sys.exit(0 if (success1 and success2) else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[中断]")
        sys.exit(1)
