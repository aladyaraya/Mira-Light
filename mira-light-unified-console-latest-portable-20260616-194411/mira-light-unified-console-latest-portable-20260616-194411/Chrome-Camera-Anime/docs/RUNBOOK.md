# Chrome Camera Anime 启动与运行手册

这份手册按实际操作顺序写，适合第一次运行、现场演示、问题复现和真实链路验收。

## 0. 前置条件

系统要求：

```text
macOS
python3
node
swift
imagesnap
CUPS/lp, 如果要打印
```

安装 `imagesnap`：

```bash
brew install imagesnap
```

确认摄像头列表：

```bash
imagesnap -l
```

正常情况下应该能看到类似：

```text
=> MacBook Air相机
```

确认 Swift 可用：

```bash
swift --version
```

确认 Node 可用：

```bash
node --version
```

确认打印队列：

```bash
lpstat -e
lpstat -d
```

## 1. 准备 API key

如果你的 `ARK_API_KEY` 已经在环境里，直接启动即可：

```bash
echo "$ARK_API_KEY"
```

如果希望写入本仓库本地配置：

```bash
cp Chrome-Camera-Anime/.env.example Chrome-Camera-Anime/.env
```

然后编辑：

```text
Chrome-Camera-Anime/.env
```

最小真实配置：

```bash
ARK_API_KEY="你的真实 key"
CAMERA_RENDER_CAMERA_NAME="MacBook Air相机"
CAMERA_RENDER_CAMERA_BACKEND=imagesnap
CAMERA_RENDER_AUTO_PRINT=1
```

注意：启动脚本会优先保留已有环境变量，`.env` 只补环境里缺失的值。

## 2. 一键启动

从 Finder 双击：

```text
Start-Camera-Render-Console.command
```

或从终端运行：

```bash
./Start-Camera-Render-Console.command
```

预期终端输出：

```text
== Chrome Camera Anime Console ==
Printer Bridge: already running at http://127.0.0.1:9771
Camera Render Bridge: OK
Browser console: OK
Leave this Terminal window open while using the console.
```

默认会打开：

```text
http://127.0.0.1:8795/
```

使用控制台期间保持这个 Terminal 窗口打开。

## 3. 安全启动测试

如果只是验证控制台能不能启动，不想弹浏览器，也不想启动 Chrome watcher：

```bash
CAMERA_RENDER_OPEN_BROWSER=0 \
CAMERA_RENDER_START_WATCH=0 \
CAMERA_RENDER_CONSOLE_PORT=18996 \
CAMERA_RENDER_BRIDGE_PORT=19996 \
./Start-Camera-Render-Console.command
```

然后检查：

```bash
curl -s http://127.0.0.1:19996/health | python3 -m json.tool
curl -s http://127.0.0.1:18996/api/health | python3 -m json.tool
```

退出：

```text
Ctrl-C
```

退出后确认服务已停：

```bash
curl http://127.0.0.1:18996/
curl http://127.0.0.1:19996/health
```

这两个请求应该连接失败。

## 4. 控制台第一屏怎么看

控制台顶部是健康状态卡：

```text
Camera          摄像头列表是否可见
Seedream API    ARK_API_KEY 是否存在
Printer Bridge  Printer Bridge /health 是否在线
CUPS            本机打印队列是否可见
Watcher         chrome_watch_daemon.py 是否运行
Worker          worker_daemon.py 是否运行
Swift           detect_faces.swift 依赖是否可用
imagesnap       摄像头抓图工具是否可用
```

如果某个卡片标红，不代表控制台坏了，只代表对应真实依赖不可用。

运行配置区域会显示：

```text
Camera
Auto Print
Print Media
Printer URL
API Key
Runtime
Output
```

任务队列区域显示最近 job，日志区域显示 bridge 启动的 watcher、worker、manual capture 日志。

## 5. 只测试拍照

先进入 runtime 目录：

```bash
cd Chrome-Camera-Anime
```

列出摄像头：

```bash
python3 manual_insta_capture.py --list-cameras
```

