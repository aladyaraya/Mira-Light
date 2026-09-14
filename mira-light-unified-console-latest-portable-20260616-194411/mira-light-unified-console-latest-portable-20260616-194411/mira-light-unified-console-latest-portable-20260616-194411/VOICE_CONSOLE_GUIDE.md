# 语音控制台启动指南

## 当前情况

PowerShell 版本太低（5.1），无法运行 `Start-Mira-Light-Voice-Console.ps1`（需要 7.0+）

---

## 解决方案

### 方案 1：直接运行 Python 语音脚本（推荐）

语音控制台的核心是 Python 脚本。直接运行它：

```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"

python -m mira-light-unified-director-console.mira_stepfun_console_voice --console-url http://127.0.0.1:8790
```

**但需要先确认：**
1. ✅ 统一导演控制台正在运行（http://127.0.0.1:8790）
2. ✅ 设置 `STEPFUN_API_KEY` 环境变量

---

### 方案 2：升级 PowerShell（一次性解决）

1. **下载 PowerShell 7**
   - 访问：https://github.com/PowerShell/PowerShell/releases
   - 下载：PowerShell-7.x.x-win-x64.msi
   - 运行安装程序

2. **使用 PowerShell 7 启动**
   ```powershell
   pwsh
   cd "mira-light-unified-console-latest-portable-20260616-194411"
   .\Start-Mira-Light-Voice-Console.ps1
   ```

---

### 方案 3：手动运行核心组件

如果上面的方法都失败，可以手动启动各个组件：

#### 步骤 1：确保控制台运行
```powershell
# 在另一个 PowerShell 窗口运行
cd "mira-light-unified-console-latest-portable-20260616-194411"
python mira-light-unified-director-console/shenzhen_console.py
```

#### 步骤 2：启动语音识别
```powershell
# 设置 API Key
$env:STEPFUN_API_KEY = "your-api-key-here"

# 运行语音脚本
cd "mira-light-unified-console-latest-portable-20260616-194411\Mira-Light-Voice-Full-Ready"
python scripts/mira_stepfun_realtime_voice_actions.py
```

---

## ⚠️ 前置条件检查

### 1. 统一导演控制台必须运行

在启动语音前，确保控制台在 http://127.0.0.1:8790 运行。

如果还没启动：
```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"
python mira-light-unified-director-console/shenzhen_console.py
```

### 2. STEPFUN_API_KEY 必须设置

```powershell
# 临时设置（当前会话有效）
$env:STEPFUN_API_KEY = "your-stepfun-api-key"

# 或永久设置（用户级别）
[System.Environment]::SetEnvironmentVariable('STEPFUN_API_KEY', 'your-api-key', 'User')
```

### 3. Python 虚拟环境（如果使用）

某些语音功能可能需要虚拟环境：
```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411\Mira-Light-Voice-Full-Ready"
.\.venv\Scripts\Activate.ps1
```

---

## 🎯 快速测试（不需要 PowerShell 7）

运行这个命令测试语音组件是否能找到：

```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"
python -c "import sys; sys.path.insert(0, 'mira-light-unified-director-console'); import mira_stepfun_console_voice; print('语音模块加载成功')"
```

如果看到 "语音模块加载成功"，说明可以直接运行。

---

## 📖 可用语音命令

一旦启动，你可以说：

**场景命令：**
- "起床" / "醒来"
- "摸一摸" / "摸摸"
- "好奇" / "观察"
- "睡觉" / "休息"
- "庆祝" / "跳舞"
- "拜拜" / "再见"

**功能命令：**
- "打开摄像头" / "拍照"
- "打印照片"
- "开始追书" / "停止追书"
- "紧急停止"

**详细列表：**
```powershell
.\Start-Mira-Light-Voice-Console.ps1 -ListCommands
```
（需要 PowerShell 7）

---

**你想先尝试哪个方案？**
