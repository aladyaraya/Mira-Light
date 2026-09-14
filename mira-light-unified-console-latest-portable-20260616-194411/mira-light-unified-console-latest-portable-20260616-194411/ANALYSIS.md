# 当前状态分析

## ✅ 已完成的配置

1. **SSH 密钥认证已配置**
   - 公钥已添加到开发板
   - 无密码登录测试成功

2. **SSH 配置文件已创建**
   - `~/.ssh/config` 包含 `mira-board` 主机配置
   - 使用 `IdentityFile ~/.ssh/id_ed25519_mira`

3. **密码环境变量已清空**
   - `MIRA_SHENZHEN_BOARD_PASSWORD` - 未设置
   - `MIRA_CAMERA_BOARD_PASSWORD` - 未设置

## ❓ 仍然存在的问题

**控制台错误信息：**
```
摄像头
自动刷新中 · plink is required for password SSH on Windows. Install PuTTY or configure SSH key auth.
```

## 🔍 代码逻辑分析

### 代码流程

1. **`shenzhen_console.py`** 读取密码（第 5310 行）
   ```python
   password = os.environ.get(args.password_env, "")
   camera_password = os.environ.get(args.camera_password_env, "") or password
   ```
   → 如果环境变量未设置，password 为空字符串 `""`

2. **`CameraSampler.capture_once()`** 调用（第 177 行）
   ```python
   image_path = digua_remote_render_pipeline.capture_remote_image(
       host=self.board_host,
       user=self.board_user,
       port=self.board_port,
       password=self.board_password,  # ← 传入密码
       ...
   )
   ```

3. **`capture_remote_image()`** 调用（第 422 行）
   ```python
   raw_output = run_ssh_capture(
       host=host,
       user=user,
       port=port,
       password=password,
       ...
   )
   ```

4. **`run_ssh_capture()`** 逻辑（第 315-354 行）
   ```python
   command = build_ssh_command(
       ...,
       batch_mode=not password,  # password="" → batch_mode=True
   )
   if password:  # "" 是 falsy → 走 else 分支
       result = run_ssh_with_password(...)  # 不会执行到这里
   else:
       result = subprocess.run(command, ...)  # ← 应该走这里
   ```

5. **`build_ssh_command()`** 构建命令（第 176-201 行）
   ```python
   command = ["ssh", "-o", "StrictHostKeyChecking=no", ...]
   if batch_mode:  # True
       command.extend(["-o", "BatchMode=yes"])  # ← 添加这个
   ```

### 理论上的行为

如果 password 为空字符串：
- ✅ batch_mode = True
- ✅ SSH 命令包含 `BatchMode=yes`
- ✅ 使用 `subprocess.run(command)`（普通 SSH）
- ✅ **不会调用 `_build_plink_command()`**
- ✅ **不会抛出 "plink is required" 错误**

### 实际观察到的行为

- ❌ 控制台显示 "plink is required" 错误
- ❌ 摄像头抓取失败

## 🤔 可能的解释

### 可能性 1：密码被某处设置

某个地方（可能是在控制台启动脚本或系统环境）设置了密码环境变量。

**验证方法：**
```powershell
# 检查所有环境变量
[System.Environment]::GetEnvironmentVariable('MIRA_SHENZHEN_BOARD_PASSWORD', 'User')
[System.Environment]::GetEnvironmentVariable('MIRA_SHENZHEN_BOARD_PASSWORD', 'Machine')
$env:MIRA_SHENZHEN_BOARD_PASSWORD
```

### 可能性 2：控制台使用了不同的代码路径

也许 `CameraSampler` 的初始化或运行逻辑有别于 `capture_remote_image` 的调用。

**需要检查：**
- `CameraSampler.capture_once()` 的完整实现
- 是否有其他地方直接调用 `run_ssh_with_password`

### 可能性 3：控制台在另一个进程中运行

如果控制台是在 **IDE、另一个终端或服务** 中运行的，它可能继承了不同的环境变量。

**验证方法：**
在控制台终端中运行：
```powershell
echo $env:MIRA_SHENZHEN_BOARD_PASSWORD
echo $env:MIRA_CAMERA_BOARD_PASSWORD
```

### 可能性 4：状态缓存或错误残留

控制台可能在启动时检测一次，然后缓存结果。即使之后配置了 SSH 密钥，也不会重新检测。

## 🛠️ 推荐的诊断步骤

### 步骤 1：确认密码环境变量

在**运行控制台的同一个 PowerShell 窗口**中执行：

```powershell
# 检查环境变量
Get-ChildItem env:* | Where-Object { $_.Name -like 'MIRA*' -or $_.Name -like '*PASSWORD*' }

# 或者
[System.Environment]::GetEnvironmentVariable('MIRA_SHENZHEN_BOARD_PASSWORD', 'Process')
[System.Environment]::GetEnvironmentVariable('MIRA_CAMERA_BOARD_PASSWORD', 'Process')
```

应该看到这两个变量都是空或未设置。

### 步骤 2：测试实际的 SSH 命令

运行测试脚本（需要先解决 Python 路径问题）：
```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"
python test_ssh_simple.py
```

### 步骤 3：重启控制台

完全关闭控制台，重新打开，确保没有缓存的状态。

### 步骤 4：如果问题 persists，临时方案

**临时方案 A：安装 PuTTY（最快）**
```powershell
choco install putty
```
或者手动下载：https://www.putty.org/

**临时方案 B：在 WSL 中运行控制台**
```powershell
wsl
cd /mnt/d/PROJECT/Mira/20260626代码加语音/mira-light-unified-console-latest-portable-20260616-194411
python3 mira-light-unified-director-console/shenzhen_console.py
```

## 📋 代码位置参考

- `shenzhen_console.py:5310` - 读取密码
- `camera_console.py:82,181` - CameraSampler 使用密码
- `digua_remote_render_pipeline.py:315` - run_ssh_capture
- `digua_remote_render_pipeline.py:176` - build_ssh_command
- `digua_remote_render_pipeline.py:216` - _build_plink_command（抛出错误）

## 🔧 潜在的代码修复

如果确认是代码 bug，可能的修复包括：

1. 在 `run_ssh_capture()` 中，如果 `password` 为空，完全跳过 plink 检查
2. 在 `CameraSampler.__init__()` 中，如果 password 为空，明确设置标志
3. 添加更详细的日志，打印 password 参数的值和来源

---

**下一步：** 请在运行控制台的 PowerShell 中执行步骤 1 的命令，并告诉我结果。
