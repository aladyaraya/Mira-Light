param(
  [string]$Audio = "",
  [string]$Prompt = "",
  [string]$Output = "",
  [string]$ApiKey = "2WcabYRkNMTItdTCWadH6LVyD11jMfVszsXsDXIXQCwwc4WEEZNMfqJP8SpHYI152",
  [string]$Endpoint = "",
  [string]$Model = "stepaudio-2.5-realtime",
  [string]$Voice = "wenrounansheng",
  [string]$ProxyUrl = "",
  [int]$ChunkMs = 100,
  [int]$TimeoutSeconds = 120,
  [int]$OutputSampleRate = 24000,
  [switch]$Play,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$ScriptPath = Join-Path $VoiceDir "scripts\stepfun_realtime_voice.py"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

if ($Prompt.Trim().Length -eq 0 -and $Audio.Trim().Length -eq 0) {
  $RuntimeDir = Join-Path $VoiceDir "runtime"
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
  "--model", $Model,
  "--voice", $Voice,
  "--chunk-ms", "$ChunkMs",
  "--timeout-seconds", "$TimeoutSeconds",
  "--output-sample-rate", "$OutputSampleRate"
)

if ($Prompt.Trim().Length -gt 0) {
  $ArgsList += @("--prompt", $Prompt)
} else {
  $ArgsList += @("--audio", $Audio)
}
if ($Output.Trim().Length -gt 0) {
  $ArgsList += @("--output", $Output)
}
if ($ApiKey.Trim().Length -gt 0) {
  $ArgsList += @("--api-key", $ApiKey)
}
if ($Endpoint.Trim().Length -gt 0) {
  $ArgsList += @("--endpoint", $Endpoint)
}
if ($ProxyUrl.Trim().Length -gt 0) {
  $ArgsList += @("--proxy-url", $ProxyUrl)
}
if ($Play) {
  $ArgsList += "--play"
}
if ($DryRun) {
  $ArgsList += "--dry-run"
}

Write-Host "== Mira Light StepFun Realtime Voice =="
Write-Host "Python: $Python"
Write-Host "Script: $ScriptPath"
if ($Prompt.Trim().Length -gt 0) {
  Write-Host "Prompt: $Prompt"
} else {
  Write-Host "Audio:  $Audio"
}
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
