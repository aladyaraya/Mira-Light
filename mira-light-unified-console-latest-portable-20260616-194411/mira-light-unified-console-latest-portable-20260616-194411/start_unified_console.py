#!/usr/bin/env python#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-D#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) ==#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) ->#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait:#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="",#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file =#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port))#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("M#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = "root#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SH#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_F#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:952#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"]#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UN#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{cele#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{cele#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{celebration_port}/"

    ##!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{celebration_port}/"

    # 打印启动信息
    print("== Mira Light Unified Director Console (Windows) ==")
#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{celebration_port}/"

    # 打印启动信息
    print("== Mira Light Unified Director Console (Windows) ==")
    print(f"Repo:      {root_dir}")
    print(f"Console:   {console_url}")
    if not args.skip_celebration:
        print(f"Celebrate: {celebration_url}")
    print(f"Bind:      unified {#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{celebration_port}/"

    # 打印启动信息
    print("== Mira Light Unified Director Console (Windows) ==")
    print(f"Repo:      {root_dir}")
    print(f"Console:   {console_url}")
    if not args.skip_celebration:
        print(f"Celebrate: {celebration_url}")
    print(f"Bind:      unified {console_host}:{console_port}")
    print(f"Local:     {console_local_url}")
    print(f"Board:     {#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{celebration_port}/"

    # 打印启动信息
    print("== Mira Light Unified Director Console (Windows) ==")
    print(f"Repo:      {root_dir}")
    print(f"Console:   {console_url}")
    if not args.skip_celebration:
        print(f"Celebrate: {celebration_url}")
    print(f"Bind:      unified {console_host}:{console_port}")
    print(f"Local:     {console_local_url}")
    print(f"Board:     {board_user}@{board_host}:{board_port}")
    print(f"Python:    {python_bin}")
    print(f"Scripts#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{celebration_port}/"

    # 打印启动信息
    print("== Mira Light Unified Director Console (Windows) ==")
    print(f"Repo:      {root_dir}")
    print(f"Console:   {console_url}")
    if not args.skip_celebration:
        print(f"Celebrate: {celebration_url}")
    print(f"Bind:      unified {console_host}:{console_port}")
    print(f"Local:     {console_local_url}")
    print(f"Board:     {board_user}@{board_host}:{board_port}")
    print(f"Python:    {python_bin}")
    print(f"Scripts:   {os.environ.get('MIRA_SHENZHEN_SCRIPTS_DIR', '')}")
    print(f"Remote:    {os#!/usr/bin/env python3
"""
Mira Light Unified Director Console - Windows 启动脚本
对应 macOS 的 Start-Mira-Light-Unified-Director-Console.command
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> dict:
    """加载 .env 文件，设置进程环境变量。"""
    loaded = {}
    if not os.path.exists(path):
        return loaded
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().strip('"').strip("'")
                if "${" not in val:
                    os.environ[key] = val
                    loaded[key] = val
    return loaded


def probe_url(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, label: str, pid: int = 0, max_wait: int = 20) -> bool:
    for _ in range(max_wait * 4):
        if probe_url(url):
            print(f"{label} OK")
            return True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                print(f"ERROR: {label} exited before ready.")
                return False
        time.sleep(0.25)
    print(f"ERROR: {label} did not become ready at {url}")
    return False


def stop_stale_process(port: int, label: str):
    """停止占用指定端口的旧 Python 进程。"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"Where-Object {{ $_.State -eq 'Listen' }} | "
             f"ForEach-Object {{ $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
             f"if ($p.Path -like '*shenzhen_console.py*') {{ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; "
             f"Write-Host 'Stopped stale {label} on port {port} (pid ' $p.Id ')' }} }}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            print(result.stdout.strip())
            time.sleep(1)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Mira Light Unified Director Console Launcher")
    parser.add_argument("--env-file", default="", help="自定义 .env 文件路径")
    parser.add_argument("--host", default="", help="控制台绑定地址")
    parser.add_argument("--port", type=int, default=8790, help="控制台端口")
    parser.add_argument("--board-host", default="", help="开发板 SSH 地址")
    parser.add_argument("--board-port", type=int, default=22, help="开发板 SSH 端口")
    parser.add_argument("--board-user", default="root", help="开发板 SSH 用户")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--skip-celebration", action="store_true", help="跳过庆祝页面服务")
    args = parser.parse_args()

    root_dir = Path(__file__).parent.resolve()
    console_dir = root_dir / "mira-light-unified-director-console"
    shenzhen_console_dir = root_dir / "mira-light-shenzhen-console"
    digua_pipeline_dir = root_dir / "Chrome-Camera-Anime"
    scripts_dir = root_dir / "Motions_Shenzhen" / "demo_fixed_protocol_v2" / "scripts"

    # Python 解释器
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if os.environ.get("MIRA_UNIFIED_PYTHON"):
        python_bin = os.environ["MIRA_UNIFIED_PYTHON"]
    elif venv_python.exists():
        python_bin = str(venv_python)
    else:
        python_bin = "python"

    # 加载 .env 文件
    env_file = args.env_file if args.env_file else str(root_dir / "portable" / "unified-console.env")
    load_env_file(env_file)

    # 配置变量
    console_host = args.host if args.host else os.environ.get("MIRA_UNIFIED_CONSOLE_HOST", "0.0.0.0")
    console_port = int(os.environ.get("MIRA_UNIFIED_CONSOLE_PORT", str(args.port)))

    board_host = args.board_host if args.board_host else os.environ.get("MIRA_SHENZHEN_BOARD_HOST", "192.168.0.183")
    board_port = int(os.environ.get("MIRA_SHENZHEN_BOARD_PORT", str(args.board_port)))
    board_user = os.environ.get("MIRA_SHENZHEN_BOARD_USER", args.board_user)

    if not os.environ.get("MIRA_SHENZHEN_BOARD_PASSWORD"):
        os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"] = ""
    if not os.environ.get("MIRA_CAMERA_BOARD_PASSWORD"):
        os.environ["MIRA_CAMERA_BOARD_PASSWORD"] = os.environ["MIRA_SHENZHEN_BOARD_PASSWORD"]

    # 远程板桌面目录（关键：解决 four_servo_control.py 路径问题）
    if not os.environ.get("MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"):
        os.environ["MIRA_SHENZHEN_REMOTE_DESKTOP_DIR"] = "/home/sunrise/Desktop"

    if not os.environ.get("MIRA_SHENZHEN_SCRIPTS_DIR"):
        if scripts_dir.exists():
            os.environ["MIRA_SHENZHEN_SCRIPTS_DIR"] = str(scripts_dir)

    if not os.environ.get("MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"):
        os.environ["MIRA_SHENZHEN_DIGUA_OUTPUT_DIR"] = str(console_dir / "runtime" / "digua-console-output")
    if not os.environ.get("MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"):
        os.environ["MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS"] = "10"
    if not os.environ.get("MIRA_UNIFIED_CAMERA_START_WATCH"):
        os.environ["MIRA_UNIFIED_CAMERA_START_WATCH"] = "1"
    if not os.environ.get("MIRA_BOOK_FOLLOW_RECEIVER_PORT"):
        os.environ["MIRA_BOOK_FOLLOW_RECEIVER_PORT"] = "18000"

    os.environ["MIRA_SHENZHEN_BOARD_HOST"] = board_host
    if not os.environ.get("MIRA_CAMERA_BOARD_HOST"):
        os.environ["MIRA_CAMERA_BOARD_HOST"] = board_host
    book_follow_base_url = os.environ.get("MIRA_BOOK_FOLLOW_BASE_URL", f"tcp://{board_host}:9527")
    os.environ["MIRA_BOOK_FOLLOW_BASE_URL"] = book_follow_base_url
    os.environ["MIRA_LIGHT_BASE_URL"] = book_follow_base_url

    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # LAN 检测
    lan_host = "127.0.0.1"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\\.' } | Select-Object -First 1 -ExpandProperty IPAddress"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            lan_host = result.stdout.strip()
    except Exception:
        pass

    console_public_host = os.environ.get("MIRA_UNIFIED_CONSOLE_PUBLIC_HOST", lan_host)
    console_url = f"http://{console_public_host}:{console_port}/"
    console_local_url = f"http://127.0.0.1:{console_port}/"

    celebration_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_HOST", "0.0.0.0")
    celebration_port = int(os.environ.get("MIRA_CELEBRATION_CONSOLE_PORT", "8777"))
    celebration_public_host = os.environ.get("MIRA_CELEBRATION_CONSOLE_PUBLIC_HOST", lan_host)
    celebration_url = f"http://{celebration_public_host}:{celebration_port}/08_celebrate/index.html"
    celebration_local_url = f"http://127.0.0.1:{celebration_port}/"

    # 打印启动信息
    print("== Mira Light Unified Director Console (Windows) ==")
    print(f"Repo:      {root_dir}")
    print(f"Console:   {console_url}")
    if not args.skip_celebration:
        print(f"Celebrate: {celebration_url}")
    print(f"Bind:      unified {console_host}:{console_port}")
    print(f"Local:     {console_local_url}")
    print(f"Board:     {board_user}@{board_host}:{board_port}")
    print(f"Python:    {python_bin}")
    print(f"Scripts:   {os.environ.get('MIRA_SHENZHEN_SCRIPTS_DIR', '')}")
    print(f"Remote:    {os.environ.get('MIRA_SHENZHEN_REMOTE_DESKTOP_DIR', '')}")
    print(f"Camera:    {os.environ.get('