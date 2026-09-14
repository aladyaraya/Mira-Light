param(
  [ValidateSet("all", "local-intents", "api-key", "llm-planner", "bridge-health", "e2e", "dispatch")]
  [string]$Test = "all",
  [string]$Text = "",
  [string]$BridgeUrl = "http://127.0.0.1:19783",
  [switch]$StartBridge,
  [switch]$DryRunBridge,
  [string]$BaseUrl = "tcp://192.168.0.183:9527",
  [switch]$Help
)

if ($Help) {
  Write-Host @"
== Mira Light Voice Pipeline Test ==

Tests the full voice→action pipeline using TEXT input (no microphone needed).

Parameters:
  -Test           Which test to run: all, local-intents, api-key, llm-planner,
                  bridge-health, e2e, dispatch  (default: all)
  -Text           Text to dispatch (required for -Test dispatch)
  -BridgeUrl      Action Bridge URL (default: http://127.0.0.1:19783)
  -StartBridge    Auto-start the Action Bridge before testing
  -DryRunBridge   Start bridge in dry-run mode (no real board commands)
  -BaseUrl        MIRA board base URL (default: tcp://192.168.0.183:9527)

Examples:
  .\Test-Mira-Light-Voice-Pipeline.ps1 -Test local-intents
  .\Test-Mira-Light-Voice-Pipeline.ps1 -Test api-key
  .\Test-Mira-Light-Voice-Pipeline.ps1 -Test e2e -StartBridge
  .\Test-Mira-Light-Voice-Pipeline.ps1 -Test dispatch -Text "跳舞" -StartBridge
  .\Test-Mira-Light-Voice-Pipeline.ps1 -Test all -StartBridge -DryRunBridge
"@
  exit 0
}

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$EnvFile = Join-Path $VoiceDir "config\windows-voice-stepfun.env"
$TestScript = Join-Path $VoiceDir "scripts\test_voice_pipeline_e2e.py"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"
$BridgeScript = Join-Path $RootDir "Start-Mira-Light-Windows-Action-Bridge.ps1"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

# Load env file for PowerShell environment
if (Test-Path $EnvFile) {
  Get-Content $EnvFile -Encoding utf8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
      if ($line.StartsWith("export ")) { $line = $line.Substring(7) }
      $parts = $line -split "=", 2
      if ($parts.Length -eq 2) {
        $key = $parts[0].Trim()
        $val = $parts[1].Trim().Trim('"').Trim("'")
        if ($val -and -not [System.Environment]::GetEnvironmentVariable($key)) {
          [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
      }
    }
  }
  Write-Host "[env] Loaded: $EnvFile"
  # Propagate proxy for Python subprocess
  $proxyUrl = $env:STEPFUN_PROXY_URL
  if ($proxyUrl -and $proxyUrl.Trim().Length -gt 0) {
    $env:HTTPS_PROXY = $proxyUrl
    $env:HTTP_PROXY = $proxyUrl
    Write-Host "[env] Proxy: $proxyUrl"
  }
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Auto-start bridge if requested
if ($StartBridge) {
  Write-Host ""
  Write-Host "== Starting Action Bridge =="
  $bridgeArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $BridgeScript,
    "-HostName", "127.0.0.1",
    "-Port", "19783",
    "-BaseUrl", $BaseUrl,
    "-Background",
    "-Json"
  )
  if ($DryRunBridge) {
    $bridgeArgs += "-DryRun"
  }
  & powershell @bridgeArgs
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[bridge] Failed to start. Continuing with tests anyway..."
  }
  Write-Host ""
}

# Run the Python test
$ArgsList = @(
  $TestScript,
  "--test", $Test,
  "--bridge-url", $BridgeUrl,
  "--env-file", $EnvFile
)
if ($Text.Trim().Length -gt 0) {
  $ArgsList += @("--text", $Text)
}

Write-Host "== Mira Light Voice Pipeline Test =="
Write-Host "Python: $Python"
Write-Host "Test:   $Test"
Write-Host "Bridge: $BridgeUrl"
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
