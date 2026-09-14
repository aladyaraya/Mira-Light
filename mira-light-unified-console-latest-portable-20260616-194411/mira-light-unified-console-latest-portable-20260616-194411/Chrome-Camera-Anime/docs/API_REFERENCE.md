# Camera Render Bridge API 参考

本文档说明新启动台暴露的本地 HTTP 接口。默认端口如下：

```text
Console Server:        http://127.0.0.1:8795
Camera Render Bridge:  http://127.0.0.1:9795
Printer Bridge:        http://127.0.0.1:9771
```

一般情况下，浏览器前端调用 Console Server 的 `/api/*`，Console Server 再转发到 Camera Render Bridge 的 `/v1/camera-render/*`。

## Console Server API

位置：

```text
camera-render-director-console/scripts/console_server.py
```

默认地址：

```text
http://127.0.0.1:8795/
```

### GET /

返回控制台 HTML。

检查：

```bash
curl -i http://127.0.0.1:8795/
```

### GET /api/health

转发到：

```text
GET http://127.0.0.1:9795/health
```

检查：

```bash
curl -s http://127.0.0.1:8795/api/health | python3 -m json.tool
```

### GET /api/status

转发到：

```text
GET /v1/camera-render/status
```

检查：

```bash
curl -s http://127.0.0.1:8795/api/status | python3 -m json.tool
```

### GET /api/cameras

转发到：

```text
GET /v1/camera-render/cameras
```

检查：

```bash
curl -s http://127.0.0.1:8795/api/cameras | python3 -m json.tool
```

### GET /api/jobs

转发到：

```text
GET /v1/camera-render/jobs
```

检查：

```bash
curl -s http://127.0.0.1:8795/api/jobs | python3 -m json.tool
```

### GET /api/jobs/<job_id>

转发到：

```text
GET /v1/camera-render/jobs/<job_id>
```

检查：

```bash
curl -s http://127.0.0.1:8795/api/jobs/<job_id> | python3 -m json.tool
```

### GET /api/logs

转发到：

```text
GET /v1/camera-render/logs
```

检查：

```bash
curl -s http://127.0.0.1:8795/api/logs | python3 -m json.tool
```

### POST /api/capture-render

转发到：

```text
POST /v1/camera-render/capture-render
```

作用：

```text
手动触发一次真实拍照、Seedream 渲染、可选自动打印。
```

检查：

```bash
curl -s -X POST http://127.0.0.1:8795/api/capture-render \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

注意：这个接口会真实调用摄像头和渲染 API。如果 `CAMERA_RENDER_AUTO_PRINT=1`，成功后会提交打印。

### POST /api/watch/start

转发到：

```text
POST /v1/camera-render/watch/start
```

作用：

```text
启动 chrome_watch_daemon.py 和 worker_daemon.py。
```

检查：

```bash
curl -s -X POST http://127.0.0.1:8795/api/watch/start \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

### POST /api/watch/stop

转发到：

```text
POST /v1/camera-render/watch/stop
```

作用：

```text
停止 bridge 本次启动的 watcher/worker。
```

检查：

```bash
curl -s -X POST http://127.0.0.1:8795/api/watch/stop \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

### POST /api/print-last

转发到：

```text
POST /v1/camera-render/print-last
```

作用：

```text
查找最近一个有 output_path 的 job，把生成图提交给 Printer Bridge。
```

检查：

```bash
curl -s -X POST http://127.0.0.1:8795/api/print-last \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

## Camera Render Bridge API

位置：

```text
tools/camera_render_bridge/bridge_server.py
```

默认地址：

```text
http://127.0.0.1:9795
```

### GET /health

返回分层健康状态。

示例：

```bash
curl -s http://127.0.0.1:9795/health | python3 -m json.tool
```

关键字段：

```text
checks.python          Python 解释器
checks.node            Node 是否存在
checks.swift           Swift 是否存在
checks.imagesnap       imagesnap 是否存在
checks.camera          imagesnap 可见的摄像头列表
checks.api             ARK_API_KEY 是否存在
checks.printerBridge   Printer Bridge /health
checks.printerStatus   Printer Bridge 默认打印机状态
checks.cups            CUPS 队列
checks.watcher         watcher 进程状态
checks.worker          worker 进程状态
checks.outputDir       输出目录
```

`/health` 的整体 `ok` 表示 bridge 服务自己正常响应，不表示所有依赖都成功。要看具体依赖，需要检查 `checks.*.ok`。

### GET /v1/camera-render/status

