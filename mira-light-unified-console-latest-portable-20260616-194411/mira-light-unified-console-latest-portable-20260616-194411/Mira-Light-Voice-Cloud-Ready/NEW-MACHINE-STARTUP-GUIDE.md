# Mira Light Voice New Machine Startup Guide

This guide is for moving `Mira-Light-Voice-Cloud-Ready` to another Mac and
starting the cloud voice route with the least ceremony.

## Quick Answer

On this current Mac, double-clicking works directly.

On a new Mac, the folder is portable, but the first run still needs local
dependencies, microphone permission, and a working cloud tunnel. The safest
target is:

```text
Start-Mira-Light-Voice-Cloud.command
```

That mode uses cloud Claw/Lingzhu for replies and disables action triggers.
It does not require the Mira lamp bridge to be healthy.

## What Each Launcher Does

```text
Start-Mira-Light-Voice-Cloud.command
```

Cloud Claw chat + TTS only. This is the recommended first launcher on a new
machine.

```text
Start-Mira-Light-Voice-Cloud-Full.command
```

Cloud Claw chat + TTS + Mira Light action triggers. This launcher now
auto-starts the local bridge before voice starts. The lamp network target still
needs to be reachable.

```text
Start-Mira-Light-Voice-Local.command
```

Local OpenClaw route. This is optional and depends on OpenClaw being installed
and the `mira-voice-spark` agent being registered.

```text
Start-Mira-Light-Bridge.command
```

Starts or reuses only the local Mira Light bridge. Use this when you want to
test lamp control without starting voice.

## New Mac Checklist

1. Copy the whole `Mira-Light-Voice-Cloud-Ready` folder to the new Mac.
2. Open Terminal in that folder.
3. Make launchers executable:

```bash
chmod +x *.command scripts/*.sh bin/*
```

4. Install the base dependencies:

```bash
./Setup-Mira-Light-Voice.command
```

5. Test the cloud route:

```bash
./Test-Mira-Light-Lingzhu-Routes.command
```

6. If you want Full mode, test the bridge:

```bash
./Test-Mira-Light-Bridge.command
```

7. Start the safe cloud voice mode:

```bash
./Start-Mira-Light-Voice-Cloud.command
```

You can double-click the `.command` files after the first setup.

## Required System Tools

The package expects a normal macOS Terminal environment with:

```text
python3.11
ssh
afplay
say
```

For the best TTS voice, install Node and `node-edge-tts`:

```bash
brew install node
npm install -g node-edge-tts
```

For password-based SSH tunnel startup, install `expect` if it is missing:

```bash
brew install expect
```

If `node-edge-tts` is missing, the runtime falls back to macOS `say`. It will
still work, but the voice will sound much more mechanical.

## What Is Already Configured

The cloud-ready folder includes:

```text
config/mira-light-realtime.env
config/private/mira-light-realtime.env
config/private/openclaw-agent-models.json
```

These files contain private credentials. They are intentionally included for
trusted machines so the cloud route can work without hunting for old keys.

Do not publish this folder or upload it to a public repo with `config/private`.

## Cloud Route Health

The cloud route goes through:

```text
local voice runtime
-> local SSH tunnel at http://127.0.0.1:31879
-> remote Lingzhu live adapter
-> cloud/OpenClaw reply backend
```

The important test command is:

```bash
./Test-Mira-Light-Lingzhu-Routes.command
```

Healthy output should include:

```text
GET /v1/health -> 200
GET /metis/agent/api/health -> 200
POST /v1/chat -> 200
POST /metis/agent/api/sse -> 200
```

If health is 200 but chat is 401, the tunnel is fine but the AK is not accepted
by the remote adapter.

## Microphone Defaults

The launchers now force the default microphone to:

```text
MacBook Air麦克风
```

This avoids accidentally using a Bluetooth speaker microphone.

To override that behavior for one launch:

```bash
MIRA_LIGHT_FORCE_BUILTIN_MIC=0 MIRA_LIGHT_MIC_DEVICE="Rick Beosound A1" ./Start-Mira-Light-Voice-Cloud.command
```

On a different Mac, the built-in microphone name may differ. If startup says the
device was not found, list input devices:

```bash
./scripts/run_mira_realtime_voice_interaction.sh enter-vad --list-inputs
```

Then launch with the correct name:

```bash
MIRA_LIGHT_FORCE_BUILTIN_MIC=0 MIRA_LIGHT_MIC_DEVICE="MacBook Pro麦克风" ./Start-Mira-Light-Voice-Cloud.command
```

## Current Voice Setup

The current default voice is male:

```text
warm_gentleman
zh-CN-YunxiNeural
rate -6%
pitch -6%
```

The previous female voice is backed up in:

```text
config/voice-presets-backup-2026-05-19.md
```

To temporarily switch back to female:

```bash
MIRA_LIGHT_TTS_MODE=gentle_sister ./Start-Mira-Light-Voice-Cloud.command
```

The dynamic TTS chain is:

```text
scripts/mira_light_audio.py
-> speaker-preferred-tts-play
-> node-edge-tts
-> afplay
```

