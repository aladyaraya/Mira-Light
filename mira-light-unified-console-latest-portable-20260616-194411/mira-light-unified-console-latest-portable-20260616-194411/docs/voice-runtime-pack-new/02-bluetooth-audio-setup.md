# Bluetooth Audio Setup

The voice runtime treats input and output separately:

- microphone input is selected by `--device`;
- speaker output follows macOS default output unless a `speaker-*` helper is
  installed.

## Current Device Names

The current machine uses:

```text
Input:  Rick Beosound A1
Output: Rick Beosound A1
```

`sounddevice` saw:

```text
0  Rick Beosound A1  inputs=1 outputs=0 sr=16000
1  Rick Beosound A1  inputs=0 outputs=2 sr=44100
```

## Pairing On A New Mac

1. Pair the Bluetooth speaker/microphone in macOS System Settings.
2. Set it as both Input and Output.
3. Run:

```bash
scripts/run_mira_realtime_voice_interaction.sh --list-inputs
```

4. Use the exact device name in startup commands:

```bash
scripts/mira-talk-open.sh --device "Rick Beosound A1" --no-trigger
```

If the new Mac shows a different device name, replace the quoted string.

## Output Behavior

If no dedicated speaker helper exists, TTS falls back to macOS `say` and plays
through the current default output device.

That means a paired Bluetooth speaker can work without extra code as long as it
is the macOS default output.

## Optional Dedicated Speaker Helpers

The audio code looks for helper commands in this order:

```text
speaker-preferred-use
speaker-hp-use
speaker-beosound-use
speaker-builtin-use
```

For playback:

```text
speaker-preferred-play
speaker-hp-play
speaker-beosound-play
speaker-builtin-play
afplay
```

For TTS:

```text
speaker-preferred-tts-play
speaker-hp-tts-play
speaker-beosound-tts-play
speaker-builtin-tts-play
```

If these helpers are absent, basic playback still falls back to `afplay` for
files and `say` for spoken replies.

