# 新电脑快速启动

## 在旧电脑上打包

在仓库根目录双击：

```bash
Build-Mira-Light-8790-Portable-Package.command
```

或者在 Terminal 里运行：

```bash
./scripts/package_unified_console_portable.sh
```

完成后会生成：

```text
dist/mira-light-unified-console-8790-portable-YYYYMMDD-HHMMSS.zip
```

## 把 zip 放到新 Mac

建议解压到：

```text
~/Documents/Github/Mira-and-Mira-Light-New
```

路径不要求完全一致，但不要只拷贝单个控制台目录。这个包依赖同级目录里的动作脚本、庆祝页、摄像头链路、语音包和 `portable/support/touch-audio-bridge`。

如果 macOS 因为隔空投送或浏览器下载加了 quarantine 标记，先运行：

```bash
xattr -dr com.apple.quarantine /path/to/mira-light-unified-console-8790-portable-*
```

## 新 Mac 首次配置

进入解压后的包目录：

```bash
cd /path/to/mira-light-unified-console-8790-portable-*
./portable/setup_new_mac.sh
```

这个脚本会做四件事：

- 检查 Homebrew 工具：`sshpass`、`expect`、`ffmpeg`、`tmux`、`portaudio`。
- 创建 `.venv`。
- 安装 `requirements.txt` 里的 Python 依赖。
- 检查板端 SSH、9527 舵机桥、8790/8777/9783 相关文件。

## 日常启动

双击：

```text
START_HERE_8790.command
```

或者直接双击：

```text
Start-Mira-Light-Unified-Director-Console.command
```

启动后打开：

```text
http://127.0.0.1:8790/
```

如果 iPad 和 Mac 在同一个 Wi-Fi，iPad 打开：

```text
http://Mac局域网IP:8790/
```

庆祝页打开：

```text
http://Mac局域网IP:8777/08_celebrate/index.html
```

## 判断是否启动成功

Terminal 里应该能看到类似信息：

```text
Unified director console: OK
Celebration page: OK
Console:   http://<Mac IP>:8790/
Celebrate: http://<Mac IP>:8777/08_celebrate/index.html
Board:     root@192.168.0.183:22
Password:  configured
```

浏览器里 8790 控制台的“状态”区域应该能读取到 `idle/running`，摸摸系统区域应该能显示端口 `9783`，庆祝页按钮应该可以触发 Mac 播放音频和台灯动作。
