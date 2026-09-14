# Chrome Camera Anime 排错手册

这份文档按症状排查。建议先看控制台顶部健康状态卡，再用对应命令定位。

## 快速总检

从仓库根目录运行：

```bash
bash -n Start-Camera-Render-Console.command
python3 -m json.tool Chrome-Camera-Anime/manifest.json
swift -frontend -parse Chrome-Camera-Anime/detect_faces.swift
node --check camera-render-director-console/web/app.js
```

安全启动：

```bash
CAMERA_RENDER_OPEN_BROWSER=0 \
CAMERA_RENDER_START_WATCH=0 \
CAMERA_RENDER_CONSOLE_PORT=18996 \
CAMERA_RENDER_BRIDGE_PORT=19996 \
./Start-Camera-Render-Console.command
```

健康检查：

```bash
curl -s http://127.0.0.1:19996/health | python3 -m json.tool
curl -s http://127.0.0.1:18996/api/health | python3 -m json.tool
```

## 1. 浏览器显示 127.0.0.1 拒绝连接

常见原因：

```text
Console Server 没有启动
端口不是 8795
启动脚本已经退出
端口被占用
```

检查启动脚本终端是否有：

```text
Browser console: OK
```

检查端口：

```bash
lsof -nP -iTCP:8795 -sTCP:LISTEN
```

检查控制台服务：

```bash
curl -i http://127.0.0.1:8795/
```

如果你用临时端口启动，浏览器地址也要换成对应端口。例如：

```bash
CAMERA_RENDER_CONSOLE_PORT=18996 ./Start-Camera-Render-Console.command
```

浏览器应打开：

```text
http://127.0.0.1:18996/
```

## 2. 页面打开了，但全是错误或空状态

这通常是 Console Server 在线，但 Camera Render Bridge 不在线。

检查：

```bash
curl -s http://127.0.0.1:8795/api/health | python3 -m json.tool
curl -s http://127.0.0.1:9795/health | python3 -m json.tool
```

如果 `9795` 失败：

```bash
lsof -nP -iTCP:9795 -sTCP:LISTEN
```

如果端口被其他程序占用，换端口启动：

```bash
CAMERA_RENDER_BRIDGE_PORT=19995 \
CAMERA_RENDER_CONSOLE_PORT=18995 \
./Start-Camera-Render-Console.command
```

## 3. Seedream API 显示 missing

控制台 `Seedream API` 卡片标红时，说明运行 Camera Render Bridge 的环境里没有 `ARK_API_KEY`。

检查当前 shell：

```bash
echo "$ARK_API_KEY"
```

如果你从 Finder 双击启动，Finder 不一定继承你 shell 里设置的环境变量。解决方式有两个：

方式一：从已经有 key 的 Terminal 启动：

```bash
./Start-Camera-Render-Console.command
```

方式二：写入本仓库 `.env`：

```bash
cp Chrome-Camera-Anime/.env.example Chrome-Camera-Anime/.env
```

然后填：

```bash
ARK_API_KEY="你的真实 key"
```

再次启动后检查：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/status \
  | python3 -m json.tool
```

看：

```text
config.apiKeyPresent: true
```

## 4. Camera 标红

先检查 `imagesnap`：

```bash
which imagesnap
imagesnap -l
```

如果 `imagesnap` 不存在：

```bash
brew install imagesnap
```

如果 `imagesnap -l` 没有 `MacBook Air相机`，把实际名字写入环境变量：

```bash
CAMERA_RENDER_CAMERA_NAME="实际摄像头名字" ./Start-Camera-Render-Console.command
```

或写入：

```text
Chrome-Camera-Anime/.env
```

```bash
CAMERA_RENDER_CAMERA_NAME="实际摄像头名字"
```

## 5. 摄像头权限失败

症状可能是：

```text
imagesnap 能列出设备，但拍照失败
manual_insta_capture.py 报摄像头无法打开
控制台点击拍照后 job 失败
```

macOS 需要给启动脚本所在的程序摄像头权限。通常是 Terminal 或 iTerm：

```text
System Settings
  -> Privacy & Security
  -> Camera
  -> enable Terminal 或 iTerm
```

改完权限后，重新打开 Terminal，再启动控制台。

只测试摄像头：

```bash
cd Chrome-Camera-Anime

python3 manual_insta_capture.py \
  --capture-only \
  --camera-name "MacBook Air相机" \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift
