# Mira Light Project Agent Rules

This workspace is the Mira Light Windows project.

Hermes is installed locally under `tools/hermes-agent`, and the Mira-specific Hermes profile is `tools/hermes-mira-home`.

When working here:

- Use Chinese with the user unless asked otherwise.
- Treat Mira as a small embodied pet soul, not a generic assistant.
- Keep Mira's runtime loop minimal: transcript -> LLM understanding -> spoken reply -> existing action group -> action bridge.
- Use only bounded local action groups for motion. Do not invent raw servo angles, LED packets, or TCP hardware commands as Mira's spoken output.
- Read the existing scene/action files before changing behavior:
  - `Mira-Light-Voice-Full-Ready/scripts/scenes.py`
  - `Mira-Light-Voice-Full-Ready/scripts/mira_voice_intents.py`
  - `Mira-Light-Voice-Full-Ready/scripts/stepfun_llm_planner.py`
  - `Mira-Light-Voice-Full-Ready/scripts/mira_stepfun_realtime_voice_actions.py`
- Do not store API keys or passwords in files.
- Do not claim physical lamp motion is working unless bridge/device verification proves it.

Mira's desired personality is cute, clever, warm, slightly boy-like, physically expressive, and not over-scripted.

