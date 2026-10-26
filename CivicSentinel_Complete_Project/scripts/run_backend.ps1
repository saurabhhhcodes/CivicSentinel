$ErrorActionPreference='Stop';$Root=Split-Path -Parent $PSScriptRoot;Set-Location $Root;$env:PYTHONPATH=$Root
if(-not(Test-Path '.venv\Scripts\python.exe')){throw 'Run scripts\setup_windows.ps1 first.'}
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
