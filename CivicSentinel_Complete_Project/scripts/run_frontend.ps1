$ErrorActionPreference='Stop';$Root=Split-Path -Parent $PSScriptRoot;Set-Location "$Root\frontend"
if(-not(Test-Path 'node_modules')){npm install}
$env:VITE_API_BASE_URL='http://127.0.0.1:8000';npm run dev -- --host 127.0.0.1
