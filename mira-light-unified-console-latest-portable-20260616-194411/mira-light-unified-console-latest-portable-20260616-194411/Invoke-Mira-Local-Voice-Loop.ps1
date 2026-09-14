param(
  [string]$BridgeUrl = "http://127.0.0.1:19783",
  [string]$Transcript = "",
  [switch]$SpeakReply,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceRoot = Join-Path $Root "Mira-Light-Voice-Full-Ready"
$Script = Join-Path $VoiceRoot "scripts\mira_local_voice_loop.py"
$VenvPython = Join-Path $VoiceRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

if ([string]::IsNullOrWhiteSpace($Transcript)) {
  $Transcript = -join ([char[]](0x6211, 0x597D, 0x7D2F, 0x554A))
}

$Command = @(
  $Script,
  "--transcript",
  $Transcript,
  "--bridge-url",
  $BridgeUrl
)

if ($SpeakReply) {
  $Command += "--speak-reply"
}

$Preview = @{
  ok = $true
  dryRun = [bool]$DryRun
  mode = "local-minimal-voice-loop"
  python = $Python
  script = $Script
  transcript = $Transcript
  bridgeUrl = $BridgeUrl
  speakReply = [bool]$SpeakReply
  expectedAction = @{
    type = "trigger"
    name = "voice_tired"
  }
  expectedScene = "voice_demo_tired"
  command = @($Python) + $Command
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 10
  } else {
    Write-Host "Mira local voice loop dry-run"
    Write-Host "Transcript: $Transcript"
    Write-Host "Bridge: $BridgeUrl"
    Write-Host "Expected action: trigger voice_tired"
    Write-Host "Expected scene: voice_demo_tired"
  }
  exit 0
}

if ($Json) {
  $Command += "--json"
}

& $Python @Command
exit $LASTEXITCODE
