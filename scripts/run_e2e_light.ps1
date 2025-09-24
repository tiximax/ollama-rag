# Run Playwright light e2e with dev-friendly env knobs
$ErrorActionPreference = "Stop"

$env:LLM_MODEL = "tinyllama"
$env:OLLAMA_NUM_THREAD = "2"
$env:OLLAMA_NUM_CTX = "1024"
$env:OLLAMA_NUM_GPU = "0"
$env:ORT_INTRA_OP_THREADS = "1"
$env:ORT_INTER_OP_THREADS = "1"
$env:UVICORN_RELOAD = "0"

npm run test:e2e:light