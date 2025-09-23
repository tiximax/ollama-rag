# Kéo models Ollama mặc định
# Yêu cầu: Ollama đã cài và đang chạy service

Write-Host "Pulling Ollama models..." -ForegroundColor Green

$models = @("llama3.1:8b", "nomic-embed-text")
foreach ($m in $models) {
  Write-Host "ollama pull $m" -ForegroundColor Yellow
  try {
    ollama pull $m
  } catch {
    Write-Host "Lỗi khi kéo model $m. Hãy đảm bảo Ollama đã được cài đặt và đang chạy." -ForegroundColor Red
  }
}
