# Chrome Camera Anime 迁移包与启动台

这个目录是从旧仓库 `Javis-Hackathon` 迁移过来的 Chrome/Camera/Anime runtime 文件集合。它现在既保留原始脚本用法，也已经被接入新仓库根目录的浏览器启动台：

```text
../Start-Camera-Render-Console.command
```

源目录：

```text
/Users/thomasjwang/Documents/GitHub/Javis-Hackathon/exports/macbook-camera-print-deploy-pack-20260329/source/current/openclaw-chrome-camera-anime/
```

目标目录：

```text
/Users/thomasjwang/Documents/GitHub/Mira-and-Mira-Light-New/Chrome-Camera-Anime/
```

## 当前状态

本目录目前是一个扁平 runtime 包：

```text
Chrome-Camera-Anime/
  manual_insta_capture.py
  pipeline.py
  digua_remote_render_pipeline.py
  mac-camera-shot
  mac-camera-common.sh
  detect_faces.swift
  job_store.py
  worker_daemon.py
  chrome_watch_daemon.py
  print_client.py
  xiaomi_home_print.py
  fig1.png ... fig4.png
  manifest.json
  tests...
```

因为用户要求“单独文件夹、扁平结构”，这里没有保留原来的 `runtime/`、`macos-camera/`、`landscapes/`、`tests/` 子目录。当前新仓库已经补齐启动台外壳：

```text
../Start-Camera-Render-Console.command
tools/camera_render_bridge/
camera-render-director-console/
```

`pipeline.py`、`job_store.py`、`print_client.py` 也已经适配当前扁平路径：默认 manifest 是 `./manifest.json`。通过启动台运行时，输出、任务状态和日志默认写入 `~/Documents/Chrome-Camera-Anime/`，不写入 repo。

## 主要链路

这个包里有三条核心链路。

第一条是 Mac 摄像头手动拍照、anime 渲染、可选打印：

```text
manual_insta_capture.py
  -> imagesnap / Insta360 / Mac 摄像头
  -> pipeline.py
  -> detect_faces.swift
  -> Seedream image generation API
  -> print_client.py, 可选
```

第二条是 Chrome 触发的后台队列链路：

```text
chrome_watch_daemon.py
  -> job_store.py
  -> worker_daemon.py
  -> pipeline.py
  -> print_client.py 或 xiaomi_home_print.py
```

第三条是地瓜板远程摄像头链路：

```text
digua_remote_render_pipeline.py
  -> ssh 到远程 Linux/地瓜板
  -> ffmpeg 从 /dev/video0 抓一帧
  -> base64 回传到本机
  -> rokid_render_pipeline.py / pipeline.py
  -> Seedream image generation API
```

## 一键启动台用法

如果是在一台新 Mac 上第一次运行，先看：

```text
NEW_COMPUTER_README.md
```

从新仓库根目录双击或运行：

```bash
./Start-Camera-Render-Console.command
```

启动顺序是：

```text
读取 Chrome-Camera-Anime/.env, 如果存在
  -> 确认或启动 Printer Bridge :9771
  -> 启动 Camera Render Bridge :9795
  -> 启动浏览器 Console Server :8795
  -> 自动打开 http://127.0.0.1:8795/
```

控制台第一屏就是运行台，包含：

```text
健康状态：Python、Node、Swift、imagesnap、摄像头、ARK_API_KEY、Printer Bridge、CUPS、Watcher、Worker
操作按钮：刷新、启动监听、暂停监听、拍照 + 渲染 + 打印、打印最新图
状态视图：运行配置、最新 job、任务队列、bridge 日志
```

默认真实链路：

```text
MacBook Air相机
  -> imagesnap
  -> manual_insta_capture.py / worker_daemon.py
  -> Seedream API, 读取 ARK_API_KEY
  -> Printer Bridge / CUPS, 自动打印
```

`ARK_API_KEY` 可以来自你已经设置好的系统环境，不必须写入 `.env`。如果你想给这个仓库固定配置，复制：

