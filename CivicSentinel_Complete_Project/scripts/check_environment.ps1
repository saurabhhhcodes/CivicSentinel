$Root=Split-Path -Parent $PSScriptRoot;Set-Location $Root
python --version;node --version;npm --version
if(Test-Path '.venv\Scripts\python.exe'){$env:PYTHONPATH=$Root;& .\.venv\Scripts\python.exe -c "import cv2,fastapi;print('OpenCV',cv2.__version__,'FastAPI',fastapi.__version__)"}else{Write-Warning 'Virtual environment not found.'}
try{Invoke-RestMethod http://127.0.0.1:8000/health|Format-List}catch{Write-Warning 'Backend is not running.'}
