# Lint check
$ErrorActionPreference = "Stop"

# Prefer .venv if present
$venvPy = ".\.venv\Scripts\python.exe"
$python = if (Test-Path $venvPy) { $venvPy } else { "python" }

Write-Host "Using Python: $python" -ForegroundColor Yellow

# Run linters
& $python -m ruff check app scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python -m black --check app scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python -m isort --check-only app scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
