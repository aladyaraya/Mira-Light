param(
  [string]$ApiKey = "",
  [string]$Endpoint = "",
  [string]$Model = "stepaudio-2.5-realtime",
  [string]$Voice = "wenrounansheng",
  [string]$ProxyUrl = "",
  [string]$EnvFile = "",
  [string]$InputDevice = "default",
  [int]$InputSampleRate = 24000,
  [int]$OutputSampleRate = 24000,
  [int]$ChunkMs = 40,
  [double]$Seconds = 0,
  [string]$RuntimeMemoryFile = "",
  [int]$RuntimeMemoryTurns = 12,
  [string]$BridgeUrl = "http://127.0.0.1:19783",
  [string]$DirectorUrl = "",
  [switch]$StartActionBridge,
  [string]$ActionBridgeHost = "127.0.0.1",
  [int]$ActionBridgePort = 19783,
  [string]$ActionBridgeBaseUrl = "tcp://192.168.0.183:9527",
  [switch]$ActionBridgeDryRun,
  [switch]$NoPlannerReply,
  [string]$PlannerProvider = "stepfun",
  [string]$PlannerApiKey = "",
  [string]$PlannerEndpoint = "https://api.stepfun.com/v1/chat/completions",
  [string]$PlannerModel = "step-3.7-flash",
  [int]$PlannerTimeoutSeconds = 90,
  [string]$PlannerReplyVoice = "tts",
  [switch]$PlannerReplyWait,
  [switch]$PlannerPlayback,
  [switch]$PlannerOwnsReply,
  [switch]$AllowLocalSemanticFallback,
  [switch]$AssistantTextActions,
  [switch]$PromptApiKey,
  [switch]$NoVoiceStateActions,
  [switch]$NoSemanticActions,
  [switch]$TwoPhaseRefinement,
  [switch]$NoTwoPhaseRefinement,
  [switch]$NoPlay,
  [switch]$RealtimePlayback,
  [switch]$NoRealtimePlayback,
  [switch]$NoPlannerPlayback,
  [switch]$SkipPreflight,
  [switch]$EnsureBoardServoBridge,
  [switch]$NoStartupWakeUp,
  [string]$BoardSshUser = "root",
  [int]$BoardSshPort = 22,
  [string]$BoardRemoteDir = "/home/sunrise/Desktop/mira-book-follow-camera",
  [string]$BoardServoDevice = "/dev/ttyS1",
  [int]$CpuLimitPercent = 80,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"
$DefaultEnvFile = Join-Path $VoiceDir "config\windows-voice-stepfun.env"
$ScriptPath = Join-Path $VoiceDir "scripts\mira_stepfun_realtime_voice_actions.py"
$ActionBridgeScript = Join-Path $RootDir "Start-Mira-Light-Windows-Action-Bridge.ps1"
$VenvPython = Join-Path $VoiceDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
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
        if ($key -and $val) {
          [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
          $loaded[$key] = $val
        }
      }
    }
  }
  return $loaded
}

function Get-MiraBridgeHealth {
  param([string]$Url)
  try {
    return Invoke-RestMethod -Uri "$($Url.TrimEnd('/'))/health" -TimeoutSec 3
  } catch {
    return $null
  }
}

function Test-MiraTcpBaseUrl {
  param([string]$BaseUrl)
  if (-not $BaseUrl.StartsWith("tcp://")) {
    return @{ skipped = $true; reason = "base url is not tcp"; ok = $true }
  }
  $uri = [Uri]$BaseUrl
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $async = $client.BeginConnect($uri.Host, $uri.Port, $null, $null)
    $connected = $async.AsyncWaitHandle.WaitOne(3000, $false)
    if (-not $connected) {
      return @{ ok = $false; host = $uri.Host; port = $uri.Port; error = "tcp connect timeout" }
    }
    $client.EndConnect($async)
    return @{ ok = $true; host = $uri.Host; port = $uri.Port }
  } catch {
    return @{ ok = $false; host = $uri.Host; port = $uri.Port; error = $_.Exception.Message }
  } finally {
    $client.Close()
  }
}

