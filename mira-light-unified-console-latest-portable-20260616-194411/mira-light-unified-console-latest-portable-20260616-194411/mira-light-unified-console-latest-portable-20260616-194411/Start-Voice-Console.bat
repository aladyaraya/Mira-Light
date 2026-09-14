@echo off
echo ========================================
echo   Mira Light Voice Console
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未找到
    echo 请安装 Python 3.10+ 并添加到 PATH
    pause
    exit /b 1
)

echo [信息] Python 已找到
python --version
echo.

REM 检查 API Key
if "%STEPFUN_API_KEY%"=="" (
    echo [警告] STEPFUN_API_KEY 环境变量未设置
    echo.
    echo 语音控制台需要 StepFun API Key。
    echo 请设置环境变量：
    echo   set STEPFUN_API_KEY=your-api-key-here
    echo.
    set /p APIKEY="或在此输入 API Key（输入时不显示）: "

    if "!APIKEY!"=="" (
        echo [错误] API Key 不能为空
        pause
        exit /b 1
    )

    set STEPFUN_API_KEY=!APIKEY!
) else (
    echo [OK] STEPFUN_API_KEY 已设置
)

echo.
echo [信息] 启动语音控制台...
echo   Console: http://127.0.0.1:8790
echo   说 "退出对话" 停止监听
echo.

REM 切换到脚本目录
cd /d "%~dp0"

REM 启动语音控制台
python mira-light-unified-director-console\mira_stepfun_console_voice.py --console-url http://127.0.0.1:8790

pause
