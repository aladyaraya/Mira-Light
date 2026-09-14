# Mira Light 项目总结与方案更新（2026-06-21）

## 文档目的

这份文档基于当前仓库 `mira-light-unified-console-latest-portable-20260616-194411` 的实际状态，整理项目已经完成的工作、已实现的核心能力，并更新后续推进方案。它替代 `docs/legacy-mira-light/mira-light-booth-scene-capability-implementation-plan.md` 作为当前有效方案文档。

---

## 一、项目概览

Mira Light 是一只具身智能台灯。它不是通用语音助手，而是一个有小灵魂的桌面宠物：能通过板端摄像头看见人、通过触摸传感器感受手、通过四路总线舵机做动作、通过灯光表达情绪，并用温暖的声音和你对话。

核心设计原则（来自 `AGENTS.md`）：

- 把 Mira 当作一个小小的具身宠物灵魂，不是通用助手
- 运行回路保持极简：语音转写 → LLM 理解 → 语音回复 → 已有动作组 → 动作桥接
- 动作只走有边界的本地动作组，不允许模型直接输出原始舵机角度、LED 数据包或 TCP 硬件命令
- Mira 的人格设定：可爱、聪明、温暖、略带小男孩气质、身体表达丰富、不过度脚本化

---

## 二、已完成的工作

### 2.1 仓库整合与便携化

项目经历了一次完整的仓库整合。原本散落在多个仓库里的摄像头渲染、语音运行时、动作脚本、导演控制台、桥接服务，现在被整理成一个可分发的统一便携包 `mira-light-unified-console-latest-portable`。

整合后的五层文件结构：

| 层 | 目录 | 职责 |
|---|---|---|
| 导演控制台层 | `mira-light-director-console/`、`mira-light-unified-director-console/`、`mira-light-shenzhen-console/`、`mira-light-camera-console/` | 浏览器控制台和 console_server |
| 桥接服务层 | `tools/mira_light_bridge/`、`tools/printer_bridge/`、`portable/support/touch-audio-bridge/` | Mira Light bridge、打印桥、摸摸语音桥 |
| 运行时脚本层 | `Mira-Light-Voice-Full-Ready/scripts/`、`Mira-Light-Voice-Cloud-Ready/scripts/` | bridge/runtime/mock lamp/语音/场景/舵机适配 |
| 动作脚本层 | `Motions/`（10 场景）、`Motions_Shenzhen/demo_fixed_protocol_v2/` | 每个场景一个独立启动脚本 |
| 摄像头渲染层 | `Chrome-Camera-Anime/`、`camera-render-director-console/`、`tools/camera_render_bridge/` | 拍照、Seedream 渲染、打印 runtime |

### 2.2 整合里程碑

1. **早期阶段**：建立 10 个主场景的 `SCENE_META` 和 `SCENES` 编排系统，包含 host_line、operatorCue、fallbackHint、cueMode、异步/同步运行、场景日志、中断停止、自动恢复姿态
2. **中期阶段**：从静态 choreography 升级到真实视觉闭环，支持 touch_detected、sigh_detected、voice_tired、multi_person_detected、farewell_detected 等统一事件入口
3. **深圳演示阶段**：按现场视频和 PDF 方案重新编号，生成 7 个固定动作脚本 + 拍照姿态 + 醒来拍照再睡串场，配套 8777 端口 Web 主控台
4. **语音阶段**：实现 Lingzhu/Claw 云端对话、本地 bridge 动作控制、StepAudio 2.5 Realtime 实时语音引擎、step-3.7-flash LLM 语义规划器
5. **便携化阶段**：整合成统一便携包，支持 macOS 一键启动和 Windows PowerShell 启动

---

## 三、已实现的核心能力

### 3.1 动作场景系统

场景编排的真值源在 `scripts/scenes.py`。runtime 支持场景级执行、动态场景上下文、异步/同步运行、中断与停止、自动恢复姿态。