function Get-MiraTcpTarget {
  param([string]$BaseUrl)
  if (-not $BaseUrl.StartsWith("tcp://")) {
    return $null
  }
  $uri = [Uri]$BaseUrl
  return @{ host = $uri.Host; port = $uri.Port }
}

function Ensure-MiraBoardServoBridge {
  param(
    [string]$BaseUrl,
    [string]$SshUser,
    [int]$SshPort,
    [string]$RemoteDir,
    [string]$ServoDevice
  )

  $target = Get-MiraTcpTarget -BaseUrl $BaseUrl
  if ($null -eq $target) {
    Write-Host "[board-servo] skipped: base url is not tcp"
    return
  }

  $boardHost = [string]$target.host
  $servoPort = [int]$target.port
  $remote = "${SshUser}@${boardHost}"
  $boardBridgeScript = Join-Path $RootDir "scripts\rdk_bus_servo_tcp_bridge.py"
  if (-not (Test-Path $boardBridgeScript)) {
    throw "Missing board servo bridge script: $boardBridgeScript"
  }

  Write-Host "[board-servo] ensuring $remote $boardHost`:$servoPort -> $ServoDevice"
  & ssh -p $SshPort $remote "mkdir -p '$RemoteDir'"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create board remote dir over SSH: ${remote}:$RemoteDir"
  }

  & scp -P $SshPort $boardBridgeScript "${remote}:$RemoteDir/rdk_bus_servo_tcp_bridge.py"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to copy board servo bridge over SCP."
  }

  $remoteScript = @"
set -e
REMOTE_DIR='$RemoteDir'
SERVO_PORT='$servoPort'
SERVO_DEVICE='$ServoDevice'
mkdir -p "`$REMOTE_DIR"
pkill -f '[r]dk_bus_servo_tcp_bridge.py' 2>/dev/null || true
nohup python3 "`$REMOTE_DIR/rdk_bus_servo_tcp_bridge.py" --host 0.0.0.0 --port "`$SERVO_PORT" --device "`$SERVO_DEVICE" > "`$REMOTE_DIR/rdk_bus_servo_tcp_bridge.log" 2>&1 < /dev/null &
sleep 1
ss -lntp | grep ":`$SERVO_PORT " || true
tail -20 "`$REMOTE_DIR/rdk_bus_servo_tcp_bridge.log" 2>/dev/null || true
"@

  $remoteScriptPath = Join-Path ([System.IO.Path]::GetTempPath()) ("mira-board-servo-" + [System.Guid]::NewGuid().ToString("N") + ".sh")
  try {
    [System.IO.File]::WriteAllText($remoteScriptPath, $remoteScript, [System.Text.UTF8Encoding]::new($false))
    Get-Content -LiteralPath $remoteScriptPath -Raw -Encoding UTF8 | & ssh -p $SshPort $remote "bash -s"
    if ($LASTEXITCODE -ne 0) {
      throw "Failed to start board servo bridge over SSH."
    }
  } finally {
    Remove-Item -LiteralPath $remoteScriptPath -Force -ErrorAction SilentlyContinue
  }
}

function Assert-MiraRealtimePreflight {
  param(
    [string]$BridgeUrl,
    [string]$ExpectedBaseUrl,
    [int]$CpuLimitPercent
  )

  $cpu = Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average
  $cpuLoad = [math]::Round([double]$cpu.Average, 1)
  if ($cpuLoad -ge $CpuLimitPercent) {
    throw "Preflight failed: CPU load is $cpuLoad%, limit is $CpuLimitPercent%."
  }

  $health = Get-MiraBridgeHealth -Url $BridgeUrl
  if ($null -eq $health -or $health.ok -ne $true) {
    throw "Preflight failed: action bridge health is not OK at $BridgeUrl/health."
  }

  $runtimeBaseUrl = [string]$health.runtime.baseUrl
  if ($runtimeBaseUrl -and $ExpectedBaseUrl -and $runtimeBaseUrl -ne $ExpectedBaseUrl) {
    throw "Preflight failed: action bridge target is '$runtimeBaseUrl', expected '$ExpectedBaseUrl'. Stop the old bridge or use a different port."
  }

  $tcp = Test-MiraTcpBaseUrl -BaseUrl $ExpectedBaseUrl
  if ($tcp.ok -ne $true) {
    throw "Preflight failed: lamp endpoint $ExpectedBaseUrl is not reachable ($($tcp.error)). Use -EnsureBoardServoBridge to start the board-side 9527 bridge over SSH."
  }

  Write-Host "[preflight] ok cpu=$cpuLoad% bridge=$BridgeUrl lamp=$ExpectedBaseUrl"
}

