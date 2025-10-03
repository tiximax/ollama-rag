#!/usr/bin/env pwsh
# 🚀 Ollama RAG - Auto Start All Services Script
# This script starts Ollama, Backend API, and Cloudflare Tunnel in one command!

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "🚀 Ollama RAG - Starting All Services" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# ========================
# 1. Start Ollama Service 🦙
# ========================
Write-Host "[1/3] 🦙 Starting Ollama..." -ForegroundColor Yellow

$ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaProcess) {
    Write-Host "  ✅ Ollama already running (PID: $($ollamaProcess.Id))" -ForegroundColor Green
} else {
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "  ✅ Ollama started!" -ForegroundColor Green
}

# Verify Ollama is responding
try {
    $ollamaHealth = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✅ Ollama is healthy (Models: $($ollamaHealth.models.Count))" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Warning: Ollama may not be ready yet" -ForegroundColor Yellow
}

Write-Host ""

# ========================
# 2. Start Backend API 🐍
# ========================
Write-Host "[2/3] 🐍 Starting Backend API..." -ForegroundColor Yellow

# Check if backend already running
try {
    $backendHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host "  ✅ Backend already running (Status: $($backendHealth.status))" -ForegroundColor Green
} catch {
    Write-Host "  Starting new backend instance..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$ProjectRoot'; Write-Host '🐍 Backend API Server' -ForegroundColor Green; uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload"
    ) -WindowStyle Normal

    Start-Sleep -Seconds 8

    # Verify backend started
    try {
        $backendHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
        Write-Host "  ✅ Backend started successfully! (Status: $($backendHealth.status))" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  Backend starting... (may take a few more seconds)" -ForegroundColor Yellow
    }
}

Write-Host ""

# ========================
# 3. Start Cloudflare Tunnel ☁️
# ========================
Write-Host "[3/3] ☁️  Starting Cloudflare Tunnel..." -ForegroundColor Yellow

# Check if tunnel already running
$tunnelProcess = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($tunnelProcess) {
    Write-Host "  ✅ Cloudflare Tunnel already running (PID: $($tunnelProcess.Id))" -ForegroundColor Green
}
} else {
    Write-Host "  Starting Quick Tunnel (no domain needed)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$ProjectRoot'; Write-Host '☁️  Cloudflare Tunnel' -ForegroundColor Cyan; Write-Host 'Connecting...' -ForegroundColor Yellow; .\cloudflared.exe tunnel --url http://localhost:8000"
    ) -WindowStyle Normal

    Start-Sleep -Seconds 5
    Write-Host "  ✅ Tunnel started! Check the PowerShell window for public URL!" -ForegroundColor Green
    Write-Host "  📡 Your public URL will look like: https://xxxxx-xxxx.trycloudflare.com" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "✅ ALL SERVICES STARTED!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Service Status:" -ForegroundColor Yellow
Write-Host "  🦙 Ollama:    http://localhost:11434" -ForegroundColor White
Write-Host "  🐍 Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  ☁️  Tunnel:    Check PowerShell window for public URL" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Access Points:" -ForegroundColor Yellow
Write-Host "  Local:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Public:  https://your-tunnel-url/docs" -ForegroundColor White
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Yellow
Write-Host "  - Local API:   curl http://localhost:8000/health" -ForegroundColor White
Write-Host "  - Public API:  curl https://your-tunnel-url/health" -ForegroundColor White
Write-Host "  - Stop All:    Close all PowerShell windows or Ctrl+C" -ForegroundColor White
Write-Host ""
Write-Host "🎉 Ready to serve requests! Happy coding! 🚀" -ForegroundColor Green
Write-Host ""
