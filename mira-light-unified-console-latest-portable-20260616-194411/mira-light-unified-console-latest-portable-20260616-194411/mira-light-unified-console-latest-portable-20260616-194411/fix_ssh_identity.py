#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 build_ssh_command 添加 IdentityFile 支持
"""

from pathlib import Path

def add_identity_file_support():
    """在 build_ssh_command 中添加 IdentityFile 选项"""

    file_path = Path(__file__).parent / "Chrome-Camera-Anime" / "digua_remote_render_pipeline.py"

    if not file_path.exists():
        print(f"[错误] 文件不存在: {file_path}")
        return False

    content = file_path.read_text(encoding='utf-8')

    # 找到 build_ssh_command 函数
    old_code = '''def build_ssh_command(
    *,
    host: str,
    user: str,
    port: int,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_script: str,
    batch_mode: bool,
) -> list[str]:
    command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"UserKnownHostsFile={known_hosts_path}",
        "-o",
        f"ConnectTimeout={connect_timeout}",
    ]
    if batch_mode:
        command.extend(["-o", "BatchMode=yes"])
    if bind_address:
        command.extend(["-b", bind_address])
    command.extend(["-p", str(port), f"{user}@{host}", "sh", "-lc", sh_quote(remote_script)])
    return command'''

    new_code = '''def build_ssh_command(
    *,
    host: str,
    user: str,
    port: int,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_script: str,
    batch_mode: bool,
    identity_file: str | None = None,
) -> list[str]:
    command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"UserKnownHostsFile={known_hosts_path}",
        "-o",
        f"ConnectTimeout={connect_timeout}",
    ]
    if batch_mode:
        command.extend(["-o", "BatchMode=yes"])
    if bind_address:
        command.extend(["-b", bind_address])
    # 添加 IdentityFile（如果提供）
    if identity_file:
        command.extend(["-i", identity_file])
    command.extend(["-p", str(port), f"{user}@{host}", "sh", "-lc", sh_quote(remote_script)])
    return command'''

    if old_code in content:
        content = content.replace(old_code, new_code)

        # 修改 run_ssh_capture 以传递 identity_file
        old_run = '''    command = build_ssh_command(
        host=host,
        user=user,
        port=port,
        bind_address=bind_address,
        known_hosts_path=known_hosts_path,
        connect_timeout=connect_timeout,
        remote_script=remote_script,
        batch_mode=not password,
    )'''

        new_run = '''    # 尝试使用标准 SSH 密钥位置
    identity_file = None
    if not password:
        # 检查常见的私钥文件
        from pathlib import Path as _Path
        home = _Path.home()
        for key_path in [
            home / ".ssh" / "id_ed25519_mira",
            home / ".ssh" / "id_ed25519",
            home / ".ssh" / "id_rsa",
        ]:
            if key_path.exists():
                identity_file = str(key_path)
                break

    command = build_ssh_command(
        host=host,
        user=user,
        port=port,
        bind_address=bind_address,
        known_hosts_path=known_hosts_path,
        connect_timeout=connect_timeout,
        remote_script=remote_script,
        batch_mode=not password,
        identity_file=identity_file,
    )'''

        content = content.replace(old_run, new_run)

        file_path.write_text(content, encoding='utf-8')
        print("[OK] 已添加 IdentityFile 支持")
        print("[OK] run_ssh_capture 现在会自动查找私钥")
        return True
    else:
        print("[错误] 未找到要修改的代码")
        print("可能代码已经修改过了")
        return False

if __name__ == "__main__":
    print("修复 SSH 密钥查找问题")
    print("=" * 60)

    success = add_identity_file_support()

    if success:
        print()
        print("修复完成！")
        print("请重启控制台并测试摄像头抓取。")
    else:
        print()
        print("修复失败")
