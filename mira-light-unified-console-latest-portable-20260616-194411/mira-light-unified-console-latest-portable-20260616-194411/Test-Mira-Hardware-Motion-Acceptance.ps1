param(
  [string]$BoardHost = "192.168.0.183",
  [int]$BoardPort = 9527,
  [string]$BridgeUrl = "http://127.0.0.1:19783",
  [string]$Transcript = "",
  [int]$PositionDeltaThreshold = 20,
  [switch]$SkipPositionChangeCheck,
  [switch]$SpeakReply,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceRoot = Join-Path $Root "Mira-Light-Voice-Full-Ready"
$Script = Join-Path $VoiceRoot "scripts\mira_hardware_motion_acceptance.py"
$VenvPython = Join-Path $VoiceRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

if ([string]::IsNullOrWhiteSpace($Transcript)) {
  $Transcript = -join ([char[]](0x6211, 0x597D, 0x7D2F, 0x554A))
}

$Command = @(
  $Script,
  "--board-host", $BoardHost,
  "--board-port", [string]$BoardPort,
  "--bridge-url", $BridgeUrl,
  "--transcript", $Transcript,
  "--position-delta-threshold", [string]$PositionDeltaThreshold
)

if ($SkipPositionChangeCheck) {
  $Command += "--skip-position-change-check"
}

if ($SpeakReply) {
  $Command += "--speak-reply"
}

$Preview = @{
  ok = $true
  dryRun = [bool]$DryRun
  mode = "hardware-motion-acceptance"
  python = $Python
  script = $Script
  boardHost = $BoardHost
  boardPort = $BoardPort
  bridgeUrl = $BridgeUrl
  transcript = $Transcript
  requiresAck = $true
  requiresPositionChange = -not [bool]$SkipPositionChangeCheck
  positionDeltaThreshold = $PositionDeltaThreshold
  command = @($Python) + $Command
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 10
  } else {
    Write-Host "Mira hardware motion acceptance dry-run"
    Write-Host "Board: $BoardHost`:$BoardPort"
    Write-Host "Bridge: $BridgeUrl"
    Write-Host "Requires 9527 ACK before voice scene"
  }
  exit 0
}

if ($Json) {
  $Command += "--json"
}

& $Python @Command
exit $LASTEXITCODE
