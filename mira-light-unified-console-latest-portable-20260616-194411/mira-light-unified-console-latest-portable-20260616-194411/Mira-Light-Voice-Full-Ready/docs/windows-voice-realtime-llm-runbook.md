# Mira Light Windows Realtime Voice + LLM Planner Runbook

This is the current preferred cloud path:

```text
Windows microphone
-> input.wav
-> StepAudio 2.5 Realtime
-> transcript.realtime.json
-> step-3.7-flash LLM Planner
-> plan.mira.json
```

The previous file ASR path remains available as a fallback:

```text
input.wav -> stepaudio-2.5-asr -> transcript.stepfun.json
```

## Models

```text
Voice model: stepaudio-2.5-realtime
LLM model:   step-3.7-flash
```

## Key Handling

Do not write the real API key into repo files. Use a process environment variable:

```powershell
$env:STEPFUN_API_KEY="your_api_key"
```

The code also accepts:

```powershell
$env:STEP_API_KEY="your_api_key"
```

On this Windows machine, StepFun currently works through the local SOCKS proxy:

```powershell
$env:STEPFUN_PROXY_URL="socks5h://127.0.0.1:10808"
```

You can also pass it per command with `-ProxyUrl`.

## Windows Full Realtime Mode

Use this for the integrated Full mode on Windows:

```text
Windows microphone
-> StepAudio 2.5 Realtime live WebSocket
-> Mira realtime audio reply
-> realtime voice-state events
-> step-3.7-flash bounded semantic planner
-> local scene/trigger whitelist
-> Mira Light bridge/actions
```

This is the path to use when Mira should speak and move from the same realtime voice session:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -StartActionBridge
```

Port split on Windows:

```text
http://127.0.0.1:9783   touch-audio bridge for the touch system
http://127.0.0.1:19783  voice-action bridge for scene/trigger action groups
tcp://192.168.0.183:9527 lamp servo target used by the voice-action bridge
```

You can start or inspect the action bridge by itself:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Action-Bridge.ps1 -Background -Port 19783 -BaseUrl "tcp://192.168.0.183:9527"
```

Dry-run the action bridge command without starting it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Action-Bridge.ps1 -DryRun -Json
```

For a safe preview that does not open the microphone, call StepFun, or trigger hardware:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -DryRun -Json
```

If you only want to verify realtime speech without actions:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -NoSemanticActions
```

To allow semantic actions, do not pass `-NoSemanticActions`. The final transcript
will go to `step-3.7-flash`, the plan will be validated against local
scene/trigger names, and only then will it be posted to the action bridge.

Voice-state motion hooks can be enabled by passing the unified director console URL:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Full-Realtime.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -DirectorUrl "http://127.0.0.1:8791"
```

The realtime engine still uses the Full mode safety boundary: the model cannot send raw servo angles, TCP frames, LED values, shell commands, or Python commands. It can only produce a validated `scene`, `trigger`, or `none` action.

## Interactive Dialogue Test

Use this when you want to talk with the StepAudio 2.5 Realtime model from the Windows terminal. It keeps the latest dialogue turns in the next prompt, returns Mira's text reply, and can play the returned voice audio.

This mode is only for model dialogue testing:

```text
terminal text input -> StepAudio 2.5 Realtime -> Mira text/audio reply
```

It does not call the action library, LLM Planner, motion bridge, servos, or lights.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Realtime-Dialogue.ps1 -ProxyUrl "socks5h://127.0.0.1:10808" -Play
```

At the `你 >` prompt, type your message and press Enter. Type `q`, `quit`, `exit`, `退出`, or `结束` to stop.

Expected files:

```text
Mira-Light-Voice-Full-Ready\runtime\windows-realtime-dialogue\<timestamp>\session.json
Mira-Light-Voice-Full-Ready\runtime\windows-realtime-dialogue\<timestamp>\turn-001\transcript.realtime.json
Mira-Light-Voice-Full-Ready\runtime\windows-realtime-dialogue\<timestamp>\turn-001\reply.wav
```

## Direct Mira Voice Reply Test

Use this one-shot test only to verify that StepAudio 2.5 Realtime can generate and play a voice reply without recording microphone input. It is not the interactive dialogue mode.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-StepFun-Realtime.ps1 -Prompt "请用 Mira 的语气说一句：唔？我在这里。" -ProxyUrl "socks5h://127.0.0.1:10808" -Play
```

Expected files:

```text
Mira-Light-Voice-Full-Ready\runtime\windows-voice-reply\<timestamp>\transcript.realtime.json
Mira-Light-Voice-Full-Ready\runtime\windows-voice-reply\<timestamp>\reply.wav
```

## Realtime Voice Dry Run

This records from the Windows microphone and generates a WebSocket event preview without calling StepFun:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Voice-Realtime.ps1 -Mode fixed -Seconds 5 -Device 1 -DryRun
```

Expected output folder:

```text
Mira-Light-Voice-Full-Ready\runtime\windows-voice-realtime\<timestamp>\
```

Expected files:

```text
input.wav
input.json
transcript.realtime.json
```

In dry-run mode, `input_audio_buffer.append` audio chunks are replaced with:

```text
<base64 omitted>
```

## Realtime Voice Real Call

After setting the API key:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Voice-Realtime.ps1 -Mode fixed -Seconds 5 -Device 1
```

The realtime result is written to:

```text
transcript.realtime.json
```

Important fields:

```text
summary.userTranscript
summary.assistantText
summary.audioBase64Bytes
events
```

## LLM Planner Dry Run

Use direct transcript text:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-StepFun-LLM.ps1 -Transcript "我今天好累" -DryRun
```

Or use the latest transcript JSON automatically:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-StepFun-LLM.ps1 -DryRun
```

Dry-run output previews the `step-3.7-flash` chat request and writes:

```text
plan.mira.json
```

## LLM Planner Real Call

After setting the API key:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-StepFun-LLM.ps1 -Transcript "我今天好累"
```

The LLM output is validated locally. It may only choose:

```text
action.type = scene | trigger | none
```

Scene names come from `scripts/scenes.py`. Trigger names come from `scripts/mira_voice_intents.py`.

The LLM must not output:

```text
servo angles
TCP frames
LED raw values
shell commands
Python commands
```

## Next Integration Step

Once `plan.mira.json` is stable:

```text
plan.mira.json -> local safety validator -> /v1/mira-light/run-scene or /v1/mira-light/trigger
plan.mira.json -> TTS/realtime audio playback -> Mira speaks
```
