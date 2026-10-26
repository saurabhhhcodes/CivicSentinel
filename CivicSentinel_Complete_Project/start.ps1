# CivicSentinel - Unified Single-Port Startup Script for Windows PowerShell
$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  CivicSentinel - Infrastructure Intelligence Platform" -ForegroundColor Cyan
Write-Host "  Single-Port Deployment (Frontend + Backend on Port 8000)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check Python tool
try {
    $pyVer = python --version
    Write-Host "[OK] Python detected: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python 3.10+ is required but was not found in PATH. Please install Python." -ForegroundColor Red
    exit 1
}

# 2. Virtual Environment verification
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[Setup] Virtual environment not found at .venv. Creating..." -ForegroundColor Yellow
    python -m venv .venv
    & "$ProjectDir\.venv\Scripts\pip.exe" install -r backend\requirements.txt
} else {
    Write-Host "[OK] Python virtual environment verified: .venv" -ForegroundColor Green
}

# 3. Environment configuration check
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[Setup] Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    }
}

# 4. Node.js and frontend check (optional if frontend\dist\index.html already built)
$distIndex = Join-Path $ProjectDir "frontend\dist\index.html"
$nodeAvailable = $false
try {
    $nodeVer = node --version
    $npmVer = npm --version
    $nodeAvailable = $true
    Write-Host "[OK] Node.js ($nodeVer) and npm (v$npmVer) detected." -ForegroundColor Green
} catch {
    Write-Host "[INFO] Node.js/npm not detected in PATH." -ForegroundColor Gray
}

if ($nodeAvailable) {
    if (-not (Test-Path "frontend\node_modules")) {
        Write-Host "[Setup] Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location "frontend"
        npm install
        Pop-Location
    }
    if (-not (Test-Path $distIndex)) {
        Write-Host "[Build] Compiling frontend application into frontend\dist..." -ForegroundColor Yellow
        Push-Location "frontend"
        npm run build
        Pop-Location
    }
}

if (-not (Test-Path $distIndex)) {
    Write-Host "[WARNING] frontend\dist\index.html not found. Install Node.js and run 'npm run build' in frontend/." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Production frontend distribution ready." -ForegroundColor Green
}

# 5. Set PYTHONPATH and launch FastAPI backend
$env:PYTHONPATH = $ProjectDir

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  CivicSentinel Online: http://localhost:8000/" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  * Complete Application:  http://localhost:8000/" -ForegroundColor Green
Write-Host "  * Dashboard Route:       http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host "  * Interactive Swagger:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  * ReDoc Technical Spec:  http://localhost:8000/redoc" -ForegroundColor Cyan
Write-Host "  * Health Diagnostics:    http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "  * Real-Time WebSocket:   ws://localhost:8000/ws" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to terminate, or run stop.bat in another terminal.`n" -ForegroundColor Gray

& $PythonExe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