```

## 6. 人脸检测失败

症状：

```text
No face detected
No primary subject detected
detect_faces.swift 失败
```

先确认 Swift 脚本语法：

```bash
swift -frontend -parse Chrome-Camera-Anime/detect_faces.swift
```

再确认照片质量：

```text
人脸不要太小
不要逆光
不要遮挡脸部
尽量正对摄像头
画面中主体不要离边缘太近
```

如果只想验证 Seedream，不想被现场摄像头质量卡住，先用已有图片：

```bash
cd Chrome-Camera-Anime

python3 pipeline.py \
  --portrait-image /path/to/source.jpg \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift \
  --output-dir ./outputs/from-file \
  --style-slug anime
```

## 7. Printer Bridge 标红

检查 Printer Bridge：

```bash
curl -s http://127.0.0.1:9771/health | python3 -m json.tool
```

如果没有响应，启动脚本正常会自动启动 repo-local Printer Bridge。手动启动：

```bash
tools/printer_bridge/start_bridge.sh
```

如果端口被占用：

```bash
lsof -nP -iTCP:9771 -sTCP:LISTEN
```

换端口：

```bash
OPENCLAW_PRINTER_BRIDGE_PORT=19771 ./Start-Camera-Render-Console.command
```

## 8. CUPS 标红或没有打印队列

检查：

```bash
lpstat -e
lpstat -d
```

如果没有队列，需要先在 macOS 系统里添加打印机。

如果默认队列不对，可以在系统打印设置里调整默认打印机，或检查：

```text
tools/printer_bridge/bridge_config.json
```

Printer Bridge 会尝试从 CUPS 队列里选择可用队列。

## 9. 打印提交失败

先确认渲染成功并有 output：

```bash
find Chrome-Camera-Anime/outputs -type f
```

或查看 job：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/jobs | python3 -m json.tool
```

如果 `output_path` 存在，再检查 token：

```bash
ls -l ~/.openclaw-printer-bridge.env
ls -l Chrome-Camera-Anime/.runtime/printer-bridge.env
```

检查默认打印机接口：

```bash
source ~/.openclaw-printer-bridge.env

curl -s http://127.0.0.1:9771/v1/printers/default \
  -H "Authorization: Bearer $OPENCLAW_PRINTER_BRIDGE_TOKEN" \
  | python3 -m json.tool
```

如果只是想先跑通渲染，不要打印：

```bash
CAMERA_RENDER_AUTO_PRINT=0 ./Start-Camera-Render-Console.command
```

## 10. watcher/worker 没有运行

检查状态：

```bash
curl -s http://127.0.0.1:9795/v1/camera-render/status | python3 -m json.tool
```

看：

```text
watcher.running
worker.running
```

手动启动：

```bash
curl -s -X POST http://127.0.0.1:9795/v1/camera-render/watch/start \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

手动停止：

```bash
curl -s -X POST http://127.0.0.1:9795/v1/camera-render/watch/stop \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

查看日志：

```bash
tail -n 120 Chrome-Camera-Anime/.runtime/logs/chrome-watch.log
tail -n 120 Chrome-Camera-Anime/.runtime/logs/worker.log
```

## 11. 启动后立刻生成任务

默认：

```text
CAMERA_RENDER_START_WATCH=1
```

如果 Chrome 已经处于某种触发状态，watcher 可能创建任务。调试时建议：

```bash
CAMERA_RENDER_START_WATCH=0 ./Start-Camera-Render-Console.command
```

等控制台打开后，再手动点击“启动监听”。

## 12. 清理坏状态

如果队列里有半截 job 或日志太多，可以清理本地运行产物：

```bash
rm -rf Chrome-Camera-Anime/.runtime
rm -rf Chrome-Camera-Anime/outputs
```

然后重新启动：

```bash
./Start-Camera-Render-Console.command
```

注意：这会删除生成图、job 历史和日志。

## 13. 报错时应收集的信息

如果需要继续定位，建议收集：

```bash
git status --short
bash -n Start-Camera-Render-Console.command
imagesnap -l
lpstat -e
lpstat -d
curl -s http://127.0.0.1:9795/health | python3 -m json.tool
curl -s http://127.0.0.1:9795/v1/camera-render/status | python3 -m json.tool
curl -s http://127.0.0.1:9795/v1/camera-render/jobs | python3 -m json.tool
curl -s http://127.0.0.1:9795/v1/camera-render/logs | python3 -m json.tool
```

如果 `9795` 不在线，把启动脚本 Terminal 里的完整输出也保留下来。

