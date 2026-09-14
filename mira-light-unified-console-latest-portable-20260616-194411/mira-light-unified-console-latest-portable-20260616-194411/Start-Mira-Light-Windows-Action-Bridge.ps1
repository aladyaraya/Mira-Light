param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 19783,
  [string]$BaseUrl = "tcp://192.168.0.183:9527",
  [string]$Config = "",
  [switch]$Background,
  [switch]$RuntimeDryRun,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"

# Allow all scenes including experimental ones
$env:MIRA_LIGHT_SHOW_EXPERIMENTAL = "1"
$BridgeScript = Join-Path $VoiceDir "tools\mira_light_bridge\bridge_server.py"
$DefaultConfig = Join-Path $VoiceDir "tools\mira_light_bridge\bridge_config.json"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"
$LogDir = Join-Path $VoiceDir "runtime\logs"
$LogPath = Join-Path $LogDir "mira-light-action-bridge.log"
$ErrLogPath = Join-Path $LogDir "mira-light-action-bridge.err.log"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

if ($Config.Trim().Length -eq 0) {
  $Config = $DefaultConfig
}

$BridgeUrl = "http://${HostName}:$Port"
$ArgsList = @(
  $BridgeScript,
  "--config", $Config,
  "--host", $HostName,
  "--port", "$Port",
  "--base-url", $BaseUrl
)
if ($RuntimeDryRun) {
  $ArgsList += "--dry-run"
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

function Get-BridgeHealth([string]$Url) {
  try {
    $payload = Invoke-RestMethod -Uri "$Url/health" -TimeoutSec 1
    if ($payload.ok -eq $true -and $payload.service -eq "mira-light-bridge") {
      return $payload
    }
    return $null
  } catch {
    return $null
  }
}

$Preview = [ordered]@{
  ok = $true
  dryRun = [bool]$DryRun
  runtimeDryRun = [bool]$RuntimeDryRun
  bridgeUrl = $BridgeUrl
  python = $Python
  script = $BridgeScript
  config = $Config
  baseUrl = $BaseUrl
  background = [bool]$Background
  command = ConvertTo-CommandPreview $Python $ArgsList
  healthUrl = "$BridgeUrl/health"
  logs = @{
    stdout = $LogPath
    stderr = $ErrLogPath
  }
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 8
  } else {
    Write-Host "== Mira Light Windows Action Bridge dry-run =="
    Write-Host "Bridge: $BridgeUrl"
    Write-Host "Lamp:   $BaseUrl"
    Write-Host "Command: $($Preview.command)"
  }
  exit 0
}

if (-not (Test-Path $BridgeScript)) {
  throw "Missing bridge server: $BridgeScript"
}

$ExistingHealth = Get-BridgeHealth $BridgeUrl
if ($null -ne $ExistingHealth) {
  $ExistingRuntimeDryRun = [bool]$ExistingHealth.runtime.dryRun
  if ($RuntimeDryRun -and -not $ExistingRuntimeDryRun) {
    $errorPayload = [ordered]@{
      ok = $false
      error = "existing bridge is not runtime dry-run"
      bridgeUrl = $BridgeUrl
      healthUrl = "$BridgeUrl/health"
      runtimeDryRun = $ExistingRuntimeDryRun
      requestedRuntimeDryRun = [bool]$RuntimeDryRun
    }
    if ($Json) {
      $errorPayload | ConvertTo-Json -Depth 8
      exit 3
    }
    throw "$($errorPayload.error): $BridgeUrl. Stop it first or use a different -Port."
  }
  if ($Json) {
    ([ordered]@{
      ok = $true
      reused = $true
      bridgeUrl = $BridgeUrl
      healthUrl = "$BridgeUrl/health"
      runtimeDryRun = $ExistingRuntimeDryRun
    }) | ConvertTo-Json -Depth 8
  } else {
    Write-Host "[action-bridge] already healthy at $BridgeUrl"
  }
  exit 0
}

if ($Background) {
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  $Process = Start-Process `
    -FilePath $Python `
    -ArgumentList $ArgsList `
    -WorkingDirectory $VoiceDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogPath `
    -RedirectStandardError $ErrLogPath `
    -PassThru

  $Ready = $false
  $ReadyHealth = $null
  for ($i = 0; $i -lt 80; $i++) {
    $ReadyHealth = Get-BridgeHealth $BridgeUrl
    if ($null -ne $ReadyHealth) {
      $Ready = $true
      break
    }
    if ($Process.HasExited) {
      break
    }
    Start-Sleep -Milliseconds 250
  }

  if (-not $Ready) {
    $errorText = "action bridge did not become healthy at $BridgeUrl"
    if ($Process.HasExited) {
      $errorText = "$errorText; process exited with code $($Process.ExitCode)"
    }
    if ($Json) {
      ([ordered]@{ ok = $false; error = $errorText; bridgeUrl = $BridgeUrl; logs = $Preview.logs }) | ConvertTo-Json -Depth 8
      exit 2
    }
    throw "$errorText. See $LogPath and $ErrLogPath"
  }

  $StartedRuntimeDryRun = [bool]$ReadyHealth.runtime.dryRun
  if ($RuntimeDryRun -and -not $StartedRuntimeDryRun) {
    $errorText = "action bridge became healthy but is not runtime dry-run at $BridgeUrl"
    if ($Json) {
      ([ordered]@{
        ok = $false
        error = $errorText
        bridgeUrl = $BridgeUrl
        runtimeDryRun = $StartedRuntimeDryRun
        requestedRuntimeDryRun = [bool]$RuntimeDryRun
        logs = $Preview.logs
      }) | ConvertTo-Json -Depth 8
      exit 3
    }
    throw "$errorText. See $LogPath and $ErrLogPath"
  }

  if ($Json) {
    ([ordered]@{
      ok = $true
      started = $true
      pid = $Process.Id
      bridgeUrl = $BridgeUrl
      healthUrl = "$BridgeUrl/health"
      runtimeDryRun = $StartedRuntimeDryRun
      logs = $Preview.logs
    }) | ConvertTo-Json -Depth 8
  } else {
    Write-Host "[action-bridge] started at $BridgeUrl"
    Write-Host "[action-bridge] log $LogPath"
  }
  exit 0
}

Write-Host "== Mira Light Windows Action Bridge =="
Write-Host "Python: $Python"
Write-Host "Script: $BridgeScript"
Write-Host "Bridge: $BridgeUrl"
Write-Host "Lamp:   $BaseUrl"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
