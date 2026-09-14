#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Paramiko 自动配置 SSH 公钥
需要: pip install paramiko
"""

import os
import sys
import socket
from pathlib import Path

def setup_encoding():
    """设置 UTF-8 编码"""
    if os.name == 'nt':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def check_paramiko():
    """检查 paramiko 是否已安装"""
    try:
        import paramiko
        return True
    except ImportError:
        return False

def setup_ssh_key_with_paramiko(host: str, user: str, password: str) -> bool:
    """使用 paramiko 配置 SSH 公钥"""
    import paramiko

    print(f"[信息] 正在连接到 {user}@{host}...")

    try:
        # 创建 SSH 客户端
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 连接
        client.connect(host, port=22, username=user, password=password, timeout=10)

        print("[OK] SSH 连接成功")

        # 读取公钥
        key_path = Path.home() / '.ssh' / 'id_ed25519_mira.pub'
        if not key_path.exists():
            print(f"[错误] 公钥文件不存在: {key_path}")
            return False

        public_key = key_path.read_text(encoding='utf-8').strip()
        print(f"[信息] 公钥已加载")

        # 执行命令
        commands = [
            'mkdir -p ~/.ssh',
            'chmod 700 ~/.ssh',
            f"echo '{public_key}' >> ~/.ssh/authorized_keys",
            'chmod 600 ~/.ssh/authorized_keys',
            'wc -l ~/.ssh/authorized_keys'
        ]

        for cmd in commands:
            stdin, stdout, stderr = client.exec_command(cmd)
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                error = stderr.read().decode('utf-8')
                print(f"[错误] 命令失败: {cmd}")
                print(f"       {error}")
                return False

            output = stdout.read().decode('utf-8').strip()
            if output:
                print(f"  → {output}")

        print("\n[成功] SSH 公钥配置完成！")

        # 测试无密码登录
        print("[测试] 测试无密码登录...")
        stdin, stdout, stderr = client.exec_command('echo "SSH 密钥认证成功"')
        output = stdout.read().decode('utf-8').strip()
        print(f"  → {output}")

        client.close()
        return True

    except paramiko.AuthenticationException:
        print("[错误] 认证失败：密码错误或 SSH 密钥配置有问题")
        return False
    except paramiko.SSHException as e:
        print(f"[错误] SSH 错误: {e}")
        return False
    except socket.error as e:
        print(f"[错误] 网络错误: {e}")
        return False
    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    setup_encoding()

    print("\n" + "=" * 60)
    print("  Mira Light SSH 公钥自动配置工具")
    print("=" * 60 + "\n")

    # 检查 paramiko
    if not check_paramiko():
        print("[提示] 需要安装 paramiko 库")
        print("       运行: pip install paramiko\n")

        response = input("是否现在安装 paramiko？(Y/N): ")
        if response.lower() == 'y':
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"])
            print()
        else:
            print("[退出] 用户取消")
            sys.exit(1)

    # 配置
    host = os.environ.get("MIRA_BOARD_HOST", "192.168.0.183")
    user = os.environ.get("MIRA_BOARD_USER", "root")

    # 输入密码
    import getpass
    password = getpass.getpass(f"请输入 {user}@{host} 的密码（输入时不显示）: ")

    if not password:
        print("[错误] 密码不能为空")
        sys.exit(1)

    print()

    # 配置公钥
    success = setup_ssh_key_with_paramiko(host, user, password)

    if success:
        print("\n" + "=" * 60)
        print("配置完成！")
        print("=" * 60)
        print(f"\n测试: ssh {user}@{host}")
        print("应该无需密码即可登录\n")
        sys.exit(0)
    else:
        print("\n[失败] 配置失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
        sys.exit(1)
