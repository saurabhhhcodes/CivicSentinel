$ErrorActionPreference='Stop';$Root=Split-Path -Parent $PSScriptRoot;Set-Location $Root
if(-not(Test-Path '.venv\Scripts\python.exe')){throw 'Run scripts\setup_windows.ps1 first.'}
if(-not(Test-Path 'frontend\node_modules')){Push-Location frontend;npm install;Pop-Location}
$env:PYTHONPATH=$Root
Start-Process -FilePath "$Root\.venv\Scripts\python.exe" -ArgumentList @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $Root
Start-Sleep -Seconds 2
Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--host','127.0.0.1') -WorkingDirectory "$Root\frontend"
Write-Host 'Dashboard: http://localhost:5173';Write-Host 'API docs: http://127.0.0.1:8000/docs';Write-Host 'Health: http://127.0.0.1:8000/health'
