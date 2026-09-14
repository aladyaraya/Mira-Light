# Mira Touch Audio Bridge —— 触觉系统的音频伴侣

> 板上的 `touch_dispatcher.py` 在用户长按 Mira 灯头时会发 HTTP 触发；本 bridge 在 Mac 上监听这个触发，**播一句温柔的语音**。

---

## 一句话

```
板子摸到触摸 ≥1.2s → POST → 本 bridge → afplay assets/speech/cute_robot_comfort.aiff
板子检测到松手    → POST → 本 bridge → 立即停止音频
```

---

## 目录结构

```
audio-bridge/
├── README.md                           ← 你在这里
├── audio_bridge_server.py              ← 精简 HTTP server (~290 行 Python)
├── bridge_config.json                  ← 配置：端口 / 音频根目录
├── Start-Audio-Bridge.command          ← 双击即起（Mac 专用，需要 afplay）
│
├── assets/                             ← 音频资产
│   └── speech/
│       ├── cute_robot_comfort.aiff     ← ⭐ 主语音（v14 默认）
│       ├── touch_affection_host.aiff   ← 备选：温柔抚摸
│       ├── cute_probe_host.aiff        ← 备选：好奇试探
│       ├── sigh_demo_host.aiff         ← 备选：叹气
│       ├── sigh_demo_line.aiff         ← 备选：短叹气
│       ├── thank_you_happy_line.aiff   ← 备选：感谢
│       └── celebrate_line.aiff         ← 备选：欢庆
│
├── launchd/
│   └── com.miralight.audio-bridge.plist  ← macOS 开机自启 (可选)
│
└── docs/
    ├── DEPLOYMENT.md                   ← 如何部署 + 开机自启
    ├── PROTOCOL.md                     ← HTTP API 协议
    └── AUDIO_LIBRARY.md                ← 音频文件清单 / 换音频指南
```

---

## 5 秒上手

```bash
cd "$(dirname "$0")"   # 进到 audio-bridge 目录
./Start-Audio-Bridge.command
```

或者直接双击 `Start-Audio-Bridge.command`。

启动后会看到：
```
[ready] listening on http://0.0.0.0:9783
[ready] assets_root=.../audio-bridge/assets
[ready] default_comfort_asset=speech/cute_robot_comfort.aiff
```

测试：
```bash
# 健康检查
curl http://127.0.0.1:9783/health

# 手动触发音频（不需要真的摸 Mira）
curl -X POST http://127.0.0.1:9783/v1/mira-light/trigger \
  -H "Content-Type: application/json" \
  -d '{"event":"long_touch_comfort","payload":{"asset_name":"speech/cute_robot_comfort.aiff"}}'

# 停止当前播放
curl -X POST http://127.0.0.1:9783/v1/mira-light/trigger \
  -H "Content-Type: application/json" \
  -d '{"event":"stop_comfort_sound"}'
```

---

## 这个 bridge 跟 Mira-Light-Voice-Full-Ready 的关系

| 维度 | 本精简 bridge | Mira-Light-Voice-Full-Ready/bridge_server.py |
|---|---|---|
| 行数 | ~290 行 | ~700 行 + 1900 行 runtime + 数千行依赖 |
| 端点 | `/v1/mira-light/trigger` `/health` `/stop` | 30+ 个端点（scenes / sensors / actions / led / ...）|
| 依赖 | 仅 Python 标准库 + macOS `afplay` | mira_light_runtime / scenes / signal_delivery / embodied_memory_client |
| 适用场景 | **只要触觉音频** | 完整 Mira 语音/场景/灯效控制 |
| 跟触觉协议兼容 | ✅ 100%（一致的 event_name / asset_name 约定）| ✅ |

**用哪个？**

- 如果你**只跑触觉系统**，没有跑别的 Mira 语音/场景控制 → 用本精简 bridge
- 如果你已经在跑 Mira-Light-Voice-Full-Ready 那套（端口 9783 已被占）→ 那套已经处理 `long_touch_comfort`，**不需要再启本 bridge**

