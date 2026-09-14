param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 19783,
  [string]$BaseUrl = "tcp://192.168.0.183:9527",
  [switch]$NoSmoke,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$BridgeScript = Join-Path $VoiceDir "tools\mira_light_bridge\bridge_server.py"
$DefaultConfig = Join-Path $VoiceDir "tools\mira_light_bridge\bridge_config.json"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"
$LogDir = Join-Path $VoiceDir "runtime\logs"
$LogPath = Join-Path $LogDir "mira-light-simplest-bridge.log"
$ErrLogPath = Join-Path $LogDir "mira-light-simplest-bridge.err.log"
$BridgeUrl = "http://${HostName}:$Port"

if (-not (Test-Path -LiteralPath $BridgeScript)) {
  throw "Missing bridge server: $BridgeScript"
}

if (Test-Path -LiteralPath $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

function Get-MiraSimplestHealth([string]$Url) {
  try {
    return Invoke-RestMethod -Uri "$Url/health" -TimeoutSec 1
  } catch {
    return $null
  }
}

$Process = $null
$ExistingHealth = Get-MiraSimplestHealth $BridgeUrl

if ($null -ne $ExistingHealth -and $ExistingHealth.ok -eq $true) {
  if (-not [bool]$ExistingHealth.runtime.dryRun) {
    throw "Existing bridge at $BridgeUrl is healthy but not runtime dry-run. Stop it first or use another -Port."
  }
} else {
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

  $ServerArgs = @(
    $BridgeScript,
    "--config", $DefaultConfig,
    "--host", $HostName,
    "--port", "$Port",
    "--base-url", $BaseUrl,
    "--dry-run"
  )

  $Process = Start-Process `
    -FilePath $Python `
    -ArgumentList $ServerArgs `
    -WorkingDirectory $VoiceDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogPath `
    -RedirectStandardError $ErrLogPath `
    -PassThru
}

if (-not $Json) {
  Write-Host "== Mira Light Simplest Mode =="
  Write-Host "Mode: local action bridge, runtime dry-run"
  Write-Host "Bridge: $BridgeUrl"
  Write-Host "Lamp target stored for config only: $BaseUrl"
  Write-Host "Log: $LogPath"
  Write-Host ""
}

$Health = $ExistingHealth
for ($i = 0; $i -lt 80 -and ($null -eq $Health -or $Health.ok -ne $true); $i++) {
  $Health = Get-MiraSimplestHealth $BridgeUrl
  if ($null -ne $Health -and $Health.ok -eq $true) {
    break
  }
  if ($null -ne $Process -and $Process.HasExited) {
    throw "Bridge process exited before becoming healthy. See $LogPath and $ErrLogPath"
  }
  Start-Sleep -Milliseconds 250
}

if ($null -eq $Health -or $Health.ok -ne $true) {
  throw "Bridge did not become healthy at $BridgeUrl/health. See $LogPath and $ErrLogPath"
}

if (-not [bool]$Health.runtime.dryRun) {
  throw "Bridge is healthy but runtime.dryRun is not true. Stop the existing bridge or use another port."
}

$SceneItems = @()
if (-not $NoSmoke) {
  $Scenes = Invoke-RestMethod -Uri "$BridgeUrl/v1/mira-light/scenes" -TimeoutSec 3
  if ($null -ne $Scenes.items) {
    $SceneItems = @($Scenes.items)
  } elseif ($null -ne $Scenes.scenes) {
    $SceneItems = @($Scenes.scenes)
  }
}

$Result = [ordered]@{
  ok = $true
  mode = "simplest-dry-run-action-bridge"
  bridgeUrl = $BridgeUrl
  healthUrl = "$BridgeUrl/health"
  scenesUrl = "$BridgeUrl/v1/mira-light/scenes"
  runtimeDryRun = [bool]$Health.runtime.dryRun
  service = $Health.service
  started = [bool]($null -ne $Process)
  pid = if ($null -ne $Process) { $Process.Id } else { $null }
  logs = [ordered]@{
    stdout = $LogPath
    stderr = $ErrLogPath
  }
  smoke = [ordered]@{
    scenesChecked = (-not $NoSmoke)
    sceneCount = if (-not $NoSmoke) { $SceneItems.Count } else { $null }
  }
}

if ($Json) {
  $Result | ConvertTo-Json -Depth 8
} else {
  Write-Host "[ok] Bridge is healthy in runtime dry-run mode."
  if ($null -ne $Result.smoke.sceneCount) {
    Write-Host "[ok] Scenes available: $($Result.smoke.sceneCount)"
  }
  Write-Host ""
  Write-Host "Health:"
  Write-Host "  Invoke-RestMethod $BridgeUrl/health"
  Write-Host "Scenes:"
  Write-Host "  Invoke-RestMethod $BridgeUrl/v1/mira-light/scenes"
  Write-Host ""
  Write-Host "This mode does not verify physical lamp motion."
}

