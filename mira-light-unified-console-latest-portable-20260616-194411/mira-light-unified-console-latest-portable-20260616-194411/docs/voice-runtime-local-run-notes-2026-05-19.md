# Mira Light Voice Runtime Local Run Notes

Date: 2026-05-19
Machine: Thomas's MacBook Air
Repo: `/Users/thomasjwang/Documents/GitHub/Mira-and-Mira-Light-New`

This document records the issues found while testing the Mira Light voice runtime
on this machine, plus the fixes and operational notes needed for the next run.

## Current Launchers

Two one-click launchers were added at the repository root:

```text
Start-Mira-Light-Voice.command
Start-Mira-Light-Voice-Safe.command
```

`Start-Mira-Light-Voice.command` starts the local bridge and then starts voice
runtime with action triggers enabled.

`Start-Mira-Light-Voice-Safe.command` starts the local bridge and then starts
voice runtime with `--no-trigger`, so it can test microphone, STT, reply, and TTS
without firing Mira Light scene actions.

Both launchers now default to:

```bash
--device "Rick Beosound A1"
--profile fast
--latency-preset low
```

Both launchers also put Homebrew's Node first in `PATH`:

```bash
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"
```

This avoids accidentally using the HarmonyOS-bundled Node when OpenClaw starts.

## Local Environment

A Python 3.11 virtual environment was created at:

```text
.venv/
```

Dependencies were installed from:

```text
mira-light-voice-runtime-pack-2026-05-19/source/requirements.txt
```

Working versions observed:

```text
Python 3.11.14
mlx 0.31.2
mlx-whisper 0.4.3
sounddevice 0.5.5
soundfile 0.13.1
```

`.venv/` and `runtime/` were added to `.gitignore`, because the hook/diff audit
was scanning third-party package source inside `.venv/` and reporting unrelated
comments from dependencies.

## Audio Devices

The expected Bluetooth microphone is visible:

```text
0  Rick Beosound A1  (inputs=1, default_sr=16000)
```

Other observed input devices:

```text
iFlyrecAudioDevice
MacBook Air microphone
LarkAudioDevice
OrayVirtualAudioDevice
```

The launchers use:

```bash
MIRA_LIGHT_MIC_DEVICE="Rick Beosound A1"
```

To override for one run:

```bash
MIRA_LIGHT_MIC_DEVICE="MacBook Air麦克风" ./Start-Mira-Light-Voice-Safe.command
```

## Bridge Behavior

Both launchers now ensure the local Mira Light bridge is running at:

```text
http://127.0.0.1:9783
```

If the bridge is already healthy at `/health`, the launcher reuses it.

If the bridge is not running, the launcher starts:

```text
tools/mira_light_bridge/bridge_server.py
```

The default bridge lamp target comes from:

```text
tools/mira_light_bridge/bridge_config.json
```

At test time it printed:

```text
lamp base url tcp://192.168.31.10:9527
auth env MIRA_LIGHT_BRIDGE_TOKEN present=False
memory context enabled=False
```

To test against the mock lamp instead of the physical target:

```bash
MIRA_LIGHT_USE_MOCK_LAMP=1 ./Start-Mira-Light-Voice.command
```

The mock lamp runs at:

```text
http://127.0.0.1:9791
```

## STT Delay And Whisper Model Downloads

The main startup delay observed came from using the default STT profile:

```text
STT profile: small
```

`small` maps to:

```text
mlx-community/whisper-small-mlx-q4
```

On first use, it downloaded about 197 MB from Hugging Face. The Terminal showed:

```text
Downloading ... 133M/197M
Warning: You are sending unauthenticated requests to the HF Hub.
```

This is expected on first run. The model is cached under:

```text
~/.cache/huggingface/hub/models--mlx-community--whisper-small-mlx-q4
```

The faster model is:

```text
mlx-community/whisper-tiny
```

It is cached under:

```text
~/.cache/huggingface/hub/models--mlx-community--whisper-tiny
```

The launchers now pass `--profile fast` to avoid the large `small` model during
normal testing.

## Continuous Listening Is Normal

When the Terminal stops at:

```text
[turn 001] listening...
```

the runtime is not frozen. It is waiting for speech from the selected microphone.

If it hears a quiet noise, it may skip the turn:

```text
skipped: low-energy-utterance
```

This means VAD detected a small audio event, but the RMS/peak level was too low
to treat as valid speech.

For noisy rooms or more controllable testing, use manual mode:

