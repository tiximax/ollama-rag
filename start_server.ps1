# Start Ollama RAG Server with Environment Variables
Write-Host "`n=== Ollama RAG Server Startup ===" -ForegroundColor Cyan

# Load .env file
Write-Host "Loading environment variables from .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        $line = $_.Trim()
        # Skip empty lines and comments
        if ($line -and -not $line.StartsWith("#")) {
            # Split on first = only
            $parts = $line -split "=", 2
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                # Set environment variable for current process
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
                if ($key -match "CACHE|SEMANTIC") {
                    Write-Host "  ✅ Set $key = $value" -ForegroundColor Green
                }
            }
        }
    }
    Write-Host "✅ Environment variables loaded!" -ForegroundColor Green
} else {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env from .env.example" -ForegroundColor Yellow
    exit 1
}

# Verify critical cache variables
Write-Host "`n=== Cache Configuration ===" -ForegroundColor Cyan
Write-Host "USE_SEMANTIC_CACHE = $env:USE_SEMANTIC_CACHE" -ForegroundColor Yellow
Write-Host "SEMANTIC_CACHE_THRESHOLD = $env:SEMANTIC_CACHE_THRESHOLD" -ForegroundColor Yellow
Write-Host "SEMANTIC_CACHE_SIZE = $env:SEMANTIC_CACHE_SIZE" -ForegroundColor Yellow
Write-Host "SEMANTIC_CACHE_TTL = $env:SEMANTIC_CACHE_TTL" -ForegroundColor Yellow

# Check if Ollama is running
Write-Host "`n=== Checking Ollama Service ===" -ForegroundColor Cyan
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Write-Host "⚠️  Ollama not running. Starting Ollama..." -ForegroundColor Yellow
    Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "✅ Ollama started!" -ForegroundColor Green
} else {
    Write-Host "✅ Ollama is already running" -ForegroundColor Green
}

# Start FastAPI server
Write-Host "`n=== Starting FastAPI Server ===" -ForegroundColor Cyan
Write-Host "🌐 Server will be available at: http://localhost:8000" -ForegroundColor Green
Write-Host "📚 API docs at: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`n📝 Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
