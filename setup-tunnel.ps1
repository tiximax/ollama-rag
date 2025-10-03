# Cloudflare Tunnel Setup Script
# Interactive setup for exposing Ollama RAG to the internet

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cloudflare Tunnel Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if cloudflared is installed
Write-Host "[Step 1] Checking cloudflared installation..." -ForegroundColor Yellow
try {
    $version = cloudflared --version 2>&1
    Write-Host "[OK] cloudflared installed: $version`n" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] cloudflared not found! Please install first:" -ForegroundColor Red
    Write-Host "  winget install --id Cloudflare.cloudflared`n" -ForegroundColor Yellow
    exit 1
}

# Check if server is running
Write-Host "[Step 2] Checking if FastAPI server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Server is running on http://localhost:8000`n" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Server not responding. Make sure to run .\start.ps1 first!" -ForegroundColor Yellow
    Write-Host "Do you want to continue anyway? (y/n): " -NoNewline -ForegroundColor Yellow
    $continue = Read-Host
    if ($continue -ne "y") {
        Write-Host "Exiting. Please start the server first with: .\start.ps1`n" -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

# Login to Cloudflare
Write-Host "[Step 3] Login to Cloudflare..." -ForegroundColor Yellow
Write-Host "This will open your browser to authenticate." -ForegroundColor Gray
Write-Host "Make sure you have a Cloudflare account with a domain added!" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Enter to continue..." -ForegroundColor Yellow
Read-Host

Write-Host "Opening browser for authentication..." -ForegroundColor Gray
cloudflared tunnel login

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Login failed! Please try again.`n" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Successfully logged in to Cloudflare!`n" -ForegroundColor Green

# Create tunnel
Write-Host "[Step 4] Creating Cloudflare Tunnel..." -ForegroundColor Yellow
Write-Host "Enter a name for your tunnel (e.g., 'ollama-rag'): " -NoNewline -ForegroundColor Yellow
$tunnelName = Read-Host

if ([string]::IsNullOrWhiteSpace($tunnelName)) {
    $tunnelName = "ollama-rag"
    Write-Host "Using default name: $tunnelName" -ForegroundColor Gray
}

Write-Host "Creating tunnel '$tunnelName'..." -ForegroundColor Gray
$tunnelOutput = cloudflared tunnel create $tunnelName 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to create tunnel!" -ForegroundColor Red
    Write-Host $tunnelOutput -ForegroundColor Red
    exit 1
}

# Extract tunnel ID
$tunnelId = ($tunnelOutput | Select-String -Pattern "tunnel\s+\w+\s+with\s+id\s+([a-f0-9\-]+)" | ForEach-Object { $_.Matches.Groups[1].Value })

if ([string]::IsNullOrWhiteSpace($tunnelId)) {
    Write-Host "[ERROR] Could not extract tunnel ID from output!" -ForegroundColor Red
    Write-Host "Output was: $tunnelOutput" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Tunnel created successfully!" -ForegroundColor Green
Write-Host "Tunnel ID: $tunnelId`n" -ForegroundColor Cyan

# Setup DNS
Write-Host "[Step 5] Setting up DNS..." -ForegroundColor Yellow
Write-Host "Enter your domain (e.g., 'example.com'): " -NoNewline -ForegroundColor Yellow
$domain = Read-Host

if ([string]::IsNullOrWhiteSpace($domain)) {
    Write-Host "[ERROR] Domain is required!" -ForegroundColor Red
    exit 1
}

Write-Host "Enter subdomain (e.g., 'ollama-rag' for ollama-rag.$domain): " -NoNewline -ForegroundColor Yellow
$subdomain = Read-Host

if ([string]::IsNullOrWhiteSpace($subdomain)) {
    $subdomain = "ollama-rag"
    Write-Host "Using default subdomain: $subdomain" -ForegroundColor Gray
}

$fullDomain = "$subdomain.$domain"

Write-Host "Creating DNS record for $fullDomain..." -ForegroundColor Gray
cloudflared tunnel route dns $tunnelId $fullDomain

if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Failed to create DNS record automatically." -ForegroundColor Yellow
    Write-Host "You can create it manually in Cloudflare Dashboard:" -ForegroundColor Yellow
    Write-Host "  Type: CNAME" -ForegroundColor Gray
    Write-Host "  Name: $subdomain" -ForegroundColor Gray
    Write-Host "  Target: $tunnelId.cfargotunnel.com" -ForegroundColor Gray
    Write-Host "  Proxy: Enabled (orange cloud)`n" -ForegroundColor Gray
} else {
    Write-Host "[OK] DNS record created successfully!`n" -ForegroundColor Green
}

