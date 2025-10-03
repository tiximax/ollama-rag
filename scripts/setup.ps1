# Bootstrap local environment for Ollama RAG App (Windows PowerShell)
# - Creates .venv if missing
# - Installs Python requirements
# - Optionally installs Playwright deps & browsers for e2e
# - Optionally pulls default Ollama models

param(
  [switch]$WithE2E = $false,
  [switch]$SkipModels = $false
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host $msg -ForegroundColor Red }

# Ensure we're in repo root (contains requirements.txt)
if (-not (Test-Path -LiteralPath "requirements.txt")) {
  Write-Err "Run this script from the repository root (requirements.txt not found)."
  exit 1
}

# Resolve Python
$venvDir = ".\.venv"
$venvPython = Join-Path $venvDir "Scripts\\python.exe"
$python = $null

if (Test-Path $venvPython) {
  $python = $venvPython
  Write-Info "Using existing venv: $venvPython"
} else {
  Write-Info "Creating virtual environment at $venvDir ..."
  try {
    python -m venv $venvDir
  } catch {
    Write-Err "Failed to create virtual environment. Ensure Python 3.10+ is installed and available in PATH."
    exit 1
  }
  if (-not (Test-Path $venvPython)) {
    Write-Err "Virtual environment python not found at $venvPython"
    exit 1
  }
  $python = $venvPython
}

Write-Info "Upgrading pip ..."
& $python -m pip install --upgrade pip

Write-Info "Installing Python requirements ..."
& $python -m pip install -r requirements.txt

if ($WithE2E) {
  Write-Info "Installing Node Playwright deps (optional) ..."
  if (-not (Test-Path -LiteralPath "package.json")) {
    Write-Warn "package.json not found; skipping e2e setup."
  } else {
    try {
      npm install
      npm run playwright:install
    } catch {
      Write-Warn "Failed to install Playwright deps. You can retry later with: npm install && npm run playwright:install"
    }
  }
}

if (-not $SkipModels) {
  Write-Info "Pulling default Ollama models (llama3.1:8b, nomic-embed-text) ..."
  try {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\pull_models.ps1
  } catch {
    Write-Warn "Could not pull models. Ensure Ollama is installed and running (http://localhost:11434)."
  }
} else {
  Write-Warn "SkipModels=true → Skipping Ollama model pulls."
}

Write-Info "Setup completed successfully. Next steps:"
Write-Host "  1) Copy .env.example to .env and adjust if needed" -ForegroundColor Cyan
Write-Host "  2) Start server:  PowerShell -ExecutionPolicy Bypass -File .\\scripts\\run_server.ps1" -ForegroundColor Cyan
Write-Host "  3) Or Desktop shell: PowerShell -ExecutionPolicy Bypass -File .\\scripts\\run_desktop.ps1" -ForegroundColor Cyan
