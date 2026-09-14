# Mira Hermes Agent Setup

Hermes Agent is installed locally at:

```text
tools/hermes-agent
```

Mira's project-local Hermes profile is:

```text
tools/hermes-mira-home
```

This keeps Hermes' `SOUL.md`, `AGENTS.md`, `config.yaml`, and `memories/MEMORY.md` / `memories/USER.md` inside the Mira project instead of the global user profile.

## Run

From the project root:

```powershell
$env:STEPFUN_API_KEY="your_stepfun_key"
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Hermes-Agent.ps1
```

For a one-shot check:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Hermes-Agent.ps1 -Prompt "用 Mira 的身份说一句你是谁。"
```

## Diagnostics

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Hermes-Agent.ps1 -ConfigCheck
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Mira-Hermes-Agent.ps1 -PromptSize
```

## Model

The local profile uses StepFun as an OpenAI-compatible custom provider:

```yaml
model:
  default: "step-3.7-flash"
  provider: "custom"
  base_url: "https://api.stepfun.com/v1"
```

Hermes reads the key from `OPENAI_API_KEY`. The launcher maps `STEPFUN_API_KEY` to `OPENAI_API_KEY` in memory if `OPENAI_API_KEY` is empty.

Do not write real keys into `.env`, `config.yaml`, docs, or scripts.
