param(
  [switch]$ListDevices,
  [string]$Device = "",
  [ValidateSet("fixed", "vad", "ptt")]
  [string]$Mode = "vad",
  [double]$Seconds = 5.0,
  [string]$Output = "",
  [int]$SampleRate = 16000
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$ScriptPath = Join-Path $VoiceDir "scripts\windows_mic_capture.py"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$ArgsList = @($ScriptPath)
if ($ListDevices) {
  $ArgsList += "--list-devices"
} else {
  $ArgsList += @("--mode", $Mode, "--seconds", "$Seconds", "--sample-rate", "$SampleRate")
  if ($Device.Trim().Length -gt 0) {
    $ArgsList += @("--device", $Device)
  }
  if ($Output.Trim().Length -gt 0) {
    $ArgsList += @("--output", $Output)
  }
}

Write-Host "== Mira Light Windows Mic Capture =="
Write-Host "Python: $Python"
Write-Host "Script: $ScriptPath"
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