```bash
cp Chrome-Camera-Anime/.env.example Chrome-Camera-Anime/.env
```

`.env.example` 内容：

```bash
ARK_API_KEY=
CAMERA_RENDER_CAMERA_NAME="MacBook Air相机"
CAMERA_RENDER_CAMERA_BACKEND=imagesnap
CAMERA_RENDER_AUTO_PRINT=1
CAMERA_RENDER_PRINT_MEDIA=4x6.Fullbleed
CAMERA_RENDER_DATA_DIR="$HOME/Documents/Chrome-Camera-Anime"
CAMERA_RENDER_OUTPUT_DIR="$HOME/Documents/Chrome-Camera-Anime/outputs"
CAMERA_RENDER_STATE_DIR="$HOME/Documents/Chrome-Camera-Anime/state"
CAMERA_RENDER_LOGS_DIR="$HOME/Documents/Chrome-Camera-Anime/logs"
CAMERA_RENDER_CAMERA_CACHE_DIR="$HOME/Documents/Chrome-Camera-Anime/localmac-camera"
CAMERA_RENDER_CONSOLE_PORT=8795
CAMERA_RENDER_BRIDGE_PORT=9795
OPENCLAW_PRINTER_BRIDGE_PORT=9771
```

启动台默认把运行产物放在 `~/Documents/Chrome-Camera-Anime/`，包括任务状态、拍照中间图、日志和最终输出图。repo 中的 `Chrome-Camera-Anime/` 只保留脚本、manifest、背景图等代码资源。

如果 `.env` 里的 `ARK_API_KEY` 还是空，但你的 shell 环境里已经有真实 key，启动脚本会保留原有环境 key，不会被空值覆盖。

更详细的分册文档：

```text
docs/README.md
docs/RUNBOOK.md
docs/ARCHITECTURE.md
docs/API_REFERENCE.md
docs/TROUBLESHOOTING.md
```

退出方式：

```text
关闭启动脚本打开的 Terminal 窗口，或按 Ctrl-C。
```

退出时会停止本次启动的 Camera Render Bridge、Console Server、Chrome watcher/worker；如果 Printer Bridge 是启动前已经在线的服务，不会被杀掉。

测试启动脚本但不自动弹浏览器时，可以临时加：

```bash
CAMERA_RENDER_OPEN_BROWSER=0 CAMERA_RENDER_START_WATCH=0 ./Start-Camera-Render-Console.command
```

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `manual_insta_capture.py` | 手动一键拍照入口。默认找 `Insta360 Link 2 Pro`，拍照后可直接渲染并打印。 |
| `pipeline.py` | 核心渲染流水线。负责选风景图、检测人脸、构造 Seedream 请求、下载生成图、写 metadata。 |
| `digua_remote_render_pipeline.py` | 远程摄像头抓图入口。通过 SSH 调远端 `ffmpeg` 抓图，再走 anime 渲染。 |
| `mac-camera-shot` | Mac 本地摄像头抓图脚本。默认可用 `imagesnap`，也支持 OpenClaw camera node fallback。 |
| `mac-camera-common.sh` | `mac-camera-shot` 的共享 shell helper。 |
| `detect_faces.swift` | macOS Vision 人脸检测脚本，被 `pipeline.py` 用来确认主体。 |
| `job_store.py` | 本地 job 状态与队列文件管理。 |
| `worker_daemon.py` | 后台 worker，处理 capture/generate/print 队列。 |
| `chrome_watch_daemon.py` | 监听 Chrome 启动边缘并创建 job。 |
| `print_client.py` | 调用本地 printer bridge，默认地址 `http://127.0.0.1:9771`。 |
| `xiaomi_home_print.py` | 通过 Android/Xiaomi Home 链路提交打印。 |
| `print_status_poller.py` | 轮询 CUPS 打印状态并更新 job。 |
| `rokid_watch_daemon.py` | Rokid 侧导入和渲染链路守护进程。 |
| `rokid_watch_control.py` | Rokid watch daemon 控制工具。 |
| `rokid_render_pipeline.py` | Rokid 输入图像到 anime 输出的渲染入口。 |
| `mac_camera_render_pipeline.py` | Mac camera 到渲染链路的包装入口。 |
| `mira_sync.py` / `mira_sync_daemon.py` | 同步类辅助脚本。 |
| `expression_monitor.swift` | 常驻表情/情绪采样脚本。 |
| `expression_monitor_control.py` | 控制 expression monitor 的启停。 |
| `install_launchd.py` | 旧包里的 launchd 安装辅助脚本。 |
| `wireless_adb_setup.py` | Android 无线 ADB 设置辅助脚本。 |
| `openclaw.hook-gateway.json` | OpenClaw hook gateway 配置样例。 |
| `openclaw.loopback.json` | OpenClaw loopback 配置样例。 |
| `rokid-watch-config.json` | Rokid watch 链路配置。注意里面仍有旧路径占位符。 |
| `manifest.json` | 风景图 manifest。因为本迁移包是扁平结构，里面的 `fig1.png` 等路径和当前目录匹配。 |
| `fig1.png` ... `fig4.png` | 内置风景参考图。 |
| `test_*.py` | 从旧包复制来的单元测试和守护逻辑测试。 |
| `UPSTREAM_RUNTIME_README.md` | 旧 runtime README 原文备份。 |

