# PuTTY 手动安装脚本
# 下载并安装 plink 到用户目录（不需要管理员权限）

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  PuTTY 安装程序" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 配置
$plinkUrl = "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe"
$puttyUrl = "https://the.earth.li/~sgtatham/putty/latest/w64/putty.exe"
$installDir = "$env:LOCALAPPDATA\PuTTY"
$downloadDir = "$env:TEMP\putty_dl"

# 创建目录
Write-Host "[步骤 0/3] 准备目录..." -ForegroundColor Yellow
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Write-Host "  [OK] 创建: $installDir`n"
} else {
    Write-Host "  [信息] 目录已存在: $installDir`n"
}

if (-not (Test-Path $downloadDir)) {
    New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
}

# 下载 plink
Write-Host "[步骤 1/3] 下载 plink.exe..." -ForegroundColor Yellow
$plinkPath = "$downloadDir\plink.exe"

Write-Host "  下载地址: $plinkUrl" -ForegroundColor Gray
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($plinkUrl, $plinkPath)
    Write-Host "  [OK] plink.exe 下载完成`n"
} catch {
    Write-Host "  [错误] 下载失败: $_`n"
    Write-Host "  请手动下载: https://www.putty.org/`n"
    Read-Host "按 Enter 键退出"
    exit 1
}

# 下载 putty（可选）
Write-Host "[步骤 2/3] 下载 putty.exe（可选）..." -ForegroundColor Yellow
$puttyPath = "$downloadDir\putty.exe"

try {
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($puttyUrl, $puttyPath)
    Write-Host "  [OK] putty.exe 下载完成`n"
} catch {
    Write-Host "  [警告] putty.exe 下载失败（plink 已足够）`n"
}

# 安装
Write-Host "[步骤 3/3] 安装到 $installDir ..." -ForegroundColor Yellow
try {
    Copy-Item $plinkPath "$installDir\plink.exe" -Force
    Write-Host "  [OK] plink.exe 已复制`n"

    if (Test-Path $puttyPath) {
        Copy-Item $puttyPath "$installDir\putty.exe" -Force
        Write-Host "  [OK] putty.exe 已复制`n"
    }
} catch {
    Write-Host "  [错误] 安装失败: $_`n"
    Read-Host "按 Enter 键退出"
    exit 1
}

# 添加到 PATH
Write-Host "[配置] 添加到 PATH..." -ForegroundColor Yellow
$currentPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$installDir*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$currentPath;$installDir", "User")
    # 同时更新当前会话
    $env:Path = "$env:Path;$installDir"
    Write-Host "  [OK] 已添加到用户 PATH`n"
} else {
    Write-Host "  [信息] 已在 PATH 中`n"
}

# 验证
Write-Host "[验证] 检查安装..." -ForegroundColor Yellow
$plinkExe = Test-Path "$installDir\plink.exe"
Write-Host "  plink.exe: $(if($plinkExe){'[OK]'}else{'[X]'}) at $installDir`n"

if ($plinkExe) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  安装成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "`n安装目录: $installDir`n"
    Write-Host "下一步:" -ForegroundColor Yellow
    Write-Host "1. 关闭并重新打开 PowerShell" -ForegroundColor White
    Write-Host "2. 或运行: `$env:Path += ';$installDir'" -ForegroundColor White
    Write-Host "3. 测试: & '$installDir\plink.exe' -V`n" -ForegroundColor White

    # 尝试显示版本
    try {
        $version = & "$installDir\plink.exe" -V 2>&1
        Write-Host "版本信息: $version`n"
    } catch {
        Write-Host "版本检查失败（可忽略）`n"
    }
} else {
    Write-Host "[错误] plink.exe 未找到`n"
}

# 清理
Remove-Item $downloadDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "[清理] 临时文件已删除`n"

Read-Host "按 Enter 键退出"
