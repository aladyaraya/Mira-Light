# Chrome Camera Anime 新电脑使用说明

这份文档只说明 Chrome 摄像头拍照、Seedream 渲染、打印启动台。它假设整个仓库已经复制到新 Mac：

```text
Mira-and-Mira-Light-New/
```

启动入口在仓库根目录：

```text
Start-Camera-Render-Console.command
```

## 1. 这个启动台会启动什么

双击启动后，链路是：

```text
Start-Camera-Render-Console.command
  -> tools/printer_bridge/start_bridge.sh
  -> tools/camera_render_bridge/bridge_server.py
  -> camera-render-director-console/scripts/console_server.py
  -> http://127.0.0.1:8795/
```

实际拍照渲染链路是：

```text
浏览器控制台
  -> Camera Render Bridge :9795
  -> Chrome-Camera-Anime runtime
  -> imagesnap / Mac 摄像头
  -> detect_faces.swift
  -> Seedream API
  -> 保存生成图
  -> 可选提交打印
```

## 2. 新电脑首次准备

安装依赖：

```bash
xcode-select --install
brew install imagesnap
```

检查：

```bash
python3 --version
node --version
swift --version
imagesnap -l
```

`imagesnap -l` 应该列出至少一个摄像头。

## 3. 创建本机配置

在仓库根目录运行：

```bash
cp Chrome-Camera-Anime/.env.example Chrome-Camera-Anime/.env
```

然后编辑：

```text
Chrome-Camera-Anime/.env
```

最重要的是这几项：

```bash
ARK_API_KEY=
CAMERA_RENDER_CAMERA_NAME="MacBook Air相机"
CAMERA_RENDER_AUTO_PRINT=0
CAMERA_RENDER_CHROME_TRIGGER_MODE=launch
```

建议新电脑首次测试时这样设置：

```bash
CAMERA_RENDER_AUTO_PRINT=0
CAMERA_RENDER_CHROME_TRIGGER_MODE=launch
```

这样不会因为打印机没连而反复报错，也不会因为切回 Chrome 就连续触发新任务。

## 4. API key 怎么放

真实渲染必须有 `ARK_API_KEY`。

方式一：写进 `.env`：

```bash
ARK_API_KEY=你的真实key
```

方式二：写进本机私有文件：

```bash
mkdir -p "$HOME/.openclaw-chrome-camera-anime"
printf '%s\n' '你的真实 ARK_API_KEY' > "$HOME/.openclaw-chrome-camera-anime/ark_api_key.txt"
chmod 600 "$HOME/.openclaw-chrome-camera-anime/ark_api_key.txt"
```

不要提交 `.env`，不要截图暴露 key。

## 5. 摄像头怎么确认

运行：

```bash
imagesnap -l
```

如果输出类似：

```text
=> MacBook Air相机
```

那么 `.env` 可以保持：

```bash
CAMERA_RENDER_CAMERA_NAME="MacBook Air相机"
```

如果新电脑显示的是别的名字，就把 `.env` 里的 `CAMERA_RENDER_CAMERA_NAME` 改成完全一致的名字。

第一次拍照时，macOS 会要求摄像头权限。请允许启动脚本所在的 Terminal/iTerm/Python 访问摄像头。

## 6. 首次启动

在 Finder 双击：

```text
Start-Camera-Render-Console.command
```

或在仓库根目录运行：

```bash
./Start-Camera-Render-Console.command
```

浏览器会打开：

```text
http://127.0.0.1:8795/
```

如果不想自动打开浏览器：

```bash
CAMERA_RENDER_OPEN_BROWSER=0 ./Start-Camera-Render-Console.command
```

## 7. 页面上应该怎么看

健康状态里重点看：

```text
Camera        绿：摄像头可见
Seedream API  绿：ARK_API_KEY 已找到
Watcher       绿：Chrome 监听进程运行中
Worker        绿：后台任务进程运行中
Swift         绿：人脸检测脚本可用
imagesnap     绿：拍照命令可用
```

打印机没接时，Printer Bridge/CUPS 可能不是完全可用。只要关闭 `CAMERA_RENDER_AUTO_PRINT=0`，就可以先测试拍照和渲染。

## 8. Chrome 监听开关

顶部按钮：

```text
切回 Chrome 触发：开/关
```

