# 板端摄像头推流说明

## 目的

追书功能需要连续 JPEG 帧进入 Mac 端：

```text
RDK X5 / 地瓜板摄像头
  -> HTTP POST image/jpeg
  -> Mac: scripts/cam_receiver_service.py
  -> captures/*.jpg
  -> tabletop detector
```

当前 repo 已有 Mac 端接收器：

```text
scripts/cam_receiver_service.py
```

当前 repo 已从旧 `Mira-Light` 仓库迁入板端发图脚本：

```text
board-camera-streaming/
  README.md
  cam_sender.py
  cam_receiver.py
  cam_preview.py
  rtsp_server.py
```

旧来源路径是：

```text
/Users/Zhuanz/Documents/Github/Mira-Light/Motions_Shenzhen/reference_rdk_x5_board/camera_streaming/cam_sender.py
```

## Mac 端启动接收器

通常不直接启动 receiver，而是通过追书 vision stack：

```bash
MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow \
bash scripts/run_mira_light_live_follow_demo.sh \
  --receiver-port 8000 \
  --runtime-dir ./runtime/book-follow-real
```

这会监听：

```text
http://0.0.0.0:8000/upload
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

输出里应看到：

```text
status=ok frame_count=...
```

## 获取 Mac IP

在 Mac 上：

```bash
ipconfig getifaddr en0
```

如果使用热点或有线网络，接口可能不是 `en0`。可以用：

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

记录一个板端能访问到的 IP，例如：

```text
192.168.0.100
```

## 板端运行方式

把 `board-camera-streaming/cam_sender.py` 放到板端后运行：

```bash
python3 cam_sender.py <Mac-IP> 8000 0
```

例子：

```bash
python3 cam_sender.py 192.168.0.100 8000 0
```

参数含义：

```text
<Mac-IP>  Mac 在同一局域网中的 IP
8000      Mac receiver 端口
0         摄像头编号，通常对应 /dev/video0
```

当前旧脚本默认行为：

```text
resolution: 960x720
fps:        10
quality:    JPEG 85
endpoint:   http://<Mac-IP>:<port>/upload
headers:    X-Seq, X-Timestamp
```

## 当前 repo 目录与推荐板端目录

当前 repo 中的源目录：

```text
board-camera-streaming/
  README.md
  cam_sender.py
  cam_receiver.py
  cam_preview.py
  rtsp_server.py
```

部署到板端时可以放在：

```text
/home/sunrise/Desktop/mira-book-follow-camera/
```

## 验证帧进入 Mac

Mac 端：

```bash
curl http://127.0.0.1:8000/health
```

应看到 `frame_count` 持续增长。

检查保存目录：

```bash
ls -lt runtime/book-follow-real/captures | head
```

## 推荐推流参数

第一版追书不需要高帧率：

```text
fps: 5-10
resolution: 960x720 或 1280x720
JPEG quality: 80-85
```

帧率太高会增加 Mac 端处理压力，反而让 tracking 抖。

## 网络注意事项

- Mac 和板端必须在同一网络，或路由可达。
- Mac 防火墙不能阻止 8000 端口。
- 如果 Mac 开了 VPN，确认板端访问的是局域网 IP，不是 VPN IP。
- 如果现场网络不稳定，优先使用固定热点或直连路由器。

## 后续产品化建议

把板端发图做成 systemd service：

```text
mira-book-follow-camera.service
```

服务应支持环境变量：

```text
MIRA_BOOK_FOLLOW_MAC_HOST=192.168.0.100
MIRA_BOOK_FOLLOW_MAC_PORT=8000
MIRA_BOOK_FOLLOW_CAMERA_INDEX=0
MIRA_BOOK_FOLLOW_FPS=8
MIRA_BOOK_FOLLOW_WIDTH=960
MIRA_BOOK_FOLLOW_HEIGHT=720
```

先不建议自动开机启动，避免现场未准备好时持续占用摄像头。
