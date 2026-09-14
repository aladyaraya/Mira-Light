param(
  [switch]$Recreate,
  [string]$IndexUrl = "https://pypi.org/simple"
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$VenvDir = Join-Path $VoiceDir ".venv"
$Python = "python"

if ($Recreate -and (Test-Path $VenvDir)) {
  Remove-Item -LiteralPath $VenvDir -Recurse -Force
}

if (-not (Test-Path $VenvDir)) {
  Write-Host "Creating venv: $VenvDir"
  & $Python -m venv $VenvDir
  if ($LASTEXITCODE -ne 0) {
    throw "venv creation failed with exit code $LASTEXITCODE"
  }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  throw "venv Python not found: $VenvPython"
}

$Requirements = Join-Path $VoiceDir "requirements-windows-voice.txt"
$PipIndexArgs = @()
if (-not [string]::IsNullOrWhiteSpace($IndexUrl)) {
  $PipIndexArgs += "--index-url"
  $PipIndexArgs += $IndexUrl
}

function Invoke-VenvPip {
  param(
    [string[]]$PipArgs
  )

  & $VenvPython -m pip @PipArgs
  if ($LASTEXITCODE -ne 0) {
    throw "pip failed with exit code $LASTEXITCODE`: $($PipArgs -join ' ')"
  }
}

Write-Host "Installing Windows voice dependencies..."
Invoke-VenvPip (@("install", "--upgrade", "pip") + $PipIndexArgs)
Invoke-VenvPip (@("install", "-r", $Requirements) + $PipIndexArgs)

Write-Host ""
Write-Host "Windows voice setup complete."
Write-Host "Next:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\Start-Mira-Light-Windows-Mic-Capture.ps1 -ListDevices"
