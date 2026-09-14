# Mira Light Voice Full Ready

This is the cleaned, portable Mira Light voice + bridge folder.

The top level intentionally has only three common launchers:

```text
Start-Chat.command
Start-Full.command
Start-Bridge.command
```

Everything else lives in `commands/`.

## Start Here

For a short Chinese setup guide on a new Mac, read:

```text
QUICK-START.md
```

On this Mac, double-click:

```text
Start-Chat.command
```

This starts cloud Claw chat + TTS only. It does not trigger lamp actions.

For full lamp control, double-click:

```text
Start-Full.command
```

Full mode automatically starts or reuses the local bridge before voice begins.

To start only the bridge:

```text
Start-Bridge.command
```

## First Run On A New Mac

Open Terminal in this folder and run:

```bash
chmod +x *.command commands/*.command scripts/*.sh bin/*
./commands/Setup.command
./commands/Test-Cloud.command
./commands/Test-Bridge.command
./Start-Chat.command
```

After that, the `.command` files can be double-clicked in Finder.

## Command Layout

Top-level launchers:

```text
Start-Chat.command    cloud chat + TTS only, no light actions
Start-Full.command    cloud chat + TTS + light actions, auto-starts bridge
Start-Bridge.command  starts/reuses only the local bridge
```

Maintenance tools:

```text
commands/Setup.command
commands/Configure-Cloud.command
commands/Test-Cloud.command
commands/Test-Lingzhu-Routes.command
commands/Test-Bridge.command
commands/Start-Chat-Continuous.command
commands/Start-Full-Continuous.command
commands/Start-Local.command
commands/Install-Local-Agent.command
```

## Capture Mode

The default launchers use `enter-vad`: press Enter once per turn, then speak.
This is the most stable mode when the speaker and microphone are near each
other.

For continuous listening, use:

```text
commands/Start-Chat-Continuous.command
commands/Start-Full-Continuous.command
```

Or run:

```bash
MIRA_LIGHT_CAPTURE_MODE=continuous ./Start-Chat.command
MIRA_LIGHT_CAPTURE_MODE=continuous ./Start-Full.command
```

Switch back with:

```bash
MIRA_LIGHT_CAPTURE_MODE=enter-vad ./Start-Chat.command
MIRA_LIGHT_CAPTURE_MODE=enter-vad ./Start-Full.command
```

## StepFun Realtime Speech Engine

Full mode can keep the old runtime, or use StepAudio 2.5 Realtime as the speech
engine while still sharing the same Full mode action boundary.

Default Full mode:

```bash
./Start-Full.command
```

Full mode with StepFun realtime speech:

```bash
MIRA_LIGHT_SPEECH_ENGINE=stepfun-realtime ./Start-Full.command
```

In this mode, StepAudio handles live speech in/out, and semantic actions still
go through the local scene/trigger whitelist before reaching the bridge. It does
not give the model direct servo, TCP, LED, shell, or Python control.

On Windows, use the equivalent launcher from the package root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -StartActionBridge
```

Windows keeps the touch-audio bridge and voice-action bridge on separate ports:

```text
Touch audio bridge:  http://127.0.0.1:9783
Voice action bridge: http://127.0.0.1:19783
Lamp target:         tcp://192.168.0.183:9527
```

Use `-NoSemanticActions` when you only want to test realtime conversation. Drop
that flag when the speech transcript should be sent to `step-3.7-flash`, mapped
through the local scene/trigger whitelist, and then dispatched to the voice
action bridge.

## Current Defaults

```text
Cloud reply: Lingzhu / Claw through http://127.0.0.1:31879
Voice action bridge: http://127.0.0.1:19783
Touch audio bridge:  http://127.0.0.1:9783
Lamp target: tcp://192.168.0.183:9527
Mic:         MacBook Air麦克风
Voice:       warm_gentleman, zh-CN-YunxiNeural
Speed:       MIRA_LIGHT_ACTION_SPEED_MULTIPLIER=1.5
Mode:        enter-vad by default; continuous available through commands/
```

## Voice Light Commands

Common console actions can be spoken in Full mode:

```text
启动跳舞模式
进入睡觉
开始追踪目标
来个发呆
摸一摸
提醒我站起来
```

Emotion phrases also trigger body reactions:

```text
我今天好累啊
唉
你好可爱
我现在很开心
我有点困了
刚刚有点吓到
```

See:

```text
docs/VOICE-LIGHT-COMMANDS.md
```

## What "Ready" Means

This folder includes the voice runtime, cloud config, local bridge, scene
runtime, bus-servo adapter, and voice command mappings.

On a new Mac it can set itself up through `commands/Setup.command`, but the Mac
still needs normal system capabilities:

```text
python3.11 or python3
ssh
afplay
say
node + node-edge-tts for the good voice
expect for password-based SSH tunnel startup
```

Full lamp control still requires the new Mac to reach the lamp network target:

```text
192.168.31.10:9527
```

Cloud chat can work even if the lamp network is unreachable.

## Private Config

The package includes private config under:

```text
config/mira-light-realtime.env
config/private/
```

Do not publish this folder or upload it to a public repository.
