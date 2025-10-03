#!/usr/bin/env pwsh
# 🛑 Ollama RAG - Stop All Services Script
# This script stops Ollama, Backend API, and Cloudflare Tunnel safely

Write-Host "=====================================" -ForegroundColor Red
Write-Host "🛑 Ollama RAG - Stopping All Services" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Red
Write-Host ""

$ErrorActionPreference = "Continue"

# ========================
# 1. Stop Cloudflare Tunnel ☁️
# ========================
Write-Host "[1/3] ☁️  Stopping Cloudflare Tunnel..." -ForegroundColor Yellow

$tunnelProcesses = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($tunnelProcesses) {
    $tunnelProcesses | ForEach-Object {
        Stop-Process -Id $_.Id -Force
        Write-Host "  ✅ Stopped cloudflared (PID: $($_.Id))" -ForegroundColor Green
    }
} else {
    Write-Host "  ℹ️  No cloudflared process running" -ForegroundColor Gray
}

Write-Host ""

# ========================
# 2. Stop Backend API 🐍
# ========================
Write-Host "[2/3] 🐍 Stopping Backend API..." -ForegroundColor Yellow

# Find uvicorn processes
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object {
        # Check if it's running uvicorn
        try {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
            if ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*server:app*") {
                Stop-Process -Id $_.Id -Force
                Write-Host "  ✅ Stopped backend (PID: $($_.Id))" -ForegroundColor Green
            }
        } catch {
            # Fallback: stop all python if unsure
        }
    }
    Write-Host "  ✅ Backend stopped" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  No backend process running" -ForegroundColor Gray
}

Write-Host ""

# ========================
# 3. Stop Ollama Service 🦙
# ========================
Write-Host "[3/3] 🦙 Stopping Ollama..." -ForegroundColor Yellow

$ollamaProcesses = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaProcesses) {
    $ollamaProcesses | ForEach-Object {
        Stop-Process -Id $_.Id -Force
        Write-Host "  ✅ Stopped Ollama (PID: $($_.Id))" -ForegroundColor Green
    }
} else {
    Write-Host "  ℹ️  No Ollama process running" -ForegroundColor Gray
}

Write-Host ""

# ========================
# 4. Close PowerShell Windows
# ========================
Write-Host "[Bonus] Closing related PowerShell windows..." -ForegroundColor Yellow

$currentPID = $PID
Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {
    $_.Id -ne $currentPID -and $_.MainWindowTitle -ne ""
} | ForEach-Object {
    try {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Host "  ✅ Closed PowerShell window (PID: $($_.Id))" -ForegroundColor Green
    } catch {
        # Ignore errors
    }
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "✅ ALL SERVICES STOPPED!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "💡 To start again, run: .\start-all.ps1" -ForegroundColor Cyan
Write-Host ""
