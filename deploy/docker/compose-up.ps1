param(
  [string]$ProjectRoot = "C:\\Users\\pc\\Downloads\\ollama-rag",
  [switch]$Build
)

Write-Host "Docker compose up (with Cloudflare Tunnel)" -ForegroundColor Green

Push-Location $ProjectRoot
try {
  if ($Build) {
    docker compose -f .\deploy\docker\docker-compose.yml build
  }
  if (-not $env:CF_TUNNEL_TOKEN) {
    Write-Host "CF_TUNNEL_TOKEN chưa được set. Hãy set biến môi trường này trước khi up." -ForegroundColor Yellow
    Write-Host "Ví dụ: $env:CF_TUNNEL_TOKEN={{CF_TUNNEL_TOKEN}}" -ForegroundColor Gray
  }
  docker compose -f .\deploy\docker\docker-compose.yml up -d
} finally {
  Pop-Location
}