两者**不能同时在 9783 端口跑**。本 bridge 默认端口 9783 跟那套冲突；要并行跑就改 `bridge_config.json` 的 `listenPort` + 板上 `touch_mapping.json` 的 `bridge_url`。

---

## 板上的对应配置

`board-files/touch_mapping.json` 的相关字段：

```json
"comfort_sound": {
  "enabled": true,
  "threshold_ms": 1200,
  "bridge_url": "http://192.168.0.46:9783/v1/mira-light/trigger",
  "event_name": "long_touch_comfort",
  "asset_name": "speech/cute_robot_comfort.aiff",
  "post_timeout_ms": 1500
}
```

注意：
- `192.168.0.46` 必须改成**你 Mac 的实际 IP**（同 5G WiFi 子网下板子能访问到的）
- 用 `ifconfig | grep "inet " | grep -v 127.0.0.1` 查 Mac IP

---

## 详细文档

| 想做什么 | 看哪 |
|---|---|
| 部署到新 Mac / 开机自启 | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| 改 HTTP API / 加新事件类型 | [docs/PROTOCOL.md](docs/PROTOCOL.md) |
| 换音频 / 生成新音频 | [docs/AUDIO_LIBRARY.md](docs/AUDIO_LIBRARY.md) |
| 触觉系统整体 | [../README.md](../README.md) |
| 板上 dispatcher 怎么发触发 | [../board-files/touch_dispatcher.py](../board-files/touch_dispatcher.py) 搜 `comfort_sound` |

---

## 设计取舍

### 为什么自己写一个 bridge 而不是用现成的？

Mira-Light-Voice-Full-Ready/bridge_server.py 是为完整 Mira 语音生态服务的——它要驱动灯/舵机/scenes，依赖 4 个 Python 模块、3 个 JSON config、1 个 ESP32 lamp 协议层。

但**触觉系统的需求很简单**：收到一个 HTTP POST → 播一个 .aiff 文件 → 收到停 → 停。把这个剥出来 200 多行就够。

少依赖 = 易部署 = 易理解 = 易调试。

### 为什么不内嵌音频到 dispatcher (板上播)?

试过。板子是 RDK X5 ARM，aplay 兼容性不好，且板子的 CPU 已经在跑触觉检测 + 舵机控制 + 状态机。音频解码会加压力。把音频外置到 Mac 是更稳的选择。

### 为什么用 .aiff 而不是 .mp3 / .wav?

- `.aiff` 是 macOS 原生格式，afplay 解码无延迟
- 音质无损，但文件比 mp3 大（cute_robot_comfort 1.85 MB）
- 触觉只有几个音频，总占用 < 3 MB，无所谓
- 如果以后要 1000 个音频，可以改用 mp3 + 装 ffmpeg

### 为什么松手要立即停 (v16 行为)?

实测：cute_robot_comfort 音频长 6 秒。如果用户摸 1.5 秒松手，音频继续播 4.5 秒——感觉跟动作脱节。所以板上 dispatcher 在 release 时主动发 `stop_comfort_sound`，让音频跟动作同步收尾。

---

## 当前已知限制

| 限制 | 后果 | 缓解 |
|---|---|---|
| 只支持 macOS | Linux/Windows 不能用 | Linux 改用 `aplay` 替换 `afplay` 调用 |
| 同一时刻只能播一个 | 短时间内多次触摸只有最新的会响 | 这是设计目标（避免叠音）|
| 没有音量控制 | 用 Mac 系统音量 | 后续可以加 `osascript -e 'set volume'` |
| 没有 auth | LAN 内任何人可以触发 | LAN 已经是受信网络；如果要 auth 加 `bridgeTokenEnv` |

---

## 看 bridge 是不是在跑

```bash
curl -s http://127.0.0.1:9783/health | python3 -m json.tool
```

期望：

```json
{
  "ok": true,
  "audio": {
    "playing": false,
    "asset": null,
    ...
    "assets_root": "/Users/.../audio-bridge/assets"
  }
}
```

如果 connection refused → bridge 没跑，去启动它。
