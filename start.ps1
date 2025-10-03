# Quick Start Script - Ollama RAG
# Usage: .\start.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ollama RAG - Quick Start" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "[Setup] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "[OK] Virtual environment created`n" -ForegroundColor Green
}

# Check if dependencies installed
$pipList = & venv\Scripts\python.exe -m pip list
if (-not ($pipList -match "fastapi")) {
    Write-Host "[Setup] Installing dependencies (one-time)..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes...`n" -ForegroundColor Gray
    & venv\Scripts\python.exe -m pip install --upgrade pip -q
    & venv\Scripts\python.exe -m pip install -r requirements.txt -q
    Write-Host "[OK] Dependencies installed`n" -ForegroundColor Green
}

# Ensure .env exists
if (-not (Test-Path ".env")) {
    Write-Host "[Setup] Creating .env config..." -ForegroundColor Yellow
    if (Test-Path ".env.production") {
        Copy-Item .env.production .env -Force
        Write-Host "[OK] Using production config`n" -ForegroundColor Green
    } elseif (Test-Path ".env.example") {
        Copy-Item .env.example .env -Force
        Write-Host "[OK] Using example config`n" -ForegroundColor Green
    }
}

# Create data directory
New-Item -Path "data/kb" -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Ollama RAG Server..." -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Local URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health: http://localhost:8000/health`n" -ForegroundColor Cyan

Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

# Start server
& venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
