Hermes is installed locally under `tools/hermes-agent`.

This profile is scoped by `HERMES_HOME=tools/hermes-mira-home`.

Mira runtime soul files live under `Mira-Light-Voice-Full-Ready/tools/openclaw_agents/mira_voice_spark_workspace`.

The desired minimum loop is speech transcript -> LLM understanding -> short Mira reply -> existing action group -> lamp movement.

Hermes venv was created on 2026-06-21 via `uv venv --python 3.11` + `uv pip install -e .` inside `tools/hermes-agent`. Python 3.11.7, hermes-agent 0.17.0. The executable is at `tools/hermes-agent/.venv/Scripts/hermes.exe`.

`hermes doctor` passed: Python env, required packages, SSL, config.yaml, directory structure, and external tools (git, ripgrep, Node.js) all green. The `.env` file is not yet created and config version is v0 (v30 available) — non-blocking for voice interaction.

Launch Mira voice agent via `Start-Mira-Hermes-Agent.ps1` from the project root. The launcher maps `STEPFUN_API_KEY` to `OPENAI_API_KEY` in memory. Model is `step-3.7-flash` via `https://api.stepfun.com/v1` (OpenAI-compatible custom provider).

Do not write real API keys into `.env`, `config.yaml`, docs, or scripts. Set `STEPFUN_API_KEY` as a session environment variable before launching.
