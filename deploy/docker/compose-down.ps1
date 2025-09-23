param(
  [string]$ProjectRoot = "C:\\Users\\pc\\Downloads\\ollama-rag"
)

Write-Host "Docker compose down" -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
  docker compose -f .\deploy\docker\docker-compose.yml down
} finally {
  Pop-Location
}
