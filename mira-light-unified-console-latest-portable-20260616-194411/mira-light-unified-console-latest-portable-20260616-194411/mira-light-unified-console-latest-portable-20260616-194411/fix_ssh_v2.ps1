# 修复 SSH 密钥查找
# 在 build_ssh_command 中添加 IdentityFile 支持

$filePath = "Chrome-Camera-Anime\digua_remote_render_pipeline.py"

Write-Host "`n修复 SSH IdentityFile 支持" -ForegroundColor Cyan
Write-Host "=" * 60

if (-not (Test-Path $filePath)) {
    Write-Host "`n[错误] 文件不存在: $filePath" -ForegroundColor Red
    Write-Host "当前目录: $(Get-Location)`n" -ForegroundColor Gray
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host "`n[信息] 读取文件..." -ForegroundColor Yellow
$content = Get-Content $filePath -Raw -Encoding UTF8
Write-Host "  [OK] 文件大小: $($content.Length) 字符`n" -ForegroundColor Green

# 修改 1: 添加 identity_file 参数
Write-Host "[步骤 1/2] 修改 build_ssh_command 函数签名..." -ForegroundColor Yellow

$oldSignature = @"
def build_ssh_command(
    *,
    host: str,
    user: str,
    port: int,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_script: str,
    batch_mode: bool,
) -> list[str]:"@

$newSignature = @"
def build_ssh_command(
    *,
    host: str,
    user: str,
    port: int,
    bind_address: str,
    known_hosts_path: Path,
    connect_timeout: int,
    remote_script: str,
    batch_mode: bool,
    identity_file: str | None = None,
) -> list[str]:"@

if ($content.Contains($oldSignature.Replace("`n", "`r`n"))) {
    $content = $content.Replace($oldSignature.Replace("`n", "`r`n"), $newSignature.Replace("`n", "`r`n"))
    Write-Host "  [OK] 函数签名已更新`n" -ForegroundColor Green
} elseif ($content.Contains($oldSignature)) {
    $content = $content.Replace($oldSignature, $newSignature)
    Write-Host "  [OK] 函数签名已更新`n" -ForegroundColor Green
} else {
    Write-Host "  [警告] 未找到原函数签名，尝试其他方法...`n" -ForegroundColor Yellow
}

# 修改 2: 添加 -i 选项
Write-Host "[步骤 2/2] 添加 IdentityFile 支持..." -ForegroundColor Yellow

$oldCommand = @'
    if bind_address:
        command.extend(["-b", bind_address])
    command.extend(["-p", str(port), f"{user}@{host}", "sh", "-lc", sh_quote(remote_script)])'@

$newCommand = @'
    if bind_address:
        command.extend(["-b", bind_address])
    # 添加 IdentityFile（如果提供）
    if identity_file:
        command.extend(["-i", identity_file])
    command.extend(["-p", str(port), f"{user}@{host}", "sh", "-lc", sh_quote(remote_script)])'@

if ($content.Contains($oldCommand.Replace("`n", "`r`n"))) {
    $content = $content.Replace($oldCommand.Replace("`n", "`r`n"), $newCommand.Replace("`n", "`r`n"))
    Write-Host "  [OK] IdentityFile 支持已添加`n" -ForegroundColor Green
} elseif ($content.Contains($oldCommand)) {
    $content = $content.Replace($oldCommand, $newCommand)
    Write-Host "  [OK] IdentityFile 支持已添加`n" -ForegroundColor Green
} else {
    Write-Host "  [错误] 未找到要修改的命令构建代码`n" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

# 修改 3: 在 run_ssh_capture 中查找并传递 identity_file
Write-Host "[步骤 3/3] 修改 run_ssh_capture 以自动查找私钥..." -ForegroundColor Yellow

$oldRun = @'
    command = build_ssh_command(
        host=host,
        user=user,
        port=port,
        bind_address=bind_address,
        known_hosts_path=known_hosts_path,
        connect_timeout=connect_timeout,
        remote_script=remote_script,
        batch_mode=not password,
    )'@

$newRun = @'
    # 尝试使用标准 SSH 密钥位置
    identity_file = None
    if not password:
        from pathlib import Path as _Path
        home = _Path.home()
        for key_path in [
            home / ".ssh" / "id_ed25519_mira",
            home / ".ssh" / "id_ed25519",
            home / ".ssh" / "id_rsa",
        ]:
            if key_path.exists():
                identity_file = str(key_path)
                break

    command = build_ssh_command(
        host=host,
        user=user,
        port=port,
        bind_address=bind_address,
        known_hosts_path=known_hosts_path,
        connect_timeout=connect_timeout,
        remote_script=remote_script,
        batch_mode=not password,
        identity_file=identity_file,
    )'@

if ($content.Contains($oldRun.Replace("`n", "`r`n"))) {
    $content = $content.Replace($oldRun.Replace("`n", "`r`n"), $newRun.Replace("`n", "`r`n"))
    Write-Host "  [OK] run_ssh_capture 已更新`n" -ForegroundColor Green
} elseif ($content.Contains($oldRun)) {
    $content = $content.Replace($oldRun, $newRun)
    Write-Host "  [OK] run_ssh_capture 已更新`n" -ForegroundColor Green
} else {
    Write-Host "  [警告] 未找到 run_ssh_capture 的调用`n" -ForegroundColor Yellow
}

# 保存
Write-Host "[保存] 写入文件..." -ForegroundColor Yellow
try {
    $content | Set-Content $filePath -Encoding UTF8 -Force
    Write-Host "  [OK] 文件已保存`n" -ForegroundColor Green
} catch {
    Write-Host "  [错误] 保存失败: $_`n" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host "=" * 60
Write-Host "修复完成！" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "`n请重启控制台并测试摄像头抓取。`n" -ForegroundColor Yellow

Read-Host "按 Enter 键退出"
