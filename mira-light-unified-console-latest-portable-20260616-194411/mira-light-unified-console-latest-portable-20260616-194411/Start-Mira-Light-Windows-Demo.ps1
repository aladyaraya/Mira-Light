param(
  [ValidateSet("local-demo", "mic-demo", "stepfun-realtime", "diagnose")]
  [string]$Mode = "local-demo",
  [ValidateSet("wake", "tired", "praise", "celebrate", "farewell", "sleep")]
  [string]$Cue = "tired",
  [string]$EnvFile = "",
  [string]$BridgeUrl = "http://127.0.0.1:19783",
  [string]$BridgeHost = "127.0.0.1",
  [int]$BridgePort = 19783,
  [string]$BaseUrl = "",
  [string]$InputDevice = "",
  [double]$MicSeconds = 3,
  [switch]$StartActionBridge,
  [switch]$UseStepFun,
  [switch]$NoAudio,
  [switch]$NoPlay,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$DemoScript = Join-Path $VoiceDir "scripts\mira_shenzhen_demo.py"
$MicScript = Join-Path $VoiceDir "scripts\windows_mic_capture.py"
$RealtimeScript = Join-Path $RootDir "Start-Mira-Light-Windows-Full-Realtime.ps1"
$BridgeScript = Join-Path $RootDir "Start-Mira-Light-Windows-Action-Bridge.ps1"
$DiagnoseScript = Join-Path $RootDir "Diagnose-Mira-Board-Network.ps1"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
  $EnvFile = Join-Path $VoiceDir "config\windows-voice-stepfun.env"
}

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

function Import-SimpleEnvFile {
  param([string]$Path)
  if (-not (Test-Path $Path)) {
    return @{}
  }
  $loaded = @{}
  Get-Content $Path -Encoding utf8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
      return
    }
    if ($line.StartsWith("export ")) {
      $line = $line.Substring(7).Trim()
    }
    $parts = $line -split "=", 2
    if ($parts.Length -eq 2) {
      $key = $parts[0].Trim()
      $val = $parts[1].Trim().Trim('"').Trim("'")
        if ($key) {
          [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
          $loaded[$key] = $val
        }
    }
  }
  return $loaded
}

$LoadedEnv = Import-SimpleEnvFile -Path $EnvFile

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = $env:MIRA_LIGHT_LAMP_BASE_URL
}
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = "tcp://192.168.0.183:9527"
}

if ([string]::IsNullOrWhiteSpace($InputDevice)) {
  $InputDevice = $env:MIRA_LIGHT_INPUT_DEVICE
}
if ([string]::IsNullOrWhiteSpace($InputDevice)) {
  $InputDevice = $env:MIRA_LIGHT_WINDOWS_MIC_DEVICE
}
if ([string]::IsNullOrWhiteSpace($InputDevice)) {
  $InputDevice = "default"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$BridgeCommand = @()
if ($StartActionBridge) {
  $BridgeUrl = "http://${BridgeHost}:$BridgePort"
  $BridgeCommand = @(
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $BridgeScript,
    "-HostName", $BridgeHost,
    "-Port", "$BridgePort",
    "-BaseUrl", $BaseUrl,
    "-Background"
  )
}

if ($Mode -eq "local-demo") {
  $ArgsList = @(
    $DemoScript,
    "--cue", $Cue,
    "--bridge-url", $BridgeUrl,
    "--timeout-seconds", "20"
  )
  if ($UseStepFun) { $ArgsList += "--use-stepfun" }
  if ($NoAudio) { $ArgsList += "--no-audio" }
  if ($DryRun) { $ArgsList += "--dry-run" }
  if ($Json) { $ArgsList += "--json" }
  $Command = @($Python) + $ArgsList
} elseif ($Mode -eq "mic-demo") {
  $ArgsList = @(
    $MicScript,
    "--mode", "fixed",
    "--seconds", "$MicSeconds",
    "--device", $InputDevice,
    "--json"
  )
  $Command = @($Python) + $ArgsList
} elseif ($Mode -eq "stepfun-realtime") {
  $Command = @(
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $RealtimeScript,
    "-EnvFile", $EnvFile,
    "-BridgeUrl", $BridgeUrl,
    "-ActionBridgeBaseUrl", $BaseUrl,
    "-InputDevice", $InputDevice
  )
  if ($StartActionBridge) { $Command += "-StartActionBridge" }
  if ($NoPlay) { $Command += "-NoPlay" }
  if ($DryRun) { $Command += "-DryRun" }
  if ($Json) { $Command += "-Json" }
} else {
  $Command = @(
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $DiagnoseScript,
    "-BoardHost", ($BaseUrl -replace "^tcp://", "" -replace ":.*$", ""),
    "-BoardPort", (($BaseUrl -replace "^tcp://[^:]+:", "") -as [int])
  )
  if ($DryRun) { $Command += "-DryRun" }
  if ($Json) { $Command += "-Json" }
}

$Preview = @{
  ok = $true
  dryRun = [bool]$DryRun
  mode = $Mode
  cue = $Cue
  envFile = $EnvFile
  stepfunKey = $(if ($env:STEPFUN_API_KEY -or $env:STEP_API_KEY) { "set" } else { "unset" })
  proxy = $env:STEPFUN_PROXY_URL
  bridgeUrl = $BridgeUrl
  baseUrl = $BaseUrl
  inputDevice = $InputDevice
  script = $(if ($Mode -eq "local-demo") { $DemoScript } elseif ($Mode -eq "mic-demo") { $MicScript } else { "" })
  command = ($Command -join " ")
  bridgeCommand = $(if ($BridgeCommand.Count -gt 0) { $BridgeCommand -join " " } else { "" })
  loadedEnvKeys = @($LoadedEnv.Keys | Sort-Object)
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 10
  } else {
    Write-Host "Mira Light Windows Demo dry-run"
    Write-Host "Mode: $Mode"
    Write-Host "Cue: $Cue"
    Write-Host "Bridge: $BridgeUrl"
    Write-Host "Board: $BaseUrl"
    Write-Host "Command: $($Preview.command)"
  }
  exit 0
}

if ($StartActionBridge) {
  & powershell @($BridgeCommand[1..($BridgeCommand.Count - 1)])
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

& $Command[0] @($Command[1..($Command.Count - 1)])
exit $LASTEXITCODE
