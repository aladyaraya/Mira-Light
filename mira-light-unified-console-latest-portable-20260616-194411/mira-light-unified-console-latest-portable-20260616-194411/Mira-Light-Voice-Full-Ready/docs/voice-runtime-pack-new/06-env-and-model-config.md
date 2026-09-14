# Environment And Model Configuration

The startup wrapper reads this optional file:

```text
~/.openclaw/mira-light-realtime.env
```

This pack includes a template at:

```text
config/mira-light-realtime.env.example
```

This repacked archive also includes private API-bearing files at:

```text
config/private/openclaw-agent-models.json
config/private/mira-light-realtime.env
```

Install them on a new Mac with:

```bash
mkdir -p ~/.openclaw/agents/main/agent
cp config/private/openclaw-agent-models.json ~/.openclaw/agents/main/agent/models.json
cp config/private/mira-light-realtime.env ~/.openclaw/mira-light-realtime.env
chmod 600 ~/.openclaw/agents/main/agent/models.json ~/.openclaw/mira-light-realtime.env
```

These files contain live API credentials. Keep the archive private.

## Historical Cloud OpenClaw Route

The booth runtime used cloud OpenClaw through a local Lingzhu tunnel:

```bash
export MIRA_LIGHT_REPLY_BACKEND=lingzhu
export MIRA_LIGHT_REPLY_AGENT=mira-voice-spark
export MIRA_LIGHT_REPLY_THINKING=off
export MIRA_LIGHT_LINGZHU_BASE_URL=http://127.0.0.1:31879
export MIRA_LIGHT_LINGZHU_AUTO_TUNNEL=1
export MIRA_LIGHT_LINGZHU_AGENT_ID=main
export MIRA_LIGHT_LINGZHU_ADDITIONAL_USER_IDS=mira-light-bridge
export MIRA_LIGHT_LINGZHU_REMOTE_HOST=43.160.239.180
export MIRA_LIGHT_LINGZHU_REMOTE_USER=ubuntu
export MIRA_LIGHT_LINGZHU_REMOTE_TARGET_HOST=127.0.0.1
export MIRA_LIGHT_LINGZHU_REMOTE_TARGET_PORT=18789
```

This resolves as:

```text
local runtime
-> local SSH tunnel 127.0.0.1:31879
-> remote Lingzhu live adapter
-> remote OpenClaw gateway / Spark
```

The packaged private env includes the remote SSH password for the tunnel.
`MIRA_LIGHT_LINGZHU_AUTH_AK` is intentionally blank because no reliable AK value
was found on this machine:

```bash
export MIRA_LIGHT_LINGZHU_REMOTE_PASSWORD="<remote SSH password in private env>"
export MIRA_LIGHT_LINGZHU_AUTH_AK=
```

Only fill `MIRA_LIGHT_LINGZHU_AUTH_AK` if the remote Lingzhu adapter requires AK
auth.

## Local OpenClaw Agent Fallback

Use this only if the cloud Lingzhu route is unavailable:

```bash
export MIRA_LIGHT_REPLY_BACKEND=openclaw-agent
export MIRA_LIGHT_REPLY_AGENT=mira-voice-spark
export MIRA_LIGHT_REPLY_THINKING=off
```

## Device Defaults

The current machine used:

```bash
export MIRA_LIGHT_MIC_DEVICE="Rick Beosound A1"
```

On the new computer, replace it with the exact name printed by:

```bash
scripts/run_mira_realtime_voice_interaction.sh --list-inputs
```

## Voice Defaults

```bash
export MIRA_LIGHT_TTS_MODE=gentle_sister
export MIRA_LIGHT_LATENCY_PRESET=low
```

`gentle_sister` and `warm_gentleman` only get their intended Edge TTS voices if
the `speaker-*` TTS helper commands exist. Without helpers, macOS `say` is used.
