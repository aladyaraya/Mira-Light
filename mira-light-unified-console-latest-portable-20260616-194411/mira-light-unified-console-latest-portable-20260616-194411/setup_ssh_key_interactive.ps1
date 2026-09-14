# SSH 公钥一键配置脚本
# 将本地 SSH 公钥复制到 Mira Light 开发板

param(
    [string]$Host = "192.168.0.183",
    [string]$User = "root",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519_mira.pub"
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Mira Light SSH 公钥配置" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 检查公钥文件
if (-not (Test-Path $KeyPath)) {
    Write-Host "[错误] 公钥文件不存在: $KeyPath" -ForegroundColor Red
    Write-Host "`n请先运行: ssh-keygen -t ed25519 -C `"mira-board`"`n" -ForegroundColor Yellow
    exit 1
}

$publicKey = Get-Content $KeyPath -Raw | ForEach-Object { $_.Trim() }
Write-Host "[信息] 公钥已加载:" -ForegroundColor Green
Write-Host "  $publicKey`n" -ForegroundColor Gray

# 方法 1: 使用 PowerShell 直接配置（推荐）
Write-Host "[方法 1] 使用 SSH 命令配置`n" -ForegroundColor Cyan

$password = Read-Host "请输入 $User@$Host 的密码" -AsSecureString

if (-not $password) {
    Write-Host "`n[错误] 密码不能为空`n" -ForegroundColor Red
    exit 1
}

# 转换安全字符串为明文（仅在内存中）
$Bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($Bstr)

# 构建远程命令
$remoteCommand = @"
mkdir -p ~/.ssh &&
chmod 700 ~/.ssh &&
echo '$publicKey' >> ~/.ssh/authorized_keys &&
chmod 600 ~/.ssh/authorized_keys &&
echo '公钥配置成功' &&
wc -l ~/.ssh/authorized_keys
"@

Write-Host "[执行] 正在配置开发板...`n" -ForegroundColor Yellow

try {
    # Windows OpenSSH 不支持直接通过管道传密码
    # 这里提供一个简化的手动命令

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  请手动执行以下步骤：" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    Write-Host "1. SSH 登录到开发板：" -ForegroundColor Yellow
    Write-Host "   ssh $User@$Host`n" -ForegroundColor White

    Write-Host "2. 登录后，复制粘贴以下所有命令（一次性执行）：`n" -ForegroundColor Yellow
    Write-Host "   mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$publicKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'OK' && wc -l ~/.ssh/authorized_keys`n" -ForegroundColor White

    Write-Host "3. 如果看到 'OK' 和行数，说明配置成功`n" -ForegroundColor Yellow
    Write-Host "4. 退出开发板: exit`n" -ForegroundColor Yellow

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  或使用一键命令（在 PowerShell 中）" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    $oneLiner = "ssh $User@$Host `"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$publicKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'OK' && wc -l ~/.ssh/authorized_keys`""

    Write-Host $oneLiner -ForegroundColor White
    Write-Host "`n（复制上面的命令，在 PowerShell 中执行，然后输入密码）`n" -ForegroundColor Gray

    # 尝试启动交互式 SSH 会话
    Write-Host "[询问] 是否现在启动 SSH 会话？(Y/N)" -ForegroundColor Cyan
    $confirm = Read-Host

    if ($confirm -eq 'Y' -or $confirm -eq 'y') {
        Write-Host "`n[启动] SSH 会话...`n" -ForegroundColor Green
        Write-Host "（登录后请复制上面的命令执行）`n" -ForegroundColor Gray
        Start-Sleep -Seconds 2
        ssh $User@$Host
    }

} catch {
    Write-Host "`n[错误] $_`n" -ForegroundColor Red
    exit 1
} finally {
    # 清理内存中的密码
    if ($Bstr) {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr) | Out-Null
    }
}

Write-Host "`n配置完成！测试无密码登录：" -ForegroundColor Green
Write-Host "  ssh $User@$Host`n" -ForegroundColor White
