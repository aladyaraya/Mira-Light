# SSH 密钥配置脚本
# 用于将公钥复制到 Mira Light 开发板

$publicKeyPath = "$env:USERPROFILE\.ssh\id_ed25519_mira.pub"
$host = "192.168.0.183"
$user = "root"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Mira Light SSH 密钥配置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查公钥是否存在
if (-not (Test-Path $publicKeyPath)) {
    Write-Host "[错误] 公钥文件不存在: $publicKeyPath" -ForegroundColor Red
    Write-Host "请先运行 ssh-keygen 生成密钥对" -ForegroundColor Yellow
    exit 1
}

Write-Host "[信息] 公钥文件: $publicKeyPath" -ForegroundColor Green
$publicKey = Get-Content $publicKeyPath -Raw
Write-Host "[信息] 公钥内容:" -ForegroundColor Green
Write-Host $publicKey
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  方法 1: 使用 ssh-copy-id（推荐）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "如果已安装 ssh-copy-id，运行：" -ForegroundColor Yellow
Write-Host "  ssh-copy-id -i `"$publicKeyPath`" $user@$host" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  方法 2: 手动复制（使用密码）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. SSH 登录到开发板：" -ForegroundColor Yellow
Write-Host "   ssh $user@$host" -ForegroundColor White
Write-Host ""
Write-Host "2. 登录后，执行以下命令：" -ForegroundColor Yellow
Write-Host "   mkdir -p ~/.ssh" -ForegroundColor White
Write-Host "   chmod 700 ~/.ssh" -ForegroundColor White
Write-Host "   echo '$publicKey' >> ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host "   exit" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  方法 3: 自动复制（需要密码）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$password = Read-Host "请输入开发板密码（输入时不显示）" -AsSecureString
$Bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($Bstr)

Write-Host ""
Write-Host "[信息] 正在复制公钥到开发板..." -ForegroundColor Green

# 创建远程脚本
$remoteScript = @"
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo '$publicKey' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo '公钥已成功添加到 authorized_keys'
"@

# 使用 ssh 执行远程脚本
try {
    $sshCommand = "ssh $user@$host `"$remoteScript`""
    Write-Host "[调试] 执行命令: $sshCommand" -ForegroundColor Gray

    # 设置 SSH 选项以接受 host key（首次连接）
    $env:SSH_OPTIONS = "-o StrictHostKeyChecking=no"

    Invoke-Expression $sshCommand

    Write-Host ""
    Write-Host "[成功] 公钥复制完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "测试无密码登录：" -ForegroundColor Yellow
    Write-Host "  ssh $user@$host" -ForegroundColor White
} catch {
    Write-Host ""
    Write-Host "[错误] 复制公钥失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "请使用方法 2 手动复制" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "按 Enter 键退出"
