param(
  [string]$Device = "",
  [ValidateSet("fixed", "vad", "ptt")]
  [string]$Mode = "vad",
  [double]$Seconds = 5.0,
  [string]$ApiKey = "",
  [string]$Endpoint = "",
  [string]$Model = "stepaudio-2.5-realtime",
  [string]$Voice = "wenrounansheng",
  [string]$ProxyUrl = "",
  [int]$SampleRate = 16000,
  [int]$ChunkMs = 100,
  [int]$TimeoutSeconds = 120,
  [int]$OutputSampleRate = 24000,
  [switch]$Play,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$RuntimeDir = Join-Path $VoiceDir "runtime\windows-voice-realtime"
$Timestamp = Get-Date -Format "yyyy-MM-ddTHH-mm-ss-ffffff"
$TurnDir = Join-Path $RuntimeDir $Timestamp
$AudioPath = Join-Path $TurnDir "input.wav"
$RealtimePath = Join-Path $TurnDir "transcript.realtime.json"
$CaptureLauncher = Join-Path $RootDir "Start-Mira-Light-Windows-Mic-Capture.ps1"
$RealtimeLauncher = Join-Path $RootDir "Start-Mira-Light-StepFun-Realtime.ps1"

New-Item -ItemType Directory -Path $TurnDir -Force | Out-Null

Write-Host "== Mira Light Windows Voice Realtime Turn =="
Write-Host "Turn:   $TurnDir"
Write-Host "Audio:  $AudioPath"
Write-Host "Output: $RealtimePath"
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

$RealtimeArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $RealtimeLauncher,
  "-Audio", $AudioPath,
  "-Output", $RealtimePath,
  "-Model", $Model,
  "-Voice", $Voice,
  "-ChunkMs", "$ChunkMs",
  "-TimeoutSeconds", "$TimeoutSeconds",
  "-OutputSampleRate", "$OutputSampleRate"
)
if ($ApiKey.Trim().Length -gt 0) {
  $RealtimeArgs += @("-ApiKey", $ApiKey)
}
if ($Endpoint.Trim().Length -gt 0) {
  $RealtimeArgs += @("-Endpoint", $Endpoint)
}
if ($ProxyUrl.Trim().Length -gt 0) {
  $RealtimeArgs += @("-ProxyUrl", $ProxyUrl)
}
if ($Play) {
  $RealtimeArgs += "-Play"
}
if ($DryRun) {
  $RealtimeArgs += "-DryRun"
}

& powershell @RealtimeArgs
if ($LASTEXITCODE -ne 0) {
  throw "StepFun realtime failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Voice realtime turn complete."
Write-Host "Audio:      $AudioPath"
Write-Host "Transcript: $RealtimePath"
