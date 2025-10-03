#!/usr/bin/env pwsh
# 🗑️ Ollama RAG - Windows Service Uninstallation Script
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
    Write-Host "  4. Run: .\uninstall-services.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "=====================================" -ForegroundColor Red
Write-Host "🗑️  Uninstalling Windows Services" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Red
Write-Host ""

$ProjectRoot = "C:\Users\pc\Downloads\ollama-rag"
$ErrorActionPreference = "Continue"

# ========================
# 1. Stop Services
# ========================
Write-Host "[1/2] 🛑 Stopping services..." -ForegroundColor Yellow

$services = @("OllamaRAGBackend", "OllamaService")
foreach ($svc in $services) {
    try {
        $existing = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "  Stopping $svc..." -ForegroundColor Cyan
            Stop-Service -Name $svc -Force
            Write-Host "  ✅ $svc stopped" -ForegroundColor Green
        } else {
            Write-Host "  ℹ️  $svc not found" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠️  Error stopping $svc : $_" -ForegroundColor Yellow
    }
}

Write-Host ""

# ========================
# 2. Remove Services
# ========================
Write-Host "[2/2] 🗑️  Removing services..." -ForegroundColor Yellow

foreach ($svc in $services) {
    try {
        $existing = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "  Removing $svc..." -ForegroundColor Cyan
            & "$ProjectRoot\nssm.exe" remove $svc confirm
            Write-Host "  ✅ $svc removed" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ⚠️  Error removing $svc : $_" -ForegroundColor Yellow
    }
}

Write-Host ""

# ========================
# 3. Verify Removal
# ========================
Write-Host "✅ Verifying removal..." -ForegroundColor Cyan

$remaining = Get-Service -Name OllamaService, OllamaRAGBackend -ErrorAction SilentlyContinue

if ($remaining) {
    Write-Host "⚠️  Warning: Some services still exist" -ForegroundColor Yellow
    $remaining | ForEach-Object {
        Write-Host "  - $($_.Name): $($_.Status)" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "✅ ALL SERVICES UNINSTALLED!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 To reinstall services, run: .\install-services.ps1" -ForegroundColor Cyan
}

Write-Host ""
