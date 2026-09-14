# Mira Light Shenzhen Demo Console

这是从旧仓库最新版深圳演示控制台迁移过来的本地主控台：

```text
/Users/thomasjwang/Documents/GitHub/Mira-Light/Motions_Shenzhen/demo_fixed_protocol_v2/console
```

它和旧版 Mira Light Director Console 并存。旧版 Director Console 仍然通过 bridge/mock lamp/runtime 工作；深圳控制台不走旧 bridge，而是直接适配深圳固定动作脚本，并在点击“执行真机”时通过 SSH 发命令到地瓜板。

## 推荐启动方式

从新仓库根目录双击：

```text
Start-Mira-Light-Latest-Console.command
```

或从终端运行：

```bash
./Start-Mira-Light-Latest-Console.command
```

`Start-Mira-Light-Shenzhen-Console.command` 是同一套控制台的原始命名入口，也可以直接使用。

默认打开：

```text
http://127.0.0.1:8777/
```

## 本目录启动方式

也可以直接进入本目录启动：

```bash
cd /Users/thomasjwang/Documents/GitHub/Mira-and-Mira-Light-New/mira-light-shenzhen-console
./start_shenzhen_console.sh
```

## 运行链路

```text
浏览器 Shenzhen Console
  -> shenzhen_console.py
  -> scene_registry.json
  -> Motions_Shenzhen/demo_fixed_protocol_v2/scripts
  -> SSH root@192.168.0.183:22
```

同一版本的深圳固定动作脚本已经迁入新仓库：

```text
Motions_Shenzhen/demo_fixed_protocol_v2/scripts
```

启动脚本会优先使用新仓库内的脚本目录。只有这个目录不存在时，才回退到旧仓库路径。也可以显式覆盖：

```bash
export MIRA_SHENZHEN_SCRIPTS_DIR="/path/to/demo_fixed_protocol_v2/scripts"
```

## 环境变量

```text
MIRA_SHENZHEN_CONSOLE_HOST=127.0.0.1
MIRA_SHENZHEN_CONSOLE_PORT=8777
MIRA_SHENZHEN_BOARD_HOST=192.168.0.183
MIRA_SHENZHEN_BOARD_PORT=22
MIRA_SHENZHEN_BOARD_USER=root
MIRA_SHENZHEN_BOARD_PASSWORD=<board-password>
MIRA_SHENZHEN_OPEN_BROWSER=1
MIRA_SHENZHEN_SCRIPTS_DIR=/path/to/demo_fixed_protocol_v2/scripts
MIRA_SHENZHEN_DIGUA_RENDER_SCRIPT=/path/to/digua_remote_render_pipeline.py
MIRA_SHENZHEN_DIGUA_OUTPUT_DIR=mira-light-shenzhen-console/runtime/digua-console-output
```

`Start-Mira-Light-Shenzhen-Console.command` 默认会设置板端密码为 `<board-password>`。如果需要临时覆盖：

```bash
MIRA_SHENZHEN_BOARD_PASSWORD="新的密码" ./Start-Mira-Light-Shenzhen-Console.command
```

## 执行方式

每个场景有两个主要动作：

```text
预览命令
  只生成将要发往板端的 shell，不碰真机。

执行真机
  把生成的 shell 通过 SSH 发到板端。
```

默认板端连接：

```text
root@192.168.0.183 -p 22
```

## 文件说明

```text
scene_registry.json              场景和救场动作登记表
console_v2_videos_mapping.md     console v2 01-08 和视频/PDF 条目对照
shenzhen_console.py              本地 HTTP server，负责预览和 SSH 执行
web/                             主控台前端页面
start_shenzhen_console.sh        源控制台自带启动脚本
```

当前 registry 有 9 个主场景。`09_wake_photo_sleep` 是新增的本地编排场景：醒来、定格拍照、板端摄像头真实抓图、本机后台二次元渲染和提交打印、再回到睡觉姿态。

## 安全边界

- 打开控制台、读取 `/api/scenes`、读取 `/api/state` 不执行真机动作。
- “预览命令”只在本机生成 shell，不通过 SSH 执行动作。
- “执行真机”、舵机手动控制、读取舵机位置、救场动作会通过 SSH 访问板端。
- `torque off` 这类可能导致机械臂下坠的动作没有放进救场按钮。

## 本地 smoke test

不自动打开浏览器，使用临时端口：

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

预期：

```text
registry.title = Mira Light Shenzhen Demo Console
registry.version = 2026-04-25-v2
scenes 数量 = 9
quickActions 数量 = 15
```
