@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   CivicSentinel - Stopping Processes
echo ============================================================

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating server process PID %%a on port 8000...
    taskkill /F /PID %%a >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" >nul 2>&1

echo [OK] CivicSentinel processes stopped.
