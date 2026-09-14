#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接修改 digua_remote_render_pipeline.py"""

import re
from pathlib import Path

# 文件路径
file_path = Path("Chrome-Camera-Anime/digua_remote_render_pipeline.py")

if not file_path.exists():
    print(f"[错误] 文件不存在: {file_path}")
    exit(1)

print(f"[信息] 读取文件: {file_path}")
content = file_path.read_text(encoding='utf-8')

# 修改 1: build_ssh_command 签名添加 identity_file
print("\n[步骤 1] 修改函数签名...")

old_sig_pattern = r'def build_ssh_command\(\s*\*,\s*host: str,\s*user: str,\s*port: int,\s*bind_address: str,\s*known_hosts_path: Path,\s*connect_timeout: int,\s*remote_script: str,\s*batch_mode: bool,\s*\) -> list[str\]:'

new_sig = '''def build_ssh_command(
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

match = re.search(old_sig_pattern, content, re.MULTILINE | re.DOTALL)
if match:
    content = content[:match.start()] + new_sig + content[match.end():]
    print("  [OK] 函数签名已更新")
else:
    print("  [警告] 未找到函数签名")

# 修改 2: 在命令中添加 -i 选项
print("\n[步骤 2] 添加 IdentityFile 支持...")

old_code = '''    if bind_address:
        command.extend(["-b", bind_address])
    command.extend'''

new_code = '''    if bind_address:
        command.extend(["-b", bind_address])
    # 添加 IdentityFile（如果提供）
    if identity_file:
        command.extend(["-i", identity_file])
    command.extend'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("  [OK] IdentityFile 支持已添加")
else:
    print("  [警告] 未找到命令构建代码")

# 修改 3: 在 run_ssh_capture 中添加私钥查找逻辑
print("\n[步骤 3] 修改 run_ssh_capture...")

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

if old_run in content:
    content = content.replace(old_run, new_run)
    print("  [OK] run_ssh_capture 已更新")
else:
    print("  [警告] 未找到 run_ssh_capture 调用")

# 保存
print("\n[步骤 4] 保存文件...")
file_path.write_text(content, encoding='utf-8')
print("  [OK] 文件已保存")

print("\n" + "=" * 60)
print("修复完成！")
print("=" * 60)
print("\n请重启控制台并测试摄像头抓取。")
