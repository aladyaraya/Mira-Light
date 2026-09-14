# Chrome Camera Anime 启动台架构说明

## 目标

Chrome Camera Anime 启动台把旧仓库里分散的拍照、Chrome 监听、anime 渲染、打印脚本，包装成一个本地浏览器控制台。设计思路和 Mira Light 控制台一致：浏览器只负责展示和发起操作，真正接设备和系统能力的逻辑都收敛到本地 bridge。

最终用户看到的是一个地址：

```text
http://127.0.0.1:8795/
```

背后实际有三层本地服务：

```text
浏览器控制台
  -> Console Server, 127.0.0.1:8795
  -> Camera Render Bridge, 127.0.0.1:9795
  -> Chrome-Camera-Anime runtime
  -> Printer Bridge, 127.0.0.1:9771
```

## 文件分层

```text
Start-Camera-Render-Console.command
  一键启动按钮。负责读配置、启动/复用服务、打开浏览器、退出清理。

camera-render-director-console/
  浏览器控制台。前端页面展示健康状态、任务队列、日志和操作按钮。

tools/camera_render_bridge/
  Camera Render Bridge。负责连接摄像头、Chrome watcher、worker、渲染脚本和打印客户端。

Chrome-Camera-Anime/
  旧 runtime 的扁平迁移包。包含拍照、渲染、队列、Chrome 监听、打印客户端。

tools/printer_bridge/
  本地 Printer Bridge 的最小迁移版。负责把打印请求转成 CUPS/lp 命令。
```

## 启动链路

根目录的 `Start-Camera-Render-Console.command` 是唯一推荐入口。它执行的顺序是：

```text
1. 定位仓库根目录和 Chrome-Camera-Anime runtime。
2. 读取 Chrome-Camera-Anime/.env, 如果存在。
3. 读取 ~/.openclaw-printer-bridge.env, 如果存在。
4. 确认 Python 可用。
5. 确认 Printer Bridge 是否已经在线。
6. 如果 Printer Bridge 不在线，就启动 repo-local tools/printer_bridge/start_bridge.sh。
7. 启动或复用 Camera Render Bridge。
8. 启动或复用 Console Server。
9. 默认打开浏览器到 http://127.0.0.1:8795/。
10. 终端保持打开，用于持有本次启动的子进程。
```

退出时：

```text
Ctrl-C 或关闭启动脚本的 Terminal
  -> 停止本次启动的 Console Server
  -> 停止本次启动的 Camera Render Bridge
  -> Camera Render Bridge 停止它自己启动的 watcher/worker
  -> 不杀启动前已经存在的 Printer Bridge
```

## 配置优先级

启动脚本的原则是“环境变量优先，`.env` 补缺”。也就是说，如果你的 shell 环境已经有：

```bash
export ARK_API_KEY="..."
```

那么 `Chrome-Camera-Anime/.env` 里的空 `ARK_API_KEY=` 不会覆盖它。

推荐配置模板：

```bash
cp Chrome-Camera-Anime/.env.example Chrome-Camera-Anime/.env
```

常用变量：

```text
ARK_API_KEY                         Seedream API key
CAMERA_RENDER_CAMERA_NAME           默认 MacBook Air相机
CAMERA_RENDER_CAMERA_BACKEND        默认 imagesnap
CAMERA_RENDER_AUTO_PRINT            默认 1
CAMERA_RENDER_PRINT_MEDIA           默认 4x6.Fullbleed
CAMERA_RENDER_CONSOLE_PORT          默认 8795
CAMERA_RENDER_BRIDGE_PORT           默认 9795
OPENCLAW_PRINTER_BRIDGE_PORT        默认 9771
OPENCLAW_PRINTER_BRIDGE_URL         默认 http://127.0.0.1:9771
CAMERA_RENDER_START_WATCH           默认 1
CAMERA_RENDER_OPEN_BROWSER          默认 1
```

## Console Server

位置：

```text
camera-render-director-console/scripts/console_server.py
```

职责：

```text
1. 静态托管 camera-render-director-console/web/。
2. 把 /api/* 转发到 Camera Render Bridge。
3. 不直接接摄像头、Chrome、Seedream 或打印机。
```

这样前端页面只依赖一个同源地址：

```text
http://127.0.0.1:8795/api/health
```

Console Server 再转发到：

```text
http://127.0.0.1:9795/health
```

## Camera Render Bridge

位置：

