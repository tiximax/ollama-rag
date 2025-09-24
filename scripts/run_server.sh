#!/usr/bin/env bash
set -euo pipefail

# Cross-platform server runner for macOS/Linux
# Usage: ./scripts/run_server.sh

export PYTHONPATH="${PYTHONPATH:-.}"

PY="python3"
if command -v python >/dev/null 2>&1; then
  PY="python"
fi
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
fi

HOST="127.0.0.1"
PORT="8000"
RELOAD="${UVICORN_RELOAD:-0}"

ARGS=( -m uvicorn app.main:app --host "$HOST" --port "$PORT" )
if [ "$RELOAD" = "1" ] || [ "$RELOAD" = "true" ]; then
  ARGS+=( --reload )
fi

echo "Using Python: $PY"
echo "Starting FastAPI on http://$HOST:$PORT"
exec "$PY" "${ARGS[@]}"
