# Mira Light — Windows 新电脑配置指南

> 最后更新：2026-06-28 | 目标环境：Windows 10/11 + Python 3.12+

---

## 第一步：环境准备

### 1.1 安装 Python
推荐 Python 3.12（3.14 的 venv 有 pip 初始化问题）。

```powershell
python --version  # 应显示 Python 3.12.x
```

### 1.2 安装依赖
```powershell
cd mira-light-unified-console-latest-portable-20260616-194411

# 核心依赖
python -m pip install numpy requests sounddevice soundfile websockets scipy

# Windows 补充
python -m pip install python-socks PySocks

# 自然 TTS（可选，网络可达时）
python -m pip install edge-tts aiohttp
```

---

## 第二步：SSH 密钥

### 2.1 生成密钥
```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519_mira" -N '""'
```

### 2.2 复制公钥到开发板
```powershell
type $env:USERPROFILE\.ssh\id_ed25519_mira.pub
# 将输出粘贴到开发板 /root/.ssh/authorized_keys
```

### 2.3 SSH config
编辑 `%USERPROFILE%\.ssh\config`：
```
Host 192.168.0.183
    User root
    IdentityFile ~/.ssh/id_ed25519_mira
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts
```

---

## 第三步：启动开发板服务

```powershell
# 确认板端 9527
ssh root@192.168.0.183 "ss -ltn | grep 9527"

# 如未运行，启动：
ssh root@192.168.0.183 "cd /home/sunrise/Desktop && python3 rdk_bus_servo_tcp_bridge.py &>/dev/null &"
```

---

## 第四步：启动服务

### 4.1 Web 控制台
```powershell
# 双击 Start-Latest-Console-Windows.bat
# 或手动：
$env:MIRA_SHENZHEN_BOARD_PASSWORD=''  # 必须为空（使用密钥）
python mira-light-unified-director-console/shenzhen_console.py `
  --host 0.0.0.0 --port 8791 `
  --board-host 192.168.0.183 --board-port 22 --board-user root
```

### 4.2 动作桥
```powershell
cd Mira-Light-Voice-Full-Ready
$env:PYTHONPATH = "$PWD\scripts;$PWD\tools\mira_light_bridge;$PWD\scripts\models"
python tools\mira_light_bridge\bridge_server.py `
  --config tools\mira_light_bridge\bridge_config.json `
  --host 127.0.0.1 --port 19783 `
  --base-url tcp://192.168.0.183:9527
```

### 4.3 语音（StepAudio 自然女声）
```powershell
# 双击 Start-Voice-Full-Windows.bat
# 或手动：
cd Mira-Light-Voice-Full-Ready\scripts
$env:STEPFUN_API_KEY='<your-key>'
$env:MIRA_LIGHT_BRIDGE_URL='http://127.0.0.1:19783'
python -u mira_stepfun_realtime_voice_actions.py `
  --mode continuous --voice wenrounvsheng `
  --assistant-text-actions `
  --bridge-url http://127.0.0.1:19783
```

---

## 第五步：验证

1. 打开 `http://127.0.0.1:8791/` → 点击"读取舵机位置"
2. 语音窗口应显示 `[turn 001] listening...`
3. 说"起床" → Mira 应动

---

## 常见问题

| 现象 | 解决 |
|------|------|
| 控制台连不上板 | 检查 SSH `ssh root@192.168.0.183 echo OK` |
| 语音识别不动 | 检查 9527 `curl http://127.0.0.1:19783/health` |
| 没声音 | StepAudio 内置 TTS 需网络；备选 Windows Huihui |
| 启动即崩溃 | 用 `--runtime-dir C:\mirart` 短路径 |

---

## 密钥（需自行填写）

| 变量 | 用途 |
|------|------|
| `STEPFUN_API_KEY` | 语音识别 + TTS |
| `OPENCLAW_NEWAPI_API_KEY` | LLM API |
| `MIRA_LIGHT_LINGZHU_AUTH_AK` | 云端对话（legacy 模式） |

---

## 第一步：环境准备

### 1.1 安装 Python
推荐 Python 3.12（3.14 的 venv 有 pip 初始化问题）。

