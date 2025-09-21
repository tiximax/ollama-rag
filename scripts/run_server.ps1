# Chạy server FastAPI (PowerShell)
$env:PYTHONPATH = "."

$venvPython = Join-Path -Path ".\.venv\Scripts" -ChildPath "python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
Write-Host "Using Python: $python" -ForegroundColor Yellow
Write-Host "Starting FastAPI on http://127.0.0.1:8000" -ForegroundColor Green
$reload = $env:UVICORN_RELOAD
if ($reload -and ($reload -eq '1' -or $reload -eq 'true')) {
  & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} else {
  & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
