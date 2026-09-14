# Mira Light 项目阅读报告与最简启动方案

生成日期：2026-06-23

## 1. 阅读范围

本报告基于当前工作区 `mira-light-unified-console-latest-portable-20260616-194411` 的本地源码、启动脚本、README、运行手册和关键 Python/PowerShell 入口整理。重点阅读范围包括：

- 根目录入口：`README.md`、`README_START_HERE.md`、`PACKAGE_GUIDE.md`、`NEW_MAC_SETUP_README.md`
- Windows 启动器：`Start-Mira-Light-Windows-Action-Bridge.ps1`、`Start-Mira-Light-Windows-Full-Realtime.ps1`、`Start-Mira-Light-Voice-Console.ps1`
- 语音主包：`Mira-Light-Voice-Full-Ready/README.md`、`QUICK-START.md`、`NEW-MACHINE-STARTUP-GUIDE.md`
- 动作与语义边界：`scripts/scenes.py`、`scripts/mira_voice_intents.py`、`scripts/stepfun_llm_planner.py`、`scripts/mira_stepfun_realtime_voice_actions.py`
- 实时动作调度：`scripts/mira_realtime_action_orchestrator.py`、`scripts/mira_action_mixer.py`、`scripts/mira_voice_event_adapter.py`
- 本地硬件边界：`tools/mira_light_bridge/bridge_server.py`、`bridge_client.py`、`README.md`
- 视觉/追书链路：`scripts/cam_receiver_service.py`、`scripts/track_target_event_extractor.py`、`scripts/vision_runtime_bridge.py`、`docs/book-follow/*`
- 控制台与演示：`mira-light-unified-director-console/`、`mira-light-director-console/`、`mira-light-shenzhen-console/`
- 相机/渲染/打印：`Chrome-Camera-Anime/`、`camera-render-director-console/`、`tools/camera_render_bridge/`、`tools/printer_bridge/`
- 触摸音频：`portable/support/touch-audio-bridge/`
- Hermes 本地代理：`tools/hermes-agent/`、`tools/hermes-mira-home/`

`tools/hermes-agent/` 是大体量外部工具包，本报告按工具入口、Mira profile 和集成边界阅读，不把其中每个依赖文件逐行展开。

## 2. 一句话结论

这个项目已经不是单一控制台，而是一个 Mira Light Windows/macOS 便携工作区：它把语音理解、可爱但有边界的回复、动作场景库、HTTP action bridge、视觉追踪、导演台、相机渲染打印、触摸音频和 Hermes 本地代理放在同一个包里。真正的运行边界应该保持为：

```text
用户语音/文字
  -> transcript
  -> LLM 语义理解
  -> spoken reply
  -> 本地 scene / trigger / action group 白名单
  -> action bridge
  -> Mira Light 设备或 dry-run runtime
```

模型不能直接输出舵机角度、LED 数据包、TCP 硬件命令、shell 命令或 Python 代码作为 Mira 的身体动作。Mira 的身体表达必须通过本地有界动作组完成。

## 3. 当前项目形态

### 3.1 顶层目录分层

| 路径 | 角色 |
| --- | --- |
| `Mira-Light-Voice-Full-Ready/` | 当前最完整的语音 + 动作 + bridge 可运行包 |
| `Mira-Light-Voice-Cloud-Ready/` | 云端语音路线的旧/轻量包 |
| `Motions/` | 10 个基础动作场景脚本与测试说明 |
| `Motions_Shenzhen/` | 深圳固定协议演示动作与控制脚本 |
| `tools/mira_light_bridge/` | 本地 HTTP bridge，隔离上层意图和下层硬件 |
| `tools/hermes-agent/` | Hermes 本地代理工具本体 |
| `tools/hermes-mira-home/` | Mira 专用 Hermes profile |
| `scripts/` | 视觉、追踪、运行桥、诊断和整合脚本 |
| `mira-light-unified-director-console/` | 综合导演台 |
| `mira-light-director-console/` | 旧导演台和场景展示 |
| `mira-light-shenzhen-console/` | 深圳演示控制台 |
| `Chrome-Camera-Anime/` | Chrome 摄像头拍照、Seedream 渲染、打印链路 |
| `camera-render-director-console/` | 相机渲染启动台 Web/API |
| `portable/support/touch-audio-bridge/` | 触摸事件对应的本机音频 bridge |
| `docs/` | 项目总结、追书、动作混合、验收和运行手册 |
| `runtime/`、`**/runtime/` | 本机运行产物，不应作为源码发布 |

### 3.2 当前项目的四条主线

