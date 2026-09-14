# 新 Mac 首次运行说明

这份文档给“把本仓库复制到一台新 macOS 电脑后继续运行”的人看。当前仓库包含三套主要入口：

```text
Start-Camera-Render-Console.command               # Chrome 摄像头拍照、Seedream 渲染、打印启动台
Start-Mira-Light-Latest-Console.command           # 推荐：最新 keyboard 版统一控制台（8791）
Start-Mira-Light-Unified-Director-Console.command # 经典统一控制台（8790）
Start-Mira-Light-Console.command                  # 旧 Mira Light Director Console / mock lamp
```

如果只关心拍照渲染启动台，先看：

```text
Chrome-Camera-Anime/NEW_COMPUTER_README.md
```

## 1. 复制哪些文件

建议复制整个仓库目录：

```text
Mira-and-Mira-Light-New/
```

不要只复制单个 `.command` 文件。启动按钮依赖这些目录：

```text
Chrome-Camera-Anime/
camera-render-director-console/
tools/camera_render_bridge/
tools/printer_bridge/
mira-light-shenzhen-console/
Motions_Shenzhen/
scripts/
config/
assets/
```

运行数据默认不在 repo 里，而是在新电脑自己的 Documents 目录里创建：

```text
~/Documents/Chrome-Camera-Anime/
```

这里会保存拍照缓存、任务状态、日志、生成图。复制仓库时不会自动带走旧电脑的输出图和旧任务，这是刻意设计的。

## 2. 新电脑需要准备什么

基础依赖：

```bash
xcode-select --install
brew install imagesnap
```

检查命令：

```bash
python3 --version
node --version
swift --version
imagesnap -l
```

如果没有 Homebrew，先安装 Homebrew，再运行 `brew install imagesnap`。

## 3. 配置 Seedream API key

真实渲染需要 `ARK_API_KEY`。不要把真实 key 提交到 git。

推荐方式一：写入本机私有文件：

```bash
mkdir -p "$HOME/.openclaw-chrome-camera-anime"
printf '%s\n' '你的真实 ARK_API_KEY' > "$HOME/.openclaw-chrome-camera-anime/ark_api_key.txt"
chmod 600 "$HOME/.openclaw-chrome-camera-anime/ark_api_key.txt"
```

推荐方式二：复制 `.env`：

```bash
cp Chrome-Camera-Anime/.env.example Chrome-Camera-Anime/.env
```

然后编辑：

```bash
ARK_API_KEY=你的真实key
```

`.env` 已经被 `.gitignore` 忽略。

## 4. 配置摄像头

列出新电脑可见摄像头：

```bash
imagesnap -l
```

如果看到的名字不是 `MacBook Air相机`，编辑：

```text
Chrome-Camera-Anime/.env
```

修改：

```bash
CAMERA_RENDER_CAMERA_NAME="这里填 imagesnap -l 看到的摄像头名"
```

第一次拍照时，macOS 可能会要求摄像头权限。请允许 Terminal、iTerm、Python 或你用来启动 `.command` 的应用访问摄像头：

```text
System Settings
  -> Privacy & Security
  -> Camera
```

## 5. 启动 Chrome Camera Anime

在 Finder 中双击：

```text
Start-Camera-Render-Console.command
```

或在终端运行：

```bash
./Start-Camera-Render-Console.command
```

启动后会打开：

```text
http://127.0.0.1:8795/
```

页面里优先看这些健康状态：

```text
Camera           应该识别到摄像头
Seedream API     应该显示 ARK_API_KEY
Watcher          应该 running
Worker           应该 running
Swift            应该找到 /usr/bin/swift
imagesnap        应该找到 imagesnap 路径
```

打印机没连接时，Printer Bridge 或 CUPS 有警告是可以接受的；这不影响拍照和渲染。

## 6. Chrome 自动触发开关

控制台顶部有按钮：

```text
切回 Chrome 触发：开/关
```

含义：

```text
关：只在 Chrome 从未运行到启动时触发
开：Chrome 启动，或从别的应用切回 Chrome 时触发
```

