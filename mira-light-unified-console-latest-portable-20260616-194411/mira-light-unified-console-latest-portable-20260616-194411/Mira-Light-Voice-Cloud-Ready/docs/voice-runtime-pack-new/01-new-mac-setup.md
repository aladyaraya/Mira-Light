# New Mac Setup

This is the recommended setup path for running Mira Light voice interaction on a
fresh Mac.

## Required Baseline

- macOS 13.5 or newer.
- Apple Silicon Mac is recommended for MLX Whisper.
- Python 3.11.
- OpenClaw CLI installed and authenticated if you want model replies.
- Bluetooth speaker/microphone paired before starting the runtime.

The known bad combination is:

- Python 3.14 for the project `.venv`.
- macOS 13.0 with current `mlx` wheels.

That combination prevents local MLX Whisper from loading.

## Repository Setup

If you are restoring from this pack, first copy `source/` into the Mira Light
repository root:

```bash
rsync -a mira-light-voice-runtime-pack-2026-05-19/source/ /path/to/Mira-Light/
```

Then from the Mira Light repository root:

```bash
rm -rf .venv
python3.11 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements.txt
```

If `python3.11` is missing, install it first. With Homebrew:

```bash
brew install python@3.11
```

Then verify:

```bash
.venv/bin/python --version
.venv/bin/python -m pip show sounddevice soundfile mlx-whisper mlx
```

## OpenClaw Model Reply Setup

If this pack includes `config/private/`, install the private config first:

```bash
mkdir -p ~/.openclaw/agents/main/agent
cp config/private/openclaw-agent-models.json ~/.openclaw/agents/main/agent/models.json
cp config/private/mira-light-realtime.env ~/.openclaw/mira-light-realtime.env
chmod 600 ~/.openclaw/agents/main/agent/models.json ~/.openclaw/mira-light-realtime.env
```

The historical booth reply route is cloud OpenClaw through the local Lingzhu
tunnel:

```text
reply-backend: lingzhu
lingzhu-base-url: http://127.0.0.1:31879
reply-agent: mira-voice-spark
reply-thinking: off
```

The tunnel target used by the old runtime was:

```text
local runtime
-> 127.0.0.1:31879
-> 43.160.239.180
-> remote Lingzhu live adapter
-> remote OpenClaw gateway / Spark
```

Important: this pack's `config/private/mira-light-realtime.env` contains the
remote SSH password for the cloud tunnel. `MIRA_LIGHT_LINGZHU_AUTH_AK` is still
blank because no reliable AK value was found on this machine. Fill it only if
the remote Lingzhu adapter requires AK auth.

Check the local OpenClaw fallback only if the cloud route is unavailable:

```bash
openclaw models status --json
openclaw agents list --json
```

To force the fallback route:

```bash
export MIRA_LIGHT_REPLY_BACKEND=openclaw-agent
```

## First Verification

List input devices:

```bash
scripts/run_mira_realtime_voice_interaction.sh --list-inputs
```

Expected shape:

```text
 0  <Bluetooth microphone name>  (inputs=1, default_sr=16000)
```

Test without action triggers:

```bash
scripts/mira-talk-open.sh --device "<Bluetooth microphone name>" --no-trigger
```

If you are in a noisy room, use the manual mode:

```bash
scripts/mira-talk-manual.sh --device "<Bluetooth microphone name>" --no-trigger
```
