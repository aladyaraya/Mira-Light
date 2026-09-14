# 一键设置 StepFun API Key
# 使用方法: .\Set-Voice-APIKey.ps1

param(
    [string]$ApiKey = ""
)

if (-not $ApiKey) {
    Write-Host "`n设置 StepFun API Key`n" -ForegroundColor Cyan
    Write-Host "1. 访问 https://platform.stepfun.com/" -ForegroundColor Yellow
    Write-Host "2. 登录并创建 API Key" -ForegroundColor Yellow
    Write-Host "3. 复制密钥`n" -ForegroundColor Yellow

    $ApiKey = Read-Host "请输入你的 StepFun API Key"

    if (-not $ApiKey -or $ApiKey.Trim() -eq "") {
        Write-Host "`n[错误] API Key 不能为空`n" -ForegroundColor Red
        exit 1
    }
}

$ApiKey = $ApiKey.Trim()

# 设置为用户环境变量（永久）
[System.Environment]::SetEnvironmentVariable('STEPFUN_API_KEY', $ApiKey, 'User')

# 同时设置为当前会话
$env:STEPFUN_API_KEY = $ApiKey

Write-Host "`n[OK] API Key 已设置！`n" -ForegroundColor Green
Write-Host "  - 已保存到用户环境变量" -ForegroundColor Gray
Write-Host "  - 当前会话已生效`n" -ForegroundColor Gray

Write-Host "现在可以启动语音控制台：" -ForegroundColor Cyan
Write-Host "  .\Start-Voice-Quick.bat`n" -ForegroundColor White

Read-Host "按 Enter 键退出"
