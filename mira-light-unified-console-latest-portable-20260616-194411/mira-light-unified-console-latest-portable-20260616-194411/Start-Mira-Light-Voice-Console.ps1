#!/usr/bin/env pwsh
#Requires -Version 7.0
<#
.SYNOPSIS
    Start Mira Light Voice Console - Voice control for the Unified Director Console.

.DESCRIPTION
    This script starts the voice control system for the Mira Light Unified Director Console.
    It bridges the StepFun realtime voice ASR with the console's HTTP API (port 8790),
    enabling voice commands for scenes, camera, printer, teach mode, and more.

    Architecture:
        Microphone -> StepFun Realtime ASR -> Intent Classification
            -> Console API Adapter -> POST /api/run/{scene_id}
                                  -> POST /api/camera/start
                                  -> POST /api/teach/start
                                  -> etc.

    The adapter reuses existing voice components from Mira-Light-Voice-Full-Ready:
        - stepfun_realtime_voice.py   (WebSocket realtime voice session)
        - mira_realtime_action_orchestrator.py (event routing)
        - mira_voice_intents.py       (local keyword classification)
        - stepfun_llm_planner.py      (LLM semantic planning)

    New components:
        - voice_console_adapter.py    (console API dispatcher)
        - mira_stepfun_console_voice.py (realtime voice + console integration)

.PARAMETER ConsoleUrl
    URL of the Unified Director Console. Default: http://127.0.0.1:8790

.PARAMETER BridgeUrl
    URL of the Mira Light bridge for TTS feedback. Default: http://127.0.0.1:19783

.PARAMETER ApiKey
    StepFun API key. Falls back to STEPFUN_API_KEY env var.

.PARAMETER ProxyUrl
    Proxy URL for StepFun API. Falls back to STEPFUN_PROXY_URL env var.

.PARAMETER NoSemanticActions
    Disable semantic action dispatching (only voice state actions).

.PARAMETER NoVoiceStateActions
    Disable voice state quick actions (listening/thinking/answer).

.PARAMETER NoTtsFeedback
    Disable TTS voice feedback after action execution.

.PARAMETER ActionTimeoutSeconds
    Timeout for console API calls. Default: 15

.PARAMETER ListCommands
    List all available voice commands and exit.

.EXAMPLE
    .\Start-Mira-Light-Voice-Console.ps1
    # Start with default settings

.EXAMPLE
    .\Start-Mira-Light-Voice-Console.ps1 -ConsoleUrl "http://127.0.0.1:8790" -NoTtsFeedback
    # Start without TTS feedback

.EXAMPLE
    .\Start-Mira-Light-Voice-Console.ps1 -ListCommands
    # List all available voice commands
#>

[CmdletBinding()]
param(
    [string]$ConsoleUrl = "http://127.0.0.1:8790",
    [string]$BridgeUrl = "http://127.0.0.1:19783",
    [string]$ApiKey = "",
    [string]$ProxyUrl = "",
    [switch]$NoSemanticActions,
    [switch]$NoVoiceStateActions,
    [switch]$NoTtsFeedback,
    [int]$ActionTimeoutSeconds = 15,
    [switch]$ListCommands
)

$ErrorActionPreference = "Stop"
$script:Root = $PSScriptRoot
if (-not $script:Root) { $script:Root = (Get-Location).Path }

# ── Paths ──
$ConsoleDir = Join-Path $script:Root "mira-light-unified-director-console"
$VoiceDir = Join-Path $script:Root "Mira-Light-Voice-Full-Ready"
$VoiceScriptsDir = Join-Path $VoiceDir "scripts"
$RuntimeDir = Join-Path $script:Root "runtime" "voice-console"

# ── Ensure directories exist ──
New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

