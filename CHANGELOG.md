# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]

### Added
- Lightweight UI-mocked Playwright tests to harden key flows without heavy backend work:
  - Multihop (UI) non-stream payload validation
  - Reranker (UI stream) with rr_* advanced options
  - Rewrite (UI stream) flags
  - Citations (UI) variants with multiple markers and filters
  - Chat exports (JSON/MD) and DB export (ZIP)
  - Logs summary (UI) rendering
  - Analytics (UI) rendering
  - Feedback (UI) sending with sources captured
  - Search chats (UI) result count rendering
  - Filters (UI) populate languages/versions
  - Chat CRUD (UI) create/rename/delete via mocked APIs (validate request bodies)
- Negative-path light tests: errors_ui (mock 500/503) to assert UI fail states.
- Nightly heavy E2E workflow (e2e-heavy.yml) to run @heavy suite on schedule and manual dispatch.
- Benchmark Notes in README.md and WARP.md with example medians from latest local run.
- Benchmark matrix script (scripts/bench/bench_matrix.py) to measure bm25/hybrid x stream/non-stream, rounds=3, save CSV.

### Changed
- Stabilized light suite (disambiguated Analytics refresh button; marked filters/multidb/upload as @heavy).

### Notes
- Heavy tests are excluded from light runs via @heavy tag and executed by the new nightly workflow once merged to default branch.
- Example benchmark summary (rounds=3, tinyllama): bm25 ns ~1.07s, bm25 stream t_ctx~0.016s/t_ans~1.07s, hybrid ns ~5.19s, hybrid stream t_ctx~3.56s/t_ans~5.13s.