## 依赖

基础依赖：

```text
python3
node
swift
```

Mac 摄像头推荐安装：

```bash
brew install imagesnap
```

真实 anime 渲染需要火山方舟 Seedream API key：

```bash
export ARK_API_KEY="..."
```

远程地瓜板摄像头链路还需要：

```text
ssh
ffmpeg, 在远端设备上
expect, 仅当使用密码 SSH 时需要
```

打印链路可选。如果要使用 `print_client.py`，需要先启动 printer bridge，并保证这些文件存在：

```text
~/.openclaw-printer-bridge/profile.json
~/.openclaw-printer-bridge.env
```

如果通过新仓库的启动台运行，根目录已经带有最小 Printer Bridge：

```text
../tools/printer_bridge/
```

启动脚本会优先复用 `http://127.0.0.1:9771` 上已经在线的 Printer Bridge；如果没有在线服务，则用 repo-local bridge 启动一个新的本地服务，并把 token/profile 写入 `~/Documents/Chrome-Camera-Anime/`。

## 使用方式一：列出可用摄像头

进入目录：

```bash
cd /Users/thomasjwang/Documents/GitHub/Mira-and-Mira-Light-New/Chrome-Camera-Anime
```

列出 `imagesnap` 能看到的摄像头：

```bash
python3 manual_insta_capture.py --list-cameras
```

如果报 `imagesnap not found in PATH`，先安装：

```bash
brew install imagesnap
```

## 使用方式二：只拍照，不渲染

控制台默认摄像头名是：

```text
MacBook Air相机
```

原始 `manual_insta_capture.py` 脚本保留旧默认值：

```text
Insta360 Link 2 Pro
```

只拍照：

```bash
python3 manual_insta_capture.py \
  --capture-only \
  --camera-name "Insta360 Link 2 Pro" \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift
```

如果使用 MacBook 内置摄像头，可以先通过 `--list-cameras` 找到名字，然后替换 `--camera-name`：

```bash
python3 manual_insta_capture.py \
  --capture-only \
  --camera-name "MacBook Air相机" \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift
```

输出会写到 job 目录，默认在：

```text
Chrome-Camera-Anime/.runtime/state/jobs/<job_id>/artifacts/
```

## 使用方式三：拍照并渲染，但不打印

这是最常用的真实渲染命令：

```bash
ARK_API_KEY="..." \
python3 manual_insta_capture.py \
  --no-print \
  --camera-name "Insta360 Link 2 Pro" \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift \
  --output-dir "$HOME/Downloads/chrome-camera-anime/manual-insta"
```

