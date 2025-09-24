# Build Desktop binary (PyQt6)
$ErrorActionPreference = "Stop"

$venv = ".\.venv\Scripts\python.exe"
$py = if (Test-Path $venv) { $venv } else { "python" }

# Ensure deps
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
& $py -m pip install -r requirements-dev.txt

# Build onefile
& $py -m PyInstaller --noconfirm --clean --name "OllamaRAG-Desktop" --onefile --windowed desktop/main.py

Write-Host "Built binary in dist/" -ForegroundColor Green