# ── Check prerequisites ──
function Test-Prerequisites {
    # Check Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "Python not found. Please install Python 3.10+ and ensure it's in PATH."
        exit 1
    }
    $pyVersion = & python --version 2>&1
    Write-Host "Python: $pyVersion" -ForegroundColor Cyan

    # Check console is running
    try {
        $r = Invoke-WebRequest -Uri "$ConsoleUrl/api/scenes" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "Console OK at $ConsoleUrl (status $($r.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Warning "Console not responding at $ConsoleUrl. Please start the console first:"
        Write-Warning "  .\Start-Mira-Light-Unified-Director-Console.command"
        Write-Host ""
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -notmatch '^[Yy]') { exit 1 }
    }

    # Check voice scripts exist
    $requiredScripts = @(
        "stepfun_realtime_voice.py",
        "mira_realtime_action_orchestrator.py",
        "mira_voice_intents.py",
        "stepfun_llm_planner.py"
    )
    foreach ($s in $requiredScripts) {
        $p = Join-Path $VoiceScriptsDir $s
        if (-not (Test-Path $p)) {
            Write-Error "Missing voice script: $p"
            exit 1
        }
    }

    # Check adapter exists
    $adapterPath = Join-Path $ConsoleDir "voice_console_adapter.py"
    if (-not (Test-Path $adapterPath)) {
        Write-Error "Voice console adapter not found: $adapterPath"
        exit 1
    }

    Write-Host "All prerequisites OK" -ForegroundColor Green
}

# ── Resolve API key ──
function Resolve-ApiKey {
    param([string]$ExplicitKey)
    $key = $ExplicitKey.Trim()
    if (-not $key) { $key = $env:STEPFUN_API_KEY }
    if (-not $key) { $key = $env:STEP_API_KEY }
    if (-not $key) {
        Write-Error "StepFun API key required. Set STEPFUN_API_KEY environment variable or pass -ApiKey."
        exit 1
    }
    return $key
}

# ── List commands ──
if ($ListCommands) {
    Write-Host "=== Mira Light Voice Console Commands ===`n" -ForegroundColor Cyan

    Write-Host "--- Scene Commands ---" -ForegroundColor Yellow
    $sceneCommands = @{
        "wake_up" = "起床, 醒来, 唤醒, 开场, 苏醒, 伸懒腰"
        "curious_observe" = "好奇, 观察, 看一下, 看看我, 歪头看"
        "touch_affection" = "摸一摸, 摸摸, 亲近, 撒娇, 靠过来, 蹭一下"
        "hand_avoid" = "躲开, 躲一下, 手靠近, 别碰, 避开"
        "cute_probe" = "卖萌, 可爱动作, 歪头, 探头, 萌一下"
        "daydream" = "发呆, 走神, 做梦, 白日梦, 放空"
        "standup_reminder" = "久坐, 站起来, 起身, 活动一下"
        "track_target" = "追踪, 跟踪, 跟着看, 看这边, 目标追踪"
        "celebrate" = "庆祝, 跳舞, 开心跳, 彩虹, 高兴一下, 跳个舞"
        "farewell" = "拜拜, 再见, 挥手, 送别, 下次见"
        "sleep" = "睡觉, 休息, 睡眠, 关灯休息, 安静下来"
        "sigh_demo" = "叹气, 叹气检测, 安慰, 唉, 哎"
        "multi_person_demo" = "多人, 两个人, 多人反应, 纠结一下"
        "voice_demo_tired" = "我今天好累, 语音理解, 听懂我累, 累了"
        "startle_sound" = "吓一跳, 受惊, 惊吓, 突然声音"
        "praise_demo" = "夸奖, 被夸奖, 开心一下, 你好可爱, 真可爱"
        "criticism_demo" = "批评, 被批评, 委屈, 表现不好, 不太行"
    }
    foreach ($cmd in $sceneCommands.GetEnumerator() | Sort-Object Key) {
        Write-Host "  $($cmd.Key): $($cmd.Value)" -ForegroundColor White
    }

    Write-Host "`n--- Console Feature Commands ---" -ForegroundColor Yellow
    $consoleCommands = @{
        "camera_start" = "打开摄像头, 启动相机, 看看周围, 打开相机"
        "camera_stop" = "关闭摄像头, 停止相机, 关掉相机"
        "camera_capture" = "拍照, 拍一张, 截图"
        "camera_print" = "打印照片, 打印图片, 打印"
        "printer_status" = "打印机状态, 检查打印"
        "teach_start" = "开始示教, 记录动作, 示教模式"
        "teach_stop" = "停止示教, 结束记录"
        "teach_play" = "播放动作, 回放"
        "book_follow_start" = "开始追书, 追书模式"
        "book_follow_stop" = "停止追书, 结束追书"
        "touch_start" = "启动触摸, 打开触摸"
        "touch_stop" = "关闭触摸, 停止触摸"
        "emergency_stop" = "紧急停止, 停下, 停止"
        "narration_play" = "播放旁白, 开始旁白"
        "show_start" = "开始表演, 启动表演"
        "show_stop" = "停止表演, 结束表演"
    }
    foreach ($cmd in $consoleCommands.GetEnumerator() | Sort-Object Key) {
        Write-Host "  $($cmd.Key): $($cmd.Value)" -ForegroundColor White
    }

    Write-Host "`n--- Voice State Actions ---" -ForegroundColor Yellow
    Write-Host "  listening  -> quick-action/voice_motion_listening (Mira starts listening)" -ForegroundColor White
    Write-Host "  thinking   -> quick-action/voice_motion_thinking (Mira is thinking)" -ForegroundColor White
    Write-Host "  answer     -> quick-action/voice_motion_answer (Mira responds)" -ForegroundColor White

    Write-Host "`nTip: Speak naturally in Chinese. The system uses local keyword matching" -ForegroundColor DarkGray
    Write-Host "     for zero-latency response, with LLM fallback for ambiguous commands." -ForegroundColor DarkGray
    exit 0
}

