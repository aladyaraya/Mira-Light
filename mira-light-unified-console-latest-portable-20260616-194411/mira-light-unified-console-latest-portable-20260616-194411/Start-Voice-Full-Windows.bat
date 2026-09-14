@echo off
chcp 65001 >nul 2>&1
title Mira Light Voice (StepAudio - Natural Female Voice)

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "VOICE_DIR=%ROOT_DIR%\Mira-Light-Voice-Full-Ready"

echo ==================================================
echo   Mira Light Voice - StepAudio Realtime
echo ==================================================
echo   Engine:   StepAudio 2.5 (natural female voice)
echo   Voice:    wenrounvsheng
echo   Bridge:   http://127.0.0.1:19783
echo   Mode:     continuous (always listening)
echo ==================================================
echo.

REM ---- API Keys (fill in your own keys) ----
set "STEPFUN_API_KEY=YOUR_STEPFUN_API_KEY"
set "OPENCLAW_NEWAPI_API_KEY=YOUR_OPENCLAW_API_KEY"

REM ---- Config ----
set "MIRA_LIGHT_BRIDGE_URL=http://127.0.0.1:19783"
set "MIRA_LIGHT_ENABLE_LOCAL_SHORTCUT=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

REM ---- Python path ----
set "PYTHONPATH=%VOICE_DIR%\scripts;%VOICE_DIR%\scripts\models;%VOICE_DIR%\tools;%VOICE_DIR%\tools\mira_light_bridge"

REM ---- Quick runtime dir (avoids Windows MAX_PATH) ----
if not exist "C:\mira-runtime" mkdir "C:\mira-runtime"

REM ---- Start ----
cd /d "%VOICE_DIR%\scripts"
python -u mira_stepfun_realtime_voice_actions.py ^
  --input-device default ^
  --input-sample-rate 24000 ^
  --output-sample-rate 24000 ^
  --chunk-ms 20 ^
  --voice wenrounvsheng ^
  --mode continuous ^
  --latency-preset low ^
  --no-denoise ^
  --assistant-text-actions ^
  --bridge-url http://127.0.0.1:19783

pause
