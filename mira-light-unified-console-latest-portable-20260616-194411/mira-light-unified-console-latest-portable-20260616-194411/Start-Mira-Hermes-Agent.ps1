param(
  [string]$Prompt = "",
  [switch]$Doctor,
  [switch]$ConfigCheck,
  [switch]$PromptSize,
  [switch]$NoStepFunKeyMapping
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$HermesDir = Join-Path $Root "tools\hermes-agent"
$HermesExe = Join-Path $HermesDir ".venv\Scripts\hermes.exe"
$HermesHome = Join-Path $Root "tools\hermes-mira-home"

if (-not (Test-Path $HermesExe)) {
  throw "Hermes executable not found: $HermesExe. Run uv venv and uv pip install -e . inside tools\hermes-agent first."
}

if (-not (Test-Path $HermesHome)) {
  throw "Mira Hermes home not found: $HermesHome"
}

$env:HERMES_HOME = $HermesHome
$env:MIRA_LIGHT_AGENT_WORKSPACE = Join-Path $Root "Mira-Light-Voice-Full-Ready\tools\openclaw_agents\mira_voice_spark_workspace"

if (-not $NoStepFunKeyMapping) {
  if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY) -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_API_KEY)) {
    $env:OPENAI_API_KEY = $env:STEPFUN_API_KEY
  }
}

Push-Location $Root
try {
  if ($Doctor) {
    & $HermesExe doctor
    exit $LASTEXITCODE
  }

  if ($ConfigCheck) {
    & $HermesExe config check
    exit $LASTEXITCODE
  }

  if ($PromptSize) {
    & $HermesExe prompt-size
    exit $LASTEXITCODE
  }

  if (-not [string]::IsNullOrWhiteSpace($Prompt)) {
    & $HermesExe -z $Prompt
    exit $LASTEXITCODE
  }

  & $HermesExe
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}

