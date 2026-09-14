# Mira Light Voice Full Ready 快速启动说明

这份文件给新电脑使用。把整个 `Mira-Light-Voice-Full-Ready` 文件夹拷过去后，优先按这里操作。

## 1. 最推荐的启动顺序

第一次到一台新 Mac：

```bash
cd Mira-Light-Voice-Full-Ready
chmod +x *.command commands/*.command scripts/*.sh bin/*
./commands/Setup.command
./commands/Test-Cloud.command
./Start-Chat.command
```

`Start-Chat.command` 是安全聊天模式：云端 Claw 回复 + TTS，不触发灯动作。它最适合先确认麦克风、语音识别、云端回复和播放都正常。

如果要控灯，再跑：

```bash
./commands/Test-Bridge.command
./Start-Full.command
```

`Start-Full.command` 会自动启动本地 bridge，并允许语音触发灯动作。

## 2. 三个顶层启动器

```text
Start-Chat.command
```

只聊天，不触发动作。新电脑优先用它。

```text
Start-Full.command
```

完整模式：聊天、TTS、自动启动 bridge、触发灯动作。要求灯本体网络可达。

```text
Start-Bridge.command
```

只启动本地灯控 bridge，用来单独测试灯控链路。

维护命令都在 `commands/` 里，比如：

```text
commands/Setup.command
commands/Test-Cloud.command
commands/Test-Lingzhu-Routes.command
commands/Test-Bridge.command
commands/Configure-Cloud.command
commands/Start-Chat-Continuous.command
commands/Start-Full-Continuous.command
```

## 2.1 Enter 模式和连续对话模式

默认启动器使用 `enter-vad`：

```text
Start-Chat.command
Start-Full.command
```

这种模式每一轮都需要在 Terminal 里按一次 Enter，然后说话；系统会在检测到静音后自动结束这一轮。它比较稳，不容易把音箱回放误当成你的下一句话。

如果要切成连续对话模式，可以双击：

```text
commands/Start-Chat-Continuous.command
commands/Start-Full-Continuous.command
```

连续模式会一直监听，不需要每轮按 Enter。它更自然，但对麦克风、音箱回声、环境噪声更敏感；如果出现重复转写、把 TTS 回声听进去、或者一直误触发，先切回默认的 `Start-Chat.command` / `Start-Full.command`。

也可以在 Terminal 里临时切换：

```bash
MIRA_LIGHT_CAPTURE_MODE=continuous ./Start-Chat.command
MIRA_LIGHT_CAPTURE_MODE=continuous ./Start-Full.command
```

切回 Enter 模式：

```bash
MIRA_LIGHT_CAPTURE_MODE=enter-vad ./Start-Chat.command
MIRA_LIGHT_CAPTURE_MODE=enter-vad ./Start-Full.command
```

## 3. 新电脑需要什么

基础要求：

```text
macOS
python3.11 或 python3
ssh
afplay
say
```

为了恢复更好听的 Edge TTS 声音，建议安装：

```bash
brew install node
npm install -g node-edge-tts
```

如果云端 tunnel 需要密码方式自动启动，建议安装：

```bash
brew install expect
```

没有 `node-edge-tts` 时仍能运行，但声音会退回 macOS `say`，听起来会机械一些。

## 4. 云端 Claw 怎么测

运行：

```bash
./commands/Test-Cloud.command
```

或者更详细：

```bash
./commands/Test-Lingzhu-Routes.command
```

看到下面几类结果就是云端通了：

```text
GET /v1/health -> 200
GET /metis/agent/api/health -> 200
POST /v1/chat -> 200
POST /metis/agent/api/sse -> 200
```

测试脚本只会打印 AK 是否存在和长度，不会打印 AK 内容。

## 5. Full 控灯为什么可能不动

Full 模式分两层：

```text
语音识别
-> 本地 intent 判断
-> 本地 bridge: http://127.0.0.1:9783
-> 灯本体: tcp://192.168.31.10:9527
```

bridge 能启动不代表灯本体一定可达。最关键的是这条命令：

```bash
nc -vz 192.168.31.10 9527
```

如果这里超时，说明新电脑不在灯所在网络，或者灯的 IP 已经变了。

当前默认配置在：

```text
config/mira-light-realtime.env
```

里面这行决定灯地址：

```bash
export MIRA_LIGHT_LAMP_BASE_URL=tcp://192.168.31.10:9527
```

如果灯换了 IP，改成：

```bash
export MIRA_LIGHT_LAMP_BASE_URL=tcp://新的灯IP:9527
```

然后重新启动：

```bash
./Start-Full.command
```

## 6. 常见现象

### 它说“身体没连上”

优先查：

```bash
./commands/Test-Bridge.command
nc -vz 192.168.31.10 9527
```

如果 `Test-Bridge` 通但 `nc` 超时，说明本地 bridge 是好的，灯本体网络不通。

### 听得到声音，但不会跳

确认你启动的是：

```text
Start-Full.command
```

不是 `Start-Chat.command`。Chat 模式会明确禁用动作。

### 说“那你就去跳吧”还是不动

当前包已经把这些话映射到跳舞场景：

```text
那你就去跳吧
你可以跳舞吗
你跳一下
你跳一跳
给我跳个舞
启动跳舞模式
```

如果仍然不动，通常是灯本体 `9527` 网络不可达。

### 旧终端还在重复说旧话

关掉旧 Terminal 窗口，或者执行：

```bash
pkill -f mira_realtime_voice_interaction.py
```

然后重新双击 `Start-Full.command`。

### 连续对话模式误识别很多

连续模式更容易受到音箱回放和环境噪声影响。优先处理：

```text
1. 把麦克风换成 MacBook 内置麦克风
2. 降低音箱音量
3. 增大麦克风和音箱距离
4. 改回 enter-vad 模式
```

最稳的启动器仍然是：

```text
Start-Chat.command
Start-Full.command
```

## 7. 隐私提醒

这个包包含私人配置：

```text
config/mira-light-realtime.env
config/private/
```

里面可能有云端 AK 或远程连接配置。这个 zip 只适合自己机器之间传，不要上传公开仓库或发给无关人员。

## 8. 推荐确认命令

新电脑完整确认：

```bash
./commands/Setup.command
./commands/Test-Cloud.command
./commands/Test-Bridge.command
./Start-Chat.command
```

如果要控灯，再确认灯本体：

```bash
nc -vz 192.168.31.10 9527
./Start-Full.command
```
