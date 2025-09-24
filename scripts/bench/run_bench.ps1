# Run lightweight benchmark with dev-friendly env and log summary
$ErrorActionPreference = "Stop"

# Suggest tiny model and low-thread to minimize CPU usage during bench
$env:LLM_MODEL = "tinyllama"
$env:OLLAMA_NUM_THREAD = "2"
$env:OLLAMA_NUM_CTX = "1024"
$env:OLLAMA_NUM_GPU = "0"
$env:ORT_INTRA_OP_THREADS = "1"
$env:ORT_INTER_OP_THREADS = "1"

# Ensure server is running (assumes you started it separately)
# Run: PowerShell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1

# Default: hybrid, k=3, logs enabled, 3 rounds
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python "scripts/bench/bench_rag.py" --url "http://127.0.0.1:8000" --db "default" --dataset "data/bench/queries.json" --method "hybrid" --k 3 --enable-logs --rounds 3