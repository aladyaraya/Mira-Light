# Mira-and-Mira-Light-New-0517

## 新电脑首次运行

如果把这个仓库复制到一台新的 Mac，先读：

```text
NEW_MAC_SETUP_README.md
```

如果只关心 Chrome 摄像头拍照、Seedream 渲染、打印启动台，直接读：

```text
Chrome-Camera-Anime/NEW_COMPUTER_README.md
```

这两份文档专门说明新电脑需要安装什么、API key 放哪里、摄像头如何改名、打印机未连接时如何避免旧任务补打，以及如何做首次健康检查。

如果希望给新电脑一个更干净的可复制运行包，可以直接复制：

```text
Ready-To-Run-Mira-Light-Anime/
```

这个文件夹根目录只保留两个主要启动按钮：

```text
Start-Mira-Light-Latest.command
Start-Chrome-Camera-Anime.command
```

## Mira Light 追书功能文档

如果要继续实现“追书 / 桌面目标跟随”，先读：

```text
docs/book-follow/README.md
docs/book-follow/IMPLEMENTATION_GUIDE.md
docs/book-follow/RUNBOOK.md
docs/book-follow/BOARD_CAMERA_STREAMING.md
docs/book-follow/PRECISION_FEEDBACK_LOOP.md
docs/book-follow/AGENT_INSTRUCTIONS.md
docs/book-follow/MIGRATED_ASSETS.md
docs/feature/30-tabletop-target-mode-first-pass.md
docs/feature/31-tabletop-target-locking-and-selection-policy.md
docs/mira-light-live-follow-demo-runbook.md
docs/legacy-mira-light/
board-camera-streaming/README.md
```

当前结论是：追书应基于已有 `tabletop_follow` live vision stack 实现，固定版 `07_tabletop_follow_demo.py` 只作为 fallback。核心链路是：

```text
板端摄像头 JPEG
  -> scripts/cam_receiver_service.py
  -> scripts/track_target_event_extractor.py
  -> scripts/vision_runtime_bridge.py
  -> scripts/mira_light_runtime.py
  -> Mira Light 舵机和灯光
```

## Chrome Camera Anime 一键启动

在 macOS Finder 里双击仓库根目录的：

```text
Start-Camera-Render-Console.command
```

这个文件是 Chrome/Camera/Anime 链路的“一键启动按钮”。它会按顺序启动：

```text
Start-Camera-Render-Console.command
  -> tools/printer_bridge/start_bridge.sh                    # 优先复用 http://127.0.0.1:9771
  -> tools/camera_render_bridge/bridge_server.py             # http://127.0.0.1:9795
  -> camera-render-director-console/scripts/console_server.py # http://127.0.0.1:8795
  -> browser opens the console
```

默认启动后会自动打开：

```text
http://127.0.0.1:8795/
```

控制台链路是：

```text
浏览器控制台
  -> camera-render-director-console/scripts/console_server.py
  -> Camera Render Bridge: http://127.0.0.1:9795
  -> Chrome-Camera-Anime runtime
  -> imagesnap / MacBook Air相机
  -> Seedream API
  -> Printer Bridge / CUPS
```

`ARK_API_KEY` 可以直接来自你当前 shell 环境，不强制写入 `.env`。如果希望固定本仓库的本地配置，可以复制：

```bash
cp Chrome-Camera-Anime/.env.example Chrome-Camera-Anime/.env
```

然后按需填写或修改摄像头、端口、打印介质等配置。`.env` 不应提交到 git。

可选环境变量：

```text
ARK_API_KEY=<Seedream API key>
CAMERA_RENDER_CAMERA_NAME=MacBook Air相机
CAMERA_RENDER_CAMERA_BACKEND=imagesnap
CAMERA_RENDER_AUTO_PRINT=1
CAMERA_RENDER_PRINT_MEDIA=4x6.Fullbleed
CAMERA_RENDER_DATA_DIR=$HOME/Documents/Chrome-Camera-Anime
CAMERA_RENDER_OUTPUT_DIR=$HOME/Documents/Chrome-Camera-Anime/outputs
CAMERA_RENDER_STATE_DIR=$HOME/Documents/Chrome-Camera-Anime/state
CAMERA_RENDER_LOGS_DIR=$HOME/Documents/Chrome-Camera-Anime/logs
CAMERA_RENDER_CONSOLE_PORT=8795
CAMERA_RENDER_BRIDGE_PORT=9795
OPENCLAW_PRINTER_BRIDGE_PORT=9771
OPENCLAW_PRINTER_BRIDGE_URL=http://127.0.0.1:9771
CAMERA_RENDER_OPEN_BROWSER=1
```

