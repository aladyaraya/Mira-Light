# Mira Light Voice Preset Backup

Created: 2026-05-19 19:35:48 CST

This file backs up the voice settings before switching the default voice to the male preset.

## Previous Default

`gentle_sister`

```bash
MIRA_LIGHT_TTS_MODE=gentle_sister
MIRA_LIGHT_TTS_VOICE=zh-CN-XiaoyiNeural
MIRA_LIGHT_TTS_LANG=zh-CN
MIRA_LIGHT_TTS_RATE=-12%
MIRA_LIGHT_TTS_PITCH=-20%
```

## New Default

`warm_gentleman`

```bash
MIRA_LIGHT_TTS_MODE=warm_gentleman
MIRA_LIGHT_TTS_VOICE=zh-CN-YunxiNeural
MIRA_LIGHT_TTS_LANG=zh-CN
MIRA_LIGHT_TTS_RATE=-6%
MIRA_LIGHT_TTS_PITCH=-6%
```

## Quick Switch

To temporarily restore the previous female voice for one launch:

```bash
MIRA_LIGHT_TTS_MODE=gentle_sister ./Start-Chat.command
```