- **10 个主场景**：wake_up、curious_observe、touch_affection、cute_probe、daydream、standup_reminder、track_target、celebrate、farewell、sleep
- **3 个补充场景**：sigh_demo、multi_person_demo、voice_demo_tired
- **深圳固定协议**：7 个固定动作脚本 + 08 拍照姿态 + 09 醒来拍照再睡串场

### 3.2 语音交互系统

三种语音模式，共享同一套 Full 模式安全边界——模型只能产出经过校验的 `scene`、`trigger` 或 `none` 动作：

- **云端对话模式**（Start-Chat）：Lingzhu/Claw 云端对话 + TTS，不触发灯动作
- **完整动作模式**（Start-Full）：云端对话 + TTS + 灯动作，自动启动本地 bridge
- **StepFun 实时语音**：StepAudio 2.5 Realtime WebSocket + step-3.7-flash 语义规划器

语音命令示例：`启动跳舞模式`、`进入睡觉`、`开始追踪目标`、`来个发呆`、`摸一摸`、`提醒我站起来`。情绪短语也能触发身体反应：`我今天好累啊`、`你好可爱`、`我有点困了`。

### 3.3 摄像头 / 渲染 / 打印链路

Chrome-Camera-Anime 是一条完整的拍照→二次元渲染→打印链路：

```text
浏览器控制台 (8795)
  → camera-render-director-console/scripts/console_server.py
  → Camera Render Bridge (9795)
  → Chrome-Camera-Anime runtime
  → imagesnap / 板端摄像头
  → Seedream API
  → Printer Bridge (9771) / CUPS
```

### 3.4 导演控制台矩阵

| 控制台 | 端口 | 职责 | 状态 |
|---|---|---|---|
| 键盘增强版统一控制台 | 8791 | 最新推荐入口，长按连续舵机微调、逐帧录制、轨迹回放 | 推荐 |
| 经典统一导演台 | 8790 | 深圳演示 + 摄像头 + 摸摸系统综合导演台 | 兼容 |
| 深圳演示主控台 | 8777 | 固定动作演示 + Celebration 庆祝页 | 已完成 |
| 摄像头导演台 | 8788 | 板端摄像头画面查看，每 10 秒抓取 JPEG | 已完成 |
| 旧 Director Console | 8765 | bridge/mock lamp 链路，不接真机也能开箱即用 | 已完成 |

### 3.5 桥接与硬件控制

Mira Light bridge (`tools/mira_light_bridge/`) 是动作下发的核心枢纽。提供统一事件入口，上层系统发标准事件而不需要耦合具体 scene 名称。bridge 连接真实灯具（`tcp://192.168.0.183:9527`）或 mock lamp（`http://127.0.0.1:9791`）。

Windows 上端口分离设计：触摸音频桥 `9783`、语音动作桥 `19783`、灯具目标 `tcp://192.168.0.183:9527`。

### 3.6 触摸音频桥

摸摸系统链路：板端触摸检测 → `http://Mac IP:9783/v1/mira-light/trigger` → Mac 播放音频。庆祝页音频链路：iPad/浏览器 → 8777 → 18777 Mac Audio Helper → 蓝牙音箱。

### 3.7 追书 / 桌面目标跟随

基于 `tabletop_follow` live vision stack 实现：

```text
板端摄像头 JPEG
  → cam_receiver_service
  → track_target_event_extractor
  → vision_runtime_bridge
  → mira_light_runtime
  → 舵机和灯光
```

默认不自动启动追书（`MIRA_BOOK_FOLLOW_AUTO_START=0`），需要时在控制台手动开启。

### 3.8 跨平台支持

- **macOS**：双击 `START_HERE.command` → 8791 键盘增强版控制台。支持 imagesnap、afplay/say、node-edge-tts、expect SSH 隧道。iPad 可通过局域网 IP 访问
- **Windows**：PowerShell 启动 `Start-Mira-Light-Windows-Full-Realtime.ps1`。StepFun 实时语音经 SOCKS 代理，支持 DryRun 安全预览