关键参数：

```text
--no-print
```

表示只保存生成图，不提交打印。输出图默认类似：

```text
~/Downloads/chrome-camera-anime/manual-insta/seedream-chrome-camera-insta-manual-YYYYMMDD-HHMMSS.jpeg
```

旁边会有 metadata：

```text
*.metadata.json
```

## 使用方式四：用已有照片直接渲染

如果不想现场打开摄像头，可以拿一张已有图片做输入：

```bash
ARK_API_KEY="..." \
python3 pipeline.py \
  --portrait-image /path/to/source.jpg \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift \
  --output-dir "$HOME/Downloads/chrome-camera-anime/from-file" \
  --style-slug anime
```

这条命令会跳过摄像头，直接进入：

```text
已有照片
  -> 人脸/主体检测
  -> 选择风景图
  -> Seedream 渲染
  -> 下载生成图
```

## 使用方式五：Mac camera sidecar 抓图

直接调用扁平目录里的抓图脚本：

```bash
MAC_CAMERA_BACKEND=imagesnap ./mac-camera-shot
```

它会把最新图写到：

```text
~/.openclaw/workspace/.cache/localmac-camera/latest.jpg
~/.openclaw/workspace/.cache/localmac-camera/latest.json
```

`MAC_CAMERA_BACKEND` 可选：

```text
imagesnap  # 本地 imagesnap，推荐默认
openclaw   # OpenClaw camera node
auto       # 优先 OpenClaw，失败后 fallback
```

## 使用方式六：地瓜板远程摄像头抓图并渲染

如果摄像头在远程 Linux/地瓜板上，例如：

```text
host: 192.168.0.183
device: /dev/video0
```

可以运行：

```bash
DIGUA_SSH_PASSWORD="..." \
ARK_API_KEY="..." \
python3 digua_remote_render_pipeline.py \
  --host 192.168.0.183 \
  --user root \
  --bind-address 192.168.0.164 \
  --remote-device /dev/video0 \
  --input-format mjpeg \
  --video-size 1280x720 \
  --capture-dir "$HOME/Downloads/chrome-camera-anime/digua-remote/source" \
  --output-dir "$HOME/Downloads/chrome-camera-anime/digua-remote"
```

只测试抓图，不调用渲染 API：

```bash
DIGUA_SSH_PASSWORD="..." \
python3 digua_remote_render_pipeline.py \
  --host 192.168.0.183 \
  --user root \
  --capture-only \
  --capture-dir "$HOME/Downloads/chrome-camera-anime/digua-remote/source"
```

## 使用方式七：Chrome 监听队列

旧包支持“打开 Chrome 触发拍照任务”的模式。它通常需要两个常驻进程：

```bash
python3 chrome_watch_daemon.py
python3 worker_daemon.py
```

这条链路依赖本地 job 队列。通过启动台运行时，队列默认在：

```text
~/Documents/Chrome-Camera-Anime/state/jobs/
~/Documents/Chrome-Camera-Anime/state/queues/
```

在新启动台里，这两个进程由 Camera Render Bridge 管理。控制台里的“启动监听 / 暂停监听”按钮会调用 bridge 的 watch 接口，不需要手动开两个 daemon。

## 路径注意事项

因为这个目录是扁平结构，已适配的默认路径和旧包不同：

```text
pipeline.py 默认找 ./manifest.json
启动台默认 data:   ~/Documents/Chrome-Camera-Anime/
启动台默认 output: ~/Documents/Chrome-Camera-Anime/outputs/
启动台默认 state:  ~/Documents/Chrome-Camera-Anime/state/
启动台默认 logs:   ~/Documents/Chrome-Camera-Anime/logs/
```

启动台会对 bridge 调用显式传入：

```text
--manifest ./manifest.json
--detector-script ./detect_faces.swift
--camera-name "$CAMERA_RENDER_CAMERA_NAME"
```

