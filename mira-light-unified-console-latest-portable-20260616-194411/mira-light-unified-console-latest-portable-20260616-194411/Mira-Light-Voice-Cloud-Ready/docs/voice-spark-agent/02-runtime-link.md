# How The Voice Runtime Uses This Agent

The historical booth runtime used cloud OpenClaw through the local Lingzhu
tunnel:

```text
MIRA_LIGHT_REPLY_BACKEND=lingzhu
MIRA_LIGHT_REPLY_AGENT=mira-voice-spark
MIRA_LIGHT_REPLY_THINKING=off
MIRA_LIGHT_LINGZHU_BASE_URL=http://127.0.0.1:31879
MIRA_LIGHT_LINGZHU_AUTO_TUNNEL=1
```

The relevant defaults are in:

- `source/scripts/mira_realtime_voice_interaction.py`
- `source/scripts/mira_realtime_claw_chat.py`

With the Lingzhu route active, the command flow is:

```text
local voice runtime
-> local SSH tunnel 127.0.0.1:31879
-> remote Lingzhu live adapter
-> remote OpenClaw gateway / Spark
```

The direct `openclaw agent --agent mira-voice-spark` path is only the local
fallback if the cloud route is unavailable.

For Bluetooth voice mode, after the Python 3.11 environment and audio
dependencies are installed:

```bash
scripts/mira-talk-open.sh --device "Rick Beosound A1" --no-trigger
```

Manual start / auto stop:

```bash
scripts/mira-talk-manual.sh --device "Rick Beosound A1" --no-trigger
```

Full action-triggering mode:

```bash
scripts/mira-talk-open.sh --device "Rick Beosound A1"
```

If the Bluetooth device name is different on the new computer, replace
`Rick Beosound A1` with the exact name shown by:

```bash
scripts/run_mira_realtime_voice_interaction.sh --list-inputs
```
