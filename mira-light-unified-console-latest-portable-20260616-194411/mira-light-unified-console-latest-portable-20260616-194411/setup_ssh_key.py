#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH 公钥自动复制脚本
用于将本地公钥复制到 Mira Light 开发板
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_encoding():
    """设置 UTF-8 编码"""
    if os.name == 'nt':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_public_key_path() -> Path:
    """获取公钥路径"""
    return Path.home() / '.ssh' / 'id_ed25519_mira.pub'

def check_key_exists() -> bool:
    """检查公钥是否存在"""
    key_path = get_public_key_path()
    return key_path.exists()

def read_public_key() -> str:
    """读取公钥内容"""
    key_path = get_public_key_path()
    if not key_path.exists():
        raise FileNotFoundError(f"公钥文件不存在: {key_path}")
    return key_path.read_text(encoding='utf-8').strip()

def setup_ssh_key_on_board(host: str, user: str, password: str = None) -> bool:
    """在开发板上设置 SSH 公钥"""

    print("=" * 60)
    print("SSH 公钥配置向导")
    print("=" * 60)
    print()

    # 检查公钥
    if not check_key_exists():
        print("[错误] 未找到公钥文件")
        print(f"       路径: {get_public_key_path()}")
        print()
        print("请先运行以下命令生成 SSH 密钥对：")
        print('  ssh-keygen -t ed25519 -C "mira-board"')
        print("  # 当提示保存路径时，输入：")
        print(f"  # {get_public_key_path()}")
        return False

    public_key = read_public_key()
    print(f"[信息] 找到公钥：")
    print(f"       {public_key[:60]}...")
    print()

    # 提示输入密码
    if not password:
        import getpass
        password = getpass.getpass(f"请输入 {user}@{host} 的密码（输入时不显示）：")

    if not password:
        print("[错误] 密码不能为空")
        return False

    print()
    print("[步骤 1/3] 测试连接...")

    # 测试连接
    try:
        result = subprocess.run(
            ["ssh", f"{user}@{host}", "echo 'SSH_OK'"],
            capture_output=True,
            text=True,
            timeout=10,
            input=password + "\n",
            encoding='utf-8'
        )
        if "SSH_OK" not in result.stdout:
            print(f"[警告] 连接测试未通过，但将继续尝试...")
            print(f"        stdout: {result.stdout[:100]}")
            print(f"        stderr: {result.stderr[:100]}")
    except Exception as e:
        print(f"[警告] 连接测试失败: {e}")
        print("         将继续尝试...")

    print()
    print("[步骤 2/3] 配置 ~/.ssh 目录...")

    # 在远程主机上执行命令
    remote_commands = f"""
mkdir -p ~/.ssh && \
chmod 700 ~/.ssh && \
echo '{public_key}' >> ~/.ssh/authorized_keys && \
chmod 600 ~/.ssh/authorized_keys && \
echo 'SSH 公钥配置成功' && \
echo '当前 authorized_keys 行数：' && \
wc -l ~/.ssh/authorized_keys
"""

    try:
        # 使用 ssh 执行远程命令
        # 注意：Windows 上 SSH 密码交互比较复杂
        # 这里尝试使用 sshpass 或者交互式方式

        print("[步骤 3/3] 上传公钥...")
        print()

        # 方法 1: 尝试使用 scp
        print("[尝试方法 1] 使用 scp...")

        # 先下载现有的 authorized_keys（如果存在）
        authorized_keys_path = Path.home() / '.ssh' / 'authorized_keys_remote'
        try:
            scp_result = subprocess.run(
                ["scp", f"{user}@{host}:~/.ssh/authorized_keys", str(authorized_keys_path)],
                capture_output=True,
                text=True,
                timeout=10,
                input=password + "\n",
                encoding='utf-8'
            )
            if scp_result.returncode == 0:
                print("  [OK] 下载现有 authorized_keys 成功")
            else:
                print("  [信息] 文件不存在或下载失败（将创建新文件）")
                authorized_keys_path.unlink(missing_ok=True)
        except Exception as e:
            print(f"  [信息] scp 不可用: {e}")
            authorized_keys_path.unlink(missing_ok=True)

        # 追加公钥
        if authorized_keys_path.exists():
            content = authorized_keys_path.read_text(encoding='utf-8')
            if public_key not in content:
                with open(authorized_keys_path, 'a', encoding='utf-8') as f:
                    f.write(public_key + '\n')
            else:
                print("  [信息] 公钥已存在，跳过")
        else:
            with open(authorized_keys_path, 'w', encoding='utf-8') as f:
                f.write(public_key + '\n')

        print(f"  [OK] 本地 authorized_keys 已更新: {authorized_keys_path}")

        # 上传回远程
        scp_upload = subprocess.run(
            ["scp", str(authorized_keys_path), f"{user}@{host}:~/.ssh/authorized_keys"],
            capture_output=True,
            text=True,
            timeout=10,
            input=password + "\n",
            encoding='utf-8'
        )

        if scp_upload.returncode == 0:
            print("  [OK] 上传成功")

            # 设置正确的权限
            ssh_chmod = subprocess.run(
                ["ssh", f"{user}@{host}", "chmod 600 ~/.ssh/authorized_keys"],
                capture_output=True,
                text=True,
                timeout=10,
                input=password + "\n",
                encoding='utf-8'
            )

            print("  [OK] 权限设置成功")
            print()
            print("=" * 60)
            print("[成功] SSH 公钥配置完成！")
            print("=" * 60)
            print()
            print("测试无密码登录：")
            print(f"  ssh {user}@{host}")
            print()

            # 清理临时文件
            authorized_keys_path.unlink(missing_ok=True)
            return True
        else:
            print(f"  [错误] 上传失败: {scp_upload.stderr}")

    except Exception as e:
        print(f"[错误] 配置失败: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("[失败] 自动配置失败")
    print("=" * 60)
    print()
    print("请手动配置：")
    print(f"  1. 运行: ssh {user}@{host}")
    print("  2. 输入密码登录")
    print(f"  3. 运行: mkdir -p ~/.ssh && chmod 700 ~/.ssh")
    print(f"  4. 将以下内容追加到 ~/.ssh/authorized_keys：")
    print()
    print(public_key)
    print()
    print("  5. 运行: chmod 600 ~/.ssh/authorized_keys")
    print()

    return False

def main():
    setup_encoding()

    host = os.environ.get("MIRA_BOARD_HOST", "192.168.0.183")
    user = os.environ.get("MIRA_BOARD_USER", "root")

    print()
    try:
        success = setup_ssh_key_on_board(host, user)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        print("[中断] 用户取消操作")
        sys.exit(1)

if __name__ == "__main__":
    main()
