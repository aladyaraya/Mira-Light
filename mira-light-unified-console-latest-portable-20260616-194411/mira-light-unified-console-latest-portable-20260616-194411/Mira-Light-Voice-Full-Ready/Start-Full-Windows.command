@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: Mira Light Windows Full-Duplex Voice Mode
:: Uses the existing mira_stepfun_realtime_voice_actions.py script
:: with low-latency parameters for < 600ms target.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ==========================================
echo   Mira Light - Full Duplex Voice (Windows)
echo ==========================================
echo.

:: ---------------------------------------------------------------------------
:: 1. Ensure Python venv is available
:: ---------------------------------------------------------------------------
if not exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
    echo [setup] Python venv not found. Running setup first...
    powershell -ExecutionPolicy Bypass -File "%ROOT_DIR%\commands\Setup-Mira-Light-Windows-Voice.ps1"
    if errorlevel 1 (
        echo [error] Setup failed. Please run Setup-Mira-Light-Windows-Voice.ps1 manually.
        exit /b 1
    )
)

set "PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"

:: ---------------------------------------------------------------------------
:: 2. Low-latency full-duplex parameters (^< 600ms target)
:: ---------------------------------------------------------------------------
set "MIRA_LIGHT_LATENCY_PRESET=low"
set "MIRA_LIGHT_CAPTURE_MODE=continuous"
set "MIRA_LIGHT_INPUT_DEVICE=default"
set "MIRA_LIGHT_TTS_MODE=warm_gentleman"
set "MIRA_LIGHT_DISABLE_LOCAL_INTENT=1"

:: ---------------------------------------------------------------------------
:: 3. Launch full-duplex realtime voice session
:: ---------------------------------------------------------------------------
echo [config] Latency target: ^< 600ms
echo [config] Mode: full-duplex (simultaneous listen + speak)
echo [config] Model: StepFun StepAudio 2.5 Realtime
echo [config] API Key: auto-resolved (env ^> hardcoded fallback)
echo.

:: ---------------------------------------------------------------------------
:: 3. cd into scripts/ so bare imports (mira_config_env, etc.) resolve correctly
:: ---------------------------------------------------------------------------
cd /d "%ROOT_DIR%\scripts"

"%PYTHON%" -u mira_stepfun_realtime_voice_actions.py ^
    --input-device default ^
    --input-sample-rate 24000 ^
    --output-sample-rate 24000 ^
    --chunk-ms 20 ^
    --voice wenrounansheng ^
    --mode continuous ^
    --latency-preset low ^
    --no-denoise ^
    --assistant-text-actions ^
    --require-model-planning ^
    --bridge-url "http://127.0.0.1:19783" ^
    %*

if errorlevel 1 (
    echo.
    echo [error] Voice session exited with code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo [done] Voice session ended.
endlocal
