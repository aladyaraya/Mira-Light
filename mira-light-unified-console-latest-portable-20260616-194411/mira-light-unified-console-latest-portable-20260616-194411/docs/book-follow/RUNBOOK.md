# 追书功能运行手册

## 目标

本手册用于联调和现场操作“追书”：

```text
板端摄像头看到桌面上的书 -> Mac 端检测 tabletop object -> Mira Light 实时跟随
```

当前仓库已经有 live vision stack，但追书专用一键入口还待补。补齐前可以用环境变量直接运行。

## 先决条件

Mac 端：

- Python 虚拟环境已准备好。
- `requirements.txt` 中的 `opencv-python`、`numpy` 可用。
- 能访问 Mira Light 所在网络。

真实灯：

- 默认灯地址：

```text
tcp://192.168.31.10:9527
```

板端摄像头：

- 默认板端 SSH：

```text
root@192.168.0.183:22
```

- 摄像头通常是：

```text
/dev/video0
```

## 1. 安装 Mac 端依赖

在 repo 根目录：

```bash
bash scripts/setup_cam_receiver_env.sh
```

如果已有 `.venv`，可直接检查：

```bash
.venv/bin/python - <<'PY'
import cv2
import numpy
print("cv2", cv2.__version__)
print("numpy", numpy.__version__)
PY
```

## 2. Mock 模式验证

不接真灯、不接真实摄像头，先跑通后半段：

```bash
MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow \
bash scripts/run_mira_light_live_follow_demo.sh \
  --mock-device \
  --replay-demo \
  --receiver-port 18000 \
  --runtime-dir ./runtime/book-follow-mock
```

观察输出文件：

```text
runtime/book-follow-mock/vision.latest.json
runtime/book-follow-mock/vision.events.jsonl
runtime/book-follow-mock/vision.bridge.state.json
runtime/book-follow-mock/vision-stack.log
runtime/book-follow-mock/mock-lamp.log
```

快速检查：

```bash
curl http://127.0.0.1:18000/health
tail -f ./runtime/book-follow-mock/vision-stack.log
tail -f ./runtime/book-follow-mock/vision.events.jsonl
```

通过标准：

- `vision.latest.json` 中能看到 `target_mode = tabletop_follow`。
- bridge 没有异常退出。
- mock lamp 日志里能看到 control / LED 请求。

## 3. 真机视觉栈启动

先在 Mac 上启动 receiver + extractor + bridge：

```bash
MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow \
MIRA_LIGHT_BASE_URL=tcp://192.168.31.10:9527 \
bash scripts/run_mira_light_live_follow_demo.sh \
  --receiver-port 8000 \
  --runtime-dir ./runtime/book-follow-real
```

这会监听：

```text
http://Mac-IP:8000/upload
```

然后让板端摄像头推 JPEG 到这个地址。板端推流说明见：

```text
docs/book-follow/BOARD_CAMERA_STREAMING.md
```

## 4. 复用已有 receiver

如果你已经有接收器在跑，并且 captures 目录已有图片，可只挂接后半段：

```bash
MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow \
MIRA_LIGHT_BASE_URL=tcp://192.168.31.10:9527 \
bash scripts/run_mira_light_live_follow_demo.sh \
  --attach-existing-receiver \
  --runtime-dir ./runtime/book-follow-real
```

默认复用：

```text
$HOME/.openclaw/workspace/runtime/captures
```

如需覆盖：

```bash
MIRA_LIGHT_CAPTURES_DIR=/path/to/captures \
MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow \
bash scripts/run_mira_light_vision_stack.sh
```

## 5. 现场操作顺序

1. 确认书本放在摄像头能看到的桌面下半区。
2. 启动 Mac 端 book-follow vision stack。
3. 启动板端摄像头推流。
4. 等待 `vision.latest.json` 出现 tabletop target。
5. 缓慢左右移动书，不要突然大幅遮挡。
6. 如果目标丢失，停住书 1-2 秒等待重新锁定。
7. 如果追踪不稳定，停止真实追书，运行固定版 07 fallback。

## 6. 关键状态文件

最新视觉事件：

```text
runtime/book-follow-real/vision.latest.json
```

事件流：

```text
runtime/book-follow-real/vision.events.jsonl
```

bridge 决策：

```text
runtime/book-follow-real/vision.bridge.state.json
```

vision operator 状态：

```text
runtime/book-follow-real/vision.operator.json
```

## 7. 期望事件

追书模式正常时，事件中应出现：

```json
{
  "tracking": {
    "target_present": true,
    "target_mode": "tabletop_follow",
    "target_class": "object",
    "detector": "tabletop_object",
    "horizontal_zone": "left",
    "confidence": 0.7
  },
  "scene_hint": {
    "name": "track_target"
  }
}
```

如果 bridge 正在应用追踪，`vision.bridge.state.json` 中应该看到类似：

```json
{
  "lastDecision": {
    "candidateScene": "track_target",
    "action": "apply_tracking"
  }
}
```

如果没有 apply tracking，要看：

```text
lastDecision.actionReason
lastDecision.trackingGateReason
lastDecision.sceneGateReason
```

## 8. 常见问题

### 没有帧进入 captures

检查：

```bash
curl http://127.0.0.1:8000/health
```

如果 `frame_count=0`：

- 板端没有推流。
- Mac IP 填错。
- Mac 和板端不在同一网络。
- 防火墙阻止了 8000 端口。

### 能看到帧，但没有 tabletop target

检查：

- 书是否在画面下半区。
- 桌面 ROI 是否需要调整。
- 书和桌面颜色是否太接近。
- 画面是否过暗或反光。

可放宽：

```bash
MIRA_LIGHT_TABLETOP_MIN_EDGE_RATIO=0.035
MIRA_LIGHT_TABLETOP_MIN_AREA_RATIO=0.003
```

### 目标频繁切换

收紧：

```bash
MIRA_LIGHT_TABLETOP_SWITCH_MARGIN=0.45
MIRA_LIGHT_TABLETOP_HOLD_MISSING_FRAMES=8
```

现场也可以减少桌面上的矩形杂物，或给目标书贴高对比标记。

### bridge blocked

看：

```text
vision.bridge.state.json -> lastDecision
```

常见原因：

- confidence 低于 tracking gate。
- runtime 正在执行其他场景。
- tracking update 处于 cooldown。
- detector 不在 allowlist。

### 真实灯不动，但 mock 正常

检查：

- `MIRA_LIGHT_BASE_URL`
- 灯的 TCP 服务是否在线。
- Mac 到灯的网络是否通。
- 当前是否有其他场景正在占用 runtime。

## 9. Fallback

视觉栈不稳定时，使用固定版：

```text
Start-Mira-Light-Latest-Console.command
  -> 场景 07 桌面追踪
```

或在综合导演台中运行同一个固定场景。

对外表达必须诚实：

```text
这是固定演示版，用来说明追书交互节奏；
真实追书需要 live vision stack 正常运行。
```