```text
tools/camera_render_bridge/bridge_server.py
```

职责：

```text
1. 提供健康检查。
2. 列出摄像头。
3. 启动和停止 Chrome watcher / worker。
4. 调用 manual_insta_capture.py 做手动拍照、渲染、打印。
5. 读取 job 状态和日志。
6. 转交最新生成图给 Printer Bridge。
```

Bridge 默认创建这些运行目录。默认位置在 `~/Documents/Chrome-Camera-Anime/`，避免把拍照、生成图和日志写进 git repo：

```text
~/Documents/Chrome-Camera-Anime/state/
~/Documents/Chrome-Camera-Anime/logs/
~/Documents/Chrome-Camera-Anime/localmac-camera/
~/Documents/Chrome-Camera-Anime/outputs/
```

这些目录属于本地运行产物，不应提交到 git。可以用 `CAMERA_RENDER_DATA_DIR`、`CAMERA_RENDER_OUTPUT_DIR`、`CAMERA_RENDER_STATE_DIR`、`CAMERA_RENDER_LOGS_DIR` 和 `CAMERA_RENDER_CAMERA_CACHE_DIR` 覆盖。

## Runtime

位置：

```text
Chrome-Camera-Anime/
```

核心脚本：

```text
manual_insta_capture.py       手动拍照入口
pipeline.py                   Seedream 渲染流水线
chrome_watch_daemon.py        Chrome 启动监听
worker_daemon.py              capture/generate/print 队列 worker
job_store.py                  job 和 queue 文件管理
print_client.py               Printer Bridge 客户端
detect_faces.swift            macOS Vision 人脸检测
mac-camera-shot               Mac 摄像头抓图 sidecar
manifest.json                 风景图配置
```

为适配新仓库扁平结构，已做路径调整：

```text
pipeline.py 默认 manifest: Chrome-Camera-Anime/manifest.json
启动台默认 data:          ~/Documents/Chrome-Camera-Anime/
启动台默认 output:        ~/Documents/Chrome-Camera-Anime/outputs/
启动台默认 state:         ~/Documents/Chrome-Camera-Anime/state/
启动台默认 logs:          ~/Documents/Chrome-Camera-Anime/logs/
```

Camera Render Bridge 调用 runtime 时会显式传入：

```text
--manifest ./manifest.json
--detector-script ./detect_faces.swift
--camera-name "$CAMERA_RENDER_CAMERA_NAME"
```

## Printer Bridge

位置：

```text
tools/printer_bridge/
```

启动策略：

```text
1. 如果 http://127.0.0.1:9771/health 已经在线，直接复用。
2. 如果不在线，启动 repo-local tools/printer_bridge/start_bridge.sh。
3. repo-local 启动时，token/profile 默认写入 ~/Documents/Chrome-Camera-Anime/。
```

打印调用路径：

```text
Camera Render Bridge
  -> Chrome-Camera-Anime/print_client.py
  -> Printer Bridge /v1/printers/default/print-image
  -> CUPS/lp
```

## 两种触发模式

### 手动触发

控制台按钮：

```text
拍照 + 渲染 + 打印
```

调用路径：

```text
POST /api/capture-render
  -> POST /v1/camera-render/capture-render
  -> manual_insta_capture.py
  -> imagesnap
  -> pipeline.py
  -> Seedream API
  -> print_client.py
```

这是最直观的端到端路径，适合真实链路验收。

### Chrome 监听触发

控制台按钮：

```text
启动监听
暂停监听
```

调用路径：

```text
POST /api/watch/start
  -> chrome_watch_daemon.py
  -> job_store.py 创建 capture job
  -> worker_daemon.py 处理 capture/generate/print
```

默认一键启动会启动 watcher/worker。如果希望只打开控制台，不启动监听，可以用：

```bash
CAMERA_RENDER_START_WATCH=0 ./Start-Camera-Render-Console.command
```

## 数据与状态

运行状态默认保存在：

```text
Chrome-Camera-Anime/.runtime/state/
```

常见文件：

```text
jobs/<job_id>/job.json
jobs/<job_id>/artifacts/
queues/capture/
queues/generate/
queues/print/
pipeline-state.json
watch-state.json
```

输出图默认保存在：

```text
Chrome-Camera-Anime/outputs/
```

日志默认保存在：

```text
Chrome-Camera-Anime/.runtime/logs/
```

控制台的“任务队列”和“日志”区域读取的就是这些本地文件。
