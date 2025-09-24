# Format code (apply fixes)
$ErrorActionPreference = "Stop"

# Prefer .venv if present
$venvPy = ".\.venv\Scripts\python.exe"
$python = if (Test-Path $venvPy) { $venvPy } else { "python" }

Write-Host "Using Python: $python" -ForegroundColor Yellow

# isort before black for stable imports
& $python -m isort app scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python -m black app scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Optional: autofix simple issues via ruff
& $python -m ruff check --fix app scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
