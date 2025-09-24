# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Essential Commands

### Development Workflow
```powershell
# Install dependencies (Python + Node.js)
pip install -r requirements.txt
npm install && npm run playwright:install

# Pull required Ollama models
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Ingest sample documents into ChromaDB
python scripts/ingest.py

# Start FastAPI server (preferred method)
PowerShell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1

# Alternative server start (if preferred)
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Start desktop PyQt6 GUI application
PowerShell -ExecutionPolicy Bypass -File .\scripts\run_desktop.ps1
```

### Testing
```powershell
# Light e2e tests (faster, suitable for development)
$env:LLM_MODEL="tinyllama"; $env:OLLAMA_NUM_THREAD="2"; $env:OLLAMA_NUM_CTX="1024"; $env:OLLAMA_NUM_GPU="0"; $env:ORT_INTRA_OP_THREADS="1"; $env:ORT_INTER_OP_THREADS="1"; $env:UVICORN_RELOAD="0"; npm run test:e2e:light

# Or use the convenience script
PowerShell -ExecutionPolicy Bypass -File .\scripts\run_e2e_light.ps1

# Full e2e tests (includes Multi-hop, Reranker)
npm run test:e2e

# Debug tests
npm run test:e2e:debug

# Run a single spec file
npx playwright test tests/e2e/<file>.spec.ts

# Run a single file via npm script
npm run test:e2e -- tests/e2e/<file>.spec.ts

# Run tests matching a title
npx playwright test -g "pattern"
```

### Unit tests (pytest)
```powershell
# Install dev tools (includes pytest)
pip install -r requirements-dev.txt

# Run unit tests
pytest -q tests/unit

# Run a single test
pytest -q tests/unit/test_rag_engine_unit.py::test_valid_db_name
```

### Lint/Format
```powershell
# Install dev tools
pip install -r requirements-dev.txt

# Lint (ruff, black --check, isort --check-only)
PowerShell -ExecutionPolicy Bypass -File .\\scripts\\lint.ps1

# Auto-format (isort, black, ruff --fix)
PowerShell -ExecutionPolicy Bypass -File .\\scripts\\fmt.ps1
```

### Pre-commit hooks (optional)
```powershell
# Install tool
pip install pre-commit
# Register Git hooks
pre-commit install
# Run on all files once
pre-commit run --all-files
```

### Database Management
```powershell
# List databases (current + names)
curl.exe "http://127.0.0.1:8000/api/dbs"

# Create a database
curl.exe -X POST "http://127.0.0.1:8000/api/dbs/create" -H "Content-Type: application/json" -d "{\"name\":\"new_db\"}"

# Switch current database
curl.exe -X POST "http://127.0.0.1:8000/api/dbs/use" -H "Content-Type: application/json" -d "{\"name\":\"new_db\"}"

# Delete a database
curl.exe -X DELETE "http://127.0.0.1:8000/api/dbs/new_db"
```

### Provider Management
```powershell
# Get current provider
curl.exe "http://127.0.0.1:8000/api/provider"

# Switch provider (ollama | openai)
curl.exe -X POST "http://127.0.0.1:8000/api/provider" -H "Content-Type: application/json" -d "{\"name\":\"openai\"}"
```

### Query examples (non-stream vs stream)
```powershell
# Non-stream
echo '{"query":"Xin chào","method":"hybrid","k":5}' | curl.exe -X POST "http://127.0.0.1:8000/api/query" -H "Content-Type: application/json" --data-binary @-

# Stream (shows [[CTXJSON]] then tokens)
echo '{"query":"Xin chào","method":"hybrid","k":5}' | curl.exe -N -X POST "http://127.0.0.1:8000/api/stream_query" -H "Content-Type: application/json" --data-binary @-
```

### Deployment
- For Cloudflare Tunnel & Docker deployment, see deploy/README.md

### Filters, Logs, and Analytics (high-level)
- Filters: GET /api/filters returns available facets (languages, versions) for the current DB
- Logs: /api/logs/* to enable/disable, export JSONL, clear, and get summaries
- Analytics: /api/analytics/db and /api/analytics/chat/{id} provide usage metrics and top sources/versions/languages

## Architecture Overview

### Core Components
- **FastAPI Backend** (`app/main.py`): REST API server serving both web UI and API endpoints
- **RAG Engine** (`app/rag_engine.py`): Core retrieval-augmented generation logic with multi-database support
- **Web Frontend** (`web/`): Simple HTML/CSS/JS interface for the RAG application
- **Desktop Shell** (`desktop/main.py`): PyQt6-based desktop wrapper around the web UI

### Key Features
1. **Multi-Database Support**: Each database stored in `data/kb/{db_name}/` with independent ChromaDB collections
2. **Retrieval Methods**: Vector search, BM25, and hybrid retrieval with RRF (Reciprocal Rank Fusion)
3. **Reranking**: BGE ONNX and embedding-based rerankers for improved relevance
4. **Multi-hop Querying**: Decompose complex queries into sub-questions with configurable depth/fanout
5. **Query Rewriting**: Generate query variants and merge results for better coverage
6. **Provider Switching**: Support for both Ollama (local) and OpenAI models
7. **Chat Sessions**: Persistent conversation history with search/export capabilities
8. **Citations**: Automatic source citation with [n] markers and UI display

### Data Flow
1. Documents ingested from `data/docs/` → chunked → embedded via Ollama → stored in ChromaDB
2. User queries → embedded → similarity search/BM25 → optional reranking → context formation
3. Context + query → LLM (Ollama/OpenAI) → answer with citations → UI display
4. Multi-hop: query decomposition → parallel sub-queries → result aggregation → final answer

### File Structure Patterns
- `app/*.py`: Core application modules (engine, clients, stores)
- `scripts/*.py`: Data ingestion and utility scripts  
- `scripts/*.ps1`: PowerShell automation scripts for Windows
- `tests/e2e/`: Playwright end-to-end test suites
- `deploy/`: Cloudflare Tunnel deployment configurations
- `data/docs/`: Document source directory for ingestion
- `data/kb/{db}/`: Per-database ChromaDB storage
- `web/`: Static web frontend files

### Environment Configuration
Critical environment variables:
- `OLLAMA_BASE_URL`: Ollama server endpoint (default: http://localhost:11434)
- `LLM_MODEL`: Generation model (default: llama3.1:8b)
- `EMBED_MODEL`: Embedding model (default: nomic-embed-text)
- `PROVIDER`: ollama|openai (affects generation, not embeddings)
- `OPENAI_API_KEY`: Required when using OpenAI provider
- `PERSIST_ROOT`: Root directory for databases (default: data/kb)

### Streaming and Citations
- Streaming endpoints (`/api/stream_query`) use special header format: `[[CTXJSON]]{json}\n` followed by answer stream
- Citations parsed from LLM responses using [n] markers, mapped to context sources
- UI automatically renders citation panels with source links

## Vietnamese Language Support
This codebase is primarily documented and interfaced in Vietnamese, with code comments and UI text in Vietnamese. The RAG system supports Vietnamese document processing and querying through the Ollama embedding models.