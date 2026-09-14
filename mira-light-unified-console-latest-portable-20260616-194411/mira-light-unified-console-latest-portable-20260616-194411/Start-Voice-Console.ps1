# 语音控制台启动器
# 用法: .\Start-Voice-Console.ps1 [-ApiKey "your-key"]

[CmdletBinding()]
param(
    [string]$ApiKey = ""
)

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Mira Light Voice Console" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 检查 Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[错误] Python 未找到`n" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}
Write-Host "[OK] Python: $(& python --version 2>&1)`n" -ForegroundColor Green

# 检查/设置 API Key
$apiKeyToUse = $ApiKey.Trim()
if (-not $apiKeyToUse) {
    $apiKeyToUse = $env:STEPFUN_API_KEY
}

if (-not $apiKeyToUse) {
    Write-Host "[错误] 需要设置 STEPFUN_API_KEY`n" -ForegroundColor Red
    Write-Host "方法 1：通过参数" -ForegroundColor Yellow
    Write-Host "  .\Start-Voice-Console.ps1 -ApiKey `"your-stepfun-api-key`"`n" -ForegroundColor White
    Write-Host "方法 2：通过环境变量" -ForegroundColor Yellow
    Write-Host "  `$env:STEPFUN_API_KEY = `"your-key`"" -ForegroundColor White
    Write-Host "  .\Start-Voice-Console.ps1`n" -ForegroundColor White
    Write-Host "方法 3：永久设置" -ForegroundColor Yellow
    Write-Host "  [System.Environment]::SetEnvironmentVariable('STEPFUN_API_KEY', 'your-key', 'User')`n" -ForegroundColor White
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host "[OK] API Key 已配置`n" -ForegroundColor Green

# 检查控制台
Write-Host "[检查] 统一导演控制台..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8790/api/scenes" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] 控制台正在运行 (状态: $($response.StatusCode))`n" -ForegroundColor Green
} catch {
    Write-Host "[X] 控制台未运行`n" -ForegroundColor Red
    Write-Host "请先启动统一导演控制台：" -ForegroundColor Yellow
    Write-Host "  .\Start-Mira-Light-Unified-Director-Console.ps1`n" -ForegroundColor White
    Read-Host "按 Enter 键退出"
    exit 1
}

# 设置环境变量
$env:STEPFUN_API_KEY = $apiKeyToUse

# 启动语音控制台
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  启动语音控制台" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Console: http://127.0.0.1:8790" -ForegroundColor Gray
Write-Host "Bridge:  http://127.0.0.1:19783`n" -ForegroundColor Gray

Write-Host "你可以开始说话了：" -ForegroundColor Cyan
Write-Host "  - '起床' / '醒来'" -ForegroundColor White
Write-Host "  - '摸一摸' / '摸摸'" -ForegroundColor White
Write-Host "  - '打开摄像头' / '拍照'" -ForegroundColor White
Write-Host "  - '睡觉' / '休息'" -ForegroundColor White
Write-Host "  - '退出对话' (停止)`n" -ForegroundColor White

$voiceScript = "mira-light-unified-director-console\mira_stepfun_console_voice.py"
$arguments = @(
    $voiceScript,
    "--console-url", "http://127.0.0.1:8790"
)

if ($ApiKey) {
    $arguments += @("--api-key", $ApiKey)
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "python"
$psi.Arguments = ($arguments | ForEach-Object { '"' + $_ + '"' }) -join " "
$psi.WorkingDirectory = (Get-Location).Path
$psi.UseShellExecute = $false

try {
    $proc = [System.Diagnostics.Process]::Start($psi)
    Write-Host "`n[OK] 语音控制台已启动 (PID: $($proc.Id))`n" -ForegroundColor Green

    # 等待退出
    $proc.WaitForExit()

    $exitCode = $proc.ExitCode
    Write-Host "`n语音控制台已退出 (代码: $exitCode)`n" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Yellow" })
} catch {
    Write-Host "`n[错误] 启动失败: $_`n" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}