function Invoke-MiraStartupWakeUp {
  param([string]$BridgeUrl)
  $payload = @{
    scene = "wake_up"
    async = $false
    cueMode = "startup"
    silentMode = $true
    context = @{
      source = "windows-full-realtime-launcher"
      reason = "startup-wake-up"
    }
  }
  try {
    $response = Invoke-RestMethod `
      -Uri "$($BridgeUrl.TrimEnd('/'))/v1/mira-light/run-scene" `
      -Method Post `
      -ContentType "application/json; charset=utf-8" `
      -Body ($payload | ConvertTo-Json -Depth 8) `
      -TimeoutSec 12
    if ($response.ok -eq $true) {
      Write-Host "[startup] wake_up scene ok"
    } else {
      Write-Host "[startup] wake_up scene returned ok=false"
    }
  } catch {
    Write-Host "[startup] wake_up scene skipped: $($_.Exception.Message)"
  }
}

$LoadedEnv = Import-SimpleEnvFile -Path $EnvFile

if (-not $PSBoundParameters.ContainsKey("Endpoint") -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_REALTIME_ENDPOINT)) {
  $Endpoint = $env:STEPFUN_REALTIME_ENDPOINT
}
if (-not $PSBoundParameters.ContainsKey("Model") -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_REALTIME_MODEL)) {
  $Model = $env:STEPFUN_REALTIME_MODEL
}
if (-not $PSBoundParameters.ContainsKey("Voice") -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_REALTIME_VOICE)) {
  $Voice = $env:STEPFUN_REALTIME_VOICE
}
if (-not $PSBoundParameters.ContainsKey("ProxyUrl") -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_PROXY_URL)) {
  $ProxyUrl = $env:STEPFUN_PROXY_URL
}
if (-not $PSBoundParameters.ContainsKey("InputDevice")) {
  if (-not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_INPUT_DEVICE)) {
    $InputDevice = $env:MIRA_LIGHT_INPUT_DEVICE
  } elseif (-not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_WINDOWS_MIC_DEVICE)) {
    $InputDevice = $env:MIRA_LIGHT_WINDOWS_MIC_DEVICE
  }
}
if (-not $PSBoundParameters.ContainsKey("InputSampleRate") -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_REALTIME_INPUT_SAMPLE_RATE)) {
  $InputSampleRate = [int]$env:STEPFUN_REALTIME_INPUT_SAMPLE_RATE
}
if (-not $PSBoundParameters.ContainsKey("OutputSampleRate") -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE)) {
  $OutputSampleRate = [int]$env:STEPFUN_REALTIME_OUTPUT_SAMPLE_RATE
}
if (-not $PSBoundParameters.ContainsKey("ChunkMs")) {
  if (-not [string]::IsNullOrWhiteSpace($env:STEPFUN_REALTIME_MIC_CHUNK_MS)) {
    $ChunkMs = [int]$env:STEPFUN_REALTIME_MIC_CHUNK_MS
  } elseif (-not [string]::IsNullOrWhiteSpace($env:STEPFUN_REALTIME_CHUNK_MS)) {
    $ChunkMs = [int]$env:STEPFUN_REALTIME_CHUNK_MS
  }
}
if (-not $PSBoundParameters.ContainsKey("RuntimeMemoryTurns") -and -not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_RUNTIME_MEMORY_TURNS)) {
  $RuntimeMemoryTurns = [int]$env:MIRA_LIGHT_RUNTIME_MEMORY_TURNS
}
if ([string]::IsNullOrWhiteSpace($RuntimeMemoryFile)) {
  if (-not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_RUNTIME_MEMORY_FILE)) {
    $RuntimeMemoryFile = $env:MIRA_LIGHT_RUNTIME_MEMORY_FILE
  } else {
    $RuntimeMemoryFile = Join-Path $VoiceDir "runtime\mira-live-memory.json"
  }
}
if (-not $PSBoundParameters.ContainsKey("ActionBridgeBaseUrl") -and -not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_LAMP_BASE_URL)) {
  $ActionBridgeBaseUrl = $env:MIRA_LIGHT_LAMP_BASE_URL
}
if (-not $PSBoundParameters.ContainsKey("PlannerProvider") -and -not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_PLANNER_PROVIDER)) {
  $PlannerProvider = $env:MIRA_LIGHT_PLANNER_PROVIDER
}
if (-not $PSBoundParameters.ContainsKey("PlannerApiKey")) {
  if ($PlannerProvider.Trim().ToLowerInvariant() -eq "stepfun" -and -not [string]::IsNullOrWhiteSpace($env:STEPFUN_API_KEY)) {
    $PlannerApiKey = $env:STEPFUN_API_KEY
  } elseif (-not [string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    $PlannerApiKey = $env:DEEPSEEK_API_KEY
  } elseif (-not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_PLANNER_API_KEY)) {
    $PlannerApiKey = $env:MIRA_LIGHT_PLANNER_API_KEY
  }
}
if (-not $PSBoundParameters.ContainsKey("PlannerEndpoint") -and -not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_PLANNER_ENDPOINT)) {
  $PlannerEndpoint = $env:MIRA_LIGHT_PLANNER_ENDPOINT
}
if (-not $PSBoundParameters.ContainsKey("PlannerModel") -and -not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_PLANNER_MODEL)) {
  $PlannerModel = $env:MIRA_LIGHT_PLANNER_MODEL
}
if (-not $PSBoundParameters.ContainsKey("PlannerTimeoutSeconds") -and -not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_PLANNER_TIMEOUT_SECONDS)) {
  $PlannerTimeoutSeconds = [int]$env:MIRA_LIGHT_PLANNER_TIMEOUT_SECONDS
}
$PlannerOwnsReplyConfigured = $PSBoundParameters.ContainsKey("PlannerOwnsReply")
if (-not $PSBoundParameters.ContainsKey("PlannerOwnsReply") -and -not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_PLANNER_OWNS_REPLY)) {
  $PlannerOwnsReply = $env:MIRA_LIGHT_PLANNER_OWNS_REPLY.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
  $PlannerOwnsReplyConfigured = $true
}
if ($RealtimePlayback -and -not $PlannerOwnsReplyConfigured) {
  $PlannerOwnsReply = $false
  $PlannerOwnsReplyConfigured = $true
}
if (-not $PlannerOwnsReplyConfigured) {
  $PlannerOwnsReply = $true
}
if ($PlannerOwnsReply -and $RealtimePlayback) {
  throw "Audio routing conflict: -RealtimePlayback cannot be used together with planner-owned replies. Remove -RealtimePlayback or pass -NoPlannerReply/-NoPlannerPlayback for a silent dry run."
}
if ($PlannerOwnsReply -and (-not $PSBoundParameters.ContainsKey("NoRealtimePlayback"))) {
  $NoRealtimePlayback = $true
}
if (-not $PSBoundParameters.ContainsKey("AllowLocalSemanticFallback")) {
  if (-not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_ALLOW_LOCAL_SEMANTIC_FALLBACK)) {
    $AllowLocalSemanticFallback = $env:MIRA_LIGHT_ALLOW_LOCAL_SEMANTIC_FALLBACK.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
  } elseif (-not [string]::IsNullOrWhiteSpace($env:MIRA_LIGHT_REQUIRE_MODEL_PLANNING)) {
    $AllowLocalSemanticFallback = -not ($env:MIRA_LIGHT_REQUIRE_MODEL_PLANNING.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on"))
  }
}
if ($PlannerProvider.Trim().ToLowerInvariant() -eq "hermes") {
  if (-not $PSBoundParameters.ContainsKey("PlannerEndpoint") -and $PlannerEndpoint -eq "https://api.deepseek.com/chat/completions") {
    $PlannerEndpoint = ""
  }
  if (-not $PSBoundParameters.ContainsKey("PlannerModel") -and $PlannerModel -eq "deepseek-v4-flash") {
    $PlannerModel = "hermes-agent"
  }
}

$ProxyArg = "--proxy-url=$ProxyUrl"

if ($PromptApiKey -and $ApiKey.Trim().Length -eq 0 -and [string]::IsNullOrWhiteSpace($env:STEPFUN_API_KEY) -and [string]::IsNullOrWhiteSpace($env:STEP_API_KEY)) {
  $SecureKey = Read-Host "StepFun API Key" -AsSecureString
  $Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
  try {
    $ApiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
  }
}
if ($ApiKey.Trim().Length -gt 0 -and [string]::IsNullOrWhiteSpace($env:STEPFUN_API_KEY)) {
  $env:STEPFUN_API_KEY = $ApiKey
}

if ($RealtimePlayback -and $NoRealtimePlayback) {
  throw "Audio routing conflict: -RealtimePlayback and -NoRealtimePlayback cannot be used together."
}
if ($PlannerPlayback -and (-not $PlannerOwnsReply) -and (-not $NoRealtimePlayback) -and (-not $NoPlay)) {
  throw "Audio routing conflict: -PlannerPlayback would run together with StepAudio realtime playback. Use -PlannerOwnsReply or -NoRealtimePlayback."
}

$RequireModelPlanning = (-not $AllowLocalSemanticFallback) -and (-not $NoSemanticActions)

if ($StartActionBridge) {
  $BridgeUrl = "http://${ActionBridgeHost}:$ActionBridgePort"
  $BridgeArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $ActionBridgeScript,
    "-HostName", $ActionBridgeHost,
    "-Port", "$ActionBridgePort",
    "-BaseUrl", $ActionBridgeBaseUrl,
    "-Background"
  )
  if ($ActionBridgeDryRun -or $DryRun) {
    $BridgeArgs += "-DryRun"
  }
  Write-Host "== Mira Light Windows Action Bridge =="
  & powershell @BridgeArgs
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
  Write-Host ""
}

if ($EnsureBoardServoBridge -and -not $DryRun) {
  Ensure-MiraBoardServoBridge `
    -BaseUrl $ActionBridgeBaseUrl `
    -SshUser $BoardSshUser `
    -SshPort $BoardSshPort `
    -RemoteDir $BoardRemoteDir `
    -ServoDevice $BoardServoDevice
}

if (-not $SkipPreflight -and -not $DryRun) {
  Assert-MiraRealtimePreflight -BridgeUrl $BridgeUrl -ExpectedBaseUrl $ActionBridgeBaseUrl -CpuLimitPercent $CpuLimitPercent
}

if (-not $NoStartupWakeUp -and -not $DryRun -and -not $NoSemanticActions) {
  Invoke-MiraStartupWakeUp -BridgeUrl $BridgeUrl
}

$ArgsList = @(
  $ScriptPath,
  "--model", $Model,
  "--voice", $Voice,
  "--input-device", $InputDevice,
  "--input-sample-rate", "$InputSampleRate",
  "--output-sample-rate", "$OutputSampleRate",
  "--chunk-ms", "$ChunkMs",
  "--seconds", "$Seconds",
  "--runtime-memory-file", $RuntimeMemoryFile,
  "--runtime-memory-turns", "$RuntimeMemoryTurns",
  $ProxyArg,
  "--bridge-url", $BridgeUrl,
  "--planner-provider", $PlannerProvider,
  "--planner-timeout-seconds", "$PlannerTimeoutSeconds"
)

if ($PlannerEndpoint.Trim().Length -gt 0) {
  $ArgsList += @("--planner-endpoint", $PlannerEndpoint)
}
if ($PlannerModel.Trim().Length -gt 0) {
  $ArgsList += @("--planner-model", $PlannerModel)
}

if ($ApiKey.Trim().Length -gt 0) {
  $ArgsList += @("--api-key", $ApiKey)
}
if ($Endpoint.Trim().Length -gt 0) {
  $ArgsList += @("--endpoint", $Endpoint)
}
if ($PlannerApiKey.Trim().Length -gt 0) {
  $ArgsList += @("--planner-api-key", $PlannerApiKey)
}
if ($DirectorUrl.Trim().Length -gt 0) {
  $ArgsList += @("--director-url", $DirectorUrl)
}
if ($NoVoiceStateActions) {
  $ArgsList += "--no-voice-state-actions"
}
if ($NoSemanticActions) {
  $ArgsList += "--no-semantic-actions"
}
if ($AssistantTextActions) {
  $ArgsList += "--assistant-text-actions"
}
if ($TwoPhaseRefinement -or -not $NoTwoPhaseRefinement) {
  $ArgsList += "--two-phase-refinement"
}
if ($RequireModelPlanning) {
  $ArgsList += "--require-model-planning"
}
if ($NoPlay) {
  $ArgsList += "--no-play"
}
if ($NoRealtimePlayback) {
  $ArgsList += "--no-realtime-playback"
}
if (($NoPlannerPlayback -or ((-not $PlannerPlayback) -and (-not $PlannerOwnsReply))) -and -not $NoPlannerReply) {
  $ArgsList += "--no-planner-playback"
}
if (-not $NoPlannerReply) {
  $ArgsList += "--speak-planner-reply"
}
if ($PlannerOwnsReply) {
  $ArgsList += "--planner-owns-reply"
}
if ($PlannerReplyVoice.Trim().Length -gt 0) {
  $ArgsList += @("--planner-reply-voice", $PlannerReplyVoice)
}
if ($PlannerReplyWait) {
  $ArgsList += "--planner-reply-wait"
}
if ($DryRun) {
  $ArgsList += "--dry-run"
}
if ($Json) {
  $ArgsList += "--json"
}

Write-Host "== Mira Light Windows Full Realtime =="
Write-Host "Python: $Python"
Write-Host "Script: $ScriptPath"
Write-Host "Bridge: $BridgeUrl"
if ($StartActionBridge) {
  Write-Host "ActionBridge: started/reused at $BridgeUrl"
  Write-Host "Lamp: $ActionBridgeBaseUrl"
}
if ($DirectorUrl.Trim().Length -gt 0) {
  Write-Host "Director: $DirectorUrl"
} else {
  Write-Host "Director: -"
}
Write-Host "AssistantTextActions: $AssistantTextActions"
Write-Host "TwoPhaseRefinement: $($TwoPhaseRefinement -or -not $NoTwoPhaseRefinement)"
Write-Host "RequireModelPlanning: $RequireModelPlanning"
Write-Host "PlannerProvider: $PlannerProvider model=$PlannerModel"
Write-Host "PlannerReply: $(-not $NoPlannerReply) voice=$PlannerReplyVoice"
Write-Host "PlannerOwnsReply: $PlannerOwnsReply"
Write-Host "RealtimePlayback: $(-not $NoRealtimePlayback -and -not $NoPlay -and -not $PlannerOwnsReply)"
Write-Host "PlannerPlayback: $(($PlannerPlayback -or $PlannerOwnsReply) -and -not $NoPlannerPlayback -and -not $NoPlay)"
Write-Host "RuntimeMemoryFile: $RuntimeMemoryFile"
Write-Host ""

& $Python @ArgsList
exit $LASTEXITCODE
