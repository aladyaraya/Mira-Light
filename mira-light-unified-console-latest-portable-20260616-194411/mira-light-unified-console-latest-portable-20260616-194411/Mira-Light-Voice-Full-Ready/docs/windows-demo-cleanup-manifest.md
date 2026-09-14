# Windows Demo Cleanup Manifest

This package is not currently protected by a Git repository, so cleanup should be archive-first, not hard-delete.

Keep as primary:

- `Start-Mira-Light-Windows-Demo.ps1`
- `Start-Mira-Light-Windows-Action-Bridge.ps1`
- `Start-Mira-Light-Windows-Full-Realtime.ps1`
- `Diagnose-Mira-Board-Network.ps1`
- `Repair-Mira-Board-Network.ps1`
- `Test-Mira-Hardware-Motion-Acceptance.ps1`

Keep as diagnostic:

- `Start-Mira-Light-Windows-Full-Sync.ps1`
- `Start-Mira-Light-Windows-Mic-Capture.ps1`
- `Test-Mira-Light-Voice-Pipeline.ps1`

Archive candidates after the demo is stable:

- one-off StepFun ASR/LLM/realtime launchers
- older dialogue-only launchers
- macOS `.command` launchers in this Windows package
- `Motions_Shenzhen` `.backup`, `.pre_`, and temporary test variants

Before archiving, run:

```powershell
rg -n "script-name-or-file" .
```

Only move files that are not referenced by the primary launcher, docs, tests, or active Shenzhen console.
