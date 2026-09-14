# Mira Light Unified Director Console

这是独立的综合导演台，保留深圳演示主控台能力，并在右侧增加摄像头预览和摸摸系统控制。它不替换原来的：

```text
http://127.0.0.1:8777/  # 深圳演示主控台
http://127.0.0.1:8788/  # 摄像头导演台
```

## 推荐启动方式

从仓库根目录双击：

```text
Start-Mira-Light-Unified-Director-Console.command
```

默认打开：

```text
http://127.0.0.1:8789/
```

## 运行链路

```text
浏览器综合导演台
  -> mira-light-unified-director-console/shenzhen_console.py
  -> scene_registry.json
  -> Motions_Shenzhen/demo_fixed_protocol_v2/scripts
  -> mira-light-camera-console/camera_console.py
  -> SSH root@192.168.0.183:22
```

## 新增接口

```text
GET  /api/camera/latest
GET  /api/camera/image/<filename>
POST /api/camera/watch/start
POST /api/camera/watch/stop
POST /api/camera/capture

GET  /api/touch/status
POST /api/touch/start
POST /api/touch/stop
POST /api/touch/disable-autostart
POST /api/touch/enable-autostart
```

摄像头默认每 10 秒从板端 `/dev/video0` 抓取一帧，图片保存到：

```text
~/Documents/Mira-Light-Camera-Console/frames/
```

摸摸系统控制对应板端 `mira-touch.service`。

## 环境变量

```text
MIRA_UNIFIED_CONSOLE_HOST=127.0.0.1
MIRA_UNIFIED_CONSOLE_PORT=8789
MIRA_UNIFIED_OPEN_BROWSER=1
MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS=10
MIRA_UNIFIED_CAMERA_START_WATCH=1
MIRA_CAMERA_CONSOLE_DATA_DIR=$HOME/Documents/Mira-Light-Camera-Console

MIRA_SHENZHEN_BOARD_HOST=192.168.0.183
MIRA_SHENZHEN_BOARD_PORT=22
MIRA_SHENZHEN_BOARD_USER=root
MIRA_SHENZHEN_BOARD_PASSWORD=<board-password>
MIRA_SHENZHEN_SCRIPTS_DIR=/path/to/demo_fixed_protocol_v2/scripts
```

## 安全边界

- 打开控制台、读取状态、查看摄像头不会执行深圳动作。
- “预览命令”只在本机生成 shell，不通过 SSH 执行动作。
- “执行真机”、舵机手动控制、救场动作和摸摸系统按钮会通过 SSH 访问板端。
- `POST /api/touch/start` 会重新启动触摸触发系统，现场未确认安全时不要测试这个按钮。

## 本地 smoke test

不自动打开浏览器，使用临时端口：

```bash
MIRA_UNIFIED_OPEN_BROWSER=0 \
MIRA_UNIFIED_CONSOLE_PORT=18789 \
MIRA_UNIFIED_CAMERA_START_WATCH=0 \
./Start-Mira-Light-Unified-Director-Console.command
```

验证接口：

```bash
curl -s http://127.0.0.1:18789/api/scenes | python3 -m json.tool
curl -s http://127.0.0.1:18789/api/state | python3 -m json.tool
curl -s http://127.0.0.1:18789/api/camera/latest | python3 -m json.tool
curl -s http://127.0.0.1:18789/api/touch/status | python3 -m json.tool
```