```bash
scripts/mira-talk-manual.sh --device "Rick Beosound A1" --no-trigger --profile fast
```

## Edge TTS Voice Helpers

The good dynamic voice is not macOS `say`. It is the Edge TTS helper path:

```text
mira-voice-spark reply text
-> scripts/mira_light_audio.py
-> speaker-preferred-tts-play / speaker-beosound-tts-play
-> node-edge-tts
-> afplay
```

This machine now has `node-edge-tts` installed globally with npm, and these
helpers were added under:

```text
~/.local/bin/speaker-preferred-tts-play
~/.local/bin/speaker-beosound-tts-play
~/.local/bin/speaker-hp-tts-play
~/.local/bin/speaker-preferred-play
~/.local/bin/speaker-beosound-play
```

`gentle_sister` now resolves to:

```bash
speaker-preferred-tts-play \
  --voice zh-CN-XiaoyiNeural \
  --lang zh-CN \
  --rate -12% \
  --pitch -20%
```

`warm_gentleman` resolves to:

```bash
speaker-preferred-tts-play \
  --voice zh-CN-YunxiNeural \
  --lang zh-CN \
  --rate -6% \
  --pitch -6%
```

The helpers play through the current macOS default output using `afplay`. Before
a live run, make sure the system output device is the intended speaker, such as
`Rick Beosound A1`.

Validation command:

```bash
speaker-preferred-tts-play --voice zh-CN-XiaoyiNeural --lang zh-CN --rate -12% --pitch -20% "你好，刚在这里，你想先聊点什么？"
```

## OpenClaw Status And Current Reply Problem

OpenClaw CLI exists:

```text
/opt/homebrew/bin/openclaw
```

Observed version:

```text
OpenClaw 2026.2.26
```

The gateway was running:

```text
127.0.0.1:18789
```

However, OpenClaw was not fully healthy for Mira voice replies.

The voice runtime default is:

```text
reply backend: openclaw-agent
reply agent: mira-voice-spark
```

But this machine's `openclaw agents list --json` did not list
`mira-voice-spark`. A direct test failed with:

```text
Unknown agent id "mira-voice-spark"
```

The default configured model was:

```text
anthropic/claude-opus-4-6
```

But Anthropic auth was missing:

```text
No API key found for provider "anthropic"
```

This means OpenClaw itself is installed and the gateway is alive, but the model
and agent config still need to be restored before Mira can get real generated
replies from OpenClaw.

## HarmonyOS Node Conflict

One runtime artifact showed OpenClaw failing with:

```text
/Users/thomasjwang/Documents/Developer/HarmonyOS/command-line-tools/tool/node/bin/node:
bad option: --disable-warning=ExperimentalWarning
```

Cause: Terminal's environment can include the HarmonyOS command-line-tools Node.
That Node is not compatible with OpenClaw's startup flags.

Fix applied in both `.command` launchers:

```bash
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"
```

Expected Node for OpenClaw:

```text
/opt/homebrew/bin/node
```

## Fallback Reply Behavior

When OpenClaw reply generation fails, the voice runtime catches the error and
uses a local fallback reply. Runtime artifacts showed:

```text
replyBackend: fallback
replyText: 我听见你了，我们继续。
```

This means STT succeeded, but OpenClaw did not produce the reply. Do not mistake
this fixed fallback sentence for a healthy model-generated response.

## Private Config And Keys

The voice runtime pack includes:

```text
mira-light-voice-runtime-pack-2026-05-19/config/private/openclaw-agent-models.json
mira-light-voice-runtime-pack-2026-05-19/config/private/mira-light-realtime.env
```

These contain real API-bearing configuration and must stay private.

The model config includes providers such as:

```text
newapi/gpt-5.2
newapi/gpt-5.4
newapi/gpt-5.3-codex
oai1/gpt-5.4
```

Do not commit these files or paste their keys into logs.

To restore the private OpenClaw model config, first back up the current config:

```bash
mkdir -p ~/.openclaw/agents/main/agent
cp ~/.openclaw/agents/main/agent/models.json \
  ~/.openclaw/agents/main/agent/models.json.bak-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
```

Then install the packed config:

```bash
cp mira-light-voice-runtime-pack-2026-05-19/config/private/openclaw-agent-models.json \
  ~/.openclaw/agents/main/agent/models.json
chmod 600 ~/.openclaw/agents/main/agent/models.json
```

Install the voice runtime env:

