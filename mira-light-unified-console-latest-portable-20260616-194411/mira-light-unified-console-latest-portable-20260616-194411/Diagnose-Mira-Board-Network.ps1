param(
  [string]$BoardHost = "192.168.0.183",
  [int]$BoardPort = 9527,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$AcceptanceScript = Join-Path $Root "Test-Mira-Hardware-Motion-Acceptance.ps1"

$Command = @(
  "powershell",
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $AcceptanceScript,
  "-BoardHost", $BoardHost,
  "-BoardPort", [string]$BoardPort,
  "-SkipPositionChangeCheck",
  "-Json"
)

$Preview = @{
  ok = $true
  dryRun = [bool]$DryRun
  mode = "mira-board-network-diagnostics"
  boardHost = $BoardHost
  boardPort = $BoardPort
  command = $Command
  purpose = "Check board ACK and Windows route risk without claiming physical motion."
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 10
  } else {
    Write-Host "Mira board network diagnostics dry-run"
    Write-Host "Board: $BoardHost`:$BoardPort"
    Write-Host "Command: $($Command -join ' ')"
  }
  exit 0
}

$output = & powershell -NoProfile -ExecutionPolicy Bypass -File $AcceptanceScript -BoardHost $BoardHost -BoardPort $BoardPort -SkipPositionChangeCheck -Json
$exitCode = $LASTEXITCODE

if ($Json) {
  $output
  exit $exitCode
}

try {
  $payload = $output | ConvertFrom-Json
  $route = $payload.checks.networkRoute
  Write-Host "Mira board network diagnostics"
  Write-Host "Board: $BoardHost`:$BoardPort"
  Write-Host "ACK: $($payload.checks.ackProbe.ok)"
  if ($route) {
    Write-Host "Route risk: $($route.risk)"
    if ($route.selectedRoute) {
      Write-Host "Selected route: $($route.selectedRoute.InterfaceAlias) via $($route.selectedRoute.NextHop)"
    }
    if ($route.suggestedActions) {
      Write-Host "Suggested actions: $($route.suggestedActions -join ', ')"
    }
  }
} catch {
  Write-Host $output
}

exit $exitCode
