# Chrome Camera Anime 文档索引

这一组文档说明新仓库里的 Chrome Camera Anime 启动台。它的目标是让这个链路像 Mira Light 控制台一样，具备明确的启动入口、健康检查、运行控制、状态观察和排错路径。

## 推荐阅读顺序

1. [新电脑使用说明](../NEW_COMPUTER_README.md)
   从复制仓库、安装依赖、配置 `.env`、摄像头权限、API key 到首次健康检查，按新 Mac 上手顺序写。

2. [启动与运行手册](./RUNBOOK.md)
   从第一次启动、环境变量、健康检查到真实链路验证，按操作顺序写。

3. [架构说明](./ARCHITECTURE.md)
   解释浏览器控制台、Console Server、Camera Render Bridge、runtime、Printer Bridge 之间如何连接。

4. [API 参考](./API_REFERENCE.md)
   说明 Camera Render Bridge 和 Console Server 暴露的接口，以及如何用 `curl` 做手动检查。

5. [排错手册](./TROUBLESHOOTING.md)
   针对页面打不开、摄像头不可见、API key 缺失、打印失败、端口冲突等问题给出定位步骤。

## 当前实现范围

当前首版默认使用真实链路：

```text
MacBook Air相机
  -> imagesnap
  -> Seedream API, 读取 ARK_API_KEY
  -> Printer Bridge / CUPS
```

这意味着控制台可以在摄像头、API key 或打印机缺失时启动，但真正点击“拍照 + 渲染 + 打印”需要这些真实依赖都可用。健康检查会把每一层依赖分开展示，便于判断当前卡在哪一层。

## 关键入口

从仓库根目录启动：

```bash
./Start-Camera-Render-Console.command
```

默认浏览器地址：

```text
http://127.0.0.1:8795/
```

默认 bridge 地址：

```text
http://127.0.0.1:9795
```

默认 printer bridge 地址：

```text
http://127.0.0.1:9771
```
