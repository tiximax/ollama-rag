#!/usr/bin/env pwsh
# 🔧 Ollama RAG - Service Management Script
# Quick commands to manage Windows Services

param(
    [Parameter(Position=0)]
    [ValidateSet("status", "start", "stop", "restart", "logs", "health")]
    [string]$Action = "status"
)

$ProjectRoot = "C:\Users\pc\Downloads\ollama-rag"

function Show-Help {
    Write-Host "🔧 Ollama RAG - Service Management" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\manage-services.ps1 [action]" -ForegroundColor White
    Write-Host ""
    Write-Host "Actions:" -ForegroundColor Yellow
    Write-Host "  status   - Show service status (default)" -ForegroundColor White
    Write-Host "  start    - Start all services" -ForegroundColor White
    Write-Host "  stop     - Stop all services" -ForegroundColor White
    Write-Host "  restart  - Restart all services" -ForegroundColor White
    Write-Host "  logs     - Show recent logs" -ForegroundColor White
    Write-Host "  health   - Check API health" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\manage-services.ps1" -ForegroundColor White
    Write-Host "  .\manage-services.ps1 start" -ForegroundColor White
    Write-Host "  .\manage-services.ps1 logs" -ForegroundColor White
    Write-Host ""
}

function Show-Status {
    Write-Host "📊 Service Status" -ForegroundColor Cyan
    Write-Host ""

    $services = Get-Service -Name OllamaService, OllamaRAGBackend -ErrorAction SilentlyContinue

    if ($services) {
        $services | Format-Table @(
            @{Label="Service"; Expression={$_.Name}},
            @{Label="Status"; Expression={$_.Status}},
            @{Label="Start Type"; Expression={$_.StartType}},
            @{Label="Display Name"; Expression={$_.DisplayName}}
        ) -AutoSize

        # Check if both running
        $allRunning = ($services | Where-Object {$_.Status -ne "Running"}).Count -eq 0

        if ($allRunning) {
            Write-Host "✅ All services running!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Some services not running" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ No services found. Run install-services.ps1 first!" -ForegroundColor Red
    }

    Write-Host ""
}

function Start-AllServices {
    Write-Host "🚀 Starting services..." -ForegroundColor Cyan
    Write-Host ""

    try {
        Start-Service OllamaService -ErrorAction Stop
        Write-Host "  ✅ Ollama Service started" -ForegroundColor Green

        Start-Sleep -Seconds 2

        Start-Service OllamaRAGBackend -ErrorAction Stop
        Write-Host "  ✅ Backend Service started" -ForegroundColor Green

        Write-Host ""
        Show-Status
    } catch {
        Write-Host "  ❌ Error: $_" -ForegroundColor Red
    }
}

function Stop-AllServices {
    Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
    Write-Host ""

    try {
        Stop-Service OllamaRAGBackend -Force -ErrorAction Stop
        Write-Host "  ✅ Backend Service stopped" -ForegroundColor Green

        Stop-Service OllamaService -Force -ErrorAction Stop
        Write-Host "  ✅ Ollama Service stopped" -ForegroundColor Green

        Write-Host ""
        Show-Status
    } catch {
        Write-Host "  ❌ Error: $_" -ForegroundColor Red
    }
}

function Restart-AllServices {
    Write-Host "🔄 Restarting services..." -ForegroundColor Cyan
    Write-Host ""

    Stop-AllServices
    Start-Sleep -Seconds 2
    Start-AllServices
}

function Show-Logs {
    Write-Host "📝 Recent Logs" -ForegroundColor Cyan
    Write-Host ""

    $ollamaLog = "$ProjectRoot\logs\ollama.log"
    $backendLog = "$ProjectRoot\logs\backend.log"

    if (Test-Path $ollamaLog) {
        Write-Host "🦙 Ollama Log (last 10 lines):" -ForegroundColor Yellow
        Get-Content $ollamaLog -Tail 10
        Write-Host ""
    }

    if (Test-Path $backendLog) {
        Write-Host "🐍 Backend Log (last 10 lines):" -ForegroundColor Yellow
        Get-Content $backendLog -Tail 10
        Write-Host ""
    }

    if (-not (Test-Path $ollamaLog) -and -not (Test-Path $backendLog)) {
        Write-Host "ℹ️  No logs found yet" -ForegroundColor Gray
    }

    Write-Host "💡 To tail logs in real-time:" -ForegroundColor Cyan
    Write-Host "  Get-Content $backendLog -Tail 50 -Wait" -ForegroundColor White
    Write-Host ""
}

function Check-Health {
    Write-Host "🏥 Health Check" -ForegroundColor Cyan
    Write-Host ""

    # Check Ollama
    try {
        Write-Host "  Checking Ollama..." -ForegroundColor Yellow
        $ollama = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
        Write-Host "  ✅ Ollama: OK (Models: $($ollama.models.Count))" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ Ollama: Not responding" -ForegroundColor Red
    }

    # Check Backend
    try {
        Write-Host "  Checking Backend..." -ForegroundColor Yellow
        $backend = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
        Write-Host "  ✅ Backend: $($backend.status) (DB: $($backend.db))" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ Backend: Not responding" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "📡 Access Points:" -ForegroundColor Cyan
    Write-Host "  Local:  http://localhost:8000" -ForegroundColor White
    Write-Host "  Docs:   http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host ""
}

# Main logic
switch ($Action) {
    "status" { Show-Status }
    "start" { Start-AllServices }
    "stop" { Stop-AllServices }
    "restart" { Restart-AllServices }
    "logs" { Show-Logs }
    "health" { Check-Health }
    default { Show-Help }
}