---

## 四、当前架构总览

整个系统由感知层、决策层、动作层、控制台层四部分组成：

- **感知层**：板端摄像头、触摸传感器、麦克风、Mac 摄像头
- **决策层**：视觉事件提取器、StepFun 实时语音、Lingzhu/Claw 云端 → Mira Light Runtime + Bridge（场景白名单校验 → scene/trigger/none → 动作组下发）
- **动作层**：四路总线舵机、LED 灯光、音频播放、拍照/渲染/打印
- **控制台层**：8791 键盘版、8790 导演台、8777 深圳、8788 摄像头、iPad 局域网访问

安全边界设计：所有上层系统（语音、视觉、云端）都不能直接控制硬件。它们只能产出标准事件或经白名单校验的 scene/trigger 动作，由 runtime 和 bridge 统一下发。

---

## 五、场景能力矩阵

| 场景 | 意图 | 代码现状 | 主要缺口 | 优先级 |
|---|---|---|---|---|
| `wake_up` | 有人来后微光亮起、起身、抖毛、伸懒腰、看向前方 | choreography 完整，可直接运行 | 缺会场级唤醒条件，易被边缘路人误唤醒 | P0 |
| `curious_observe` | 先看你，试探靠近，害羞转开，再探出点头 | choreography 可运行，偏固定导演版 | 缺和真实目标方向绑定 | P1 |
| `touch_affection` | 伸手时主动靠近蹭手，手移开后追一下再回位 | 场景和动态触发骨架已存在 | 缺稳定 hand-near/touch side 真实输入源 | P0 |
| `cute_probe` | 呆萌看你、轻点头、左右找角度、胆小探头 | 最成熟的纯动作场景之一 | 缺轻随机化和方向感 | P2 |
| `daydream` | 看远处发呆，或打瞌睡后惊醒 | choreography 已成熟 | 缺自然 idle 触发时机 | P2 |
| `standup_reminder` | 蹭蹭提醒你起来，点头确认，被拒绝后摇头 | 动作已写好，scene 可直接点 | 缺真实"久坐来源" | P2 |
| `track_target` | 灯头和光持续跟着桌上移动的书走 | scene fallback 已有，真实 live tracking 已存在 | 缺指定书本强锁定、多物体稳定仲裁 | P0 |
| `celebrate` | 音乐起、灯光多色变化、上下摇、慢慢减速收尾 | choreography、灯效、音频、舞蹈接近完成态 | 缺真实业务事件来源和音箱策略 | P1 |
| `farewell` | 目送离开方向，两次点头挥手，低头不舍 | scene 较成熟，runtime 支持动态触发 | 缺可靠 departureDirection 事件来源 | P0 |
| `sleep` | 人走远后低头、降臂、伸懒腰、蜷缩回睡姿、灯光渐暗 | 动作接近完成态 | 缺更自然的入睡条件 | P1 |

P0 优先场景：`track_target`、`touch_affection`、`farewell`、`wake_up`——这 4 个场景最直接决定观众会不会相信"Mira 真的感知到了你"。

---

## 六、更新后的项目方案

### 6.1 当前阶段目标

当前阶段的目标不是继续增加更多概念场景，而是把已经存在的场景能力做成：

```text
可触发 → 可联调 → 可重复演示 → 可在嘈杂人多的会场中稳定运行
```

最重要的不是"场景数量"，而是这 3 件事：

- 它真的看见了你——视觉感知闭环稳定
- 它真的会回应你——语音/触摸触发可靠
- 它能稳定演完一整轮——从 wake_up 到 sleep 全链路不崩

### 6.2 会场约束与设计原则

