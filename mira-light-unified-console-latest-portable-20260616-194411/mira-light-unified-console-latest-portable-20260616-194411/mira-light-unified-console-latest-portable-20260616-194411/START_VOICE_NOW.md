# 语音控制台快速启动指南

## 🎯 快速启动

我已经为你创建了启动脚本，可以直接运行：

### 方法 1：双击运行批处理文件

直接双击项目目录下的：
```
Start-Voice-Console.bat
```

**首次运行会提示输入 StepFun API Key。**

---

### 方法 2：PowerShell 命令

在 PowerShell 中运行：

```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"

# 设置 API Key（如果还没设置）
$env:STEPFUN_API_KEY = "your-stepfun-api-key-here"

# 启动语音控制台
python mira-light-unified-director-console\mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790
```

---

## ⚠️ 前置条件

### 1. 统一导演控制台必须正在运行

如果控制台还没启动，先在一个 PowerShell 窗口运行：

```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"
python mira-light-unified-director-console/shenzhen_console.py
```

保持这个窗口打开，然后在**另一个 PowerShell 窗口**启动语音控制台。

---

### 2. StepFun API Key

如果还没有 API Key：

1. 访问 StepFun 开放平台：https://platform.stepfun.com/
2. 注册/登录账号
3. 创建 API Key
4. 设置为环境变量：
   ```powershell
   [System.Environment]::SetEnvironmentVariable('STEPFUN_API_KEY', 'your-key', 'User')
   ```

---

## 📋 启动步骤（完整）

### 步骤 1：启动统一导演控制台

```powershell
# PowerShell 窗口 1
cd "mira-light-unified-console-latest-portable-20260616-194411"
python mira-light-unified-director-console/shenzhen_console.py
```

看到 `open http://127.0.0.1:8790` 表示成功。

---

### 步骤 2：启动语音控制台

**新开一个 PowerShell 窗口**，运行：

```powershell
# PowerShell 窗口 2
cd "mira-light-unified-console-latest-portable-20260616-194411"

# 设置 API Key（只需一次）
$env:STEPFUN_API_KEY = "your-stepfun-api-key"

# 启动语音
python mira-light-unified-director-console\mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790
```

---

### 步骤 3：测试语音

看到以下输出表示启动成功：

```
========================================
  Mira Light Voice Console
  Voice Control for Unified Director
========================================

Speak naturally to control the console.
Say '退出对话' to stop listening.
```

然后尝试说：
- "起床"
- "打开摄像头"
- "摸一摸"
- "退出对话"（停止）

---

## 🎤 可用语音命令

### 场景控制

| 你说 | 执行 |
|------|------|
| "起床" / "醒来" | 启动起床场景 |
| "摸一摸" / "摸摸" | 启动摸摸场景 |
| "好奇" / "观察" | 好奇观察 |
| "睡觉" / "休息" | 睡觉场景 |
| "庆祝" / "跳舞" | Offer 庆祝 |
| "拜拜" / "再见" | 送别 |

### 功能控制

| 你说 | 执行 |
|------|------|
| "打开摄像头" | 启动摄像头预览 |
| "拍照" | 拍照 |
| "打印照片" | 打印照片 |
| "开始追书" | 启动追书模式 |
| "紧急停止" | 紧急停止 |
| "退出对话" | 停止语音监听 |

---

## 🔧 高级选项

### 列出所有命令

```powershell
python mira-light-unified-director-console\mira_stepfun_console_voice.py --list-commands
```

### 禁用 TTS 反馈

```powershell
python mira-light-unified-director-console\mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790 --no-tts-feedback
```

### 只启用语义动作（禁用语音状态动作）

```powershell
python mira-light-unified-director-console\mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790 --no-voice-state-actions
```

### 设置 API 代理

```powershell
python mira-light-unified-director-console\mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790 --proxy-url http://your-proxy:port
```

---

## 🐛 常见问题

### Q: 提示 "Console not responding"

**A**: 确保统一导演控制台正在运行（步骤 1）

### Q: 提示 "StepFun API key required"

**A**: 设置环境变量：
```powershell
$env:STEPFUN_API_KEY = "your-key"
```

### Q: 语音识别不准确

**A**: 检查：
1. 麦克风是否工作正常
2. API Key 是否有效
3. 网络连接是否正常

### Q: 命令不执行

**A**: 检查：
1. 控制台日志是否有错误
2. 语音控制台日志显示的命令识别是否正确
3. 控制台 API 是否可访问

---

## 📖 详细文档

完整文档：`VOICE_CONSOLE_GUIDE.md`

---

**现在请：**

1. 确保统一导演控制台正在运行
2. 设置 STEPFUN_API_KEY
3. 运行启动命令

**需要我帮你检查控制台是否运行，或者帮你设置 API Key 吗？**
