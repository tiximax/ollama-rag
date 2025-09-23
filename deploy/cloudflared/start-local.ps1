# Khởi chạy cloudflared native trên Windows bằng Tunnel ID
param(
  [string]$TunnelId,
  [string]$ConfigPath = "$env:USERPROFILE\.cloudflared\config.yml"
)

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
  Write-Host "cloudflared chưa được cài. Cài bằng: winget install Cloudflare.cloudflared" -ForegroundColor Yellow
  exit 1
}

if (-not $TunnelId) {
  Write-Host "Thiếu -TunnelId. Dùng: .\start-local.ps1 -TunnelId <TUNNEL_ID>" -ForegroundColor Red
  exit 1
}

Write-Host "Sử dụng config: $ConfigPath" -ForegroundColor Gray
cloudflared tunnel --config $ConfigPath run $TunnelId