`rokid-watch-config.json` 中也保留了旧包路径和 `__HOME__` 占位符。使用 Rokid watch 链路前，需要把里面的路径改成当前目录，例如：

```text
/Users/thomasjwang/Documents/GitHub/Mira-and-Mira-Light-New/Chrome-Camera-Anime/manifest.json
/Users/thomasjwang/Documents/GitHub/Mira-and-Mira-Light-New/Chrome-Camera-Anime/detect_faces.swift
```

## 常见问题

### 1. 真实摄像头没有启动怎么办？

这和 Mira Light 的真实灯类似，不应该阻塞控制台启动。控制台会正常打开，健康检查里的摄像头项会标红。首版没有 mock renderer；你可以先用已有照片走 `pipeline.py --portrait-image`，或等摄像头权限/设备就绪后再点击手动触发。

### 2. 没有 `ARK_API_KEY` 能不能用？

控制台和 Camera Render Bridge 可以启动，健康检查会显示 `Seedream API` 缺失；可以做摄像头列表、状态检查、Chrome watcher 启停。真实 Seedream 渲染不能运行。没有 key 时建议先使用：

```bash
python3 manual_insta_capture.py --capture-only
```

如果你的 shell 环境里已经有 `ARK_API_KEY`，启动脚本会继承它，不需要再写入 `.env`。

### 3. 摄像头权限失败怎么办？

macOS 需要给运行脚本的程序摄像头权限。通常是 Terminal、iTerm 或你从中启动脚本的 App：

```text
System Settings
  -> Privacy & Security
  -> Camera
  -> enable Terminal/iTerm
```

### 4. `swift detect_faces.swift` 失败怎么办？

确认系统有 Swift：

```bash
swift --version
```

如果人脸检测失败，`pipeline.py` 可能会报：

```text
No primary subject detected in captured photo
```

可以换一张主体更清晰、正对镜头、光照更好的照片。

### 5. 打印失败怎么办？

打印不是渲染必需项。先用：

```bash
--no-print
```

跑通拍照和渲染。打印链路需要另一个 printer bridge，默认是：

```text
http://127.0.0.1:9771
```

## 启动台相关文件

```text
Start-Camera-Render-Console.command
tools/camera_render_bridge/bridge_server.py
camera-render-director-console/scripts/console_server.py
camera-render-director-console/web/
```

实际链路：

```text
浏览器控制台
  -> camera-render-director-console/scripts/console_server.py
  -> Camera Render Bridge: http://127.0.0.1:9795
  -> Chrome-Camera-Anime runtime
  -> imagesnap / Mac 摄像头
  -> Seedream API
  -> Printer Bridge / CUPS
```

Camera Render Bridge 提供这些接口：

```text
GET  /health
GET  /v1/camera-render/status
GET  /v1/camera-render/cameras
GET  /v1/camera-render/jobs
GET  /v1/camera-render/logs
POST /v1/camera-render/capture-render
POST /v1/camera-render/watch/start
POST /v1/camera-render/watch/stop
POST /v1/camera-render/watch/mode
POST /v1/camera-render/print-last
```

Chrome 监听有两种模式：

```text
launch          只在 Chrome 从未运行到启动时触发
launch_or_focus Chrome 启动，或从别的应用切回 Chrome 时触发
```

默认是 `launch_or_focus`。可以在 `Chrome-Camera-Anime/.env` 里设置：

```bash
CAMERA_RENDER_CHROME_TRIGGER_MODE=launch_or_focus
```

也可以在浏览器控制台点击“切回 Chrome 触发：开/关”切换。切换会保存到：

```text
~/Documents/Chrome-Camera-Anime/state/chrome-trigger-mode.json
```

切换时会自动重启 watcher，worker 和已经生成的任务不会被清空。

控制台服务只做静态文件服务和 API proxy：

```text
http://127.0.0.1:8795/api/*
  -> http://127.0.0.1:9795/v1/camera-render/*
```