建议新电脑首次测试保持：

```text
切回 Chrome 触发：关
```

两种模式含义：

```text
关 launch          只在 Chrome 从未运行到启动时触发
开 launch_or_focus Chrome 启动，或从别的应用切回 Chrome 时触发
```

按钮切换会自动重启 watcher，不会清空已经生成的图片和 job 记录。设置会保存到：

```text
~/Documents/Chrome-Camera-Anime/state/chrome-trigger-mode.json
```

## 9. 文件会保存到哪里

代码在 repo：

```text
Mira-and-Mira-Light-New/Chrome-Camera-Anime/
```

运行数据在 Documents：

```text
~/Documents/Chrome-Camera-Anime/
```

常用目录：

```text
~/Documents/Chrome-Camera-Anime/outputs/          # 最终生成图
~/Documents/Chrome-Camera-Anime/logs/             # chrome-watch.log, worker.log
~/Documents/Chrome-Camera-Anime/state/jobs/       # 每个任务的 job.json
~/Documents/Chrome-Camera-Anime/localmac-camera/  # 摄像头最新抓图缓存
```

连接打印机之前产生的旧图不会自动补打。只有新任务进入 print 队列，或你手动点击“打印最新图”，才会提交打印。

## 10. 建议的首次测试顺序

第一步，只测服务：

```bash
CAMERA_RENDER_OPEN_BROWSER=0 \
CAMERA_RENDER_START_WATCH=0 \
CAMERA_RENDER_CONSOLE_PORT=18995 \
CAMERA_RENDER_BRIDGE_PORT=19995 \
./Start-Camera-Render-Console.command
```

另开终端：

```bash
curl -s http://127.0.0.1:19995/health | python3 -m json.tool
```

第二步，只测摄像头：

```bash
cd Chrome-Camera-Anime
python3 manual_insta_capture.py \
  --capture-only \
  --camera-name "MacBook Air相机" \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift
```

如果摄像头名不同，替换 `--camera-name`。

第三步，测渲染但不打印：

```bash
cd Chrome-Camera-Anime
python3 manual_insta_capture.py \
  --no-print \
  --camera-name "MacBook Air相机" \
  --manifest ./manifest.json \
  --detector-script ./detect_faces.swift \
  --output-dir "$HOME/Documents/Chrome-Camera-Anime/outputs/manual-test"
```

第四步，再打开浏览器控制台点击：

```text
拍照 + 渲染 + 打印
```

如果 `.env` 设置了 `CAMERA_RENDER_AUTO_PRINT=0`，这里实际会拍照和渲染，但不会提交打印。

## 11. 打印机接入

新电脑必须先在 macOS 系统里添加打印机。

检查队列：

```bash
lpstat -p -d
lpstat -e
lpstat -o
```

如果打印机没连接，保持：

```bash
CAMERA_RENDER_AUTO_PRINT=0
```

连接并确认队列后，再改成：

```bash
CAMERA_RENDER_AUTO_PRINT=1
```

注意：旧的 `failed_print` 任务不会因为打印机连接后自动补打。想打印旧图只能手动点击“打印最新图”。

## 12. 常用排错

页面打不开：

```bash
lsof -nP -iTCP:8795 -sTCP:LISTEN
lsof -nP -iTCP:9795 -sTCP:LISTEN
```

看 Bridge 健康状态：

```bash
curl -s http://127.0.0.1:9795/health | python3 -m json.tool
```

看日志：

```bash
tail -120 "$HOME/Documents/Chrome-Camera-Anime/logs/chrome-watch.log"
tail -120 "$HOME/Documents/Chrome-Camera-Anime/logs/worker.log"
```

看最近任务：

```bash
find "$HOME/Documents/Chrome-Camera-Anime/state/jobs" -name job.json -maxdepth 3 -print
```

检查系统打印任务是否积压：

```bash
lpstat -o
```

如果 `lpstat -o` 没输出，说明系统打印队列没有待打印任务。

## 13. 新电脑最小成功标准

达到下面状态就说明迁移成功：

```text
http://127.0.0.1:8795/ 可以打开
Camera 是绿的
Seedream API 是绿的
Watcher 和 Worker 是绿的
点击手动触发后 outputs/ 里出现新 jpeg
没有打印机时最多停在 failed_print，生成图仍然保存
```