The helper also plays a short silent warmup before the reply audio. This helps
Bluetooth speakers avoid cutting off the first syllables.

## Interaction Mode

The launchers use `enter-vad` mode.

That means:

1. Press Enter.
2. Speak one utterance.
3. Wait for STT, cloud reply, and TTS playback.
4. Press Enter again for the next utterance.

This is more stable than continuous listening because it avoids ambient noise
being transcribed as repeated phrases.

## Latency

A normal turn may feel like a two to three second pause. The time is usually
spent in these places:

```text
VAD end wait
local MLX Whisper STT
cloud Lingzhu/Claw reply
Edge TTS generation
Bluetooth playback startup
```

The realtime script now prints per-turn timing, for example:

```text
[turn 003] timing: capture=2.430s stt=0.612s trigger=0.001s reply=0.487s tts+play=0.930s cooldown=0.250s total=4.710s
```

Use that line to decide what is slow:

```text
capture   VAD / recording wait
stt       local speech-to-text
reply     cloud model response
tts+play  Edge TTS generation and audio playback
cooldown  post-playback pause
```

## Full Mode Requirements

Full mode now starts the local bridge automatically. The startup sequence is:

```text
Start-Mira-Light-Voice-Cloud-Full.command
-> scripts/ensure_mira_light_bridge.sh
-> tools/mira_light_bridge/bridge_server.py
-> scripts/run_mira_realtime_voice_interaction.sh
```

The bridge is reused if `http://127.0.0.1:9783/health` is already healthy.
If it is not healthy, the launcher starts a local bridge and waits for health
before voice begins.

Full mode still needs more than cloud chat. It expects:

```text
local bridge at http://127.0.0.1:9783
lamp/device network reachable from the Mac
action trigger config loaded
```

The default lamp target is:

```text
tcp://192.168.31.10:9527
```

To test only the bridge:

```bash
./Test-Mira-Light-Bridge.command
```

To start only the bridge:

```bash
./Start-Mira-Light-Bridge.command
```

If bridge health is OK but actions do not move the lamp, check whether the Mac
can reach the lamp network target. For the default target:

```bash
nc -vz 192.168.31.10 9527
```

If full mode says the bridge health failed, cloud chat can still work. Start with:

```bash
./Start-Mira-Light-Voice-Cloud.command
```

Then debug the bridge separately.

## Voice Commands For Full Mode

Common console actions can now be spoken directly. Examples:

```text
启动起床
启动跳舞模式
进入睡觉
开始追踪目标
来个发呆
摸一摸
提醒我站起来
```

The phrase mapping lives in:

```text
scripts/mira_voice_intents.py
```

The human-readable command list is:

```text
docs/VOICE-LIGHT-COMMANDS.md
```

Emotional phrases also trigger body reactions:

```text
我很开心      -> celebrate
我有点困了    -> sleep
我在发呆      -> daydream
刚刚吓到我了  -> startle_sound
```

The default motion speed is 1.5x:

```text
MIRA_LIGHT_ACTION_SPEED_MULTIPLIER=1.5
```

## Common Problems

### Missing `.venv`

Run:

```bash
./Setup-Mira-Light-Voice.command
```

### Cloud Returns 401

Run:

```bash
./Test-Mira-Light-Lingzhu-Routes.command
```

If health is 200 but chat is 401, the remote adapter and local AK do not match.
The local package is not the only thing to check; the remote adapter reads its
own `authAk` from its server-side config.

### Voice Sounds Mechanical

Install Edge TTS:

```bash
brew install node
npm install -g node-edge-tts
```

Then restart the launcher.

### Bluetooth Cuts Off The Beginning

The helper already includes a short silent warmup. If the speaker still cuts the
first syllable, increase the warmup in:

```text
bin/speaker-preferred-tts-play
~/.local/bin/speaker-preferred-tts-play
```

Look for:

```text
duration_seconds = 0.18
```

### Wrong Microphone

The launchers force the built-in mic by default. If a new Mac has a different
device name, list inputs and override it:

```bash
./scripts/run_mira_realtime_voice_interaction.sh enter-vad --list-inputs
MIRA_LIGHT_FORCE_BUILTIN_MIC=0 MIRA_LIGHT_MIC_DEVICE="exact device name" ./Start-Mira-Light-Voice-Cloud.command
```

### Repeated Garbage Transcript

This usually means the microphone is hearing speaker playback, room noise, or a
bad input device. Use the built-in microphone, keep the speaker a little away
from the Mac, and keep `enter-vad` mode.

## Recommended First Test On A New Mac

Run these in order:

```bash
cd Mira-Light-Voice-Cloud-Ready
chmod +x *.command scripts/*.sh bin/*
./Setup-Mira-Light-Voice.command
./Test-Mira-Light-Lingzhu-Routes.command
./Start-Mira-Light-Voice-Cloud.command
```

When the runtime starts, look for:

```text
Claw:   cloud
Reply backend: lingzhu
Input device: MacBook Air麦克风
```

Then press Enter and speak.
