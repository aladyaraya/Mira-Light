param(
  [string]$ApiKey = "",
  [string]$BaseUrl = "tcp://192.168.0.183:9527",
  [string]$BridgeHost = "127.0.0.1",
  [int]$BridgePort = 19783,
  [string]$InputDevice = "default",
  [string]$Model = "stepaudio-2.5-realtime",
  [string]$Voice = "wenrounansheng",
  [int]$InputSampleRate = 16000,
  [int]$OutputSampleRate = 24000,
  [int]$ChunkMs = 40,
  [double]$Seconds = 0,
  [switch]$NoPlay,
  [switch]$NoSemanticActions,
  [switch]$NoVoiceStateActions,
  [switch]$DryRunBridge,
  [switch]$DryRun,
  [switch]$Json,
  [switch]$Help
)

if ($Help) {
  Write-Host "== Mira Light Voice Full Pipeline =="
  Write-Host "Usage: .\Start-Mira-Light-Windows-Voice-Full-Pipeline.ps1 [-DryRunBridge] [-Seconds 10]"
  exit 0
}

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$EnvFile = Join-Path $VoiceDir "config\windows-voice-stepfun.env"
$ScriptPath = Join-Path $VoiceDir "scripts\mira_stepfun_realtime_voice_actions.py"
$BridgeScript = Join-Path $RootDir "Start-Mira-Light-Windows-Action-Bridge.ps1"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

Write-Host ""
Write-Host "###################################################"
Write-Host "  Mira Light Full Voice Pipeline"
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "###################################################"
Write-Host ""

if (Test-Path $EnvFile) {
  Write-Host "[Step 1/3] Loading config: $EnvFile"
  Get-Content $EnvFile -Encoding utf8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
      if ($line.StartsWith("export ")) { $line = $line.Substring(7) }
      $parts = $line -split "=", 2
      if ($parts.Length -eq 2) {
        $key = $parts[0].Trim()
        $val = $parts[1].Trim().Trim('"').Trim("'")
        if ($val) {
          [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
      }
    }
  }

  $apiKeyDisplay = $env:STEPFUN_API_KEY
  if ($apiKeyDisplay -and $apiKeyDisplay.Length -gt 8) {
    $apiKeyDisplay = "..." + $apiKeyDisplay.Substring($apiKeyDisplay.Length - 8)
  }
  Write-Host "  STEPFUN_API_KEY: $apiKeyDisplay"
  Write-Host "  STEPFUN_PROXY_URL: $($env:STEPFUN_PROXY_URL)"
  Write-Host "  Board: $BaseUrl"
  $pxy = $env:STEPFUN_PROXY_URL
  if ($pxy -and $pxy.Trim().Length -gt 0) {
    $env:HTTPS_PROXY = $pxy
    $env:HTTP_PROXY = $pxy
    $env:NO_PROXY = "127.0.0.1,localhost,192.168.0.183"
  } else {
    Remove-Item env:HTTPS_PROXY -ErrorAction SilentlyContinue
    Remove-Item env:HTTP_PROXY -ErrorAction SilentlyContinue
    Remove-Item env:http_proxy -ErrorAction SilentlyContinue
    Remove-Item env:https_proxy -ErrorAction SilentlyContinue
    Remove-Item env:ALL_PROXY -ErrorAction SilentlyContinue
    Remove-Item env:all_proxy -ErrorAction SilentlyContinue
  }
  Write-Host ""
} else {
  Write-Host "[Step 1/3] WARNING: Config not found: $EnvFile"
  Write-Host ""
}

if ($ApiKey.Trim().Length -gt 0) {
  $env:STEPFUN_API_KEY = $ApiKey
  $env:STEP_API_KEY = $ApiKey
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$BridgeUrl = "http://${BridgeHost}:$BridgePort"

Write-Host "[Step 2/3] Starting Action Bridge ($BridgeUrl -> $BaseUrl)"
$bridgeArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $BridgeScript,
  "-HostName", $BridgeHost,
  "-Port", "$BridgePort",
  "-BaseUrl", $BaseUrl,
  "-Background"
)
if ($DryRunBridge -or $DryRun) {
  $bridgeArgs += "-DryRun"
  Write-Host "  (dry-run mode)"
}
& powershell @bridgeArgs
if ($LASTEXITCODE -ne 0) {
  Write-Host "[bridge] ERROR: Action Bridge failed to start"
  exit 1
}
Write-Host ""

Write-Host "[Step 3/3] Starting Realtime Voice Session"
Write-Host "  Model:  $Model"
Write-Host "  Voice:  $Voice"
Write-Host "  Device: $InputDevice"
Write-Host "  Bridge: $BridgeUrl"
Write-Host ""
Write-Host "  Speak into microphone! Say 'tiao wu' / 'hao lei' / 'bai bai' to trigger actions"
Write-Host "  Press Ctrl+C to stop"
Write-Host ""

$ArgsList = @(
  $ScriptPath,
  "--model", $Model,
  "--voice", $Voice,
  "--input-device", $InputDevice,
  "--input-sample-rate", "$InputSampleRate",
  "--output-sample-rate", "$OutputSampleRate",
  "--chunk-ms", "$ChunkMs",
  "--seconds", "$Seconds",
  "--bridge-url", $BridgeUrl
)

$pxyUrl = $env:STEPFUN_PROXY_URL
if ($pxyUrl -and $pxyUrl.Trim().Length -gt 0) {
  $ArgsList += @("--proxy-url", $pxyUrl)
}

if ($NoVoiceStateActions) {
  $ArgsList += "--no-voice-state-actions"
}
if ($NoSemanticActions) {
  $ArgsList += "--no-semantic-actions"
}
if ($NoPlay) {
  $ArgsList += "--no-play"
}
if ($DryRun) {
  $ArgsList += "--dry-run"
}
if ($Json) {
  $ArgsList += "--json"
}

& $Python @ArgsList
exit $LASTEXITCODE