# Create config file
Write-Host "[Step 6] Creating configuration file..." -ForegroundColor Yellow

$configDir = "$env:USERPROFILE\.cloudflared"
$configPath = "$configDir\config.yml"
$credentialsPath = "$configDir\$tunnelId.json"

# Ensure directory exists
New-Item -Path $configDir -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null

# Create config content
$configContent = @"
tunnel: $tunnelId
credentials-file: $credentialsPath

ingress:
  - hostname: $fullDomain
    service: http://localhost:8000
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false
  - service: http_status:404

# Optional: Enable logging
# logfile: $configDir\tunnel.log
# loglevel: info
"@

# Write config file
$configContent | Out-File -FilePath $configPath -Encoding UTF8 -Force

Write-Host "[OK] Configuration file created at: $configPath`n" -ForegroundColor Green

# Update .env CORS
Write-Host "[Step 7] Updating CORS configuration..." -ForegroundColor Yellow

$envPath = ".env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    $newCorsOrigins = "CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,https://$fullDomain"
    
    if ($envContent -match "CORS_ORIGINS=.*") {
        $envContent = $envContent -replace "CORS_ORIGINS=.*", $newCorsOrigins
    } else {
        $envContent += "`n$newCorsOrigins`n"
    }
    
    $envContent | Out-File -FilePath $envPath -Encoding UTF8 -Force
    Write-Host "[OK] CORS updated to include: https://$fullDomain`n" -ForegroundColor Green
} else {
    Write-Host "[WARN] .env file not found, skipping CORS update`n" -ForegroundColor Yellow
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Tunnel Information:" -ForegroundColor Cyan
Write-Host "  Name: $tunnelName" -ForegroundColor White
Write-Host "  ID: $tunnelId" -ForegroundColor White
Write-Host "  Public URL: https://$fullDomain" -ForegroundColor White
Write-Host "  Local URL: http://localhost:8000`n" -ForegroundColor White

Write-Host "Configuration File:" -ForegroundColor Cyan
Write-Host "  $configPath`n" -ForegroundColor White

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Start your server (if not already running):" -ForegroundColor White
Write-Host "     .\start.ps1`n" -ForegroundColor Gray

Write-Host "  2. Start the tunnel (choose one):" -ForegroundColor White
Write-Host "     a) Foreground (for testing):" -ForegroundColor White
Write-Host "        cloudflared tunnel run $tunnelName" -ForegroundColor Gray
Write-Host "     b) As Windows Service (for production):" -ForegroundColor White
Write-Host "        cloudflared service install" -ForegroundColor Gray
Write-Host "        Start-Service cloudflared`n" -ForegroundColor Gray

Write-Host "  3. Test your deployment:" -ForegroundColor White
Write-Host "     https://$fullDomain/docs" -ForegroundColor Gray
Write-Host "     https://$fullDomain/health`n" -ForegroundColor Gray

Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  List tunnels:  cloudflared tunnel list" -ForegroundColor White
Write-Host "  Stop tunnel:   Stop-Service cloudflared" -ForegroundColor White
Write-Host "  Delete tunnel: cloudflared tunnel delete $tunnelName`n" -ForegroundColor White

Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Do you want to start the tunnel now? (y/n): " -NoNewline -ForegroundColor Yellow
$startNow = Read-Host

if ($startNow -eq "y") {
    Write-Host "`nStarting tunnel in foreground mode..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop the tunnel`n" -ForegroundColor Yellow
    cloudflared tunnel run $tunnelName
} else {
    Write-Host "`nSetup complete! Run the tunnel manually when ready.`n" -ForegroundColor Green
}