1. 语音陪伴主线  
   用户说话后，StepFun realtime 或旧语音链路生成 transcript；`stepfun_llm_planner.py` 负责把语义限制到可执行 action manifest；`mira_realtime_action_orchestrator.py` 或后续的 ActionMixer 负责派发动作。

2. 本地动作主线  
   `scenes.py` 定义 Mira 的动作世界，包括场景元数据、舵机校准、基础姿态、LED、动作组和组合动作。`mira_voice_intents.py` 把常见中文口令、情绪表达和 scene/trigger 做本地映射。

3. 视觉/追书主线  
   `cam_receiver_service.py` 接收板端 JPEG；`track_target_event_extractor.py` 做单相机目标事件提取；`vision_runtime_bridge.py` 把视觉事件转为 scene、tracking 或 touch 行为。追书应优先复用 `tabletop_follow` live vision stack，固定动作 demo 只作为 fallback。

4. 控制台/演示主线  
   综合导演台和深圳控制台提供人工操作、固定场景演示、相机侧栏、触摸/语音接入和现场展示能力。它们适合演示和调参，不应该绕过 action bridge 直接控制硬件。

## 4. 核心运行链路

### 4.1 Windows 最完整语音链路

入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -StartActionBridge
```

关键默认值：

| 配置 | 默认值 |
| --- | --- |
| StepAudio realtime model | `stepaudio-2.5-realtime` |
| realtime voice | `wenrounansheng` |
| planner provider | `stepfun` |
| planner model | `step-3.7-flash` |
| action bridge | `http://127.0.0.1:19783` |
| lamp target | `tcp://192.168.0.183:9527` |
| runtime memory | `Mira-Light-Voice-Full-Ready/runtime/mira-live-memory.json` |

运行行为：

```text
Start-Mira-Light-Windows-Full-Realtime.ps1
  -> 可选启动 Start-Mira-Light-Windows-Action-Bridge.ps1
  -> 预检 bridge / lamp endpoint / CPU
  -> 可选 wake_up
  -> mira_stepfun_realtime_voice_actions.py
  -> StepFun realtime audio
  -> planner / semantic action
  -> RealtimeActionOrchestrator
  -> /v1/mira-light/run-scene 或 /trigger
```

适用场景：完整语音交互、需要 Mira 说话并带身体表达。  
依赖条件：StepFun API key、麦克风、扬声器、action bridge、灯网络可达。  
安全开关：`-NoSemanticActions` 只测实时对话，不派发动作；`-ActionBridgeDryRun` 或 `-DryRun` 用于避免真实动作。

### 4.2 本地 action bridge

