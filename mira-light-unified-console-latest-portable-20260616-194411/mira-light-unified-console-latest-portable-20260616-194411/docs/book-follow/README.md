# Mira Light 追书功能文档包

本目录把“追书”功能从聊天分析落实成仓库内的长期说明文件。

这里的“追书”指：

```text
用户在桌面上移动一本书或书本形目标，
Mira Light 通过板端摄像头看到目标，
灯头进入低头桌面工作姿态，并持续跟随书的位置。
```

## 当前结论

这个功能不需要从零开始。当前仓库已经有大部分底座：

- `scripts/cam_receiver_service.py`：Mac 端 HTTP JPEG 接收器。
- `scripts/track_target_event_extractor.py`：视觉事件提取器，已经支持 `tabletop_follow`。
- `scripts/vision_runtime_bridge.py`：把视觉事件转成 `track_target` 或 live tracking 更新。
- `scripts/mira_light_runtime.py`：把 `control_hint` 映射成舵机与灯光控制。
- `scripts/run_mira_light_vision_stack.sh`：启动 receiver、extractor、bridge。
- `scripts/run_mira_light_live_follow_demo.sh`：真人/目标跟随 demo 启动器。
- `Motions_Shenzhen/demo_fixed_protocol_v2/scripts/07_tabletop_follow_demo.py`：固定动作版追书 fallback。
- `mira-light-director-console/`：旧导演台已经包含 `tabletop_follow` 目标模式开关和视觉状态展示。

当前主要缺口不是算法雏形，而是：

- 没有面向“追书”的一键入口。
- 综合导演台还没有接入 live book follow 控制。
- 板端发图脚本已经迁入 `board-camera-streaming/`，但还没有做成追书专用一键部署包。
- `tabletop_follow` 的舵机映射还需要按桌面低头场景专门调参。
- 旧 `Mira-Light` 仓库里的 tabletop 相关回归测试已经迁入，后续需要保持在当前 repo 中持续通过。

## 文档顺序

建议按下面顺序读：

1. [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)  
   面向开发：架构、缺口、应该补哪些文件。

2. [RUNBOOK.md](./RUNBOOK.md)  
   面向现场/联调：如何 mock 验证、真机验证、看哪些状态文件。

3. [BOARD_CAMERA_STREAMING.md](./BOARD_CAMERA_STREAMING.md)  
   面向板端：摄像头如何把 JPEG 帧推到 Mac。

4. [PRECISION_FEEDBACK_LOOP.md](./PRECISION_FEEDBACK_LOOP.md)  
   面向算法/现场调参：如何针对黄色书封面做快速、稳定、精确反馈链路。

5. [AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md)  
   面向后续实现者或 coding agent：边界、验收标准、不要踩的坑。

6. [MIGRATED_ASSETS.md](./MIGRATED_ASSETS.md)  
   面向维护：本轮从旧仓库迁入了哪些文件、哪些核心脚本保持当前版本。

## 功能分层

推荐把追书分成两层交付：

```text
真实追书：
  board camera -> Mac receiver -> tabletop detector -> vision bridge -> live servo tracking

固定 fallback：
  深圳控制台 scene 07 -> fixed left/center/right choreography
```

这两个能力必须明确区分。视觉栈未工作时，不要把固定动作版包装成“真实追踪”。

## 最小验收口径

第一版可用功能至少应满足：

- mock 模式下能跑通 `tabletop_follow` 事件到 runtime 控制。
- 真机模式下能看到板端摄像头帧进入 Mac 端 captures 目录。
- 移动一本书时，`vision.latest.json` 中出现：

```json
{
  "tracking": {
    "target_mode": "tabletop_follow",
    "target_class": "object",
    "detector": "tabletop_object"
  }
}
```

- `vision.bridge.state.json` 中 action 能进入 `apply_tracking`，或明确说明 blocked 原因。
- 目标丢失或视觉不稳定时，可以退回固定版 `07_tabletop_follow_demo.py`。
