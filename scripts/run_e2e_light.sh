#!/usr/bin/env bash
set -euo pipefail

# Light e2e with resource limits for macOS/Linux
# Usage: ./scripts/run_e2e_light.sh

export LLM_MODEL="tinyllama"
export OLLAMA_NUM_THREAD="2"
export OLLAMA_NUM_CTX="1024"
export OLLAMA_NUM_GPU="0"
export ORT_INTRA_OP_THREADS="1"
export ORT_INTER_OP_THREADS="1"
export UVICORN_RELOAD="0"

npm run test:e2e:light
