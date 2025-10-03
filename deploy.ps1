# 🚀 Ollama RAG - Quick Deploy Script
# Usage: .\deploy.ps1

Write-Host "Ollama RAG - Production Deployment" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Step 1: Check Python
Write-Host "[Step 1] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python not found! Install Python 3.9+" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python installed: $pythonVersion`n" -ForegroundColor Green

# Step 2: Check Ollama
Write-Host "[Step 2] Checking Ollama..." -ForegroundColor Yellow
$ollamaCheck = ollama list 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Ollama not found! Install from: https://ollama.ai" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Ollama installed`n" -ForegroundColor Green

# Step 3: Check Models
Write-Host "[Step 3] Checking Ollama models..." -ForegroundColor Yellow
$models = ollama list | Select-String -Pattern "llama3.2:3b|nomic-embed-text"
if (-not $models) {
    Write-Host "[WARN] Required models not found! Pulling..." -ForegroundColor Yellow
    ollama pull llama3.2:3b
    ollama pull nomic-embed-text
}
Write-Host "[OK] Models ready`n" -ForegroundColor Green

# Step 4: Create Virtual Environment (if needed)
Write-Host "[Step 4] Setting up Python environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}
Write-Host "[OK] Virtual environment ready`n" -ForegroundColor Green

# Step 5: Activate venv & Install Dependencies
Write-Host "[Step 5] Installing dependencies..." -ForegroundColor Yellow
Write-Host "Activating virtual environment..." -ForegroundColor Gray

# Activate venv and install packages
& "venv\Scripts\Activate.ps1"
pip install --upgrade pip -q
pip install -r requirements.txt -q

Write-Host "[OK] Dependencies installed`n" -ForegroundColor Green

# Step 6: Copy Production Config
Write-Host "[Step 6] Setting up production config..." -ForegroundColor Yellow
if (Test-Path ".env.production") {
    Copy-Item .env.production .env -Force
    Write-Host "[OK] Production config loaded`n" -ForegroundColor Green
} else {
    Write-Host "[WARN] .env.production not found, using .env.example" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item .env.example .env -Force
    }
}

# Step 7: Create data directory
Write-Host "[Step 7] Setting up data directories..." -ForegroundColor Yellow
New-Item -Path "data/kb" -ItemType Directory -Force | Out-Null
Write-Host "[OK] Data directories ready`n" -ForegroundColor Green

# Step 8: Start Application
Write-Host "[Step 8] Starting application..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ready to launch!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Local URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

# Run with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
