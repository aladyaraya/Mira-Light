# Voice Runtime Runbook

Run commands from the Mira Light repository root.

## Quick Start

Continuous open-mic mode:

```bash
scripts/mira-talk-open.sh --device "Rick Beosound A1" --no-trigger
```

Manual start, automatic end-of-speech:

```bash
scripts/mira-talk-manual.sh --device "Rick Beosound A1" --no-trigger
```

Full action-triggering mode:

```bash
scripts/mira-talk-open.sh --device "Rick Beosound A1"
```

## Modes

`continuous`:

- keeps listening;
- VAD detects speech start and end;
- best for booth reception after tuning.

`enter-vad`:

- operator presses `Enter` once to start a turn;
- VAD detects when the user stops speaking;
- better for noisy rooms.

`ptt`:

- press Enter to start and stop recording;
- useful for direct STT testing.

`fixed`:

- records a fixed number of seconds.

## Common Commands

List input devices:

```bash
scripts/run_mira_realtime_voice_interaction.sh --list-inputs
```

Use a faster STT profile:

```bash
scripts/mira-talk-open.sh --device "Rick Beosound A1" --profile fast --no-trigger
```

Use the more careful profile:

```bash
scripts/mira-talk-open.sh --device "Rick Beosound A1" --profile accurate --no-trigger
```

Lower latency VAD:

```bash
scripts/mira-talk-open.sh \
  --device "Rick Beosound A1" \
  --vad-start-ms 100 \
  --vad-end-ms 400 \
  --profile fast \
  --no-trigger
```

Replay an existing sample turn:

```bash
scripts/run_mira_realtime_voice_interaction.sh \
  --file runtime/realtime-voice-interaction/2026-04-09T13-06-20-940875/turn-001/input.wav \
  --once \
  --dry-run-audio \
  --no-trigger
```

## Runtime Artifacts

Each session writes files under:

```text
runtime/realtime-voice-interaction/<timestamp>/
```

Typical files:

```text
session.json
turn-001/input.wav
turn-001/transcript.txt
turn-001/transcript.json
turn-001/reply.txt
turn-001/reply.api.json
turn-001/reply.audio.json
turn-001/turn.json
```

These files are useful for debugging STT quality, reply behavior, and audio
playback.

