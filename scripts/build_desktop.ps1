# Build Windows desktop bundle using PyInstaller (one-folder)
# Produces dist/OllamaRAGDesktop/OllamaRAGDesktop.exe

$ErrorActionPreference = "Stop"

# Prefer venv Python
$venvPy = ".\\.venv\\Scripts\\python.exe"
if (Test-Path $venvPy) { $python = $venvPy } else { $python = "python" }

function Write-Info($msg) { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host $msg -ForegroundColor Red }

Write-Info "Ensuring PyInstaller is installed ..."
try {
  & $python -c "import PyInstaller" | Out-Null
} catch {
  & $python -m pip install pyinstaller
}

# Clean previous build
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist\\OllamaRAGDesktop") { Remove-Item -Recurse -Force "dist\\OllamaRAGDesktop" }
if (Test-Path "OllamaRAGDesktop.spec") { Remove-Item -Force "OllamaRAGDesktop.spec" }

Write-Info "Building Desktop bundle ..."
# Collect PyQt6 WebEngine resources and include web assets
# Hidden imports help ensure uvicorn & fastapi modules are packaged
& $python -m PyInstaller `
  --noconfirm `
  --name "OllamaRAGDesktop" `
  --add-data "web;web" `
  --collect-all "PyQt6" `
  --collect-all "PyQt6.QtWebEngineWidgets" `
  --hidden-import "uvicorn" `
  --hidden-import "fastapi" `
  desktop/main.py

Write-Info "Build completed. Run: .\\dist\\OllamaRAGDesktop\\OllamaRAGDesktop.exe"
Write-Warn "Note: The bundled app embeds the FastAPI server automatically when packaged. Ensure Ollama is running locally."
