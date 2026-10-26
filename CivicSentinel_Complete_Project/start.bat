@echo off
setlocal
cd /d "%~dp0"
title CivicSentinel Infrastructure Intelligence Platform

echo ============================================================
echo   CivicSentinel - Single-Port Deployment (Port 8000)
echo   OpenCV AI Competition 2026 Powered by AWS
echo ============================================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ is required but not found in PATH.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)

if not exist ".venv\Scripts\python.exe" (
    echo [Setup] Creating Python virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [Setup] Installing backend dependencies...
    .venv\Scripts\pip.exe install -r backend\requirements.txt
)

where node >nul 2>nul
if %errorlevel% equ 0 (
    where npm >nul 2>nul
    if %errorlevel% equ 0 (
        if not exist "frontend\node_modules" (
            echo [Setup] Installing frontend dependencies...
            cd frontend
            call npm install
            cd ..
        )
        if not exist "frontend\dist\index.html" (
            echo [Build] Compiling frontend application into frontend\dist...
            cd frontend
            call npm run build
            cd ..
        )
    )
)

if not exist "frontend\dist\index.html" (
    echo [WARNING] frontend\dist\index.html not found. Node.js is required to build frontend.
)

set PYTHONPATH=%cd%
echo.
echo ============================================================
echo   CivicSentinel Online: http://localhost:8000/
echo ============================================================
echo   - Complete Application:  http://localhost:8000/
echo   - Dashboard Route:       http://localhost:8000/dashboard
echo   - API Documentation:     http://localhost:8000/docs
echo   - Health Diagnostics:    http://localhost:8000/health
echo   - Real-Time WebSocket:   ws://localhost:8000/ws
echo.
echo Press Ctrl+C in this terminal, or run stop.bat in another terminal to stop.
echo.
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
pause
