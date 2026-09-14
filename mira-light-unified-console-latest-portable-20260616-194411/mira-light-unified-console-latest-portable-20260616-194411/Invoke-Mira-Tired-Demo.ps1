param(
  [string]$BridgeUrl = "http://127.0.0.1:19783",
  [string]$Transcript = "",
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Transcript)) {
  $Transcript = -join ([char[]](0x6211, 0x597D, 0x7D2F, 0x554A))
}

$TargetUrl = "$($BridgeUrl.TrimEnd('/'))/v1/mira-light/trigger"
$Body = @{
  event = "voice_tired"
  payload = @{
    source = "mira-tired-demo"
    transcript = $Transcript
    cueMode = "manual-demo"
    silentMode = $true
  }
}

$Preview = @{
  ok = $true
  dryRun = [bool]$DryRun
  url = $TargetUrl
  body = $Body
  expectedScene = "voice_demo_tired"
}

if ($DryRun) {
  if ($Json) {
    $Preview | ConvertTo-Json -Depth 8
  } else {
    Write-Host "Mira tired demo dry-run"
    Write-Host "URL: $TargetUrl"
    Write-Host "Event: voice_tired"
    Write-Host "Transcript: $Transcript"
    Write-Host "Expected scene: voice_demo_tired"
  }
  exit 0
}

$Response = Invoke-RestMethod `
  -Uri $TargetUrl `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ($Body | ConvertTo-Json -Depth 8) `
  -TimeoutSec 20

if ($Json) {
  $Response | ConvertTo-Json -Depth 12
} else {
  Write-Host "Triggered Mira tired demo."
  Write-Host "Bridge: $BridgeUrl"
  Write-Host "Transcript: $Transcript"
  Write-Host "Expected scene: voice_demo_tired"
}
