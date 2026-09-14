#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接修复：修改 build_ssh_command 中的引号转义
"""

import re
from pathlib import Path

def fix_sh_quote_for_windows():
    """修复 Windows 下的引号问题"""

    file_path = Path(__file__).parent / "Chrome-Camera-Anime" / "digua_remote_render_pipeline.py"

    if not file_path.exists():
        print(f"[错误] 文件不存在: {file_path}")
        return False

    content = file_path.read_text(encoding='utf-8')

    # 查找 sh_quote 函数
    old_sh_quote = '''def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"'''

    new_sh_quote = '''def sh_quote(value: str) -> str:
    # Windows PowerShell 兼容：使用双引号
    if os.name == 'nt':
        return '"' + value.replace('"', '\\"') + '"'
    return "'" + value.replace("'", "'\"'\"'") + "'"'''

    if old_sh_quote in content:
        content = content.replace(old_sh_quote, new_sh_quote)
        file_path.write_text(content, encoding='utf-8')
        print("[OK] 已修复 sh_quote 函数")
        return True
    else:
        print("[警告] 未找到 sh_quote 函数")
        return False

if __name__ == "__main__":
    print("修复 Windows PowerShell 引号问题")
    print("=" * 60)

    success = fix_sh_quote_for_windows()

    if success:
        print()
        print("修复完成！请重启控制台并测试摄像头抓取。")
    else:
        print()
        print("修复失败")
