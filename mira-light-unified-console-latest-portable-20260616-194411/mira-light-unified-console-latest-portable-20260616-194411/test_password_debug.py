#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试测试：检查 password 参数传递
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
CHROME_CAMERA_DIR = REPO_ROOT / "Chrome-Camera-Anime"
sys.path.insert(0, str(CHROME_CAMERA_DIR))

import digua_remote_render_pipeline

def test_password_parameter():
    """测试 password 参数传递"""

    print("=" * 60)
    print("Password 参数调试测试")
    print("=" * 60)
    print()

    # 模拟控制台配置
    host = "192.168.0.183"
    user = "root"
    port = 22
    password = ""  # 空密码（应该使用 SSH 密钥）

    print(f"配置:")
    print(f"  host: {host}")
    print(f"  user: {user}")
    print(f"  port: {port}")
    print(f"  password: {repr(password)}")
    print(f"  bool(password): {bool(password)}")
    print(f"  not password: {not password}")
    print()

    # 测试 build_ssh_command
    print("[测试 1] build_ssh_command")
    print("-" * 60)

    try:
        command = digua_remote_render_pipeline.build_ssh_command(
            host=host,
            user=user,
            port=port,
            bind_address="",
            known_hosts_path=Path.home() / ".ssh" / "known_hosts",
            connect_timeout=10,
            remote_script="echo 'TEST_SSH_OK'",
            batch_mode=not password,
        )

        print(f"命令: {' '.join(command)}")
        print()

        # 检查 BatchMode
        if "-o" in command:
            batch_idx = command.index("-o") if "BatchMode=yes" in command else -1
            if "BatchMode=yes" in command:
                print("[OK] 包含 BatchMode=yes")
            else:
                print("[警告] 缺少 BatchMode=yes")
        else:
            print("[错误] 命令格式异常")

    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # 测试 run_ssh_capture
    print("[测试 2] run_ssh_capture（应该看到调试信息）")
    print("-" * 60)

    try:
        # 这会调用 build_ssh_command 并执行
        result_bytes = digua_remote_render_pipeline.run_ssh_capture(
            host=host,
            user=user,
            port=port,
            password=password,
            bind_address="",
            known_hosts_path=Path.home() / ".ssh" / "known_hosts",
            connect_timeout=10,
            remote_script="echo 'CAPTURE_TEST_OK'",
            timeout=15,
        )

        result_text = result_bytes.decode("utf-8", errors="replace")
        print(f"返回码: 0")
        print(f"输出: {result_text[:200]}")

        if "CAPTURE_TEST_OK" in result_text:
            print()
            print("[成功] SSH 密钥认证工作正常！")
            return True
        else:
            print()
            print("[警告] SSH 成功但输出异常")
            return True

    except Exception as e:
        print(f"[异常] {e}")
        print()
        print("这个异常包含调试信息（上面的 [DEBUG ...] 行）")
        print("请将完整输出发给我")
        import traceback
        traceback.print_exc()
        return False

def main():
    print()
    success = test_password_parameter()
    print()
    print("=" * 60)
    if success:
        print("[结论] SSH 密钥认证应该能工作")
    else:
        print("[结论] 需要进一步调试")
    print("=" * 60)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[中断]")
        sys.exit(1)
