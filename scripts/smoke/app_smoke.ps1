# Smoke test for rag2app Docker image (local, without cloudflared)
$ErrorActionPreference = "Stop"

# Build image
Write-Host "Building rag2app:local..." -ForegroundColor Yellow
docker build -f deploy/docker/Dockerfile -t rag2app:local .

# Run container
Write-Host "Starting container..." -ForegroundColor Yellow
$cid = docker run -d -p 8000:8000 --name rag2app_smoke rag2app:local

try {
  # Wait for health
  $ok = $false
  for ($i=0; $i -lt 30; $i++) {
    try {
      $res = Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000 -TimeoutSec 2
      if ($res.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  if (-not $ok) { throw "App did not become healthy in time" }

  Write-Host "Smoke OK: GET / returned 200" -ForegroundColor Green
}
finally {
  Write-Host "Cleaning up container..." -ForegroundColor Yellow
  docker rm -f $cid | Out-Null
}
