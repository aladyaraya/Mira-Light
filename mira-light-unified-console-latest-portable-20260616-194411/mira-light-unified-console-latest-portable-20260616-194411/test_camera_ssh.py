#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试摄像头 SSH 抓取
"""

import os
import sys
from pathlib import Path

# 添加 Chrome-Camera-Anime 到路径
REPO_ROOT = Path(__file__).parent
CHROME_CAMERA_DIR = REPO_ROOT / "Chrome-Camera-Anime"
sys.path.insert(0, str(CHROME_CAMERA_DIR))

import digua_remote_render_pipeline

def test_camera_capture():
    """测试摄像头抓取"""

    print("=" * 60)
    print("摄像头 SSH 抓取测试")
    print("=" * 60)
    print()

    # 配置
    host = os.environ.get("MIRA_BOARD_HOST", "192.168.0.183")
    port = int(os.environ.get("MIRA_BOARD_PORT", "22"))
    user = os.environ.get("MIRA_BOARD_USER", "root")
    password = os.environ.get("MIRA_BOARD_PASSWORD", "")

    print(f"主机: {user}@{host}:{port}")
    print(f"密码: {'[已配置]' if password else '[未配置 - 使用 SSH 密钥]'}")
    print()

    # 测试 SSH 命令构建
    print("[步骤 1/3] 构建 SSH 命令...")

    try:
        command = digua_remote_render_pipeline.build_ssh_command(
            host=host,
            user=user,
            port=port,
            bind_address="",
            known_hosts_path=Path.home() / ".ssh" / "known_hosts",
            connect_timeout=10,
            remote_script="echo 'SSH_OK'",
            batch_mode=not password,
        )
        print(f"  [OK] SSH 命令: {' '.join(command[:8])}...")
    except Exception as e:
        print(f"  [错误] 构建命令失败: {e}")
        return False

    # 测试执行
    print()
    print("[步骤 2/3] 执行 SSH 命令...")

    try:
        import subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=15,
            text=True
        )

        print(f"  返回码: {result.returncode}")
        print(f"  输出: {result.stdout[:200]}")
        if result.stderr:
            print(f"  错误: {result.stderr[:200]}")

        if result.returncode == 0 and "SSH_OK" in result.stdout:
            print()
            print("  [OK] SSH 连接成功！")
        else:
            print()
            print("  [错误] SSH 连接失败")

    except subprocess.TimeoutExpired:
        print("  [错误] SSH 超时")
    except Exception as e:
        print(f"  [错误] 执行失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试实际摄像头抓取（可选）
    print()
    print("[步骤 3/3] 测试摄像头抓取（可选）")

    response = input("是否测试实际摄像头抓取？(y/N): ")
    if response.lower() != 'y':
        print("跳过摄像头抓取测试")
        return True

    try:
        capture_dir = REPO_ROOT / "test_captures"
        capture_dir.mkdir(exist_ok=True)

        print("  正在抓取...")
        image_path = digua_remote_render_pipeline.capture_remote_image(
            host=host,
            user=user,
            port=port,
            password=password,
            bind_address="",
            known_hosts_path=Path.home() / ".ssh" / "known_hosts",
            connect_timeout=10,
            remote_device="/dev/video0",
            input_format="mjpeg",
            video_size="1280x720",
            remote_temp_path="/tmp/camera-test.jpg",
            capture_dir=capture_dir,
            timestamp="test",
            timeout=30,
            ssh_retries=1,
            ssh_retry_delay_seconds=1.0,
        )

        print(f"  [OK] 摄像头抓取成功: {image_path}")
        print(f"  文件大小: {image_path.stat().st_size} 字节")

    except Exception as e:
        print(f"  [错误] 摄像头抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_camera_capture()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消")
        sys.exit(1)