```powershell
# 从 python.org 下载安装，确保勾选 "Add Python to PATH"
python --version  # 应显示 Python 3.12.x 或 3.14.x
```

### 1.2 安装 Git Bash (可选，用于运行 .command 脚本)
```powershell
winget install --id Git.Git -e
```

### 1.3 安装 Python 依赖
```powershell
cd mira-light-unified-console-latest-portable-20260616-194411

# 基础依赖
python -m pip install numpy requests sounddevice soundfile websockets scipy

# Windows 语音补充依赖
python -m pip install python-socks PySocks

# 自然语音 (可选，需要网络)
python -m pip install edge-tts aiohttp
```

---

## 第二步：SSH 密钥配置

### 2.1 生成密钥（如尚无）
```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519_mira" -N '""'
```

### 2.2 复制公钥到开发板
```powershell
# 方式 A：手动复制
type $env:USERPROFILE\.ssh\id_ed25519_mira.pub
# 将输出粘贴到开发板的 /root/.ssh/authorized_keys

# 方式 B：ssh-copy-id（如果开发板密码可用）
ssh-copy-id -i $env:USERPROFILE\.ssh\id_ed25519_mira root@192.168.0.183
```

### 2.3 配置 SSH config
编辑 `%USERPROFILE%\.ssh\config`：
```
Host mira-board
    HostName 192.168.0.183
    User root
    IdentityFile ~/.ssh/id_ed25519_mira
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts

Host 192.168.0.183
    User root
    IdentityFile ~/.ssh/id_ed25519_mira
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts
```

### 2.4 验证
```powershell
ssh root@192.168.0.183 "echo SSH_OK"
# 应输出: SSH_OK（无需密码）
```

---

## 第三步：检查开发板

### 3.1 确认板端 9527 服务在运行
```powershell
ssh root@192.168.0.183 "ss -ltn | grep 9527"
```
如果无输出，启动它：
```powershell
ssh root@192.168.0.183 "cd /home/sunrise/Desktop && python3 rdk_bus_servo_tcp_bridge.py > /dev/null 2>&1 &"
```

### 3.2 确认板端串口设备
```powershell
ssh root@192.168.0.183 "ls -l /dev/ttyS1"
# 应显示 /dev/ttyS1 存在
```

---

## 第四步：启动服务

推荐按以下顺序启动（每个都在独立命令窗口）：

### 4.1 Web 控制台
```powershell
# 方式 A：双击批处理文件
Start-Latest-Console-Windows.bat

# 方式 B：手动启动
python mira-light-unified-director-console/shenzhen_console.py ^
  --host 0.0.0.0 --port 8791 ^
  --board-host 192.168.0.183 --board-port 22 --board-user root
```
- 浏览器访问：`http://127.0.0.1:8791/`
- 环境变量 `MIRA_SHENZHEN_BOARD_PASSWORD` 必须为空（使用密钥）

### 4.2 动作桥 (Voice → Hardware)
```powershell
cd Mira-Light-Voice-Full-Ready
set PYTHONPATH=%CD%\scripts;%CD%\tools\mira_light_bridge;%CD%\scripts\models
python tools\mira_light_bridge\bridge_server.py ^
  --config tools\mira_light_bridge\bridge_config.json ^
  --host 127.0.0.1 --port 19783 ^
  --base-url tcp://192.168.0.183:9527
```
- 健康检查：`http://127.0.0.1:19783/health`

### 4.3 语音 Full 会话
```powershell
cd Mira-Light-Voice-Full-Ready\scripts

# 设置必要的环境变量
set STEPFUN_API_KEY=<你的 StepFun Key>
set OPENCLAW_NEWAPI_API_KEY=<你的 OpenClaw Key>
set MIRA_LIGHT_LINGZHU_AUTH_AK=<你的 Lingzhu Key>
set MIRA_LIGHT_BRIDGE_URL=http://127.0.0.1:19783

python -u mira_realtime_voice_interaction.py ^
  --mode continuous ^
  --device default ^
  --profile fast ^
  --transcriber stepfun ^
  --bridge-url http://127.0.0.1:19783 ^
  --runtime-dir C:\mira-runtime ^
  --vad-end-ms 400 ^
  --post-tts-cooldown-seconds 0.15 ^
  --no-startup-warmup
```
- 语音窗口持续监听，无需按回车

