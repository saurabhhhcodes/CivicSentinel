$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $PSScriptRoot; Set-Location $Root
if(-not(Get-Command python -ErrorAction SilentlyContinue)){throw 'Install Python 3.11/3.12 and reopen PowerShell.'}
if(-not(Get-Command node -ErrorAction SilentlyContinue)){throw 'Install Node.js 20+ and reopen PowerShell.'}
python --version; node --version; npm --version
if(-not(Test-Path '.venv')){python -m venv .venv}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if(-not(Test-Path '.env')){Copy-Item '.env.example' '.env'}
Push-Location frontend; npm install; Pop-Location
$env:PYTHONPATH=$Root
& .\.venv\Scripts\python.exe -c "import cv2,fastapi,sqlalchemy;print('OpenCV',cv2.__version__,'FastAPI',fastapi.__version__)"
& .\.venv\Scripts\python.exe -c "from backend.app.main import app;print('API import OK')"
Write-Host 'Setup complete. Run .\scripts\run_all.ps1' -ForegroundColor Green