新电脑首次测试建议保持“关”，避免切换窗口时连续触发拍照和渲染。这个设置会保存到：

```text
~/Documents/Chrome-Camera-Anime/state/chrome-trigger-mode.json
```

## 7. 打印机说明

生成图会保存到：

```text
~/Documents/Chrome-Camera-Anime/outputs/
```

打印是最后一步，可失败，不会删除生成图。新电脑需要重新配置系统打印机和 CUPS 队列。

查看系统打印队列：

```bash
lpstat -p -d
lpstat -o
```

如果没有连接打印机，建议先在 `Chrome-Camera-Anime/.env` 中关闭自动打印：

```bash
CAMERA_RENDER_AUTO_PRINT=0
```

这样点击“拍照 + 渲染 + 打印”时会只做拍照和渲染，不会提交打印。

## 8. 安全测试命令

不自动打开浏览器、不启动 Chrome watcher，只测试服务能否启动：

```bash
CAMERA_RENDER_OPEN_BROWSER=0 \
CAMERA_RENDER_START_WATCH=0 \
CAMERA_RENDER_CONSOLE_PORT=18995 \
CAMERA_RENDER_BRIDGE_PORT=19995 \
./Start-Camera-Render-Console.command
```

另开一个终端检查：

```bash
curl -s http://127.0.0.1:19995/health | python3 -m json.tool
curl -s http://127.0.0.1:18995/ | head
```

按 `Ctrl-C` 退出测试。

## 9. Mira Light 最新控制台

推荐入口：

```text
Start-Mira-Light-Latest-Console.command
```

默认地址：

```text
http://127.0.0.1:8791/
```

真机默认连接：

```text
root@192.168.0.183:22
```

这套入口会启动 keyboard 版统一控制台，包含：

- 8791 最新控制台
- 舵机长按连续控制
- 逐帧 Record / Save / Clear
- 本地轨迹录制 / 回放面板
- 摸摸系统、灯光、摄像头、追书、庆祝页联动

经典 8790 兼容入口仍然保留：

```text
Start-Mira-Light-Unified-Director-Console.command
```

安全启动测试：

```bash
MIRA_UNIFIED_OPEN_BROWSER=0 \
MIRA_UNIFIED_CONSOLE_PORT=18791 \
./Start-Mira-Light-Unified-Director-Console-Keyboard.command
```

检查：

```bash
curl -s http://127.0.0.1:18791/api/scenes | python3 -m json.tool
curl -s http://127.0.0.1:18791/api/state | python3 -m json.tool
```

预期包含 9 个场景，其中第 9 个是 `09_wake_photo_sleep`。

## 10. 常见问题

### 双击 `.command` 没反应

检查权限：

```bash
chmod +x Start-Camera-Render-Console.command
chmod +x Start-Mira-Light-Latest-Console.command
chmod +x Start-Mira-Light-Unified-Director-Console-Keyboard.command
chmod +x Start-Mira-Light-Shenzhen-Console.command
chmod +x Start-Mira-Light-Console.command
```

如果 macOS 阻止来自网络下载的脚本，可以在仓库根目录运行：

```bash
xattr -dr com.apple.quarantine .
```

### 页面打不开

检查端口：

```bash
lsof -nP -iTCP:8795 -sTCP:LISTEN
lsof -nP -iTCP:9795 -sTCP:LISTEN
```

重新启动：

```bash
./Start-Camera-Render-Console.command
```

### Seedream API 显示 missing

检查：

```bash
test -s "$HOME/.openclaw-chrome-camera-anime/ark_api_key.txt" && echo "key file exists"
grep '^ARK_API_KEY=' Chrome-Camera-Anime/.env 2>/dev/null
```

不要在聊天、截图或 git diff 里暴露真实 key。

### 摄像头红灯

检查：

```bash
imagesnap -l
```

然后确认 `CAMERA_RENDER_CAMERA_NAME` 和列表里的名字一致。

### 打印失败

先确认是否有真实打印机队列：

```bash
lpstat -p -d
```

没有打印机时，打印失败是正常的。生成图仍然在：

```text
~/Documents/Chrome-Camera-Anime/outputs/
```
