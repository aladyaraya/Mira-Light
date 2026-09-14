param(
  [string]$ApiKey = "",
  [string]$Endpoint = "",
  [string]$Model = "stepaudio-2.5-realtime",
  [string]$Voice = "wenrounansheng",
  [string]$ProxyUrl = "",
  [int]$TimeoutSeconds = 120,
  [int]$OutputSampleRate = 24000,
  [int]$HistoryTurns = 6,
  [string]$OutputDir = "",
  [switch]$Play
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$ScriptPath = Join-Path $VoiceDir "scripts\mira_realtime_dialogue_console.py"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$ArgsList = @(
  $ScriptPath,
  "--model", $Model,
  "--voice", $Voice,
  "--timeout-seconds", "$TimeoutSeconds",
  "--output-sample-rate", "$OutputSampleRate",
  "--history-turns", "$HistoryTurns"
)

if ($ApiKey.Trim().Length -gt 0) {
  $ArgsList += @("--api-key", $ApiKey)
}
if ($Endpoint.Trim().Length -gt 0) {
  $ArgsList += @("--endpoint", $Endpoint)
}
if ($ProxyUrl.Trim().Length -gt 0) {
  $ArgsList += @("--proxy-url", $ProxyUrl)
}
if ($OutputDir.Trim().Length -gt 0) {
  $ArgsList += @("--output-dir", $OutputDir)
}
if ($Play) {
  $ArgsList += "--play"
}

Write-Host "== Mira Light Realtime Dialogue =="
Write-Host "Python: $Python"
Write-Host "Script: $ScriptPath"
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
