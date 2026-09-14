# Troubleshooting

## Script Fails With `ModuleNotFoundError: sounddevice`

The `.venv` is missing dependencies or was created with the wrong Python.

Use Python 3.11:

```bash
rm -rf .venv
python3.11 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements.txt
```

## `mlx` Installs But Fails To Load

If you see an error like:

```text
Symbol not found: _cblas_cgemm$NEWLAPACK
built for macOS 13.5 which is newer than running OS
```

upgrade macOS to 13.5 or newer.

The current machine was on macOS 13.0, which is too old for the available MLX
wheel.

## No Bluetooth Microphone In `--list-inputs`

Check macOS System Settings:

- Bluetooth device is connected.
- Input device is set to the Bluetooth microphone.
- The browser or Terminal has microphone permission if macOS prompts for it.

Then run:

```bash
scripts/run_mira_realtime_voice_interaction.sh --list-inputs
```

Use the exact listed name:

```bash
scripts/mira-talk-open.sh --device "<exact device name>" --no-trigger
```

## No Speaker Output

First confirm the Mac output device is the Bluetooth speaker.

Then test direct system speech:

```bash
say "你好，我是 Mira。"
```

If `say` works, the runtime fallback should also work.

If you need the richer voice preset, add a `speaker-preferred-tts-play` or
`speaker-beosound-tts-play` helper later.

## Replies Use The Wrong Model

Check OpenClaw:

```bash
openclaw models status --json
openclaw agents list --json
```

Without `~/.openclaw/mira-light-realtime.env`, the runtime defaults to direct
OpenClaw agent replies.

With the env file and Lingzhu values, it uses the Lingzhu adapter route.

## Voice Is Too Sensitive Or Cuts Off Early

Use manual mode first:

```bash
scripts/mira-talk-manual.sh --device "Rick Beosound A1" --no-trigger
```

If continuous mode cuts off too early, increase `--vad-end-ms`:

```bash
scripts/mira-talk-open.sh \
  --device "Rick Beosound A1" \
  --vad-end-ms 900 \
  --no-trigger
```

If latency is too high, reduce it:

```bash
scripts/mira-talk-open.sh \
  --device "Rick Beosound A1" \
  --vad-end-ms 400 \
  --profile fast \
  --no-trigger
```

