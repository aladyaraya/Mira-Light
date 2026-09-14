param(
  [string]$BoardHost = "192.168.0.183",
  [int]$BoardPort = 9527,
  [string]$Gateway = "",
  [string]$InterfaceAlias = "",
  [switch]$ApplyRoute,
  [switch]$UpdateConfig,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $Root "Mira-Light-Voice-Full-Ready"
$RuntimeConfig = Join-Path $VoiceDir "config\bus_servo_runtime.json"
$StepfunEnv = Join-Path $VoiceDir "config\windows-voice-stepfun.env"

if ([string]::IsNullOrWhiteSpace($Gateway)) {
  $route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
    Sort-Object RouteMetric, InterfaceMetric |
    Select-Object -First 1
  if ($route) {
    $Gateway = [string]$route.NextHop
  }
}

$RouteArgs = @("ADD", $BoardHost, "MASK", "255.255.255.255")
if (-not [string]::IsNullOrWhiteSpace($Gateway)) {
  $RouteArgs += $Gateway
}
if (-not [string]::IsNullOrWhiteSpace($InterfaceAlias)) {
  $adapter = Get-NetAdapter -Name $InterfaceAlias -ErrorAction SilentlyContinue
  if ($adapter) {
    $RouteArgs += @("IF", [string]$adapter.ifIndex)
  }
}

$AdminRouteCommand = "route " + ($RouteArgs -join " ")
$ConfigPaths = @($RuntimeConfig, $StepfunEnv)

$Preview = @{
  ok = $true
  dryRun = [bool]$DryRun
  mode = "mira-board-network-repair"
  boardHost = $BoardHost
  boardPort = $BoardPort
  gateway = $Gateway
  interfaceAlias = $InterfaceAlias
  willApplyRoute = [bool]$ApplyRoute
  willUpdateConfig = [bool]$UpdateConfig
  adminRouteCommand = $AdminRouteCommand
  configPaths = $ConfigPaths
  lampBaseUrl = "tcp://${BoardHost}:$BoardPort"
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 10
  } else {
    Write-Host "Mira board network repair dry-run"
    Write-Host "Board: $BoardHost`:$BoardPort"
    Write-Host "Route command: $AdminRouteCommand"
    Write-Host "Config update: $($Preview.lampBaseUrl)"
  }
  exit 0
}

if ($ApplyRoute) {
  & route @RouteArgs
}

if ($UpdateConfig) {
  if (Test-Path $RuntimeConfig) {
    $runtime = Get-Content $RuntimeConfig -Raw -Encoding utf8 | ConvertFrom-Json
    $runtime.host = $BoardHost
    $runtime.port = $BoardPort
    $runtime | ConvertTo-Json -Depth 20 | Set-Content $RuntimeConfig -Encoding utf8
  }
  if (Test-Path $StepfunEnv) {
    $lines = Get-Content $StepfunEnv -Encoding utf8
    $updated = $false
    $lines = $lines | ForEach-Object {
      if ($_ -match "^MIRA_LIGHT_LAMP_BASE_URL=") {
        $updated = $true
        "MIRA_LIGHT_LAMP_BASE_URL=tcp://${BoardHost}:$BoardPort"
      } else {
        $_
      }
    }
    if (-not $updated) {
      $lines += "MIRA_LIGHT_LAMP_BASE_URL=tcp://${BoardHost}:$BoardPort"
    }
    $lines | Set-Content $StepfunEnv -Encoding utf8
  }
}

if ($Json) {
  $Preview | ConvertTo-Json -Depth 10
} else {
  Write-Host "Mira board network repair complete."
  Write-Host "Board: $BoardHost`:$BoardPort"
}
