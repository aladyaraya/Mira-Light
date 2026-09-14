# 网络、端口和 iPad 访问

## 最稳网络形态

最推荐：

```text
iPad、Mac、台灯板端都在同一个 Wi-Fi
```

Mac 跑 8790/8777/9783。台灯板端暴露 SSH 22 和舵机桥 9527。iPad 只访问 Mac 的网页，不直接访问板端。

## 端口表

| 端口 | 位置 | 用途 |
|---:|---|---|
| 8790 | Mac | 统一控制台 |
| 8777 | Mac | Celebration 庆祝网页 |
| 9783 | Mac | 摸摸语音桥 |
| 18777 | Mac | Celebration 音频 helper 内部端口 |
| 18000 | Mac | 追书视觉事件接收 |
| 22 | 台灯板端 | SSH 执行动作、恢复服务 |
| 9527 | 台灯板端 | 舵机/追书运行桥 |
| 9771 | Mac | 打印桥，可选 |

## 查看 Mac 局域网 IP

```bash
ipconfig getifaddr en0
ipconfig getifaddr en1
```

也可以看启动窗口里打印的：

```text
Console:   http://<Mac IP>:8790/
Celebrate: http://<Mac IP>:8777/08_celebrate/index.html
```

## iPad 打开方式

主控制台：

```text
http://Mac局域网IP:8790/
```

庆祝页：

```text
http://Mac局域网IP:8777/08_celebrate/index.html
```

例子：

```text
http://192.168.0.164:8790/
http://192.168.0.164:8777/08_celebrate/index.html
```

## macOS 防火墙

如果 iPad 打不开 Mac 页面，先在 Mac 上确认本机能打开：

```bash
curl -I http://127.0.0.1:8790/
curl -I http://127.0.0.1:8777/08_celebrate/index.html
```

本机能开但 iPad 不能开时，检查：

- Mac 和 iPad 是否同一 Wi-Fi。
- Mac 防火墙是否拦截了 Python。
- 启动器是否绑定 `0.0.0.0`，而不是只绑定 `127.0.0.1`。

便携包默认：

```bash
export MIRA_UNIFIED_CONSOLE_HOST="0.0.0.0"
export MIRA_CELEBRATION_CONSOLE_HOST="0.0.0.0"
```

这表示允许局域网访问。

## 为什么 iPad 点击能真实控灯

iPad 点击按钮后，请求发到 Mac：

```text
iPad Safari -> Mac 8790/8777 -> Mac 后端 -> SSH/HTTP/TCP -> 台灯板端
```

所以 iPad 不需要安装任何东西。只要 Mac 和台灯通，iPad 就能通过网页间接控制灯。
