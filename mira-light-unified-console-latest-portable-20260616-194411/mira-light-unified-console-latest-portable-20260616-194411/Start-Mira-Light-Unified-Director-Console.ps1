param(
  [string]$EnvFile = "",
  [string]$ConsoleHost = "",
  [int]$ConsolePort = 8790,
  [string]$BoardHost = "",
  [int]$BoardPort = 22,
  [string]$BoardUser = "root",
  [switch]$NoBrowser,
  [switch]$SkipCelebration
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConsoleDir = Join-Path $RootDir "mira-light-unified-director-console"
$ShenzhenConsoleDir = Join-Path $RootDir "mira-light-shenzhen-console"
$ScriptsDir = Join-Path $RootDir "Motions_Shenzhen\demo_fixed_protocol_v2\scripts"
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"

function Import-EnvFile {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return }
  Get-Content $Path -Encoding utf8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    if ($line.StartsWith("export ")) { $line = $line.Substring(7).Trim() }
    $parts = $line -split "=", 2
    if ($parts.Length -ne 2) { return }
    $key = $parts[0].Trim()
    $val = $parts[1].Trim().Trim('"').Trim("'")
    if ($key -and $val -notmatch '\$\{') {
      [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
  }
}

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
  $EnvFile = Join-Path $RootDir "portable\unified-console.env"
}
Import-EnvFile -Path $EnvFile

if ($env:MIRA_UNIFIED_PYTHON) {
  $PythonBin = $env:MIRA_UNIFIED_PYTHON
} elseif (Test-Path $VenvPython) {
  $PythonBin = $VenvPython
} else {
  $PythonBin = "python"
}

if ([string]::IsNullOrWhiteSpace($ConsoleHost)) {
  $ConsoleHost = if ($env:MIRA_UNIFIED_CONSOLE_HOST) { $env:MIRA_UNIFIED_CONSOLE_HOST } else { "0.0.0.0" }
}
if ($env:MIRA_UNIFIED_CONSOLE_PORT) {
  $ConsolePort = [int]$env:MIRA_UNIFIED_CONSOLE_PORT
}
if ([string]::IsNullOrWhiteSpace($BoardHost)) {
  $BoardHost = if ($env:MIRA_SHENZHEN_BOARD_HOST) { $env:MIRA_SHENZHEN_BOARD_HOST } else { "192.168.0.183" }
}
if ($env:MIRA_SHENZHEN_BOARD_PORT) {
  $BoardPort = [int]$env:MIRA_SHENZHEN_BOARD_PORT
}
if ($env:MIRA_SHENZHEN_BOARD_USER) {
  $BoardUser = $env:MIRA_SHENZHEN_BOARD_USER
}

if (-not $env:MIRA_SHENZHEN_BOARD_PASSWORD) { $env:MIRA_SHENZHEN_BOARD_PASSWORD = "" }
if (-not $env:MIRA_CAMERA_BOARD_PASSWORD) { $env:MIRA_CAMERA_BOARD_PASSWORD = $env:MIRA_SHENZHEN_BOARD_PASSWORD }
if (-not $env:MIRA_CAMERA_BOARD_HOST) { $env:MIRA_CAMERA_BOARD_HOST = $BoardHost }
if (-not $env:MIRA_SHENZHEN_REMOTE_DESKTOP_DIR) { $env:MIRA_SHENZHEN_REMOTE_DESKTOP_DIR = "/home/sunrise/Desktop" }
if (-not $env:MIRA_SHENZHEN_REMOTE_LED_ENABLED) { $env:MIRA_SHENZHEN_REMOTE_LED_ENABLED = "1" }
if (-not $env:MIRA_SHENZHEN_REMOTE_TOUCH_ENABLED) { $env:MIRA_SHENZHEN_REMOTE_TOUCH_ENABLED = "1" }
if (-not $env:MIRA_SHENZHEN_SCRIPTS_DIR -and (Test-Path $ScriptsDir)) { $env:MIRA_SHENZHEN_SCRIPTS_DIR = $ScriptsDir }
if (-not $env:MIRA_SHENZHEN_DIGUA_OUTPUT_DIR) {
  $env:MIRA_SHENZHEN_DIGUA_OUTPUT_DIR = Join-Path $ConsoleDir "runtime\digua-console-output"
}
if (-not $env:MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS) { $env:MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS = "10" }
if (-not $env:MIRA_UNIFIED_CAMERA_START_WATCH) { $env:MIRA_UNIFIED_CAMERA_START_WATCH = "1" }
if (-not $env:MIRA_BOOK_FOLLOW_RECEIVER_PORT) { $env:MIRA_BOOK_FOLLOW_RECEIVER_PORT = "18000" }

$env:MIRA_SHENZHEN_BOARD_HOST = $BoardHost
$env:MIRA_LIGHT_BASE_URL = if ($env:MIRA_BOOK_FOLLOW_BASE_URL) { $env:MIRA_BOOK_FOLLOW_BASE_URL } else { "tcp://${BoardHost}:9527" }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$LanHost = "127.0.0.1"
try {
  $LanAdapter = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notmatch "Loopback" -and $_.IPAddress -notmatch "^169\."
  } | Select-Object -First 1
  if ($LanAdapter) { $LanHost = $LanAdapter.IPAddress }
} catch { }

