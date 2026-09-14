# 常见故障排查

## 一键自检

在包目录运行：

```bash
./portable/check_new_mac_prereqs.sh
```

它会检查命令、Python 依赖、关键文件、板端 SSH 和 9527 舵机桥。

## 8790 打不开

先看端口：

```bash
lsof -nP -iTCP:8790 -sTCP:LISTEN
curl -I http://127.0.0.1:8790/
```

如果端口被旧控制台占用，直接重新双击启动器。启动器会尝试清掉属于本仓库的旧 8790 进程。

如果是别的程序占用，需要手动换端口：

```bash
export MIRA_UNIFIED_CONSOLE_PORT="8890"
./Start-Mira-Light-Unified-Director-Console.command
```

## iPad 打不开，但 Mac 能打开

确认启动器打印的是局域网地址，不只是 `127.0.0.1`。便携配置里应为：

```bash
export MIRA_UNIFIED_CONSOLE_HOST="0.0.0.0"
export MIRA_CELEBRATION_CONSOLE_HOST="0.0.0.0"
```

然后检查 Mac 防火墙和 Wi-Fi。

## 按按钮没有控灯

先测 SSH：

```bash
source portable/unified-console.env
sshpass -p "$MIRA_SHENZHEN_BOARD_PASSWORD" ssh \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  -p "$MIRA_SHENZHEN_BOARD_PORT" \
  "$MIRA_SHENZHEN_BOARD_USER@$MIRA_SHENZHEN_BOARD_HOST" true
```

SSH 不通时，先处理台灯电源、Wi-Fi、IP 和密码。8790 的按钮大多通过 SSH 触发板端脚本，SSH 不通就不会动。

## 按钮有延迟

救场按钮当前多为：

```text
浏览器 -> 8790 入队 -> SSH -> 板端 python 脚本
```

所以它不是毫秒级直连。局域网 SSH 一次空跑接近 1 秒是常见现象。要进一步压低延迟，需要把灯光类动作改成板端常驻服务或 TCP/HTTP 快速通道。

## 庆祝页没有声音

检查 Mac Audio Helper：

```bash
curl http://127.0.0.1:18777/health
```

检查音频文件：

```bash
ls -lh mira-light-shenzhen-console/runtime/mac-audio/
```

当前庆祝音频应是：

```text
mira-light-shenzhen-console/runtime/mac-audio/celebrate.wav
```

如果蓝牙音箱没声，先在 macOS 声音设置里确认输出设备，再重新点庆祝页按钮。

## 摸摸没声音

检查 9783：

```bash
curl http://127.0.0.1:9783/health
```

如果 Mac 端正常但摸摸时没声，重点看板端 `bridge_url` 是否还指向旧电脑 IP。板端应该访问：

```text
http://新Mac局域网IP:9783/v1/mira-light/trigger
```

本机语音桥文件应该在：

```text
portable/support/touch-audio-bridge/
```

## 追书没反应

检查 9527：

```bash
source portable/unified-console.env
nc -G 2 -z "$MIRA_SHENZHEN_BOARD_HOST" 9527
```

再看 8790 的追书面板：

- `running` 是否为 yes。
- `detector` 是否为 `book_cover_color`。
- `target` 是否为 `book / yellow_book`。
- 摄像头画面是否真的刷新。

如果黄色书检测不到，优先调低饱和度阈值；如果桌面被误识别，调高黄色占比。

## 摄像头 payload empty

这通常是板端摄像头发送进程、`/dev/video0` 或 ffmpeg 卡住。8790 里“恢复板端服务”会做：

- 检查 SSH 22。
- 检查 servo bridge 9527。
- 重启 `rdk_bus_servo_tcp_bridge.py`。
- 清掉占用 `/dev/video0` 的旧 camera sender/ffmpeg。

如果还是空，断电重启台灯板端后再点恢复。
