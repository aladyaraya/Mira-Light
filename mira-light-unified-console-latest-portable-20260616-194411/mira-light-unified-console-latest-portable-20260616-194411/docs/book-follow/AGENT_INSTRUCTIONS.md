# 追书功能后续实现指示

本文是给后续实现者和 coding agent 的约束文件。修改追书功能时优先遵守这里的设计边界。

## 任务定义

“追书”不是普通固定动作场景。它是一个 hybrid feature：

```text
进入/退出：可以是固定 choreography
核心过程：必须由 live vision tracking 驱动
失败兜底：允许固定版 07 fallback，但必须诚实标注
```

## 关键原则

- 真实追书必须使用 `tabletop_follow`，不要复用默认 `person_follow` 叙事。
- 任何 UI 都必须区分 `live follow` 和 `fixed fallback`。
- 不要绕过 `MiraLightRuntime` 直接裸写舵机，除非是已经存在的深圳固定脚本路径。
- 第一验证路径必须是 mock 或 dry-run，再接真灯。
- 现场控制界面必须显示 blocked reason，不能只显示“失败”。
- 目标锁定要保守，宁可短暂保持旧目标，也不要在多个矩形物之间快速跳。

## 推荐实现任务

### Task 1：启动器

新增：

```text
Start-Mira-Light-Book-Follow.command
Start-Mira-Light-Book-Follow-Mock.command
```

验收：

- `bash -n` 通过。
- mock 启动后生成 `runtime/book-follow-mock/vision-stack.log`。
- real 启动前不要求真实硬件在线，但错误提示要清楚。

### Task 2：综合导演台 book-follow 面板

修改：

```text
mira-light-unified-director-console/shenzhen_console.py
mira-light-unified-director-console/web/index.html
mira-light-unified-director-console/web/app.js
mira-light-unified-director-console/web/styles.css
```

必须展示：

```text
running/stopped
target_mode
target_class
detector
confidence
horizontal_zone
object_lock_strength
selected reason
bridge action
bridge blocked reason
```

必须提供：

```text
start live book follow
stop live book follow
switch tabletop mode
run fixed 07 fallback
emergency stop / neutral
```

### Task 3：tabletop 专用 runtime 映射

当前已经在：

```text
scripts/mira_light_runtime.py
```

实现第一版。后续修改要求：

- 按 `tracking.target_mode == "tabletop_follow"` 分支。
- 保留现有人物跟随逻辑。
- 桌面追书默认低头、功能白光、小幅平滑 yaw。
- 限制更新频率和最大单步变化。
- 对目标丢失调用现有清理路径，不要残留 tracking active。
- 保留 `book_cover_color` / `tabletop_book` 这条黄色书封面专用路径。

### Task 4：板端发图包

当前已经迁入：

```text
board-camera-streaming/
```

来源：

```text
/Users/Zhuanz/Documents/Github/Mira-Light/Motions_Shenzhen/reference_rdk_x5_board/camera_streaming/cam_sender.py
```

要求：

- 不引入新依赖；沿用 OpenCV。
- 支持 host、port、camera index、fps、resolution。
- README 写清楚如何在板端运行。
- 后续可以补 `start_book_follow_camera_sender.sh`，但不要破坏现有临时调试脚本。

### Task 5：测试

迁移或补齐：

```text
tests/test_track_target_event_extractor.py
tests/test_vision_runtime_bridge.py
tests/test_console_server.py
```

至少覆盖：

- synthetic book-like rectangle -> `tabletop_object`
- `tracking.target_mode == tabletop_follow`
- `tracking.target_class == object`
- `scene_hint.name == track_target`
- bridge 对 tabletop event 调 `apply_tracking`
- console 持久化 `targetMode = tabletop_follow`

## 验收命令建议

语法检查：

```bash
bash -n scripts/run_mira_light_live_follow_demo.sh
bash -n scripts/run_mira_light_vision_stack.sh
```

Python 测试：

```bash
.venv/bin/python -m unittest discover -s tests
```

Mock smoke：

```bash
MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow \
bash scripts/run_mira_light_live_follow_demo.sh \
  --mock-device \
  --replay-demo \
  --receiver-port 18000 \
  --runtime-dir ./runtime/book-follow-mock
```

如果 smoke 需要人工中断，最终报告必须说明运行时长和观察到的状态文件。

## Done Definition

追书功能可以称为第一版完成，必须同时满足：

- 有一键启动或综合导演台启动入口。
- mock 链路可重复跑通。
- 真机链路至少能验证帧进入 Mac receiver。
- `vision.latest.json` 能稳定出现 tabletop object。
- runtime 能收到并处理 `apply_tracking_event()`。
- UI 或日志能解释 blocked 原因。
- 固定版 07 fallback 仍然可用。
- 文档说明 live/fallback 差异。

## 风险提示

- `tabletop_object` 当前是 heuristic，不等于可靠书本识别。
- 复杂桌面会误锁矩形杂物。
- 真实灯追踪过快会显得抖，宁可慢一点。
- 低头姿态必须现场确认安全，避免碰到书、手或桌面。
- 如果要强叙事“它真的认出这本书”，应先加 ArUco / AprilTag 或高对比书本标记。
