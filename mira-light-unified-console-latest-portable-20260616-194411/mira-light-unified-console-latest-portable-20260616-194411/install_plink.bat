@echo off
echo ========================================
echo   PuTTY (plink) 安装程序
echo ========================================
echo.
echo 正在下载 plink.exe...
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\PuTTY"
set "DOWNLOAD_FILE=%TEMP%\plink.exe"
set "PLINK_URL=https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe"

REM 创建目录
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM 使用 PowerShell 下载
echo [1/3] 下载 plink.exe ...
powershell -Command "try { Invoke-WebRequest -Uri '%PLINK_URL%' -OutFile '%DOWNLOAD_FILE%' -UseBasicParsing; Write-Host '[OK] 下载完成' } catch { Write-Host '[错误] 下载失败'; exit 1 }"

if not exist "%DOWNLOAD_FILE%" (
    echo.
    echo [错误] 下载失败！
    echo.
    echo 请手动下载: https://www.putty.org/
    echo.
    pause
    exit /b 1
)

echo.
echo [2/3] 安装到 %INSTALL_DIR% ...
copy /Y "%DOWNLOAD_FILE%" "%INSTALL_DIR%\plink.exe" >nul
echo [OK] 安装完成

echo.
echo [3/3] 添加到 PATH ...
setx PATH "%PATH%;%INSTALL_DIR%" >nul 2>&1
echo [OK] 已添加到用户 PATH

echo.
echo ========================================
echo   安装成功！
echo ========================================
echo.
echo 安装目录: %INSTALL_DIR%
echo.
echo 下一步:
echo 1. 关闭并重新打开 PowerShell
echo 2. 测试: plink -V
echo.
pause