```bash
cp mira-light-voice-runtime-pack-2026-05-19/config/private/mira-light-realtime.env \
  ~/.openclaw/mira-light-realtime.env
chmod 600 ~/.openclaw/mira-light-realtime.env
```

Then set a usable default model:

```bash
openclaw models set newapi/gpt-5.4
```

## Mira Voice Agent Registration

The pack includes a Mira voice workspace:

```text
mira-light-voice-runtime-pack-2026-05-19/source/tools/openclaw_agents/mira_voice_spark_workspace/
```

It contains:

```text
AGENTS.md
HEARTBEAT.md
IDENTITY.md
SOUL.md
TOOLS.md
USER.md
```

Register it with OpenClaw:

```bash
openclaw agents add mira-voice-spark \
  --workspace /Users/thomasjwang/Documents/GitHub/Mira-and-Mira-Light-New/mira-light-voice-runtime-pack-2026-05-19/source/tools/openclaw_agents/mira_voice_spark_workspace \
  --model newapi/gpt-5.4 \
  --non-interactive \
  --json
```

Then verify:

```bash
openclaw agents list --json
openclaw agent --agent mira-voice-spark --thinking off --timeout 45 --json --message "请只回复：OK"
```

Expected healthy behavior: the second command returns an OpenClaw JSON response
with the reply text `OK` or equivalent.

## TTS Voice Quality

No richer Edge TTS or `speaker-*` helper was found on this machine:

```text
speaker-preferred-tts-play: not found
speaker-hp-tts-play: not found
speaker-beosound-tts-play: not found
speaker-builtin-tts-play: not found
```

The only available speech command was:

```text
/usr/bin/say
```

The fallback TTS was changed to use a Chinese macOS voice:

```bash
/usr/bin/say -v Tingting -r 175
```

The launchers set:

```bash
MIRA_LIGHT_SAY_VOICE=Tingting
MIRA_LIGHT_SAY_RATE=175
```

To try another installed Chinese voice:

```bash
MIRA_LIGHT_SAY_VOICE="Flo (中文（中国大陆）)" MIRA_LIGHT_SAY_RATE=165 ./Start-Mira-Light-Voice-Safe.command
```

Other voices observed on this machine include:

```text
Tingting
Meijia
Sinji
Flo (中文（中国大陆）)
Shelley (中文（中国大陆）)
Sandy (中文（中国大陆）)
```

For significantly better speech quality, install or recreate a
`speaker-preferred-tts-play` helper that can use the intended Edge TTS presets:

```text
gentle_sister -> zh-CN-XiaoyiNeural, rate -12%, pitch -20%
warm_gentleman -> zh-CN-YunxiNeural, rate -6%, pitch -6%
```

## Testing Commands

List input devices:

```bash
scripts/run_mira_realtime_voice_interaction.sh --list-inputs
```

Run safe voice mode:

```bash
./Start-Mira-Light-Voice-Safe.command
```

Run full voice mode with action triggers:

```bash
./Start-Mira-Light-Voice.command
```

Replay a sample audio file without action triggers:

```bash
scripts/run_mira_realtime_voice_interaction.sh \
  --file mira-light-voice-runtime-pack-2026-05-19/samples/runtime/realtime-voice-interaction/2026-04-09T16-29-28-800122/turn-001/input.wav \
  --once \
  --profile fast \
  --no-trigger \
  --dry-run-audio
```

Run focused audio tests:

```bash
PYTHONPATH="$PWD/scripts" .venv/bin/python -m unittest \
  mira-light-voice-runtime-pack-2026-05-19/source/tests/test_mira_light_audio.py -v
```

Run all packed voice tests in the integrated repo context:

```bash
PYTHONPATH="$PWD/scripts" .venv/bin/python -m unittest discover \
  -s mira-light-voice-runtime-pack-2026-05-19/source/tests -v
```

## Known Current State

Working:

- Python 3.11 environment exists.
- `mlx` and `mlx-whisper` import correctly.
- Bluetooth microphone is detected.
- Local STT can transcribe sample audio.
- Local bridge can be started by the launchers.
- Safe and full launchers exist.
- `say` fallback now uses a Chinese voice.

Still needs attention:

- Restore private OpenClaw model config if real generated replies are needed.
- Register `mira-voice-spark` with OpenClaw.
- Verify `openclaw agent --agent mira-voice-spark ...` returns a real reply.
- Consider installing a proper TTS helper for higher-quality speech than
  macOS `say`.
