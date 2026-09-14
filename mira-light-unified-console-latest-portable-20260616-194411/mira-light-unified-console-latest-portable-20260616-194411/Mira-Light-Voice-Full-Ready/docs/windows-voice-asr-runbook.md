# Mira Light Windows Voice ASR Runbook

This runbook covers the current Windows voice stage only:

Windows microphone -> `input.wav` -> StepFun StepAudio ASR -> transcript JSON/TXT.

## Current State

- Windows microphone capture is implemented with `sounddevice`.
- StepFun ASR request construction is implemented for `stepaudio-2.5-asr`.
- Dry-run mode is available without an API key.
- Real ASR calls require `STEPFUN_API_KEY` or `STEP_API_KEY`.
- Mary/Mira personality is not applied inside ASR. ASR only returns text; Mary behavior is carried forward in `personaContext` for the next LLM semantic layer.

## One-Turn Dry Run

Use this before the API key is available:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Voice-ASR.ps1 -Mode fixed -Seconds 5 -Device 1 -DryRun
```

This creates a new folder under:

```text
Mira-Light-Voice-Full-Ready\runtime\windows-voice-asr\<timestamp>\
```

Expected files:

```text
input.wav
input.json
transcript.stepfun.json
transcript.stepfun.txt
```

In dry-run mode, `transcript.stepfun.json` contains the StepFun request preview. The audio base64 is intentionally omitted, but its length is recorded as `request.body.audio.dataLength`.

## Real ASR Call

After the API key is available:

```powershell
$env:STEPFUN_API_KEY="your_api_key"

powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Voice-ASR.ps1 -Mode fixed -Seconds 5 -Device 1
```

The final transcript text is written to:

```text
transcript.stepfun.txt
```

The full response, events, hotwords, audio metadata, and Mary context are written to:

```text
transcript.stepfun.json
```

When inspecting JSON with Windows PowerShell 5.1, read it as UTF-8:

```powershell
$j = Get-Content .\transcript.stepfun.json -Raw -Encoding UTF8 | ConvertFrom-Json
```

## Separate Steps

Record only:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Mic-Capture.ps1 -Mode fixed -Seconds 5 -Device 1
```

ASR only, using the latest `input.wav`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-StepFun-ASR.ps1
```

ASR dry-run, using the latest `input.wav`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Light-StepFun-ASR.ps1 -DryRun
```

## Configuration

See:

```text
Mira-Light-Voice-Full-Ready\config\windows-voice-stepfun.env.example
```

Verified local microphone device:

```text
Device 1: 麦克风 (Realtek(R) Audio)
```

Default built-in ASR hotwords include:

```text
Mira, Mira Light, 米拉, Mary, 麦瑞, 场景音频, 语音交互, 动作库, 唤醒, 陪伴
```
