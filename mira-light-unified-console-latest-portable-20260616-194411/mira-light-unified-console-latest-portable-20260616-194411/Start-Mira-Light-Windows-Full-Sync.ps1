param(
  [ValidateSet("continuous", "enter-vad", "ptt", "fixed")]
  [string]$Mode = "continuous",
  [string]$BaseUrl = "tcp://192.168.0.183:9527",
  [string]$BridgeHost = "127.0.0.1",
  [int]$BridgePort = 19783,
  [string]$InputDevice = "default",
  [int]$InputSampleRate = 16000,
  [double]$PostTtsCooldown = 0.9,
  [ValidateSet("openclaw-agent", "lingzhu", "stepfun")]
  [string]$ReplyBackend = "stepfun",
  [string]$ReplyAgent = "mira-voice-spark",
  [string]$VoiceMode = "warm_gentleman",
  [double]$SkipLowRms = 0.0045,
  [double]$SkipLowPeak = 0.04,
  [double]$MinSpeechCv = 0.35,
  [switch]$NoPlay,
  [switch]$NoTrigger,
  [switch]$DryRunBridge,
  [switch]$DryRun,
  [switch]$Json,
  [switch]$Help
)

if ($Help) {
  Write-Host "== MIRA Light Windows Full Sync & Fallback Voice Loop =="
  Write-Host "Usage: .\Start-Mira-Light-Windows-Full-Sync.ps1 [-Mode continuous] [-ReplyBackend openclaw-agent]"
  exit 0
}

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$EnvFile = Join-Path $VoiceDir "config\windows-voice-stepfun.env"
$ScriptPath = Join-Path $VoiceDir "scripts\mira_realtime_voice_interaction.py"
$BridgeScript = Join-Path $RootDir "Start-Mira-Light-Windows-Action-Bridge.ps1"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

Write-Host ""
Write-Host "###################################################"
Write-Host "  MIRA Light Windows Voice Loop: Sync & Fallback"
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

  $apiKeyDisplay = "unset"
  if ($env:STEPFUN_API_KEY) {
    $apiKeyDisplay = "set"
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

$BridgeUrl = "http://${BridgeHost}:$BridgePort"

$bridgeArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $BridgeScript,
  "-HostName", $BridgeHost,
  "-Port", "$BridgePort",
  "-BaseUrl", $BaseUrl,
  "-Background"
)
if ($DryRunBridge) {
  $bridgeArgs += "-RuntimeDryRun"
}

$ArgsList = @(
  $ScriptPath,
  "--mode", $Mode,
  "--device", $InputDevice,
  "--sample-rate", "$InputSampleRate",
  "--transcriber", "stepfun",
  "--reply-backend", $ReplyBackend,
  "--reply-agent", $ReplyAgent,
  "--voice-mode", $VoiceMode,
  "--bridge-url", $BridgeUrl,
  "--post-tts-cooldown-seconds", "$PostTtsCooldown",
  "--skip-low-rms", "$SkipLowRms",
  "--skip-low-peak", "$SkipLowPeak",
  "--min-speech-cv", "$MinSpeechCv"
)

if ($NoPlay) {
  $ArgsList += "--dry-run-audio"
}
if ($NoTrigger) {
  $ArgsList += "--no-trigger"
}

function ConvertTo-CommandPreview([string]$FilePath, [string[]]$Arguments) {
  $items = @($FilePath) + $Arguments
  return ($items | ForEach-Object {
    if ($_ -match '\s') {
      '"' + ($_ -replace '"', '\"') + '"'
    } else {
      $_
    }
  }) -join " "
}

$Preview = [ordered]@{
  ok = $true
  dryRun = [bool]$DryRun
  mode = $Mode
  inputDevice = $InputDevice
  replyBackend = $ReplyBackend
  replyAgent = $ReplyAgent
  voiceMode = $VoiceMode
  bridgeUrl = $BridgeUrl
  baseUrl = $BaseUrl
  python = $Python
  script = $ScriptPath
  bridgeCommand = ConvertTo-CommandPreview "powershell" $bridgeArgs
  command = ConvertTo-CommandPreview $Python $ArgsList
  noiseFilters = [ordered]@{
    skipLowRms = $SkipLowRms
    skipLowPeak = $SkipLowPeak
    minSpeechCv = $MinSpeechCv
  }
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 8
  } else {
    Write-Host "== MIRA Light Windows Full Sync dry-run =="
    Write-Host "Bridge: $BridgeUrl -> $BaseUrl"
    Write-Host "Voice:  $($Preview.command)"
    Write-Host "Bridge command: $($Preview.bridgeCommand)"
    Write-Host "Noise Filters: RMS Gate=$SkipLowRms Peak Gate=$SkipLowPeak Speech CV Gate=$MinSpeechCv"
  }
  exit 0
}

Write-Host "[Step 2/3] Starting Action Bridge ($BridgeUrl -> $BaseUrl)"
if ($DryRunBridge) {
  Write-Host "  (bridge dry-run mode)"
}
& powershell @bridgeArgs
if ($LASTEXITCODE -ne 0) {
  Write-Host "[bridge] ERROR: Action Bridge failed to start"
  exit 1
}
Write-Host ""

Write-Host "[Step 3/3] Starting Synchronized Voice Session"
Write-Host "  Mode:          $Mode"
Write-Host "  Device:        $InputDevice"
Write-Host "  Reply Backend: $ReplyBackend"
Write-Host "  Reply Agent:   $ReplyAgent"
Write-Host "  Voice Mode:    $VoiceMode"
Write-Host "  Bridge:        $BridgeUrl"
Write-Host "  Noise Filters: RMS Gate=$SkipLowRms Peak Gate=$SkipLowPeak Speech CV Gate=$MinSpeechCv"
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
