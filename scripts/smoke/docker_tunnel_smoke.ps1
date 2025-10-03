Write-Host "--- Cloudflare Tunnel (Docker Compose) smoke test ---" -ForegroundColor Cyan

# 1) Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker chưa được cài. Cài Docker Desktop và bật 'Docker Compose'." -ForegroundColor Yellow
  exit 1
}

# 2) docker compose version
$dcv = (docker compose version) 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Không chạy được 'docker compose version'" -ForegroundColor Red
  exit 1
}
Write-Host "docker compose OK: $dcv" -ForegroundColor Green

# 3) Kiểm tra biến môi trường CF_TUNNEL_TOKEN (chỉ kiểm tra tồn tại, KHÔNG in giá trị)
if (-not $env:CF_TUNNEL_TOKEN) {
  Write-Host "Thiếu biến môi trường CF_TUNNEL_TOKEN (không in giá trị)." -ForegroundColor Yellow
  Write-Host "Thiết lập trước khi up: $env:CF_TUNNEL_TOKEN=\"{{CF_TUNNEL_TOKEN}}\"" -ForegroundColor Gray
} else {
  Write-Host "CF_TUNNEL_TOKEN đã được thiết lập (ẩn)." -ForegroundColor Green
}

# 4) Validate docker-compose.yml
$composePath = "deploy/docker/docker-compose.yml"
if (-not (Test-Path $composePath)) {
  Write-Host "Không tìm thấy $composePath" -ForegroundColor Red
  exit 1
}
$cfg = (docker compose -f $composePath config) 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "docker compose config lỗi" -ForegroundColor Red
  exit 1
}
Write-Host "docker compose file hợp lệ." -ForegroundColor Green

# Không tự chạy up -d để tránh side effects
Write-Host "Gợi ý chạy: docker compose -f $composePath up -d" -ForegroundColor Gray

exit 0
