# 追书功能实现指南

## 目标

实现一个可操作、可验证、可 fallback 的 Mira Light 追书功能：

```text
桌面上的书移动 -> Mira 看见并锁定目标 -> 灯头低头跟随 -> 书停下时灯也停住
```

这不是“再写一个固定动作场景”。固定动作只作为 fallback。真正的追书应该使用当前仓库已有的 live vision stack。

## 已有能力

### 1. 固定动作 fallback

当前深圳演示场景 07 已经是固定版桌面追踪：

```text
Motions_Shenzhen/demo_fixed_protocol_v2/scripts/07_tabletop_follow_demo.py
```

它负责稳定演示“左 -> 中 -> 右 -> 停 -> 回到桌面位”的叙事节奏，但不是实时视觉闭环。

### 2. Mac 端视觉接收与事件提取

当前实时视觉链路已经存在：

```text
scripts/cam_receiver_service.py
  -> 接收板端或回放器 POST 的 JPEG
  -> 保存到 captures 目录

scripts/track_target_event_extractor.py
  -> 轮询 captures 目录
  -> 在 tabletop_follow 模式下检测桌面 ROI 内的 object
  -> 输出 vision.latest.json / vision.events.jsonl
```

`track_target_event_extractor.py` 已经有这些 tabletop 能力：

- `--default-target-mode tabletop_follow`
- `--tabletop-roi-*`
- `--tabletop-min-area-ratio`
- `--tabletop-min-edge-ratio`
- `--tabletop-min-motion-ratio`
- `--tabletop-hold-missing-frames`
- `--tabletop-switch-margin`
- `object_lock_strength`
- `edge_ratio / motion_ratio / aspect_ratio / fill_ratio`

### 3. 视觉事件到运动控制

```text
scripts/vision_runtime_bridge.py
  -> 读取 vision.latest.json
  -> 对 tabletop_follow 目标优先走 track_target
  -> 调用 MiraLightRuntime.apply_tracking_event()

scripts/mira_light_runtime.py
  -> 根据 control_hint 计算 servo1~servo4
  -> 下发 control 和 LED 命令
```

### 4. 控制台现状

旧 Director Console 已经有比较完整的 vision operator 状态：

```text
mira-light-director-console/scripts/console_server.py
mira-light-director-console/web/app.js
mira-light-director-console/web/index.html
```

它支持写入：

```text
runtime/live-vision/vision.operator.json
```

并能切换：

```text
targetMode = person_follow
targetMode = tabletop_follow
```

综合导演台目前主要集成深圳场景、摄像头预览和摸摸系统，还没有正式接 live book follow 控制：

```text
mira-light-unified-director-console/
```

## 推荐补充顺序

### P0：新增追书启动入口

新增两个启动器：

```text
Start-Mira-Light-Book-Follow.command
Start-Mira-Light-Book-Follow-Mock.command
```

真实模式应设置：

```bash
export MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow
export MIRA_LIGHT_BASE_URL="${MIRA_LIGHT_BASE_URL:-tcp://192.168.31.10:9527}"

bash scripts/run_mira_light_live_follow_demo.sh \
  --receiver-port "${MIRA_LIGHT_VISION_PORT:-8000}" \
  --runtime-dir ./runtime/book-follow-real
```

Mock 模式应设置：

```bash
export MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow

bash scripts/run_mira_light_live_follow_demo.sh \
  --mock-device \
  --replay-demo \
  --receiver-port 18000 \
  --runtime-dir ./runtime/book-follow-mock
```

### P1：补板端摄像头推流说明或脚本包

已从旧 `Mira-Light` 仓库迁入板端发图脚本：

```text
board-camera-streaming/
  README.md
  cam_sender.py
  cam_receiver.py
  cam_preview.py
  rtsp_server.py
```

旧来源保留为追溯信息：

```text
/Users/Zhuanz/Documents/Github/Mira-Light/Motions_Shenzhen/reference_rdk_x5_board/camera_streaming/
```

当前还应补一个追书专用启动脚本：

