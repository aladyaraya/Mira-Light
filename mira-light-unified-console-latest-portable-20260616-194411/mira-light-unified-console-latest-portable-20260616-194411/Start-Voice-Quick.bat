@echo off
chcp 65001 >nul
echo ========================================
echo   语音统一导演控制台启动器
echo ========================================
echo.

REM 检查 STEPFUN_API_KEY
if "%STEPFUN_API_KEY%"=="" (
    echo [错误] 未设置 STEPFUN_API_KEY
    echo.
    echo 请先设置 API Key：
    echo   方法 1: set STEPFUN_API_KEY=your-key-here
    echo   方法 2: 运行 .\Set-Voice-APIKey.ps1
    echo.
    pause
    exit /b 1
)

echo [OK] API Key 已设置
echo.

REM 检查控制台是否运行
echo [检查] 统一导演控制台...
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8790/api/scenes', timeout=2)" 2>nul
if errorlevel 1 (
    echo [X] 控制台未运行
    echo.
    echo 请先启动控制台：
    echo   python mira-light-unified-director-console\shenzhen_console.py
    echo.
    pause
    exit /b 1
)

echo [OK] 控制台正在运行
echo.

REM 启动语音控制台
echo ========================================
echo   启动语音控制台
echo ========================================
echo.
echo 语音命令：
echo   - "起床" / "醒来"
echo   - "摸一摸" / "摸摸"
echo   - "打开摄像头" / "拍照"
echo   - "睡觉" / "休息"
echo   - "退出对话" (停止)
echo.

cd /d "%~dp0"
python mira-light-unified-director-console\mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790

pause
