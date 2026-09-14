# Mira Light Voice Cloud Ready

This folder is a portable Mira Light voice runtime package. It is designed so a
new Mac can start with the cloud Claw route first.

## What Works

- Cloud Claw route through the Lingzhu live adapter.
- Local microphone capture and MLX Whisper STT.
- Edge TTS voice helpers when `node-edge-tts` is available.
- macOS `say` fallback when Edge TTS is not installed.
- Safe mode startup with action triggers disabled.

## First Run On A New Mac

1. Open Terminal in this folder.
2. Run:

```bash
./Setup-Mira-Light-Voice.command
```

3. Configure the cloud AK:

```bash
./Configure-Mira-Light-Voice-Cloud.command
```

4. Test cloud connectivity:

```bash
./Test-Mira-Light-Voice-Cloud.command
```

5. Start safe voice mode:

```bash
./Start-Mira-Light-Voice-Cloud.command
```

You can also double-click the `.command` files in Finder.

## Files You Usually Use

- `Start-Mira-Light-Voice-Cloud.command`: chat + TTS only, no Mira Light actions.
- `Start-Mira-Light-Voice-Cloud-Full.command`: full mode; action triggers enabled.
- `Start-Mira-Light-Bridge.command`: starts/reuses only the local Mira Light bridge.
- `Test-Mira-Light-Bridge.command`: starts/reuses the local bridge and prints health.
- `Setup-Mira-Light-Voice.command`: creates `.venv`, installs Python deps and TTS helpers.
- `Configure-Mira-Light-Voice-Cloud.command`: writes `config/mira-light-realtime.env`.
- `Test-Mira-Light-Voice-Cloud.command`: checks tunnel and cloud chat.
- `Install-Local-Mira-Voice-Spark.command`: optional local OpenClaw agent setup.
- `Start-Mira-Light-Voice-Local.command`: optional local model route.
- `Test-Mira-Light-Voice-Local.command`: optional local route connectivity test.

## Included Secret

This package includes the private env and OpenClaw model config from `0519`.
Cloud chat uses:

```bash
MIRA_LIGHT_LINGZHU_AUTH_AK
```

The active file is:

```text
config/mira-light-realtime.env
```

That file contains private credentials and should stay local to trusted
machines. If `Test-Mira-Light-Voice-Cloud.command` returns `401 unauthorized`,
the included AK is present but not accepted by the current cloud service; run
`Configure-Mira-Light-Voice-Cloud.command` and enter a fresh AK.

## Default Device

The default microphone is:

```text
MacBook Air麦克风
```

To use another microphone for one run:

```bash
MIRA_LIGHT_MIC_DEVICE="MacBook Air麦克风" ./Start-Mira-Light-Voice-Cloud.command
```

## Voice

The preferred dynamic voice path is:

```text
speaker-preferred-tts-play -> node-edge-tts -> afplay
```

The default preset is:

```text
warm_gentleman: zh-CN-YunxiNeural, rate -6%, pitch -6%
```

If Node or Edge TTS is missing, the helper falls back to macOS `say`.

The previous female preset is backed up in:

```text
config/voice-presets-backup-2026-05-19.md
```

## Notes

- Use safe mode first on a new computer.
- Full mode now auto-starts the local Mira Light bridge before voice starts.
- Full mode still expects the lamp network target to be reachable.
- Voice control phrases are listed in `docs/VOICE-LIGHT-COMMANDS.md`.
- If cloud test says `unauthorized`, the AK is missing or wrong.
- This folder also includes the `mira-voice-spark` workspace from `0519`, so
  local OpenClaw mode can be installed later without another archive.
