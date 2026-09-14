# Mira Light 8790 便携包说明索引

这个目录记录 `http://127.0.0.1:8790/` 对应的统一控制台如何打包、搬到新 Mac、配置私有密钥、启动和排错。

## 当前目标

- 让新电脑解压后可以一键启动 8790 控制台。
- 同包携带开发自用配置：板端 IP、SSH 用户、SSH 密码、端口、追书和摸摸相关默认值。
- 同包携带庆祝页、摸摸语音桥、拍照/渲染链路、追书链路、动作脚本、语音包、测试和工具代码。
- 不携带 `.git`、`.omx`、`tmp`、`.venv`、`dist` 这类对运行控制台没有帮助的状态目录。
- 保留私有说明，方便以后自己回来看。

## 快速入口

- 打包当前机器最新版：`Build-Mira-Light-8790-Portable-Package.command`
- 新电脑首次配置：`portable/setup_new_mac.sh`
- 新电脑日常启动：`START_HERE_8790.command`
- 主控制台：`http://127.0.0.1:8790/`
- 庆祝页：`http://127.0.0.1:8777/08_celebrate/index.html`

## 文档顺序

1. [新电脑快速启动](01-new-mac-quick-start.md)
2. [私有配置和密钥](02-private-config-and-keys.md)
3. [网络、端口和 iPad 访问](03-network-ports-and-ipad.md)
4. [启动后会拉起哪些服务](04-runtime-services.md)
5. [常见故障排查](05-troubleshooting.md)

## 私有性提醒

便携包里的 `portable/unified-console.env` 是开发自用配置，里面默认包含板端 SSH 密码。打包脚本还会尝试把当前 Mac 的 `ARK_API_KEY` 从环境变量或 Keychain 带进包里。这个 zip 不适合公开分发。