默认情况下，运行产物不会再写入 repo。任务状态、拍照中间图、生成图和日志会写到 `~/Documents/Chrome-Camera-Anime/`；仓库里的 `Chrome-Camera-Anime/` 只作为脚本 runtime。

如果真实摄像头或打印机不在线，控制台仍会打开；对应健康检查会显示失败项。真实渲染需要 `ARK_API_KEY`，真实拍照需要 macOS 给 Terminal 或 iTerm 摄像头权限。

更详细的 Chrome/Camera/Anime 文档：

```text
Chrome-Camera-Anime/docs/README.md
Chrome-Camera-Anime/docs/RUNBOOK.md
Chrome-Camera-Anime/docs/ARCHITECTURE.md
Chrome-Camera-Anime/docs/API_REFERENCE.md
Chrome-Camera-Anime/docs/TROUBLESHOOTING.md
```

## Mira Light 最新深圳演示控制台一键启动

新仓库现在并存两套 Mira Light 控制台：

```text
Start-Mira-Light-Latest-Console.command                 # 推荐：最新 keyboard 版统一控制台（8791）
Start-Mira-Light-Unified-Director-Console.command      # 经典统一控制台（8790）
Start-Mira-Light-Shenzhen-Console.command              # 深圳控制台原始命名入口
Start-Mira-Light-Console.command                       # 旧 Director Console，bridge/mock lamp 链路
```

最新版推荐入口现在是 keyboard 版统一控制台：

```text
Start-Mira-Light-Latest-Console.command
```

同一版本的动作脚本也已经迁入新仓库：

```text
Motions_Shenzhen/demo_fixed_protocol_v2/scripts
```

当前最新版包含 9 个主场景：`01` 到 `08` 是固定动作/拍照姿态，`09_wake_photo_sleep` 是新增的“醒来拍照再睡”本地编排场景。第 9 场景会调用板端摄像头拍照，并在本机后台触发二次元渲染和打印。

在 macOS Finder 里双击仓库根目录的：

```text
Start-Mira-Light-Latest-Console.command
```

默认启动后会自动打开：

```text
http://127.0.0.1:8791/
```

它的运行链路是：

```text
浏览器深圳演示主控台
  -> mira-light-shenzhen-console/shenzhen_console.py
  -> mira-light-shenzhen-console/scene_registry.json
  -> Motions_Shenzhen/demo_fixed_protocol_v2/scripts
  -> SSH root@192.168.0.183:22
```

启动脚本会优先使用新仓库里的动作脚本：

```text
Motions_Shenzhen/demo_fixed_protocol_v2/scripts
```

只有当这个目录不存在时，才回退到旧仓库路径。

可选环境变量：

```text
MIRA_SHENZHEN_CONSOLE_HOST=127.0.0.1
MIRA_SHENZHEN_CONSOLE_PORT=8777
MIRA_SHENZHEN_BOARD_HOST=192.168.0.183
MIRA_SHENZHEN_BOARD_PORT=22
MIRA_SHENZHEN_BOARD_USER=root
MIRA_SHENZHEN_BOARD_PASSWORD=<board-password>
MIRA_SHENZHEN_OPEN_BROWSER=1
MIRA_SHENZHEN_SCRIPTS_DIR=/path/to/demo_fixed_protocol_v2/scripts
MIRA_SHENZHEN_DIGUA_OUTPUT_DIR=mira-light-shenzhen-console/runtime/digua-console-output
MIRA_SHENZHEN_CAPTURE_DIR=tmp/mira-light-board-camera
MIRA_SHENZHEN_JAVIS_RUNTIME=Chrome-Camera-Anime
```

安全启动测试：

```bash
MIRA_SHENZHEN_OPEN_BROWSER=0 \
MIRA_SHENZHEN_CONSOLE_PORT=18777 \
./Start-Mira-Light-Shenzhen-Console.command
```

验证接口：

