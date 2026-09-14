# Register mira-voice-spark

`mira-voice-spark` must be registered in OpenClaw before the voice runtime can
use it as `--reply-agent mira-voice-spark`.

## 1. Copy Files Into The Mira Light Repo

From the extracted pack:

```bash
rsync -a source/ /path/to/Mira-Light/
cd /path/to/Mira-Light
```

The agent workspace should then exist at:

```text
/path/to/Mira-Light/tools/openclaw_agents/mira_voice_spark_workspace/
```

## 2. Register The Agent

```bash
openclaw agents add mira-voice-spark \
  --workspace /path/to/Mira-Light/tools/openclaw_agents/mira_voice_spark_workspace \
  --agent-dir ~/.openclaw/agents/mira-voice-spark/agent \
  --model newapi/gpt-5.4 \
  --non-interactive
```

Or run:

```bash
setup/register_mira_voice_spark.sh /path/to/Mira-Light
```

## 3. Install Model/API Config

```bash
mkdir -p ~/.openclaw/agents/main/agent ~/.openclaw/agents/mira-voice-spark/agent
cp config/private/openclaw-agent-models.json ~/.openclaw/agents/main/agent/models.json
cp config/private/openclaw-agent-models.json ~/.openclaw/agents/mira-voice-spark/agent/models.json
cp config/private/mira-light-realtime.env ~/.openclaw/mira-light-realtime.env
chmod 600 ~/.openclaw/agents/main/agent/models.json ~/.openclaw/agents/mira-voice-spark/agent/models.json ~/.openclaw/mira-light-realtime.env
```

## 4. Verify

```bash
openclaw agents list | grep mira-voice-spark
openclaw agent --agent mira-voice-spark --thinking off --message "你好，我今天有点累。"
```

Expected behavior: the reply should be short, gentle, and in spoken Mandarin.

