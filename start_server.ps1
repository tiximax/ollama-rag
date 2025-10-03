# Start Ollama RAG Server
Write-Host "🚀 Starting Ollama RAG Server..." -ForegroundColor Cyan

# Check if Ollama is running
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Write-Host "⚠️  Ollama not running. Starting Ollama..." -ForegroundColor Yellow
    Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Change to project directory
Set-Location "C:\Users\pc\Downloads\ollama-rag"

# Start FastAPI server
Write-Host "🌐 Starting FastAPI server on http://localhost:8000..." -ForegroundColor Green
Write-Host "📝 Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