```bash
curl -s http://127.0.0.1:18777/api/scenes | python3 -m json.tool
curl -s http://127.0.0.1:18777/api/state | python3 -m json.tool
```

预期 `/api/scenes` 中：

```text
registry.title = Mira Light Shenzhen Demo Console
registry.version = 2026-04-25-v2
scenes 数量 = 9
quickActions 数量 = 15
第 9 个场景 = 09_wake_photo_sleep
```

需要注意：“预览命令”只生成 shell，不碰真机；“执行真机”、舵机控制和救场动作会通过 SSH 访问板端。

## Mira Light 综合导演台

如果希望在一个页面里同时操作深圳演示、查看板端摄像头、控制摸摸系统，可以双击：

```text
Start-Mira-Light-Unified-Director-Console.command
```

默认打开：

```text
http://127.0.0.1:8789/
```

这套入口不会替换 `8777` 深圳控制台和 `8788` 摄像头导演台。它复用同一份深圳演示动作和舵机微调接口，并在右侧新增中间侧栏：

```text
主动作区 | 摄像头/摸摸系统侧栏 | 舵机微调侧栏
```

摄像头默认约每 10 秒从板端 `/dev/video0` 抓取一张 JPEG，仍保存到：

```text
~/Documents/Mira-Light-Camera-Console/frames/
```

摸摸系统控制对应板端 `mira-touch.service`：

```text
临时启动        -> systemctl start mira-touch.service
临时关闭        -> systemctl stop mira-touch.service
关闭开机自启    -> systemctl disable mira-touch.service
恢复开机自启    -> systemctl enable mira-touch.service
```

可选环境变量：

```text
MIRA_UNIFIED_CONSOLE_HOST=127.0.0.1
MIRA_UNIFIED_CONSOLE_PORT=8789
MIRA_UNIFIED_OPEN_BROWSER=1
MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS=10
MIRA_UNIFIED_CAMERA_START_WATCH=1
MIRA_CAMERA_CONSOLE_DATA_DIR=$HOME/Documents/Mira-Light-Camera-Console
```

## Mira Light 摄像头导演台

如果只想看台灯板端摄像头的最新画面，可以双击：

```text
Start-Mira-Light-Camera-Director-Console.command
```

短名入口也可用：

```text
Start-Mira-Light-Camera-Console.command
```

默认打开：

```text
http://127.0.0.1:8788/
```

这套轻量控制台会通过 SSH 连接地瓜板，调用板端 `/dev/video0`，约每 10 秒抓取一张 JPEG 并显示在浏览器里。抓图链路复用现有的：

```text
Chrome-Camera-Anime/digua_remote_render_pipeline.py
```

默认连接参数：

```text
MIRA_CAMERA_BOARD_HOST=192.168.0.183
MIRA_CAMERA_BOARD_PORT=22
MIRA_CAMERA_BOARD_USER=root
MIRA_CAMERA_BOARD_PASSWORD=<board-password>
MIRA_CAMERA_INTERVAL_SECONDS=10
DIGUA_CAMERA_DEVICE=/dev/video0
DIGUA_CAMERA_VIDEO_SIZE=1280x720
```

抓到的图片默认保存到：

```text
~/Documents/Mira-Light-Camera-Console/frames/
```

## Mira Light 旧 Director Console 一键启动

在 macOS Finder 里双击仓库根目录的：

```text
Start-Mira-Light-Console.command
```

这个文件就是 Mira Light 控制台的“一键启动按钮”。现在它会启动完整本地链路：

```text
Start-Mira-Light-Console.command
  -> scripts/mock_lamp_server.py                         # 默认 mock 灯
  -> tools/mira_light_bridge/bridge_server.py            # http://127.0.0.1:9783
  -> mira-light-director-console/scripts/console_server.py # http://127.0.0.1:8765
  -> browser opens the console
```

默认启动后会自动打开：

```text
http://127.0.0.1:8765/
```

控制台请求会先进入本地 console proxy，再转发到 Mira Light bridge：

```text
浏览器控制台
  -> mira-light-director-console/scripts/console_server.py
  -> Mira Light bridge: http://127.0.0.1:9783
  -> mock lamp: http://127.0.0.1:9791
```

也就是说，不接真实灯具时，双击按钮也能开箱即用：控制台、bridge、scene 列表、运行控制都会连接到 mock lamp。接真实 Mira Light 硬件时，用环境变量切换 lamp target：