```text
board-camera-streaming/start_book_follow_camera_sender.sh
```

板端操作说明已经写入：

```text
docs/book-follow/BOARD_CAMERA_STREAMING.md
```

### P2：综合导演台接入 live book follow

建议改：

```text
mira-light-unified-director-console/shenzhen_console.py
mira-light-unified-director-console/web/index.html
mira-light-unified-director-console/web/app.js
mira-light-unified-director-console/web/styles.css
```

新增接口：

```text
GET  /api/book-follow/status
POST /api/book-follow/start
POST /api/book-follow/stop
POST /api/book-follow/mode/tabletop
GET  /api/book-follow/latest-event
GET  /api/book-follow/bridge-state
```

新增 UI：

```text
开始真实追书
停止真实追书
切到桌面目标
运行固定版 07 fallback
强停归位
```

状态显示：

```text
target_mode
target_class
detector
confidence
horizontal_zone
object_lock_strength
selected_target.reason
bridge action
blocked reason
latest frame path
```

### P3：tabletop 专用舵机映射

当前已经在：

```text
scripts/mira_light_runtime.py
```

中按 `tracking.target_mode == "tabletop_follow"` 分支，加入桌面低头映射。黄色书封面检测命中时会走：

```text
trackingProfile: tabletop_book
detector: book_cover_color
```

桌面追书映射原则：

- `servo1`：主要左右跟随书，幅度小，平滑。
- `servo2`：保持低头桌面高度，不频繁上下跳。
- `servo3`：保持中等前探，避免大幅伸缩。
- `servo4`：只做小角度灯头补偿，让光落在书附近。
- LED：使用功能性白光，不使用情绪暖光或彩灯。
- yaw/pitch 带 deadband，避免 1-2 像素抖动直接传到舵机。
- 每次更新限制最大单步变化，避免灯头突然跳。

需要现场校准的参数：

```text
tabletop_center_pose
tabletop_left_pose
tabletop_right_pose
min_safe_tabletop_height
max_safe_yaw_delta
max_update_frequency
tracking_smoothing_alpha
```

### P4：保持旧仓库 tabletop 测试可运行

已从旧仓库迁入下列测试：

```text
tests/test_track_target_event_extractor.py
tests/test_vision_runtime_bridge.py
tests/test_console_server.py
```

这些测试应持续覆盖：

- book-like synthetic frame 能产生 `tabletop_object`。
- event 中 `tracking.target_mode == tabletop_follow`。
- event 中 `tracking.target_class == object`。
- `scene_hint.name == track_target`。
- bridge 对 tabletop target 优先 `apply_tracking`，不走 `wake_up`。
- console 能持久化 `targetMode = tabletop_follow`。

### P5：可选增强：指定书本识别

当前 tabletop detector 是启发式：

```text
桌面 ROI + 边缘密度 + 前景运动 + 矩形形状
```

如果现场桌面杂物多，建议给书增加识别标记：

- 第一优先：ArUco / AprilTag marker。
- 第二优先：高对比彩色贴纸。
- 第三优先：固定封面颜色或固定 ROI。

实现策略：

```text
marker detector 命中 -> 直接生成 tabletop_object，置信度高
marker detector 未命中 -> fallback 到现有 tabletop heuristic
```

## 不要做的事

- 不要把固定动作版 `07_tabletop_follow_demo.py` 说成真实追踪。
- 不要让追书直接控制原始舵机绕过 runtime 的 safety / state。
- 不要在视觉不稳定时快速切换多个目标。
- 不要默认启动真实硬件控制，mock 和 dry-run 应该是第一验证路径。
- 不要在综合导演台里只放“开始追书”按钮而不显示 blocked reason，否则现场排障会变成猜。

## 推荐最终运行形态

```text
Start-Mira-Light-Unified-Director-Console.command
  -> 综合导演台 http://127.0.0.1:8789/
  -> 点击“开始真实追书”
  -> 自动启动或复用 book-follow vision stack
  -> UI 显示锁定目标和 bridge decision
  -> 视觉失败时可运行固定版 07 fallback
```
