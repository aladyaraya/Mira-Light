# Mira Voice Spark Agent Pack

Date: 2026-05-19

This package contains the `mira-voice-spark` OpenClaw agent workspace and the
Mira Light voice scripts that call it.

## What This Agent Is

`mira-voice-spark` is the reply-generation agent used by Mira Light voice mode.
It is not a Python package. It is an OpenClaw agent id backed by a workspace:

```text
tools/openclaw_agents/mira_voice_spark_workspace/
```

That workspace contains the prompt/personality files that make Mira answer in
short spoken Mandarin for TTS playback.

## Included

- `source/tools/openclaw_agents/mira_voice_spark_workspace/`
- `source/scripts/` voice scripts that call `--reply-agent mira-voice-spark`
- `source/requirements.txt`
- `reference/` copied setup docs from the larger voice runtime package
- `setup/register_mira_voice_spark.sh`
- `config/private/` API-bearing OpenClaw model/env config from this machine

## Fresh Machine Quick Setup

From the extracted pack:

```bash
rsync -a source/ /path/to/Mira-Light/
cd /path/to/Mira-Light

../mira-voice-spark-agent-pack-2026-05-19/setup/register_mira_voice_spark.sh /path/to/Mira-Light

mkdir -p ~/.openclaw/agents/main/agent ~/.openclaw/agents/mira-voice-spark/agent
cp ../mira-voice-spark-agent-pack-2026-05-19/config/private/openclaw-agent-models.json ~/.openclaw/agents/main/agent/models.json
cp ../mira-voice-spark-agent-pack-2026-05-19/config/private/openclaw-agent-models.json ~/.openclaw/agents/mira-voice-spark/agent/models.json
cp ../mira-voice-spark-agent-pack-2026-05-19/config/private/mira-light-realtime.env ~/.openclaw/mira-light-realtime.env
chmod 600 ~/.openclaw/agents/main/agent/models.json ~/.openclaw/agents/mira-voice-spark/agent/models.json ~/.openclaw/mira-light-realtime.env
```

Then verify:

```bash
openclaw agents list | grep mira-voice-spark
openclaw agent --agent mira-voice-spark --thinking off --message "你好，我今天有点累。"
```

## Sensitive Files

This archive contains live API credentials under `config/private/`. Do not
upload it to GitHub or public cloud storage.