```bash
MIRA_LIGHT_USE_MOCK_LAMP=0 \
MIRA_LIGHT_LAMP_BASE_URL=tcp://192.168.31.10:9527 \
./Start-Mira-Light-Console.command
```

可选环境变量：

```text
MIRA_LIGHT_CONSOLE_HOST=127.0.0.1
MIRA_LIGHT_CONSOLE_PORT=8765
MIRA_LIGHT_BRIDGE_HOST=127.0.0.1
MIRA_LIGHT_BRIDGE_PORT=9783
MIRA_LIGHT_MOCK_LAMP_HOST=127.0.0.1
MIRA_LIGHT_MOCK_LAMP_PORT=9791
MIRA_LIGHT_USE_MOCK_LAMP=1
MIRA_LIGHT_LAMP_BASE_URL=http://127.0.0.1:9791
MIRA_LIGHT_BRIDGE_TOKEN=<optional bridge token>
```

## 已迁移的运行文件

这次迁移后，新仓库包含五层文件：

```text
mira-light-director-console/      # 浏览器控制台和 console_server.py
tools/mira_light_bridge/          # Mira Light bridge
scripts/                          # bridge/runtime/mock lamp 依赖
config/                           # signal delivery、servo runtime、profile 示例配置
assets/audio/                     # scenes 使用的本地音频素材
```

深圳演示控制台相关文件：

```text
mira-light-shenzhen-console/      # 最新深圳现场演示主控台
mira-light-unified-director-console/ # 深圳演示 + 摄像头 + 摸摸系统综合导演台
Motions_Shenzhen/demo_fixed_protocol_v2/scripts
Start-Mira-Light-Latest-Console.command
Start-Mira-Light-Shenzhen-Console.command
Start-Mira-Light-Unified-Director-Console.command
```

Chrome/Camera/Anime 启动台相关文件：

```text
Chrome-Camera-Anime/              # 摄像头、Chrome watcher、Seedream 渲染、打印 runtime
camera-render-director-console/   # 浏览器控制台和 console_server.py
tools/camera_render_bridge/       # Camera Render Bridge
tools/printer_bridge/             # 本地 Printer Bridge 最小迁移
Start-Camera-Render-Console.command
```

## 检查可用性

检查 Chrome Camera Anime 按钮文件是否可双击执行：

```bash
ls -l Start-Camera-Render-Console.command
```

检查一键脚本语法：

```bash
bash -n Start-Camera-Render-Console.command
```

不自动打开浏览器、不启动 watcher 的安全启动测试：

```bash
CAMERA_RENDER_START_WATCH=0 \
CAMERA_RENDER_OPEN_BROWSER=0 \
CAMERA_RENDER_CONSOLE_PORT=18996 \
CAMERA_RENDER_BRIDGE_PORT=19996 \
./Start-Camera-Render-Console.command
```

终端里应该看到 `Printer Bridge`、`Camera Render Bridge: OK`、`Browser console: OK`。按 `Ctrl-C` 后，本次启动的 `18996` 和 `19996` 服务会停止。

检查 Mira Light 按钮文件是否可双击执行：

```bash
ls -l Start-Mira-Light-Console.command
```

权限里应该包含 `x`，例如：

```text
-rwxr-xr-x
```

检查一键脚本语法：

```bash
bash -n Start-Mira-Light-Console.command
```

检查 mock lamp：

```bash
python3 scripts/mock_lamp_server.py --host 127.0.0.1 --port 9791
```

检查 bridge 是否在线：

```bash
python3 - <<'PY'
import urllib.request
url = "http://127.0.0.1:9783/health"
try:
    with urllib.request.urlopen(url, timeout=2) as response:
        print("bridge ok", response.status)
except Exception as exc:
    print("bridge unavailable:", exc)
PY
```

检查控制台是否在线：

```bash
python3 - <<'PY'
import urllib.request
url = "http://127.0.0.1:8765/"
try:
    with urllib.request.urlopen(url, timeout=2) as response:
        print("console ok", response.status)
except Exception as exc:
    print("console unavailable:", exc)
PY
```

最简单的检查方式仍然是直接双击 `Start-Mira-Light-Console.command`。终端里应该依次看到 `Mock lamp: OK`、`Mira Light bridge: OK`、`Browser console: OK`。
