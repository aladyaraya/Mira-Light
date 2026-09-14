# TTS And Speaker Output Options

Mira Light can speak through several layers. The runtime chooses the best
available local command.

## Current Fallback

If no `speaker-*` helper exists, the runtime uses:

```text
/usr/bin/say
```

This plays through the macOS default output device. If the Bluetooth speaker is
selected as the default output, speech comes out of that speaker.

This fallback is enough for basic testing.

## Voice Modes

The runtime accepts:

```text
gentle_sister
warm_gentleman
female
male
```

`female` maps to `gentle_sister`.

`male` maps to `warm_gentleman`.

With proper Edge TTS helpers, the intended presets are:

```text
gentle_sister -> zh-CN-XiaoyiNeural, rate -12%, pitch -20%
warm_gentleman -> zh-CN-YunxiNeural, rate -6%, pitch -6%
```

Without those helpers, both modes fall back to macOS `say`.

## Optional Helper Commands

For richer voice presets, install or recreate one of these helper families:

```text
speaker-preferred-tts-play
speaker-beosound-tts-play
speaker-hp-tts-play
speaker-builtin-tts-play
```

The helper should accept arguments in the shape used by
`scripts/mira_light_audio.py`:

```bash
speaker-preferred-tts-play \
  --voice zh-CN-XiaoyiNeural \
  --lang zh-CN \
  zh-CN \
  --rate -12% \
  --pitch -20% \
  "你好，我是 Mira。"
```

If helper creation is not urgent, leave it for later and use `say` first.

## Prerecorded Assets

The package includes prerecorded booth lines under:

```text
assets/audio/speech/
```

When a reply matches a known preset line, `AudioCuePlayer` can play the local
asset directly instead of generating TTS.