入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Action-Bridge.ps1 -RuntimeDryRun -Background
```

关键接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | bridge 健康检查 |
| GET | `/v1/mira-light/status` | Mira runtime 状态 |
| GET | `/v1/mira-light/scenes` | 场景列表 |
| GET | `/v1/mira-light/actions` | 动作能力列表 |
| POST | `/v1/mira-light/run-scene` | 执行白名单场景 |
| POST | `/v1/mira-light/trigger` | 触发语义事件 |
| POST | `/v1/mira-light/speak` | 本地 TTS / 语音反馈 |
| POST | `/v1/mira-light/stop` | 停止当前动作 |
| POST | `/v1/mira-light/reset` | 重置 |
| POST | `/v1/mira-light/device/*` | 板端/设备状态上报 |

bridge 是最重要的安全边界：上层只能向它发送已定义 scene/trigger/control 请求；硬件细节由 `MiraLightRuntime` 和本地配置处理。

### 4.3 语音动作库

`Mira-Light-Voice-Full-Ready/scripts/scenes.py` 包含：

- `DEFAULT_SERVO_CALIBRATION`
- `DEFAULT_POSES`
- `SCENE_META`
- `SCENES`
- `comment`、`delay`、`led`、`pose`、`absolute`、`nudge`、`action`、`reset`、`audio`
- `micro_shiver`、`rub_motion`、`pawing_bump`、`celebration_sway`、`fade_to_sleep`

当前动作语义覆盖：

| 场景 | 目的 |
| --- | --- |
| `wake_up` | 醒来/进入互动 |
| `curious_observe` | 好奇观察 |
| `touch_affection` | 被摸/亲近反馈 |
| `cute_probe` | 试探、撒娇式靠近 |
| `daydream` | 发呆/小憩 |
| `standup_reminder` | 站起提醒 |
| `track_target` | 目标跟随 |
| `celebrate` | 庆祝 |
| `farewell` | 告别 |
| `sleep` | 睡觉 |
| 补充场景 | 累、叹气、多人、情绪类表达 |

Mira 的性格应落在这些动作组中表达：可爱、聪明、温暖、略微男孩气、身体反应丰富，但不过度脚本化。

### 4.4 LLM planner

`stepfun_llm_planner.py` 的职责不是自由生成动作，而是：

1. 从 `SCENES`、`SCENE_META`、`INTENT_ACTIONS` 构造 action manifest。
2. 给 LLM 一个只允许输出结构化 plan 的系统提示。
3. 校验 LLM 输出是否落在允许的 action/scene/trigger 内。
4. 对短句和强命令提供本地 shortcut/fallback。
5. 可选使用 StepFun、DeepSeek 或 Hermes provider。

这使得 Mira 的“灵魂”可以更自然地理解用户，但身体动作仍然保持可控。

### 4.5 Action Mixer

`mira_action_mixer.py` 是后续稳定性关键。它把动作拆成多层：

| 层级 | 角色 |
| --- | --- |
| L0 Background | 呼吸、待机、小幅生命感 |
| L1 Tracking | 视觉追踪、目标跟随 |
| L2 Voice | 语音触发的表情动作 |

它要解决旧状态机的几个问题：追踪和语音动作互斥、抢占导致抖动、状态残留、没有统一优先级。后续应该把长时间运行的主循环更多地交给 ActionMixer，而不是让每条链路各自抢舵机。

## 5. 视觉与追书

追书链路的推荐方向不是新造一套控制系统，而是复用已有 `tabletop_follow`：

```text
板端摄像头 JPEG
  -> scripts/cam_receiver_service.py
  -> scripts/track_target_event_extractor.py
  -> scripts/vision_runtime_bridge.py
  -> scripts/mira_light_runtime.py
  -> action bridge / Mira Light
```

关键设计：

- `book_cover_color` 可作为低成本书本检测器。
- `target_mode=tabletop_follow` 表示桌面目标/书本优先。
- `vision_runtime_bridge.py` 内部有 detector allowlist、confidence、persistence、cooldown 和 scene gate。
- 固定脚本 `07_tabletop_follow_demo.py` 只能作为 fallback，不应成为长期主线。

最小验收应看三件事：

1. 板端 JPEG 是否持续进入 captures。
2. extractor 是否产出包含 selected target 的 vision event。
3. runtime bridge 是否只在 gate 通过时触发 `track_target` 或 live tracking 更新。

## 6. 控制台和演示

### 6.1 综合导演台

`mira-light-unified-director-console/` 是现场操作中心，聚合深圳演示、场景控制、语音/动作侧栏和部分相机能力。推荐仍通过根目录启动脚本进入，而不是直接运行内部文件。

### 6.2 深圳控制台

`mira-light-shenzhen-console/` 更偏固定演示和协议稳定性，适合会场表演。它保留了固定视频、音频、动作触发和 offer demo。

### 6.3 旧 Director Console

`mira-light-director-console/` 是旧 Web 场景展示/动作调试台，仍有场景脚本、Web 展示和测试说明。它适合做动作资产核对，但不应成为未来唯一控制入口。

## 7. Camera Anime / 打印链路

`Chrome-Camera-Anime/` 和 `camera-render-director-console/` 负责另一条独立体验链路：

```text
Web 控制台
  -> camera-render-director-console/scripts/console_server.py
  -> tools/camera_render_bridge/bridge_server.py
  -> Chrome-Camera-Anime runtime
  -> 摄像头抓图
  -> Seedream 渲染
  -> printer bridge / CUPS
```

这条链路和 Mira Light 身体动作不是同一个安全面。它主要依赖摄像头权限、Seedream API key、打印机和本机端口。

## 8. 触摸音频 bridge

`portable/support/touch-audio-bridge/` 是触觉系统的音频伴侣，默认端口与 voice action bridge 分开：

| 服务 | 默认端口 |
| --- | --- |
| Touch audio bridge | `9783` |
| Voice action bridge | `19783` |
| Voice lab / debug UI | `19785` |
| Unified console | `8790` / `8791` 等 |
| Camera render bridge | `9795` |
| Printer bridge | `9771` |
| Lamp TCP target | `9527` |

注意：部分 client 默认值仍指向 `9783`，写新调用时要明确区分“触摸音频 bridge”和“动作 bridge”。

## 9. Hermes 集成

Hermes 位于：

```text
tools/hermes-agent/
tools/hermes-mira-home/
```

Mira profile 当前关注：

- 默认模型：`step-3.7-flash`
- provider：`custom`
- base URL：`https://api.stepfun.com/v1`
- memory enabled
- max turns：`40`

在 Mira 项目中，Hermes 应作为“理解/规划/协作工具”，不是硬件直控通道。它产出的动作意图仍要进入本地白名单和 action bridge。

## 10. 最简单模式启动

### 10.1 推荐最简单模式：本地 dry-run action bridge

这个模式最适合第一次确认项目有没有活起来：

- 不需要 API key。
- 不需要麦克风。
- 不需要 StepFun realtime。
- 不需要灯在线。
- 不会触发真实舵机或灯光。
- 能验证 Python 环境、动作库导入、bridge server、HTTP 健康检查和 scene registry。

从项目根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Simplest-Mode.ps1
```

启动成功后检查：

```powershell
Invoke-RestMethod http://127.0.0.1:19783/health
Invoke-RestMethod http://127.0.0.1:19783/v1/mira-light/scenes
```

可选 smoke test，仍然是 dry-run：

```powershell
$body = @{ scene = "wake_up"; payload = @{ source = "manual-simplest-smoke" } } | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:19783/v1/mira-light/run-scene -ContentType "application/json" -Body $body
```

判断成功的最低标准：

- `/health` 返回 `ok: true`。
- `service` 是 `mira-light-bridge`。
- `runtime.dryRun` 是 `true`。
- `/v1/mira-light/scenes` 能列出 scene。

### 10.2 第二简单模式：只聊天，不动身体

macOS 语音包已有明确推荐：

```bash
cd Mira-Light-Voice-Full-Ready
./Start-Chat.command
```

这个模式是云端 Claw 回复 + TTS，不触发灯动作。它适合验证麦克风、语音识别、云端回复和播放链路。

Windows 上若要测 StepFun realtime 对话但不派发动作，可使用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -NoSemanticActions -SkipPreflight
```

该模式仍需要 StepFun realtime API key、麦克风和音频输出。

### 10.3 完整动作模式

当 dry-run bridge、语音、网络和灯都确认后，再进入完整模式：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -StartActionBridge
```

如果需要代理：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -StartActionBridge
```

完整模式前必须确认：

- `http://127.0.0.1:19783/health` 正常。
- `runtime.dryRun` 与预期一致。
- 灯端 `tcp://192.168.0.183:9527` 或配置中的 lamp target 可达。
- 不把模型输出直接当硬件命令执行。

## 11. 当前风险和需要清理的点

1. 本地运行态文件很多  
   当前工作区包含 `.env`、`runtime`、大量日志、缓存、虚拟环境和嵌套 `.git`。这些不应发布到公开仓库。

2. `start_unified_console.py` 有明显拼接痕迹  
   文件中出现多段重复 `#!/usr/bin/env python3`、重复 import 和函数定义，像是多次拼接产生的历史包袱。短期优先使用 PowerShell 或 `.command` 启动器；长期建议重建一个干净 launcher。

3. Windows 与 macOS 启动路径并行  
   macOS 文档主推 `Start-Chat.command` / `Start-Full.command`，Windows 主推 PowerShell realtime/bridge 脚本。后续文档要明确平台，避免用户把 macOS 命令拿到 Windows 执行。

4. Bridge 默认端口需要统一表达  
   touch audio bridge 是 `9783`，voice action bridge 是 `19783`。部分历史 client 默认值容易混淆，新增代码必须显式传 `MIRA_LIGHT_BRIDGE_URL` 或参数。

5. 真实硬件动作不能只靠源码判断  
   只有代码、bridge 健康和 dry-run 都不等于真机动作成功。要声明物理动作可用，必须验证 bridge、设备网络、lamp target 和实际动作反馈。

6. LLM planner 必须保持有界  
   后续无论接 StepFun、DeepSeek 还是 Hermes，都应继续通过 `action_manifest`、`validate_plan`、scene whitelist 和 bridge dispatch，不应扩大成自由工具调用。

## 12. 建议下一步

1. 把 `Start-Mira-Light-Simplest-Mode.ps1` 作为 Windows 第一步固定入口。
2. 给 macOS 保留 `Mira-Light-Voice-Full-Ready/Start-Chat.command` 作为第一步入口。
3. 修复或替换 `start_unified_console.py`，避免现场启动时被历史拼接问题拖住。
4. 为 `19783` action bridge 和 `9783` touch audio bridge 写一页端口边界表，减少后续误接。
5. 让 ActionMixer 成为长时间运行的主调度层，逐步减少旧抢占式状态机的抖动问题。
6. 对每个“可演示路径”保留三档验收：dry-run、bridge connected、device verified。

