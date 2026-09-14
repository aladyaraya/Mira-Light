# Mira Light Shenzhen Console Windows 修复指南

## 问题诊断

根据控制台错误日志，发现以下问题：

### 1. [已修复] SSH 队列模式配置
✅ **已完成**：在 `tools/hermes-mira-home/config.yaml` 中添加了 `busy_input_mode: queue`

### 2. ❌ SSH 连接失败 - pty is unavailable
**问题**：Windows 上缺少伪终端支持
```
SSH 异常 · pty is unavailable on this platform
```

**解决方案**（选择一种）：

#### 方案 A：安装 PuTTY plink（推荐，最简单）

1. 下载 PuTTY：https://www.putty.org/
2. 安装时将 `plink.exe` 添加到 PATH
3. 或者使用 Chocolatey：
   ```powershell
   choco install putty
   ```

#### 方案 B：配置 SSH 密钥认证

```powershell
# 1. 生成 SSH 密钥（如果还没有）
ssh-keygen -t ed25519 -C "mira-board"

# 2. 复制公钥到开发板
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@192.168.0.183 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# 3. 测试连接（应该不需要密码）
ssh root@192.168.0.183 "echo 'SSH 连接成功'"
```

### 3. ❌ 追书脚本路径问题
**问题**：Windows 路径格式不正确
```
/bin/bash: C:UsersllwxyDownloadsmira-light-unified-console-latest-portable-20260616-194411scriptsrun_mira_light_vision_stack.sh: No such file or directory
```

**问题根源**：
- 控制台在 Windows 上尝试直接用 `bash` 执行脚本
- Windows 路径 `C:\Users\...` 被直接传给 bash，应该转换为 `/mnt/c/Users/...`（WSL 格式）

**解决方案**（选择一种）：

#### 方案 A：在 WSL 中运行控制台（推荐）

```powershell
# 1. 安装 WSL（如果还没有）
wsl --install

# 2. 在 WSL 终端中进入项目目录
cd /mnt/d/PROJECT/Mira/20260626代码加语音/mira-light-unified-console-latest-portable-20260616-194411

# 3. 在 WSL 中启动控制台
python3 mira-light-unified-director-console/shenzhen_console.py
```

#### 方案 B：安装 Git Bash

1. 下载 Git for Windows：https://gitforwindows.org/
2. 安装时选择 "Use Git and optional Unix tools from the Command Prompt"
3. 在 Git Bash 中运行控制台

### 4. ⚠️ 打印机桥接令牌缺失
**问题**：
```
http://127.0.0.1:9771 · token missing · missing OPENCLAW_PRINTER_BRIDGE_TOKEN
```

**解决方案**（可选，如果不需要打印功能可以忽略）：

```powershell
# 设置打印机桥接令牌（替换为实际令牌）
$env:OPENCLAW_PRINTER_BRIDGE_TOKEN = "your-printer-token-here"

# 或者在控制台启动前设置环境变量
[System.Environment]::SetEnvironmentVariable('OPENCLAW_PRINTER_BRIDGE_TOKEN', 'your-token', 'User')
```

### 5. ⚠️ 舵机位置读取失败
**问题**：
```
读取失败：pty is unavailable on this platform
```

这是和 SSH 相同的问题，安装 plink 或配置 SSH 密钥后会自动解决。

---

## 快速修复清单

### 立即执行（按顺序）：

1. **安装 PuTTY**
   - 下载：https://www.putty.org/
   - 或使用 Chocolatey：`choco install putty`

2. **测试 SSH 连接**
   ```powershell
   # 应该能成功连接（可能会提示确认 host key）
   plink root@192.168.0.183 "echo 'SSH 连接成功'"
   ```

3. **重启控制台**
   - 关闭当前控制台
   - 重新启动
   - 检查 SSH 自检是否通过

4. **如果需要使用追书功能**
   - 在 WSL 中重新启动控制台
   - 或者在 Git Bash 中启动

---

## 环境变量参考

在启动控制台前，可以设置以下环境变量：

```powershell
# 开发板连接
$env:MIRA_BOARD_HOST = "192.168.0.183"
$env:MIRA_BOARD_PORT = "22"
$env:MIRA_BOARD_USER = "root"
$env:MIRA_BOARD_PASSWORD = "your-password"  # 不推荐，建议用 SSH 密钥

# 打印机桥接（可选）
$env:OPENCLAW_PRINTER_BRIDGE_TOKEN = "your-token"

# Windows 特定：使用 plink
$env:MIRA_USE_PLINK = "1"
```

---

## 验证修复

安装 plink 并重启控制台后，应该看到：

- ✅ SSH 自检：通过
- ✅ 摄像头抓取：可用
- ✅ 舵机位置读取：成功
- ✅ 追书功能：需要 WSL 环境

---

## 常见问题

### Q1: plink 安装后仍然提示未找到？
**A**: 重启终端或 IDE，确保 PATH 已更新。或者直接指定 plink 路径：
```powershell
$env:PATH = "C:\Program Files\PuTTY;" + $env:PATH
```

### Q2: SSH 密钥认证仍然提示密码？
**A**: 检查公钥是否正确复制：
```powershell
# 在开发板上检查
ssh root@192.168.0.183 "cat ~/.ssh/authorized_keys"
```

### Q3: 追书功能在 Windows 上有其他方法吗？
**A**: 目前追书功能依赖 bash 脚本，建议：
- 在 WSL 中运行控制台（推荐）
- 或者远程连接到 WSL/Linux 机器上运行

---

最后更新：2026-06-26
