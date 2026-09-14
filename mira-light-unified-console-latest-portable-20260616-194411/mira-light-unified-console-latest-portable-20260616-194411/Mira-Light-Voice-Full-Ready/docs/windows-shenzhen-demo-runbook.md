# Mira Light Shenzhen Demo Runbook

## 1. Configuration

Edit:

`Mira-Light-Voice-Full-Ready/config/windows-voice-stepfun.env`

Keep secrets and short settings in this file. Long prompts live in:

- `Mira-Light-Voice-Full-Ready/config/prompts/stepfun_llm_system_prompt.md`
- `Mira-Light-Voice-Full-Ready/config/prompts/stepfun_planner_system_prompt.md`
- `Mira-Light-Voice-Full-Ready/config/prompts/stt_initial_prompt.md`

Useful fields:

```env
STEPFUN_API_KEY=your_key
STEPFUN_PROXY_URL=socks5h://127.0.0.1:10808
MIRA_LIGHT_LAMP_BASE_URL=tcp://192.168.0.183:9527
MIRA_LIGHT_WINDOWS_MIC_DEVICE=default
MIRA_LIGHT_INPUT_DEVICE=default
MIRA_LIGHT_LLM_SYSTEM_PROMPT_FILE=config/prompts/stepfun_llm_system_prompt.md
MIRA_LIGHT_REALTIME_SYSTEM_PROMPT_FILE=config/prompts/stepfun_llm_system_prompt.md
MIRA_LIGHT_PLANNER_SYSTEM_PROMPT_FILE=config/prompts/stepfun_planner_system_prompt.md
MIRA_LIGHT_STT_INITIAL_PROMPT_FILE=config/prompts/stt_initial_prompt.md
```

## 2. P0 Local Demo

Start with dry-run:

```powershell
.\Start-Mira-Light-Windows-Demo.ps1 -Mode local-demo -Cue tired -DryRun -Json -NoAudio
```

Run a cue against the bridge:

```powershell
.\Start-Mira-Light-Windows-Demo.ps1 -Mode local-demo -Cue tired
```

Available cues:

- `wake`
- `tired`
- `praise`
- `celebrate`
- `farewell`
- `sleep`

Default behavior:

- Uses local planner: `useStepFun=false`
- Calls bridge: `http://127.0.0.1:19783/v1/mira-light/voice-lab/plan`
- Plays optional audio from `assets/audio/shenzhen_demo/`
- Does not require ASR, STT, TTS, or cloud LLM

## 3. Action Bridge

Use one primary bridge port:

```powershell
.\Start-Mira-Light-Windows-Action-Bridge.ps1 -Port 19783 -BaseUrl tcp://192.168.0.183:9527 -Background
```

Check health:

```powershell
Invoke-RestMethod http://127.0.0.1:19783/health | ConvertTo-Json -Depth 8
```

Healthy P0 signs:

- `ok` is `true`
- `dryRun` is `false`
- `baseUrl` matches the board
- `lastError` is `null` after a cue run

## 4. Board Diagnostics

Preview route/config repair:

```powershell
.\Repair-Mira-Board-Network.ps1 -BoardHost 192.168.0.183 -Gateway 192.168.123.254 -DryRun -Json
```

Check ACK path:

```powershell
.\Diagnose-Mira-Board-Network.ps1 -BoardHost 192.168.0.183 -BoardPort 9527 -Json
```

If the board IP changes, update both:

- `config/bus_servo_runtime.json`
- `config/windows-voice-stepfun.env` field `MIRA_LIGHT_LAMP_BASE_URL`

## 5. Recording Audio Assets

Record or place files in:

`Mira-Light-Voice-Full-Ready/assets/audio/shenzhen_demo/`

Expected filenames:

```text
wake.wav
tired.wav
praise.wav
celebrate.wav
farewell.wav
sleep.wav
```

Missing files do not block motion dispatch. The runner skips missing audio and still sends the cue to the bridge.

## 6. Mic Check

List devices:

```powershell
.\Start-Mira-Light-Windows-Demo.ps1 -Mode mic-demo -DryRun -Json
```

Capture a short sample:

```powershell
.\Start-Mira-Light-Windows-Demo.ps1 -Mode mic-demo -InputDevice default -MicSeconds 3
```

Use `MIRA_LIGHT_WINDOWS_MIC_DEVICE` or `MIRA_LIGHT_INPUT_DEVICE` in the env file to pin a device.

## 7. StepFun Realtime Mode

Dry-run first:

```powershell
.\Start-Mira-Light-Windows-Full-Realtime.ps1 -DryRun -Json -NoPlay
```

Or through the unified launcher:

```powershell
.\Start-Mira-Light-Windows-Demo.ps1 -Mode stepfun-realtime -DryRun -Json -NoPlay
```

StepFun mode should be treated as P2. The P0 demo should remain usable even when StepFun is slow or unavailable.

## 8. Troubleshooting Ladder

Check in this order:

1. Mic: confirm the intended input device is selected and not silent.
2. ASR/STT: confirm transcript text appears.
3. Planner: confirm local cue maps to `scene` or `trigger`.
4. Bridge: confirm `/health` and `/voice-lab/plan` respond.
5. Board: confirm `tcp://host:9527` is reachable and ACKs.
6. Servo: confirm neutral pose and one scene move real hardware.

For the Shenzhen demo, do not debug StepFun first. Prove local cue motion first, then add cloud voice.