- **主触发优先级**：视觉 > 触摸/近距输入 > 导演台/Claw > 开放式语音
- **开放式麦克风不应作为主链路**——会场嘈杂，语音只作为辅助
- **多人环境必须有"主目标选择"逻辑**——不能谁动跟谁
- **所有关键链路都需要 fallback**——视觉挂了有导演台，语音挂了有固定动作
- **每个演示段落都要能被导演台一键打断**——回到 neutral 或 sleep

### 6.3 四条主链路方案

**A. 基础演示主链路**

调用 `runtime.start_scene()` / `/v1/mira-light/run-scene` / 导演台 `/api/run/<scene>`。适用于：wake_up、curious_observe、cute_probe、daydream、standup_reminder、celebrate、sleep。

**B. 感知触发链路**

调用 `runtime.trigger_event()` / `/v1/mira-light/trigger`。适用于：touch_affection、sigh_demo、voice_demo_tired、multi_person_demo、farewell。上层系统发标准事件而不耦合具体 scene 名称。

**C. 视觉实时闭环链路**

调用 track_target_event_extractor → vision_runtime_bridge → `runtime.apply_tracking_event()`。适用于：track_target、farewell、multi_person_demo、未来的 touch_affection 视觉版。

**D. 音频播报链路**

调用 scene 内 `audio()` 步骤、host_line TTS 播报、celebrate 音乐播放、蓝牙音箱播放。适用于所有需要声音表达的场景。

### 6.4 便携包分发方案

当前便携包已包含完整运行所需的一切。不携带 `.git`、`.omx`、`tmp`、`.venv`、`dist` 等状态目录。

注意：`portable/unified-console.env` 含私有开发配置（板端 IP、SSH 密码、端口默认值），不适合公开分发。

---

## 七、下一步推进建议

### 7.1 P0：感知闭环优先

1. **track_target 追书稳定化**：指定书本强锁定、多桌面物体稳定仲裁、真实物体 identity、overlay 显示。验收：同一本书移动时持续跟住，书停 3-5 秒不丢，桌面有第二个物体时不乱切
2. **touch_affection 真实输入**：建立稳定的 hand-near/touch side 输入源，处理 touch_affection 和 hand_avoid 的优先级。验收：伸手接近时稳定触发，左右手方向合理，无人伸手时不"空蹭"
3. **farewell 方向推断**：建立可靠的 departureDirection 事件来源，区分"短遮挡"和"真离场"。验收：左侧离开目送左边，右侧离开目送右边，短时遮挡不误触发
4. **wake_up 唤醒条件**：加入 engagement zone 和 wake cooldown 的展位级调参。验收：单人进入主展示区稳定触发，边缘经过不乱醒

### 7.2 P1：触发可靠性

- **curious_observe**：把半转和探头方向与真实目标方向绑定
- **celebrate**：接入真实业务事件来源，完善音箱/音量策略
- **sleep**：完善 no-target timeout 状态机，避免视觉抖动导致睡得太早

### 7.3 P2：细节打磨

- **cute_probe**：加入轻随机化和方向感
- **daydream**：实现自然 idle 触发时机
- **standup_reminder**：接入真实"久坐来源"或主持人口播上下文

### 7.4 工程基础设施

- **测试覆盖**：Mira-Light-Voice-Full-Ready 已有 20+ 测试文件，继续补充视觉链路和场景触发的集成测试
- **Hermes Agent**：本地 Hermes agent 已集成，Mira 专属 profile 在 `tools/hermes-mira-home/`，继续完善 SOUL.md 人格配置
- **文档同步**：legacy-mira-light 目录保留旧版设计文档，新文档统一写入 docs/ 对应子目录

---

## 八、总结

Mira Light 已经从分散的实验性仓库，成长为一套可分发、跨平台、有安全边界的具身智能台灯系统。10 个主场景的 choreography 基本完成，语音/视觉/触摸三条感知链路已打通，5 个 Web 控制台覆盖从排练到现场的全流程。

下一步的核心是让 P0 场景的真实感知闭环稳定下来——当 Mira 能可靠地看见你、回应你、送别你时，整个展位系统的说服力就会质变。
