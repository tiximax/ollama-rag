# Chạy server FastAPI (PowerShell)
$env:PYTHONPATH = "."

$venvPython = Join-Path -Path ".\.venv\Scripts" -ChildPath "python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
Write-Host "Using Python: $python" -ForegroundColor Yellow
Write-Host "Starting FastAPI on http://127.0.0.1:8000" -ForegroundColor Green
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
