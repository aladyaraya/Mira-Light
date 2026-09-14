param(
  [string]$Transcript = "",
  [string]$TranscriptJson = "",
  [string]$Output = "",
  [string]$ApiKey = "",
  [string]$Endpoint = "",
  [string]$Model = "",
  [int]$TimeoutSeconds = 0,
  [string]$EnvFile = "",
  [string]$ProxyUrl = "",
  [switch]$NoProxy,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$DefaultEnvFile = Join-Path $VoiceDir "config\windows-voice-stepfun.env"
$ScriptPath = Join-Path $VoiceDir "scripts\stepfun_llm_planner.py"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

if ($Transcript.Trim().Length -eq 0 -and $TranscriptJson.Trim().Length -eq 0) {
  $RuntimeDir = Join-Path $VoiceDir "runtime"
  $LatestTranscript = Get-ChildItem -Path $RuntimeDir -Recurse -Include "transcript.stepfun.json", "transcript.realtime.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $LatestTranscript) {
    throw "No transcript JSON found. Pass -Transcript or run ASR/realtime first."
  }
  $TranscriptJson = $LatestTranscript.FullName
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
  $EnvFile = $DefaultEnvFile
}

function Import-SimpleEnvFile {
  param([string]$Path)
  $loaded = @{}
  if (-not (Test-Path $Path)) {
    return $loaded
  }
  Get-Content $Path -Encoding utf8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
      if ($line.StartsWith("export ")) {
        $line = $line.Substring(7).Trim()
      }
      $parts = $line -split "=", 2
      if ($parts.Length -eq 2) {
        $key = $parts[0].Trim()
        $val = $parts[1].Trim().Trim('"').Trim("'")
        if ($key) {
          [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
          $loaded[$key] = $val
        }
      }
    }
  }
  return $loaded
}

$LoadedEnv = Import-SimpleEnvFile -Path $EnvFile

if ([string]::IsNullOrWhiteSpace($Endpoint)) {
  $Endpoint = $env:STEPFUN_LLM_ENDPOINT
}
if ([string]::IsNullOrWhiteSpace($Model)) {
  $Model = $env:STEPFUN_LLM_MODEL
}
if ([string]::IsNullOrWhiteSpace($Model)) {
  $Model = "step-3.7-flash"
}
if ($TimeoutSeconds -le 0) {
  if (-not [string]::IsNullOrWhiteSpace($env:STEPFUN_LLM_TIMEOUT_SECONDS)) {
    $TimeoutSeconds = [int]$env:STEPFUN_LLM_TIMEOUT_SECONDS
  } else {
    $TimeoutSeconds = 90
  }
}

if ($NoProxy) {
  $env:STEPFUN_PROXY_URL = ""
  Remove-Item env:HTTP_PROXY -ErrorAction SilentlyContinue
  Remove-Item env:HTTPS_PROXY -ErrorAction SilentlyContinue
  Remove-Item env:http_proxy -ErrorAction SilentlyContinue
  Remove-Item env:https_proxy -ErrorAction SilentlyContinue
  Remove-Item env:ALL_PROXY -ErrorAction SilentlyContinue
  Remove-Item env:all_proxy -ErrorAction SilentlyContinue
} elseif ($PSBoundParameters.ContainsKey("ProxyUrl")) {
  $env:STEPFUN_PROXY_URL = $ProxyUrl
  if ([string]::IsNullOrWhiteSpace($ProxyUrl)) {
    Remove-Item env:HTTP_PROXY -ErrorAction SilentlyContinue
    Remove-Item env:HTTPS_PROXY -ErrorAction SilentlyContinue
    Remove-Item env:http_proxy -ErrorAction SilentlyContinue
    Remove-Item env:https_proxy -ErrorAction SilentlyContinue
    Remove-Item env:ALL_PROXY -ErrorAction SilentlyContinue
    Remove-Item env:all_proxy -ErrorAction SilentlyContinue
  }
}

$ArgsList = @($ScriptPath, "--model", $Model, "--timeout-seconds", "$TimeoutSeconds")

if ($Transcript.Trim().Length -gt 0) {
  $ArgsList += @("--transcript", $Transcript)
} else {
  $ArgsList += @("--transcript-json", $TranscriptJson)
}
if ($Output.Trim().Length -gt 0) {
  $ArgsList += @("--output", $Output)
}
if ($ApiKey.Trim().Length -gt 0) {
  $ArgsList += @("--api-key", $ApiKey)
}
if ($Endpoint.Trim().Length -gt 0) {
  $ArgsList += @("--endpoint", $Endpoint)
}
if ($DryRun) {
  $ArgsList += "--dry-run"
}
if ($Json) {
  $ArgsList += "--json"
}

Write-Host "== Mira Light StepFun LLM Planner =="
Write-Host "Python: $Python"
Write-Host "Script: $ScriptPath"
Write-Host "EnvFile: $EnvFile"
Write-Host "Model: $Model"
Write-Host "Endpoint: $Endpoint"
Write-Host "Proxy: $($env:STEPFUN_PROXY_URL)"
Write-Host "PlannerPrompt: $($env:MIRA_LIGHT_PLANNER_SYSTEM_PROMPT_FILE)"
if ($Transcript.Trim().Length -gt 0) {
  Write-Host "Transcript: $Transcript"
} else {
  Write-Host "Transcript JSON: $TranscriptJson"
}
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
