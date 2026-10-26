# CivicSentinel - Shutdown Script for Windows PowerShell
Write-Host "Stopping CivicSentinel processes..." -ForegroundColor Yellow

$procs = Get-Process python, node -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "civicsentinel" -or $_.CommandLine -match "uvicorn" -or $_.CommandLine -match "vite"
}

if ($procs) {
    $procs | ForEach-Object {
        Write-Host "Terminating PID $($_.Id) ($($_.ProcessName))..." -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "CivicSentinel processes stopped." -ForegroundColor Green
} else {
    Write-Host "No active CivicSentinel processes found." -ForegroundColor Gray
}
