param(
  [string]$ConfigPath = "$env:USERPROFILE\.cloudflared\config.yml"
)

Write-Host "--- Cloudflared (native) smoke test ---" -ForegroundColor Cyan

# 1) cloudflared binary
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
  Write-Host "cloudflared chưa được cài. Cài với: winget install Cloudflare.cloudflared" -ForegroundColor Yellow
  exit 1
}

$version = (cloudflared --version) 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Không chạy được 'cloudflared --version'" -ForegroundColor Red
  exit 1
}
Write-Host "cloudflared OK: $version" -ForegroundColor Green

# 2) config.yml
if (Test-Path $ConfigPath) {
  Write-Host "Tìm thấy config: $ConfigPath" -ForegroundColor Green
} else {
  Write-Host "Không thấy config tại: $ConfigPath" -ForegroundColor Yellow
  Write-Host "Tham khảo deploy/cloudflared/config.yml.example" -ForegroundColor Yellow
}

# 3) Gợi ý chạy thử (không tự động run):
Write-Host "Gợi ý: cloudflared tunnel run <TUNNEL_ID>" -ForegroundColor Gray
Write-Host "Hoặc: .\\deploy\\cloudflared\\start-local.ps1 -TunnelId <TUNNEL_ID>" -ForegroundColor Gray

exit 0