# ── Main ──
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Mira Light Voice Console" -ForegroundColor Cyan
Write-Host "  Voice Control for Unified Director" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Test-Prerequisites
$apiKey = Resolve-ApiKey -ExplicitKey $ApiKey

# Set environment variables for the voice system
$env:STEPFUN_API_KEY = $apiKey
if ($ProxyUrl) { $env:STEPFUN_PROXY_URL = $ProxyUrl }

# Build arguments for the realtime voice script
$voiceScript = Join-Path $ConsoleDir "mira_stepfun_console_voice.py"

$arguments = @(
    $voiceScript,
    "--console-url", $ConsoleUrl,
    "--bridge-url", $BridgeUrl,
    "--action-timeout-seconds", $ActionTimeoutSeconds
)

if ($NoSemanticActions) { $arguments += "--no-semantic-actions" }
if ($NoVoiceStateActions) { $arguments += "--no-voice-state-actions" }
if ($NoTtsFeedback) { $arguments += "--no-tts-feedback" }
if ($ApiKey) { $arguments += @("--api-key", $ApiKey) }
if ($ProxyUrl) { $arguments += @("--proxy-url", $ProxyUrl) }

Write-Host "Starting voice console..." -ForegroundColor Green
Write-Host "  Console: $ConsoleUrl" -ForegroundColor Gray
Write-Host "  Bridge:  $BridgeUrl" -ForegroundColor Gray
Write-Host "  Semantic actions: $(-not $NoSemanticActions)" -ForegroundColor Gray
Write-Host "  Voice state actions: $(-not $NoVoiceStateActions)" -ForegroundColor Gray
Write-Host "  TTS feedback: $(-not $NoTtsFeedback)" -ForegroundColor Gray
Write-Host ""
Write-Host "Speak naturally to control the console." -ForegroundColor Cyan
Write-Host "Say 'list commands' or run with -ListCommands to see all commands." -ForegroundColor DarkGray
Write-Host "Press Ctrl+C to stop.`n" -ForegroundColor DarkGray

# Start the voice process
$pythonPath = (Get-Command python).Source
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonPath
$psi.Arguments = ($arguments | ForEach-Object { '"' + $_ + '"' }) -join " "
$psi.WorkingDirectory = $script:Root
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $false
$psi.RedirectStandardError = $false

$proc = [System.Diagnostics.Process]::Start($psi)

# Wait for process
Write-Host "Voice console started (PID: $($proc.Id))" -ForegroundColor Green
Write-Host ""

try {
    $proc.WaitForExit()
} finally {
    if (-not $proc.HasExited) {
        Write-Host "`nStopping voice console..." -ForegroundColor Yellow
        $proc.Kill()
    }
    $exitCode = $proc.ExitCode
    Write-Host "Voice console exited with code $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })
}