返回运行配置、watcher/worker 状态、最新 job。

示例：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/status | python3 -m json.tool
```

关键字段：

```text
config.runtimeDir
config.stateDir
config.outputDir
config.manifestPath
config.detectorScript
config.captureScript
config.cameraName
config.cameraBackend
config.autoPrint
config.printMedia
config.printerUrl
config.apiKeyPresent
watcher.running
worker.running
latestJob
```

### GET /v1/camera-render/cameras

调用：

```text
imagesnap -l
```

返回 bridge 能看到的摄像头列表。

示例：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/cameras | python3 -m json.tool
```

### GET /v1/camera-render/jobs

读取：

```text
Chrome-Camera-Anime/.runtime/state/jobs/*/job.json
```

示例：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/jobs | python3 -m json.tool
```

### GET /v1/camera-render/jobs/<job_id>

读取单个 job。

示例：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/jobs/<job_id> | python3 -m json.tool
```

### GET /v1/camera-render/logs

读取：

```text
Chrome-Camera-Anime/.runtime/logs/*.log
```

示例：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/logs | python3 -m json.tool
```

### GET /v1/camera-render/artifacts/<artifact_name>

按文件名在这些目录里查找 artifact：

```text
Chrome-Camera-Anime/outputs/
Chrome-Camera-Anime/.runtime/state/
```

找到后返回文件内容。

示例：

```bash
curl -o artifact.jpg http://127.0.0.1:9795/v1/camera-render/artifacts/example.jpg
```

### POST /v1/camera-render/capture-render

执行：

```text
manual_insta_capture.py
```

Bridge 会显式传入：

```text
--state-dir Chrome-Camera-Anime/.runtime/state
--camera-name "$CAMERA_RENDER_CAMERA_NAME"
--manifest Chrome-Camera-Anime/manifest.json
--landscape-state-path Chrome-Camera-Anime/.runtime/state/pipeline-state.json
--output-dir Chrome-Camera-Anime/outputs/manual-insta
--detector-script Chrome-Camera-Anime/detect_faces.swift
--print-media "$CAMERA_RENDER_PRINT_MEDIA"
```

如果 `CAMERA_RENDER_AUTO_PRINT=0`，bridge 会额外传入：

```text
--no-print
```

示例：

```bash
curl -s -X POST http://127.0.0.1:9795/v1/camera-render/capture-render \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

### POST /v1/camera-render/watch/start

启动：

```text
chrome_watch_daemon.py
worker_daemon.py
```

worker 使用 repo-local 路径：

```text
--state-dir Chrome-Camera-Anime/.runtime/state
--manifest Chrome-Camera-Anime/manifest.json
--landscape-state-path Chrome-Camera-Anime/.runtime/state/pipeline-state.json
--output-dir Chrome-Camera-Anime/outputs
--capture-script Chrome-Camera-Anime/mac-camera-shot
--latest-image-path Chrome-Camera-Anime/.runtime/localmac-camera/latest.jpg
--detector-script Chrome-Camera-Anime/detect_faces.swift
--print-submit-delay-seconds 0
```

示例：

```bash
curl -s -X POST http://127.0.0.1:9795/v1/camera-render/watch/start \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

### POST /v1/camera-render/watch/stop

停止 bridge 管理的 watcher/worker。

示例：

```bash
curl -s -X POST http://127.0.0.1:9795/v1/camera-render/watch/stop \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

### POST /v1/camera-render/print-last

寻找最近有 `output_path` 的 job，并调用：

```text
Chrome-Camera-Anime/print_client.py
```

提交到：

```text
POST http://127.0.0.1:9771/v1/printers/default/print-image
```

示例：

```bash
curl -s -X POST http://127.0.0.1:9795/v1/camera-render/print-last \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

## Printer Bridge 相关接口

Camera Render Bridge 依赖 Printer Bridge 的这些接口：

```text
GET  /health
GET  /v1/printers/default
POST /v1/printers/default/print-image
```

检查 Printer Bridge 是否在线：

```bash
curl -s http://127.0.0.1:9771/health | python3 -m json.tool
```

如果需要访问鉴权接口，token 一般来自：

```text
~/.openclaw-printer-bridge.env
Chrome-Camera-Anime/.runtime/printer-bridge.env
```

检查默认打印机：

```bash
source ~/.openclaw-printer-bridge.env

curl -s http://127.0.0.1:9771/v1/printers/default \
  -H "Authorization: Bearer $OPENCLAW_PRINTER_BRIDGE_TOKEN" \
  | python3 -m json.tool
```