$ConsolePublicHost = if ($env:MIRA_UNIFIED_CONSOLE_PUBLIC_HOST) { $env:MIRA_UNIFIED_CONSOLE_PUBLIC_HOST } else { $LanHost }
$ConsoleUrl = "http://${ConsolePublicHost}:${ConsolePort}/"
$ConsoleLocalUrl = "http://127.0.0.1:${ConsolePort}/"
$CelebrationHost = if ($env:MIRA_CELEBRATION_CONSOLE_HOST) { $env:MIRA_CELEBRATION_CONSOLE_HOST } else { "0.0.0.0" }
$CelebrationPort = if ($env:MIRA_CELEBRATION_CONSOLE_PORT) { [int]$env:MIRA_CELEBRATION_CONSOLE_PORT } else { 8777 }
$CelebrationLocalUrl = "http://127.0.0.1:${CelebrationPort}/"

function Require-File {
  param([string]$Path, [string]$Label)
  if (-not (Test-Path $Path)) {
    throw "$Label not found: $Path"
  }
}

function Probe-Url {
  param([string]$Url)
  try {
    $request = [System.Net.HttpWebRequest]::Create($Url)
    $request.Timeout = 1500
    $response = $request.GetResponse()
    $response.Close()
    return $true
  } catch {
    return $false
  }
}

function Wait-ForUrl {
  param([string]$Url, [string]$Label, [int]$ProcessId = 0)
  for ($i = 0; $i -lt 80; $i++) {
    if (Probe-Url -Url $Url) {
      Write-Host "$Label OK" -ForegroundColor Green
      return
    }
    if ($ProcessId -gt 0 -and -not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
      throw "$Label exited before it became ready."
    }
    Start-Sleep -Milliseconds 250
  }
  throw "$Label did not become ready at $Url"
}

function Stop-StaleProcess {
  param([int]$Port)
  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($connection in $connections) {
    $ownerPid = $connection.OwningProcess
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerPid" -ErrorAction SilentlyContinue
    if ($processInfo.CommandLine -match "shenzhen_console.py") {
      Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
      Start-Sleep -Milliseconds 300
    }
  }
}

Require-File -Path (Join-Path $ConsoleDir "shenzhen_console.py") -Label "Unified console"
Require-File -Path (Join-Path $ConsoleDir "scene_registry.json") -Label "Scene registry"
Require-File -Path (Join-Path $ConsoleDir "web\index.html") -Label "Web UI"
Require-File -Path (Join-Path $ShenzhenConsoleDir "shenzhen_console.py") -Label "Celebration console"

Write-Host "== Mira Light Unified Director Console ==" -ForegroundColor Cyan
Write-Host "Repo:      $RootDir"
Write-Host "Console:   $ConsoleUrl"
Write-Host "Local:     $ConsoleLocalUrl"
Write-Host "Board:     ${BoardUser}@${BoardHost}:${BoardPort}"
Write-Host "Python:    $PythonBin"
Write-Host "LED:       $env:MIRA_SHENZHEN_REMOTE_LED_ENABLED"
Write-Host ""

Stop-StaleProcess -Port $ConsolePort
if (-not $SkipCelebration) { Stop-StaleProcess -Port $CelebrationPort }

$CelebrationPid = 0
if (-not $SkipCelebration) {
  if (-not (Probe-Url -Url $CelebrationLocalUrl)) {
    $celebrationArgs = @(
      (Join-Path $ShenzhenConsoleDir "shenzhen_console.py"),
      "--host", $CelebrationHost,
      "--port", "$CelebrationPort",
      "--board-host", $BoardHost,
      "--board-port", "$BoardPort",
      "--board-user", $BoardUser
    )
    $celebrationProcess = Start-Process -FilePath $PythonBin -ArgumentList $celebrationArgs -PassThru -WindowStyle Hidden
    $CelebrationPid = $celebrationProcess.Id
    Wait-ForUrl -Url $CelebrationLocalUrl -Label "Celebration page" -ProcessId $CelebrationPid
  }
}

$ConsolePid = 0
if (Probe-Url -Url $ConsoleLocalUrl) {
  Write-Host "Unified director console already running at $ConsoleLocalUrl"
} else {
  $consoleArgs = @(
    (Join-Path $ConsoleDir "shenzhen_console.py"),
    "--host", $ConsoleHost,
    "--port", "$ConsolePort",
    "--board-host", $BoardHost,
    "--board-port", "$BoardPort",
    "--board-user", $BoardUser
  )
  $consoleProcess = Start-Process -FilePath $PythonBin -ArgumentList $consoleArgs -PassThru -WindowStyle Hidden
  $ConsolePid = $consoleProcess.Id
  Wait-ForUrl -Url $ConsoleLocalUrl -Label "Unified director console" -ProcessId $ConsolePid
}

$OpenBrowser = if ($env:MIRA_UNIFIED_OPEN_BROWSER) { $env:MIRA_UNIFIED_OPEN_BROWSER } else { "1" }
if (-not $NoBrowser -and $OpenBrowser -match "^(1|true|yes|on)$") {
  Start-Process $ConsoleUrl
}

Write-Host ""
Write-Host "Leave this PowerShell window open while using the unified director console." -ForegroundColor Yellow
Write-Host "Press Ctrl-C here to stop the console." -ForegroundColor Yellow

try {
  if ($ConsolePid -gt 0) {
    $process = Get-Process -Id $ConsolePid -ErrorAction SilentlyContinue
    if ($process) { $process.WaitForExit() }
  } else {
    Read-Host "Press Enter to close this launcher"
  }
} finally {
  if ($CelebrationPid -gt 0) {
    Stop-Process -Id $CelebrationPid -Force -ErrorAction SilentlyContinue
  }
}
