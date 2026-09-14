# 旧 Mira-Light 可复用资产迁移清单

本清单记录本轮为了追书 / `tabletop_follow` 功能，从旧仓库迁入当前 repo 的内容。

旧仓库来源：

```text
/Users/Zhuanz/Documents/Github/Mira-Light
```

## 已迁入

### 功能设计与运行文档

```text
docs/feature/
docs/mira-light-live-follow-demo-runbook.md
docs/legacy-mira-light/
```

其中与追书最直接相关的是：

```text
docs/feature/30-tabletop-target-mode-first-pass.md
docs/feature/31-tabletop-target-locking-and-selection-policy.md
docs/feature/29-vision-target-stability-and-bridge-observability-upgrade.md
docs/feature/23-vision-runtime-scene-5-minute-integration-checklist.md
docs/feature/25-on-site-troubleshooting-decision-tree.md
```

`docs/legacy-mira-light/` 额外收纳了旧仓库中可复用的 Markdown / YAML / HTML 文档，用于后续查证旧版场景、OpenClaw、视觉、ESP32、交付和调试设计。二进制 PDF、归档包、`.DS_Store` 和临时运行文件没有迁入。

### 板端摄像头脚本

```text
board-camera-streaming/
  README.md
  cam_preview.py
  cam_receiver.py
  cam_sender.py
  rtsp_server.py
```

这些脚本用于 RDK X5 / 摄像头 HTTP 发图、Mac 端临时收图和 RTSP 调试。追书真实链路优先使用当前 repo 的 `scripts/cam_receiver_service.py` 作为 Mac 端接收器，板端可复用 `board-camera-streaming/cam_sender.py`。

### 回归测试与 fixtures

```text
tests/test_*.py
fixtures/
runtime/vision-demo-captures/
```

`runtime/vision-demo-captures/` 是一组稳定回放素材，已在 `.gitignore` 中单独放开；其他 runtime 产物仍然忽略。

这些文件用于验证：

- `tabletop_follow` 能产生 `tabletop_object`。
- `vision_runtime_bridge` 能把 tracking event 转成 runtime tracking 控制。
- console 能持久化 `targetMode = tabletop_follow`。
- replay/demo captures 可用于离线视觉链路验证。
- bus servo、mock device、signal contract、offline rehearsal、scene trace、memory、local model 等旧能力仍有回归测试锚点。

### 旧 Director Console 静态资源与动作脚本

```text
web/
Motions/
```

当前根目录 `scripts/console_server.py` 默认读取 repo root 下的 `web/` 和 `Motions/`。旧仓库中的这两组资源已经迁入，避免只迁服务脚本但缺静态页面或场景脚本。

## 未覆盖或保留现状

以下核心脚本当前 repo 已经具备，和旧仓库版本一致或已是当前主线版本，本轮没有覆盖重写：

```text
scripts/track_target_event_extractor.py
scripts/vision_runtime_bridge.py
scripts/run_mira_light_vision_stack.sh
scripts/run_mira_light_live_follow_demo.sh
scripts/console_server.py
mock_mira_light_device.py
tools/mira_light_bridge/bridge_server.py
```

`Javis-Hackathon` 中和本功能最接近的是摄像头、渲染、打印和 OpenClaw 联调经验；当前 repo 已经有 `Chrome-Camera-Anime/`、`tools/camera_render_bridge/`、打印 bridge 和综合控制台相关内容，所以本轮没有把 Javis 文件成批复制进追书链路。

## 后续仍需实现

- 新增追书一键启动器：`Start-Mira-Light-Book-Follow.command` 和 mock 版本。
- 在综合导演台中加入 live book follow 面板。
- 为 `board-camera-streaming/` 补追书专用板端启动脚本或 systemd 模板。