---

## 第五步：验证

### 5.1 控制台验证
1. 打开 `http://127.0.0.1:8791/`
2. 点击 "读取舵机位置"，应返回 4 个舵机的数值
3. 点击任意场景（如 "歪头"），开发板应执行动作

### 5.2 语音验证
1. 确认语音窗口显示 `[turn 001] listening...`
2. 对着麦克风说 "起床"，应：
   - 窗口显示识别结果
   - Mira 硬件执行起床动作
   - 听到中文语音回复 "好，我醒一下"

### 5.3 诊断
```powershell
# SSH 连接诊断
curl -X POST http://127.0.0.1:8791/api/connection-diagnose

# 动作桥健康
curl http://127.0.0.1:19783/health
```

---

## 常见问题

### Q: 控制台连不上开发板
**检查 SSH**：`ssh root@192.168.0.183 echo OK` 是否通？不通则检查网线、IP、密钥。

**检查密码环境变量**：确认 `MIRA_SHENZHEN_BOARD_PASSWORD` 为空（不是 "rootroot"）。

### Q: 语音识别了但不动机器
**检查 9527**：`ssh root@192.168.0.183 "ss -ltn | grep 9527"` 是否有输出？

**检查动作桥**：`curl http://127.0.0.1:19783/health` 显示 `baseUrl: tcp://192.168.0.183:9527`？

### Q: 没有语音播报声音
**检查 Windows 语音**：运行 `powershell -Command "Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.GetInstalledVoices() | ForEach-Object {$_.VoiceInfo.Name}"`，应包含 `Microsoft Huihui Desktop`。

### Q: 语音播报太机械
安装 edge-tts 自动切换到自然语音：
```powershell
python -m pip install edge-tts aiohttp
```

### Q: 语音启动后立即退出
**检查 runtime 路径**：确保 `C:\mira-runtime` 可写，或用 `--runtime-dir` 指定其他短路径（避免 Windows MAX_PATH 260字符限制）。

---

## 完整文件结构速查

```
mira-light-unified-console-latest-portable-20260616-194411\
├── mira-light-unified-director-console/
│   └── shenzhen_console.py        ← Web 控制台后端 (端口 8791)
├── Mira-Light-Voice-Full-Ready/    ← 语音包（推荐）
│   ├── scripts/
│   │   ├── mira_realtime_voice_interaction.py  ← 语音主程序
│   │   ├── mira_light_audio.py                 ← TTS 播放
│   │   ├── mira_voice_intents.py               ← 意图识别
│   │   └── stepfun_llm_planner.py              ← LLM 规划器
│   ├── tools/
│   │   ├── mira_light_bridge/                  ← 动作桥 (19783)
│   │   └── speaker-edge-tts-play.py            ← Edge 自然语音
│   └── config/                                 ← 配置文件
├── Motions_Shenzhen/              ← 动作脚本
├── Start-Latest-Console-Windows.bat ← 一键启动控制台
├── CHANGELOG_2026-06-26_to_2026-06-27.md
├── SETUP_GUIDE_WINDOWS.md          ← 本指南
└── README_VOICE_FULL.md            ← 语音功能说明
```

---

## 密钥与凭证（需自行填写）

以下密钥需在启动语音前设置环境变量：

| 环境变量 | 用途 | 获取方式 |
|---------|------|---------|
| `STEPFUN_API_KEY` | StepAudio 语音识别 | StepFun 控制台 |
| `OPENCLAW_NEWAPI_API_KEY` | LLM API | OpenClaw 控制台 |
| `MIRA_LIGHT_LINGZHU_AUTH_AK` | Lingzhu 云端对话 | Lingzhu 配置 |

> ⚠️ 原包内含有硬编码的密钥（STEPFUN、OPENCLAW、LINGZHU），对外分发时需移除或替换。
