# Mira Light 最新便携控制台说明

## 这是什么

这是当前整理后的最新版 Mira Light 可分发运行包。解压后，在另一台 Mac 上完成一次初始化，就可以直接使用。

推荐入口：

- `START_HERE.command`
- `Start-Mira-Light-Latest-Console.command`
- `http://127.0.0.1:8791/`

兼容入口：

- `START_HERE_8790.command`
- `Start-Mira-Light-Unified-Director-Console.command`
- `http://127.0.0.1:8790/`

## 这版已经包含的能力

- 8791 键盘增强版统一控制台
- 长按连续舵机微调
- 舵机逐帧 Record / Save / Clear
- 本地轨迹录制 / 文件回放面板
- 默认开启摸摸系统
- 默认开启灯光 / 头部命令
- 通过 `MIRA_REMOTE_DESKTOP_DIR` 适配不同板端桌面路径

## 在新 Mac 上如何使用

1. 如果 macOS 拦截，先去隔离：

```bash
xattr -dr com.apple.quarantine /path/to/mira-light-unified-console-latest-portable-*
```

2. 解压整个 zip
3. 双击 `portable/setup_new_mac.sh`
4. 等待它完成 Homebrew 依赖和 Python 依赖安装
5. 双击 `START_HERE.command`

## 包内关键默认配置

包里自带可直接用的 `portable/unified-console.env` 私有配置。

关键默认值：

- 板子地址：`192.168.0.183`
- 摸摸语音桥端口：`9783`
- 最新控制台端口：`8791`
- Celebration 页面端口：`8777`
- 板端桌面目录：`/home/sunrise/Desktop`

## 分发和使用注意事项

- 真机动作是否成功，仍然取决于板子 SSH 和板端脚本是否可达
- 日常推荐使用 8791 页面
- 8790 仍保留在包里，用于兼容旧流程
- `portable/unified-console.env` 含私有配置，分发时请只在可信环境内使用