只拍照，不调用 Seedream，不打印：

```bash
python3 manual_insta_capture.py \
  --capture-only \
  --camera-name "MacBook Air相机" \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift
```

成功后，job artifact 会写入：

```text
Chrome-Camera-Anime/.runtime/state/jobs/<job_id>/artifacts/
```

如果这里失败，先不要测渲染。优先处理摄像头权限、摄像头名称或 `imagesnap`。

## 6. 用已有图片测试渲染

如果暂时不想打开摄像头，可以用已有图片验证 Seedream 链路：

```bash
cd Chrome-Camera-Anime

python3 pipeline.py \
  --portrait-image /path/to/source.jpg \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift \
  --output-dir ./outputs/from-file \
  --style-slug anime
```

这会验证：

```text
ARK_API_KEY
Seedream API
风景图 manifest
detect_faces.swift
输出图下载
metadata 写入
```

不会验证：

```text
imagesnap 摄像头抓图
Printer Bridge
CUPS 打印
```

## 7. 手动完整链路

从控制台点击：

```text
拍照 + 渲染 + 打印
```

这会调用：

```text
manual_insta_capture.py
  -> imagesnap 拍照
  -> detect_faces.swift 检测主体
  -> pipeline.py 调 Seedream
  -> print_client.py 提交 Printer Bridge
```

如果 `CAMERA_RENDER_AUTO_PRINT=1`，渲染成功后会自动打印。如果只想渲染不打印：

```bash
CAMERA_RENDER_AUTO_PRINT=0 ./Start-Camera-Render-Console.command
```

或在 `.env` 里写：

```bash
CAMERA_RENDER_AUTO_PRINT=0
```

## 8. Chrome 监听模式

默认一键启动时：

```text
CAMERA_RENDER_START_WATCH=1
```

Camera Render Bridge 会启动：

```text
chrome_watch_daemon.py
worker_daemon.py
```

控制台按钮：

```text
启动监听
暂停监听
```

分别对应：

```text
POST /v1/camera-render/watch/start
POST /v1/camera-render/watch/stop
```

如果你不想启动时自动监听 Chrome：

```bash
CAMERA_RENDER_START_WATCH=0 ./Start-Camera-Render-Console.command
```

这适合调试控制台 UI、健康检查、打印状态，不会因为 Chrome 已经打开而意外创建任务。

## 9. 端口说明

默认端口：

```text
8795  Browser Console Server
9795  Camera Render Bridge
9771  Printer Bridge
```

临时换端口：

```bash
CAMERA_RENDER_CONSOLE_PORT=18995 \
CAMERA_RENDER_BRIDGE_PORT=19995 \
./Start-Camera-Render-Console.command
```

如果 `9771` 已被其他服务占用，但不是 Printer Bridge，启动脚本会报错。要换 Printer Bridge 端口：

```bash
OPENCLAW_PRINTER_BRIDGE_PORT=19771 \
./Start-Camera-Render-Console.command
```

## 10. 停止和清理

正常停止：

```text
在启动脚本的 Terminal 里按 Ctrl-C
```

停止效果：

```text
Console Server 停止
Camera Render Bridge 停止
watcher/worker 停止
启动前已经存在的 Printer Bridge 保持运行
```

清理本地运行产物：

```bash
rm -rf Chrome-Camera-Anime/.runtime
rm -rf Chrome-Camera-Anime/outputs
```

清理不会影响源码，但会删除 job、日志和生成图。

## 11. 推荐验收顺序

第一次真实验收建议按这个顺序：

```text
1. bash -n Start-Camera-Render-Console.command
2. imagesnap -l
3. python3 manual_insta_capture.py --list-cameras
4. manual_insta_capture.py --capture-only
5. pipeline.py --portrait-image /path/to/source.jpg
6. CAMERA_RENDER_START_WATCH=0 启动控制台
7. 打开 /api/health 确认健康状态
8. 控制台点击“拍照 + 渲染 + 打印”
9. 查看任务队列和日志
10. 确认 CUPS 里出现打印任务
```

