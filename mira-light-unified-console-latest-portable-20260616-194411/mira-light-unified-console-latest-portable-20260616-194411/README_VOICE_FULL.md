# Mira Light — 语音控制完整说明 (Voice Full-Ready)

> 基于 `Mira-Light-Voice-Full-Ready` 语音包（2026-06-18 更新）

---

## 功能概述

Mira Light 语音系统支持**自然语言中文对话 + 硬件动作控制**。对着麦克风说话，Mira 理解语义后执行对应场景（起床、跳舞、睡觉等），同时用中文语音回复。

### 支持的硬件动作（34 场景 + 5 触发器）

#### 直接控制（说"启动XXX"）

| 口语 | 执行场景 | 硬件行为 |
|------|---------|---------|
| 起床 / 醒来 / 早安 | `wake_up` | 缓缓起立 |
| 跳舞 / 庆祝 / 跳个舞 | `celebrate` | 舞蹈动作 |
| 睡觉 / 休息 / 去睡吧 | `sleep` | 趴下熄灯 |
| 摸一摸 / 撒娇 / 贴贴 | `touch_affection` | 亲近互动 |
| 歪头 / 卖萌 | `cute_probe` | 歪头卖萌 |
| 拜拜 / 再见 / 晚安 | `farewell` | 离别挥手 |
| 看看我 / 好奇你是谁 | `curious_observe` | 观察行为 |
| 躲开 / 退后 | `hand_avoid` | 躲避动作 |
| 发呆 / 放空 | `daydream` | 发呆状 |
| 追踪 / 跟着我 | `track_target` | 跟踪目标 |

#### 情绪共情

| 口语 | 执行场景 |
|------|---------|
| 我好开心 / 太开心了 | `happy_dance` |
| 好难过 / 心情不好 | `sad_comfort` |
| 好害羞 / 脸红了 | `shy_blush` |
| 我爱你 / 比心 | `love_heart` |
| 笑死我了 / 哈哈哈 | `laugh_giggle` |
| 吓一跳 / 好吓人 | `alert_startle` |
| 你真棒 / 好可爱 | `praise_detected` (trigger) |
| 唉 (叹气) | `sigh_detected` (trigger) |

---

## 架构

```
┌─────────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│  麦克风输入  │───→│ StepAudio │───→│ 意图识别   │───→│ 动作桥    │
│  (continuous)│    │ ASR 语音  │    │ 本地/LLM  │    │ :19783    │
└─────────────┘    │ 识别 0.8s │    │ 规划      │    └────┬─────┘
                   └──────────┘    └───────────┘         │
                                                      │ TCP 发包
                                                    ┌─┴──────────┐
                                                    │ 开发板:9527 │
                                                    │ 舵机/LED   │
                                                    └────────────┘
```

### 两层意图识别

1. **本地关键词**（零延迟）：常见命令走本地 keyword 匹配，不依赖 LLM。如"跳舞"→`celebrate`。
2. **LLM 白名单规划**（0.8s）：自然语言走 step-3.7-flash，只能从预定义白名单中选择 scene/trigger。

### 延迟（优化后）

| 环节 | 时间 |
|------|------|
| 说话→VAD 结束 | ~1.4s（1s 说话 + 0.4s 静默） |
| 语音识别 (STT) | ~0.8s |
| 意图决策 | ~0s（本地匹配）或 ~0.8s（LLM） |
| **硬件动作触发** | **同时发生** |
| TTS 语音回复 | 后台播放，不阻塞 |

**从说完话到硬件动作：约 2 秒。**

---

## 启动方式

### Mac
```bash
# 仅聊天（不动机器）
./Start-Chat.command

# 语音控制动作（完整功能）
./Start-Full.command

# 仅启动桥
./Start-Bridge.command
```

### Windows
```powershell
cd Mira-Light-Voice-Full-Ready\scripts

# 设置密钥
set STEPFUN_API_KEY=<your-key>
set OPENCLAW_NEWAPI_API_KEY=<your-key>
set MIRA_LIGHT_LINGZHU_AUTH_AK=<your-key>
set MIRA_LIGHT_BRIDGE_URL=http://127.0.0.1:19783

# 启动（持续监听，无需回车）
python -u mira_realtime_voice_interaction.py ^
  --mode continuous ^
  --device default ^
  --transcriber stepfun ^
  --bridge-url http://127.0.0.1:19783 ^
  --runtime-dir C:\mira-runtime ^
  --vad-end-ms 400 ^
  --post-tts-cooldown-seconds 0.15
```

---

## 关键配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--mode` | `continuous` | 持续监听 / `enter-vad` 按回车 |
| `--vad-end-ms` | `400` | 说话结束后的静音等待（越小反应越快） |
| `--post-tts-cooldown-seconds` | `0.15` | TTS 播放后冷却时间 |
| `--transcriber` | `stepfun` | 语音识别引擎（Windows 推荐） |
| `--bridge-url` | `http://127.0.0.1:19783` | 动作桥地址 |
| `--voice` | `warm_gentleman` | TTS 声音配置 |

---

## TTS 语音播报

### Windows
- **默认**：Microsoft Huihui Desktop（慧慧）中文语音 — 微软内置，较机械
- **推荐**：Edge-TTS 神经网络语音 — 需要安装 `edge-tts` 和 `aiohttp`，自动切换
  ```powershell
  python -m pip install edge-tts aiohttp
  ```

### Mac
- 使用项目自带的扬声器 TTS 工具（`speaker-preferred-tts-play` 等）
- 配置文件：`config/mira_light_profile.local.json`

---

## 文件结构

```
Mira-Light-Voice-Full-Ready/
├── scripts/
│   ├── mira_realtime_voice_interaction.py    ← 语音主入口
│   ├── mira_stepfun_realtime_voice_actions.py ← StepAudio 实时版
│   ├── mira_realtime_action_orchestrator.py  ← 动作编排器
│   ├── mira_voice_intents.py                ← 本地意图匹配（34 场景）
│   ├── stepfun_llm_planner.py               ← LLM 白名单规划
│   ├── mira_light_audio.py                  ← TTS 播放
│   ├── scenes.py                             ← 动作场景定义
│   └── models/                               ← 模型配置
├── tools/
│   ├── mira_light_bridge/                    ← 动作桥 (19783)
│   │   ├── bridge_server.py
│   │   └── bridge_config.json
│   └── speaker-edge-tts-play.py              ← Edge-TTS 桥接
├── config/
│   ├── mira-light-realtime.env              ← 环境配置
│   └── mira_light_profile.local.json       ← 灯光/舵机配置
├── runtime/                                  ← 运行日志
├── commands/                                 ← Shell 命令集
├── Start-Chat.command
├── Start-Full.command
├── Start-Bridge.command
├── Start-Full-Windows.command
└── README.md
```

---

## 故障排查

| 现象 | 可能原因 | 检查方法 |
|------|---------|---------|
| 识别了但没动作 | 动作桥或 9527 未启动 | `curl http://127.0.0.1:19783/health` |
| 没听到声音 | Windows 语音未选中 | 见 SETUP_GUIDE 常见问题 |
| 启动立刻崩溃 | runtime 路径太长 | 用 `--runtime-dir C:\mirart` |
| 识别慢 | StepFun API 延迟 | 正常 ~0.8s，可控 |
| 一直监听不结束 | VAD 阈值太高 | 调低 `--vad-min-rms` |
