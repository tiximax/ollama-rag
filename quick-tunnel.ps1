# Quick Cloudflare Tunnel - Get Live URL Instantly
# Usage: .\quick-tunnel.ps1

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Cloudflare Quick Tunnel" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Starting tunnel to http://localhost:8000..." -ForegroundColor Yellow
Write-Host "Please wait for URL...`n" -ForegroundColor Gray

# Run cloudflared and capture output
cloudflared tunnel --url http://localhost:8000
