# WARP — Developer Guide

This document captures key commands and architecture notes used during development on this repo.

## Benchmark Notes

- Purpose: track end-to-end latency for common query paths on a local machine.
- Methodology:
  - Warm up embeddings/index by running a sample ingest against data/docs
  - Measure two timings for streaming APIs:
    - t_ctx: time to first contexts header ([[CTXJSON]]), an indicator of retrieval speed
    - t_ans: total time until stream completes, an indicator of end-to-end answer latency
  - For non-stream APIs, measure total request latency
- Matrix (default):
  - bm25 non-stream, bm25 stream, hybrid non-stream, hybrid stream
  - rounds=3, report mean/median/min/max
- Scripts:
  - python scripts/bench/bench_matrix.py --rounds 3
- Results are written to bench-results/bench-matrix-YYYYMMDD-HHMMSS.csv

Example (rounds=3 on local, tinyllama):
- bm25 non-stream latency: ~1.07s median
- bm25 stream: t_ctx ~0.016s, t_ans ~1.07s median
- hybrid non-stream latency: ~5.19s median
- hybrid stream: t_ctx ~3.56s, t_ans ~5.13s median

## Common Dev Commands

- Run server (Windows PowerShell):
  PowerShell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1

- Run e2e light locally (headless):
  npm run test:e2e:light

- Run only @heavy tests (CI/nightly):
  npx playwright test --config=playwright.ci.config.js --grep @heavy

