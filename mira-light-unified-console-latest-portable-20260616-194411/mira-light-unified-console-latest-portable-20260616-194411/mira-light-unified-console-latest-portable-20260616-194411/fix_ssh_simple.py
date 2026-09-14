#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简化版修复脚本：直接字符串替换"""

from pathlib import Path

file_path = Path("Chrome-Camera-Anime/digua_remote_render_pipeline.py")

if not file_path.exists():
    print(f"[错误] 文件不存在: {file_path}")
    exit(1)

print(f"[信息] 读取文件...")
content = file_path.read_text(encoding='utf-8')

# 修改 1: 添加 identity_file 到函数参数
print("\n[步骤 1] 添加 identity_file 参数...")

old1 = '''def build_ssh_command(
    *,
    host: str,
    user: str,
    port: int,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_script: str,
    batch_mode: bool,
) -> list[str]:'''

new1 = '''def build_ssh_command(
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
) -> list[str]:'''

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("  [OK] 函数签名已更新")
else:
    print("  [X] 未找到函数签名")

# 修改 2: 添加 -i 选项
print("\n[步骤 2] 添加 -i IdentityFile 选项...")

old2 = '''    if bind_address:
        command.extend(["-b", bind_address])
    command.extend(["-p", str(port), f"{user}@{host}", "sh", "-lc", sh_quote(remote_script)])
    return command'''

new2 = '''    if bind_address:
        command.extend(["-b", bind_address])
    # 添加 IdentityFile（如果提供）
    if identity_file:
        command.extend(["-i", identity_file])
    command.extend(["-p", str(port), f"{user}@{host}", "sh", "-lc", sh_quote(remote_script)])
    return command'''

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("  [OK] 已添加 -i 选项")
else:
    print("  [X] 未找到命令构建代码")

# 修改 3: 在 run_ssh_capture 中查找私钥
print("\n[步骤 3] 修改 run_ssh_capture 自动查找私钥...")

old3 = '''    command = build_ssh_command(
        host=host,
        user=user,
        port=port,
        bind_address=bind_address,
        known_hosts_path=known_hosts_path,
        connect_timeout=connect_timeout,
        remote_script=remote_script,
        batch_mode=not password,
    )'''

new3 = '''    # 尝试使用标准 SSH 密钥位置
    identity_file = None
    if not password:
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

if old3 in content:
    content = content.replace(old3, new3, 1)
    print("  [OK] run_ssh_capture 已更新")
else:
    print("  [X] 未找到 run_ssh_capture 调用")

# 保存
print("\n[步骤 4] 保存文件...")
file_path.write_text(content, encoding='utf-8')
print("  [OK] 文件已保存")

print("\n" + "=" * 60)
print("修复完成！")
print("=" * 60)
print("\n请重启控制台并测试摄像头抓取功能。")
print("SSH 密钥将自动从 ~/.ssh/ 目录查找。")
