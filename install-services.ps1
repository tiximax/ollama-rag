#!/usr/bin/env pwsh
# 🔧 Ollama RAG - Windows Service Installation Script
# Run this script as Administrator!

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor White
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "  3. Navigate to: cd C:\Users\pc\Downloads\ollama-rag" -ForegroundColor White
    Write-Host "  4. Run: .\install-services.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "🔧 Installing Windows Services" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = "C:\Users\pc\Downloads\ollama-rag"
$ErrorActionPreference = "Stop"

# ========================
# 1. Stop existing services if any
# ========================
Write-Host "[0/3] 🛑 Stopping existing services (if any)..." -ForegroundColor Yellow

$services = @("OllamaRAGBackend", "OllamaService")
foreach ($svc in $services) {
    try {
        $existing = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "  Stopping $svc..." -ForegroundColor Cyan
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
            & "$ProjectRoot\nssm.exe" remove $svc confirm
            Write-Host "  ✅ Removed existing $svc" -ForegroundColor Green
        }
    } catch {
        # Ignore errors
    }
}

Start-Sleep -Seconds 2
Write-Host ""

# ========================
# 2. Install Ollama Service 🦙
# ========================
Write-Host "[1/3] 🦙 Installing Ollama Service..." -ForegroundColor Yellow

# Find ollama.exe path
$ollamaPath = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollamaPath) {
    $ollamaPath = "ollama.exe"  # Try system PATH
}

Write-Host "  Ollama path: $ollamaPath" -ForegroundColor Cyan

& "$ProjectRoot\nssm.exe" install OllamaService $ollamaPath "serve"
& "$ProjectRoot\nssm.exe" set OllamaService DisplayName "Ollama LLM Service"
& "$ProjectRoot\nssm.exe" set OllamaService Description "Ollama local LLM inference server for RAG application"
& "$ProjectRoot\nssm.exe" set OllamaService Start SERVICE_AUTO_START
& "$ProjectRoot\nssm.exe" set OllamaService AppStdout "$ProjectRoot\logs\ollama.log"
& "$ProjectRoot\nssm.exe" set OllamaService AppStderr "$ProjectRoot\logs\ollama_error.log"
& "$ProjectRoot\nssm.exe" set OllamaService AppRotateFiles 1
& "$ProjectRoot\nssm.exe" set OllamaService AppRotateBytes 1048576  # 1MB

Write-Host "  ✅ Ollama Service installed!" -ForegroundColor Green
Write-Host ""

# ========================
# 3. Install Backend Service 🐍
# ========================
Write-Host "[2/3] 🐍 Installing Backend Service..." -ForegroundColor Yellow

# Find python.exe path
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    Write-Host "  ❌ Python not found in PATH!" -ForegroundColor Red
    exit 1
}

Write-Host "  Python path: $pythonPath" -ForegroundColor Cyan

$backendArgs = "-m uvicorn src.api.server:app --host 0.0.0.0 --port 8000"

& "$ProjectRoot\nssm.exe" install OllamaRAGBackend $pythonPath $backendArgs
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend DisplayName "Ollama RAG Backend API"
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend Description "FastAPI backend for Ollama RAG application"
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend Start SERVICE_AUTO_START
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend AppDirectory $ProjectRoot
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend AppStdout "$ProjectRoot\logs\backend.log"
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend AppStderr "$ProjectRoot\logs\backend_error.log"
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend AppRotateFiles 1
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend AppRotateBytes 1048576  # 1MB

Write-Host "  ✅ Backend Service installed!" -ForegroundColor Green
Write-Host ""

# ========================
# 4. Configure Dependencies & Auto-Restart
# ========================
Write-Host "[3/3] ⚙️  Configuring services..." -ForegroundColor Yellow

# Backend depends on Ollama
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend DependOnService OllamaService
Write-Host "  ✅ Backend depends on Ollama" -ForegroundColor Green

# Auto-restart on failure
& "$ProjectRoot\nssm.exe" set OllamaService AppExit Default Restart
& "$ProjectRoot\nssm.exe" set OllamaService AppRestartDelay 5000  # 5 seconds
Write-Host "  ✅ Ollama auto-restart enabled" -ForegroundColor Green

& "$ProjectRoot\nssm.exe" set OllamaRAGBackend AppExit Default Restart
& "$ProjectRoot\nssm.exe" set OllamaRAGBackend AppRestartDelay 5000  # 5 seconds
Write-Host "  ✅ Backend auto-restart enabled" -ForegroundColor Green

Write-Host ""

# ========================
# 5. Start Services
# ========================
Write-Host "🚀 Starting services..." -ForegroundColor Cyan

Start-Service OllamaService
Write-Host "  ✅ Ollama Service started!" -ForegroundColor Green

Start-Sleep -Seconds 3

Start-Service OllamaRAGBackend
Write-Host "  ✅ Backend Service started!" -ForegroundColor Green

Start-Sleep -Seconds 3

Write-Host ""

# ========================
# 6. Verify Services
# ========================
Write-Host "✅ Verifying services..." -ForegroundColor Cyan

$ollamaStatus = Get-Service OllamaService
$backendStatus = Get-Service OllamaRAGBackend

Write-Host ""
Write-Host "📊 Service Status:" -ForegroundColor Yellow
Write-Host "  🦙 Ollama:  $($ollamaStatus.Status) ($($ollamaStatus.StartType))" -ForegroundColor White
Write-Host "  🐍 Backend: $($backendStatus.Status) ($($backendStatus.StartType))" -ForegroundColor White
Write-Host ""

if ($ollamaStatus.Status -eq "Running" -and $backendStatus.Status -eq "Running") {
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "✅ ALL SERVICES INSTALLED & RUNNING!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 Success! Services will auto-start on Windows boot!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📡 Access Points:" -ForegroundColor Yellow
    Write-Host "  Local:  http://localhost:8000" -ForegroundColor White
    Write-Host "  Docs:   http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 Logs Location:" -ForegroundColor Yellow
    Write-Host "  Ollama:  $ProjectRoot\logs\ollama.log" -ForegroundColor White
    Write-Host "  Backend: $ProjectRoot\logs\backend.log" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Manage Services:" -ForegroundColor Yellow
    Write-Host "  Get-Service OllamaService, OllamaRAGBackend" -ForegroundColor White
    Write-Host "  Restart-Service OllamaService, OllamaRAGBackend" -ForegroundColor White
    Write-Host "  Stop-Service OllamaService, OllamaRAGBackend" -ForegroundColor White
    Write-Host ""
    Write-Host "🗑️  Uninstall Services:" -ForegroundColor Yellow
    Write-Host "  Run: .\uninstall-services.ps1 (as Admin)" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "⚠️  Warning: Some services may not be running" -ForegroundColor Yellow
    Write-Host "Check logs in: $ProjectRoot\logs\" -ForegroundColor Cyan
}
