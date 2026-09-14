# Mira Light 最新控制台启动说明

推荐流程：

1. 首次到新电脑：双击 `portable/setup_new_mac.sh`
2. 日常启动：双击 `START_HERE.command`
3. 最新推荐控制台：`http://127.0.0.1:8791/`
4. 兼容旧流程控制台：`http://127.0.0.1:8790/`
5. 同一 Wi-Fi 下的 iPad 可打开：`http://<Mac 局域网 IP>:8791/`

入口文件：

- `START_HERE.command`：最新推荐入口，启动 8791 键盘增强版统一控制台
- `START_HERE_8791_KEYBOARD.command`：直接启动 8791 键盘增强版
- `START_HERE_8790.command`：兼容旧流程，启动经典 8790 控制台

这个包已经包含：

- 8791 最新键盘增强版统一控制台
- 8790 兼容版统一控制台
- 8777 Celebration 页面
- 摸摸语音桥
- 相机 / anime / 动作脚本 / 语音包 / 文档 / 测试 / 工具脚本

这个包不会包含：

- `.git`
- `.omx`
- 顶层 `tmp`
- 顶层 `runtime`
- `.venv`
- `dist`

详细说明见 `PACKAGE_GUIDE.md` 和 `docs/unified-console-portable/`。

注意：`portable/unified-console.env` 含私有开发配置，不要公开传播。
