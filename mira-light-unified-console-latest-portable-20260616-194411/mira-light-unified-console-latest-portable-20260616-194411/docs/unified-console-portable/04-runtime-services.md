# 启动后会拉起哪些服务

`Start-Mira-Light-Unified-Director-Console.command` 是总入口。它不是只启动一个网页，而是把现场需要的一组服务串起来。

## 主服务

| 服务 | 默认地址 | 说明 |
|---|---|---|
| Unified Console | `http://127.0.0.1:8790/` | 主控制台、救场按钮、追书、摸摸、摄像头、动作队列 |
| Celebration Page | `http://127.0.0.1:8777/08_celebrate/index.html` | iPad/浏览器庆祝页 |
| Touch Audio Bridge | `http://127.0.0.1:9783/health` | 板端摸摸事件触发 Mac 播放声音 |
| Mac Audio Helper | `http://127.0.0.1:18777/health` | 低延迟播放庆祝音频 |

## 启动器做的事

1. 读取 `portable/unified-console.env`。
2. 选择 `.venv/bin/python3` 或系统 `python3`。
3. 检查 8790 控制台文件、8777 庆祝页文件、摄像头渲染文件、动作脚本。
4. 清掉旧的 8788 摄像头控制台，避免占用 `/dev/video0`。
5. 尝试启动或修复打印桥。
6. 从 `portable/support/touch-audio-bridge` 启动 9783 摸摸语音桥。
7. 启动 8777 庆祝页。
8. 启动 8790 主控制台。
9. 可选启动追书视觉链路。

## 默认不会自动启动追书

默认：

```bash
export MIRA_BOOK_FOLLOW_AUTO_START="0"
```

这样开控制台不会立刻抢摄像头。需要追书时，在 8790 控制台里点“启动追书”。

如果要新电脑打开控制台就自动追书，改成：

```bash
export MIRA_BOOK_FOLLOW_AUTO_START="1"
```

## 默认会启动摄像头自动刷新

```bash
export MIRA_UNIFIED_CAMERA_START_WATCH="1"
```

如果只是调动作，不想让摄像头链路占资源：

```bash
export MIRA_UNIFIED_CAMERA_START_WATCH="0"
```

## 摸摸语音链路

摸摸的完整链路是：

```text
板端触摸检测 -> http://Mac IP:9783/v1/mira-light/trigger -> Mac 播放音频
```

板端配置里应该指向新 Mac 的局域网 IP。换电脑后如果摸摸动作有反应但没声音，通常是板端 `bridge_url` 还指向旧 Mac IP。

## 庆祝页音频链路

庆祝页点击后：

```text
iPad/浏览器 -> 8777 /api/mac-audio/celebrate -> 18777 Mac Audio Helper -> 蓝牙音箱
```

这样可以绕开 iPad Safari 的自动播放限制，让声音在 Mac/蓝牙音箱上低延迟播放。

## 进程关闭

启动窗口不要关。按 `Ctrl-C` 会停止 8790 和本次启动的 8777。已经存在的后台桥接服务可能会继续跑，这是为了避免每次启动都重新暖机。
