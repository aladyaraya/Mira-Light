param(
  [string]$Audio = "",
  [string]$Output = "",
  [string]$ApiKey = "2WcabYRkNMTItdTCWadH6LVyD11jMfVszsXsDXIXQCwwc4WEEZNMfqJP8SpHYI152",
  [string]$Hotwords = "",
  [string]$Endpoint = "",
  [string]$Model = "stepaudio-2.5-asr",
  [string]$Language = "zh",
  [int]$TimeoutSeconds = 120,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$ScriptPath = Join-Path $VoiceDir "scripts\stepfun_asr_client.py"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

if ($Audio.Trim().Length -eq 0) {
  $RuntimeDir = Join-Path $VoiceDir "runtime\windows-voice-capture"
  $LatestAudio = Get-ChildItem -Path $RuntimeDir -Recurse -Filter "input.wav" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $LatestAudio) {
    throw "No captured input.wav found. Run Start-Mira-Light-Windows-Mic-Capture.ps1 first."
  }
  $Audio = $LatestAudio.FullName
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$ArgsList = @(
  $ScriptPath,
  "--audio", $Audio,
  "--model", $Model,
  "--language", $Language,
  "--timeout-seconds", "$TimeoutSeconds"
)

if ($Output.Trim().Length -gt 0) {
  $ArgsList += @("--output", $Output)
}
if ($ApiKey.Trim().Length -gt 0) {
  $ArgsList += @("--api-key", $ApiKey)
}
if ($Hotwords.Trim().Length -gt 0) {
  $ArgsList += @("--hotwords", $Hotwords)
}
if ($Endpoint.Trim().Length -gt 0) {
  $ArgsList += @("--endpoint", $Endpoint)
}
if ($DryRun) {
  $ArgsList += "--dry-run"
}

Write-Host "== Mira Light StepFun ASR =="
Write-Host "Python: $Python"
Write-Host "Script: $ScriptPath"
Write-Host "Audio:  $Audio"
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
