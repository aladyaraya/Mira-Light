# 私有配置和密钥

便携包的私有配置文件是：

```text
portable/unified-console.env
```

启动器会在最前面自动读取它。这个文件不应该公开上传，因为里面可以包含 SSH 密码、渲染 API key 和本地端口配置。

## 默认板端配置

当前开发默认值：

```bash
export MIRA_SHENZHEN_BOARD_HOST="192.168.0.183"
export MIRA_SHENZHEN_BOARD_PORT="22"
export MIRA_SHENZHEN_BOARD_USER="root"
export MIRA_SHENZHEN_BOARD_PASSWORD=""
```

如果台灯换了 Wi-Fi 或 DHCP 分配了新 IP，只需要改 `MIRA_SHENZHEN_BOARD_HOST`。

## 控制台端口

```bash
export MIRA_UNIFIED_CONSOLE_PORT="8790"
export MIRA_CELEBRATION_CONSOLE_PORT="8777"
export MIRA_TOUCH_AUDIO_BRIDGE_PORT="9783"
```

8790 是主控制台。8777 是庆祝页。9783 是摸摸语音桥。通常不要改，除非新电脑上端口被占用。

## 追书和舵机桥

```bash
export MIRA_BOOK_FOLLOW_BASE_URL="tcp://${MIRA_SHENZHEN_BOARD_HOST}:9527"
export MIRA_BOOK_FOLLOW_RECEIVER_PORT="18000"
```

9527 是板端舵机/追书桥。18000 是 Mac 侧接收视觉事件的端口。追书没有反应时先检查板端 9527 是否通。

## ARK_API_KEY

拍照渲染、地瓜照片渲染、部分动画生成链路需要 `ARK_API_KEY`。打包脚本会按这个顺序尝试带入：

1. `portable/unified-console.env` 里已有的 `ARK_API_KEY`
2. 当前 shell 环境变量 `ARK_API_KEY`
3. macOS Keychain 服务 `mira-light-ark-api-key`

如果没有找到，包仍然可以启动；只是涉及真实云端渲染的功能会提示缺 key。

新电脑上手动写入：

```bash
printf '\nexport ARK_API_KEY=%q\n' '你的真实key' >> portable/unified-console.env
chmod 600 portable/unified-console.env
```

也可以放入 Keychain：

```bash
security add-generic-password -a "$USER" -s mira-light-ark-api-key -w '你的真实key' -U
```

## 为什么不用绝对路径

便携包里的路径都尽量相对解压目录。比如庆祝音频、摸摸语音桥、动作脚本、摄像头渲染脚本都通过 `ROOT_DIR` 推导。这样换电脑后不需要保持 `/Users/Zhuanz/...` 这个旧路径。

## 推荐权限

```bash
chmod 600 portable/unified-console.env
chmod +x START_HERE_8790.command
chmod +x Start-Mira-Light-Unified-Director-Console.command
```

这个 env 是“开发自用钥匙串替代品”。最舒服，但也最需要私藏好。
