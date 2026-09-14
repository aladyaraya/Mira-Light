param(
  [string]$Device = "",
  [ValidateSet("fixed", "vad", "ptt")]
  [string]$Mode = "vad",
  [double]$Seconds = 5.0,
  [string]$ApiKey = "",
  [string]$Hotwords = "",
  [string]$Endpoint = "",
  [string]$Model = "stepaudio-2.5-asr",
  [string]$Language = "zh",
  [int]$SampleRate = 16000,
  [int]$TimeoutSeconds = 120,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$RuntimeDir = Join-Path $VoiceDir "runtime\windows-voice-asr"
$Timestamp = Get-Date -Format "yyyy-MM-ddTHH-mm-ss-ffffff"
$TurnDir = Join-Path $RuntimeDir $Timestamp
$AudioPath = Join-Path $TurnDir "input.wav"
$TranscriptPath = Join-Path $TurnDir "transcript.stepfun.json"
$CaptureLauncher = Join-Path $RootDir "Start-Mira-Light-Windows-Mic-Capture.ps1"
$AsrLauncher = Join-Path $RootDir "Start-Mira-Light-StepFun-ASR.ps1"

New-Item -ItemType Directory -Path $TurnDir -Force | Out-Null

Write-Host "== Mira Light Windows Voice ASR Turn =="
Write-Host "Turn:   $TurnDir"
Write-Host "Audio:  $AudioPath"
Write-Host "Output: $TranscriptPath"
Write-Host ""

$CaptureArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $CaptureLauncher,
  "-Mode", $Mode,
  "-Seconds", "$Seconds",
  "-Output", $AudioPath,
  "-SampleRate", "$SampleRate"
)
if ($Device.Trim().Length -gt 0) {
  $CaptureArgs += @("-Device", $Device)
}

& powershell @CaptureArgs
if ($LASTEXITCODE -ne 0) {
  throw "Microphone capture failed with exit code $LASTEXITCODE"
}

$AsrArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $AsrLauncher,
  "-Audio", $AudioPath,
  "-Output", $TranscriptPath,
  "-Model", $Model,
  "-Language", $Language,
  "-TimeoutSeconds", "$TimeoutSeconds"
)
if ($ApiKey.Trim().Length -gt 0) {
  $AsrArgs += @("-ApiKey", $ApiKey)
}
if ($Hotwords.Trim().Length -gt 0) {
  $AsrArgs += @("-Hotwords", $Hotwords)
}
if ($Endpoint.Trim().Length -gt 0) {
  $AsrArgs += @("-Endpoint", $Endpoint)
}
if ($DryRun) {
  $AsrArgs += "-DryRun"
}

& powershell @AsrArgs
if ($LASTEXITCODE -ne 0) {
  throw "StepFun ASR failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Voice ASR turn complete."
Write-Host "Audio:      $AudioPath"
Write-Host "Transcript: $TranscriptPath"
