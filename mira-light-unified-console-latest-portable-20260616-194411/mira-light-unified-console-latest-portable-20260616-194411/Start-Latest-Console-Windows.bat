@echo off
chcp 65001 >nul 2>&1
title Mira Light Latest Console (8791)

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

REM ---- 推荐使用 SSH 密钥认证，密码留空 ----
set "MIRA_SHENZHEN_BOARD_HOST=192.168.0.183"
set "MIRA_SHENZHEN_BOARD_PORT=22"
set "MIRA_SHENZHEN_BOARD_USER=root"
set "MIRA_SHENZHEN_BOARD_PASSWORD="

set "MIRA_UNIFIED_CONSOLE_HOST=0.0.0.0"
set "MIRA_UNIFIED_CONSOLE_PORT=8791"
set "MIRA_UNIFIED_OPEN_BROWSER=1"

set "MIRA_CELEBRATION_CONSOLE_HOST=0.0.0.0"
set "MIRA_CELEBRATION_CONSOLE_PORT=8777"
set "MIRA_TOUCH_AUDIO_BRIDGE_PORT=9783"

set "MIRA_SHENZHEN_REMOTE_DESKTOP_DIR=/home/sunrise/Desktop"
set "MIRA_SHENZHEN_REMOTE_LED_ENABLED=1"
set "MIRA_SHENZHEN_REMOTE_TOUCH_ENABLED=1"

set "MIRA_UNIFIED_CAMERA_INTERVAL_SECONDS=10"
set "MIRA_UNIFIED_CAMERA_START_WATCH=1"
set "MIRA_UNIFIED_STOP_LEGACY_CAMERA_CONSOLE=1"

set "MIRA_SHENZHEN_SCRIPTS_DIR=%ROOT_DIR%\Motions_Shenzhen\demo_fixed_protocol_v2\scripts"
set "MIRA_UNIFIED_WEB_ROOT=%ROOT_DIR%\mira-light-unified-director-console-keyboard\web"
set "MIRA_SHENZHEN_DIGUA_OUTPUT_DIR=%ROOT_DIR%\mira-light-unified-director-console\runtime\digua-console-output"

set "MIRA_CAMERA_BOARD_HOST=192.168.0.183"
set "MIRA_CAMERA_BOARD_PASSWORD=rootroot"
set "MIRA_LIGHT_BASE_URL=tcp://192.168.0.183:9527"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ==================================================
echo   Mira Light Latest Console (8791)
echo ==================================================
echo   Console:  http://127.0.0.1:8791/
echo   Board:    root@192.168.0.183:22
echo   Web Root: %MIRA_UNIFIED_WEB_ROOT%
echo   Scripts:  %MIRA_SHENZHEN_SCRIPTS_DIR%
echo ==================================================
echo.

REM ---- 先启动 Celebration 页面 (8777) ----
echo Starting Celebration page on port 8777 ...
start "Mira Celebration (8777)" /min python "%ROOT_DIR%\mira-light-shenzhen-console\shenzhen_console.py" --host 0.0.0.0 --port 8777 --board-host 192.168.0.183 --board-port 22 --board-user root

REM ---- 等待 Celebration 就绪 ----
timeout /t 3 /nobreak >nul

REM ---- 启动最新统一控制台 (8791) ----
echo Starting Unified Director Console on port 8791 ...
start "Mira Console (8791)" python "%ROOT_DIR%\mira-light-unified-director-console\shenzhen_console.py" --host 0.0.0.0 --port 8791 --board-host 192.168.0.183 --board-port 22 --board-user root

REM ---- 等待控制台就绪 ----
echo Waiting for console to become ready ...
set /a TRIES=0
:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a TRIES+=1
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8791/ > "%TEMP%\mira_console_probe.txt" 2>nul
set /p PROBE=<"%TEMP%\mira_console_probe.txt"
if "%PROBE%"=="200" goto :READY
if %TRIES% LSS 20 goto :WAIT_LOOP
echo WARNING: console did not become ready within 20 seconds.

:READY
echo Console probe: %PROBE%
echo.
echo Opening browser ...
start http://127.0.0.1:8791/

echo.
echo ==================================================
echo  Console started in a separate window.
echo  Close that window to stop the console.
echo  URL: http://127.0.0.1:8791/
echo ==================================================
echo.
echo This launcher window can be closed.
timeout /t 5 /nobreak >nul
