# Ollama RAG App

[![e2e-light](https://github.com/tiximax/ollama-rag/actions/workflows/e2e.yml/badge.svg)](https://github.com/tiximax/ollama-rag/actions/workflows/e2e.yml)

Ứng dụng RAG nhẹ sử dụng FastAPI + ChromaDB + Ollama (LLM + Embeddings), chạy web UI cục bộ.

Tính năng:
- Ingest tài liệu .txt trong data/docs
- Tìm kiếm theo vector (ChromaDB)
- Tạo câu trả lời nhờ mô hình Ollama (mặc định llama3.1:8b)
- Sử dụng embedding model của Ollama (mặc định nomic-embed-text)
- Web UI đơn giản: nhập câu hỏi, xem kết quả và nguồn ngữ cảnh

Yêu cầu:
- Windows / macOS / Linux
- Python 3.10+
- Node.js + npm (để chạy Playwright e2e)
- Ollama (http://localhost:11434) hoặc OpenAI API Key

Cài đặt nhanh (Windows):
1) Cài Python packages
   pip install -r requirements.txt

2) (Tùy chọn e2e) Cài Playwright
   npm install
   npm run playwright:install

3) Cấu hình (tạo .env từ mẫu)
   copy .env.example .env
   - Sửa PROVIDER=ollama hoặc openai
   - Nếu dùng OpenAI, đặt OPENAI_API_KEY (đừng echo/log khóa)

4) Nếu dùng Ollama: kéo models mặc định
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text

5) Chạy server (ổn định – không reload)
   py -m uvicorn app.main:app --host 127.0.0.1 --port 8001
   (hoặc dùng script: py start_server.py / py start_server.py dev)

6) Mở UI:
   http://127.0.0.1:8001

Health/Preflight
- Backend health API: GET /api/health
  - provider: ollama|openai
  - overall_status: ok|warning|error
  - suggestions: gợi ý khắc phục (ollama serve, ollama pull, cấu hình OPENAI_API_KEY)
- UI hiển thị chip “Backend” (màu sắc + tooltip). Khi backend chưa OK, các nút Ingest/Gửi sẽ bị vô hiệu hóa tạm thời.

Triển khai qua Cloudflare Tunnel (tùy chọn)
- Xem deploy/README.md
- Docker compose: deploy/docker/docker-compose.yml (cần CF_TUNNEL_TOKEN)
- cloudflared native trên Windows: deploy/cloudflared/config.yml.example + start-local.ps1

Chạy tests
- Unit/Smoke: py -m pip install httpx && py -m unittest -q
- Playwright e2e (tùy chọn):
- Cài đặt một lần: npm install && npm run playwright:install
- Chế độ nhẹ (khuyến nghị khi dev, giảm CPU):
  PowerShell:
    $env:LLM_MODEL="tinyllama"; $env:OLLAMA_NUM_THREAD="2"; $env:OLLAMA_NUM_CTX="1024"; $env:OLLAMA_NUM_GPU="0"; $env:ORT_INTRA_OP_THREADS="1"; $env:ORT_INTER_OP_THREADS="1"; $env:UVICORN_RELOAD="0";
    npm run test:e2e:light
- Chạy full (gồm Multi-hop, Reranker):
    npm run test:e2e

## Benchmark Notes

- Chạy benchmark matrix nội bộ với rounds=3 để làm mượt kết quả.
- Ma trận mặc định: bm25 non-stream, bm25 stream, hybrid non-stream, hybrid stream.
- Đo thời gian:
  - Non-stream: tổng latency của /api/query
  - Stream: t_ctx (thời gian tới header [[CTXJSON]]), t_ans (tổng thời gian stream)
- Cách chạy:
  - python scripts/bench/bench_matrix.py --rounds 3
  - Kết quả CSV: bench-results/bench-matrix-YYYYMMDD-HHMMSS.csv

Troubleshooting
- Lỗi 11434 (Connection refused): chạy ollama serve; kiểm tra http://localhost:11434/api/tags
- Thiếu model: ollama pull nomic-embed-text, ollama pull llama3.1:8b
- Dùng OpenAI: set OPENAI_API_KEY rồi đổi Provider sang openai
- UI không cập nhật: hard refresh (Ctrl+F5)

Ví dụ benchmark (rounds=3 trên máy local, tinyllama):
- bm25 non-stream (latency s): ~1.07 median
- bm25 stream (t_ctx/t_ans s): ~0.016 / ~1.07 median
- hybrid non-stream (latency s): ~5.19 median
- hybrid stream (t_ctx/t_ans s): ~3.56 / ~5.13 median

UI — các điều khiển chính
- Menu Hỗ trợ: Quick Start (hướng dẫn 3 bước)
- Provider: Ollama | OpenAI (generate/stream dùng provider đã chọn; Embeddings luôn dùng Ollama/local)
- Phương pháp: vector | bm25 | hybrid (+ w BM25)
- Reranker: bật/tắt + Top-N
- Rewrite: bật/tắt + n (sinh biến thể truy vấn, hợp nhất RRF trước rerank; mặc định tắt)
- Multi-hop: bật/tắt + Depth + Fanout (+ Fanout-1st, Budget ms)
- Citations: panel hiển thị chú thích [n] theo nguồn/ngữ cảnh
- DB: chọn DB, tạo/xóa DB
- Chat: chọn session, New/Rename/Delete, checkbox “Lưu hội thoại” (auto-save Q/A)

Chat Sessions (API nhanh)
- GET /api/chats?db=<DB>
- POST /api/chats { db?, name? }
- GET /api/chats/{id}?db=<DB>
- PATCH /api/chats/{id}?db=<DB> { name }
- DELETE /api/chats/{id}?db=<DB>
- Lưu tự động Q/A khi hỏi: trong body /api/query (và stream/multihop) thêm chat_id và save_chat=true

Chat advanced (Search / Export / Delete All)
- UI:
  - Ô “Tìm trong DB…” + nút Search: tìm theo nội dung messages, kết quả tóm tắt hiển thị ở khối Result
  - Export JSON/MD: tải file hội thoại hiện chọn (JSON hoặc Markdown)
  - Delete All: xóa toàn bộ hội thoại của DB hiện tại (không thể hoàn tác)
- API nhanh (curl minh họa, Windows PowerShell dùng curl alias Invoke-WebRequest):
  - Tìm: curl "http://127.0.0.1:8000/api/chats/search?db=<DB>&q=<keyword>"
  - Export JSON: curl "http://127.0.0.1:8000/api/chats/<CHAT_ID>/export?db=<DB>&format=json"
  - Export MD: curl "http://127.0.0.1:8000/api/chats/<CHAT_ID>/export?db=<DB>&format=md"
  - Xóa tất cả: curl -X DELETE "http://127.0.0.1:8000/api/chats?db=<DB>"

Provider switch (Ollama/OpenAI)
- UI: chọn Provider ở thanh điều khiển (mặc định: Ollama). Embeddings mặc định dùng Ollama local.
- API nhanh:
  - GET /api/provider → { provider }
  - POST /api/provider { name: "ollama" | "openai" }
  - Per-request override: thêm provider vào body của /api/query, /api/stream_query, /api/multihop_query, /api/stream_multihop_query
- Biến môi trường:
  - PROVIDER=ollama|openai (mặc định ollama)
  - OPENAI_API_KEY={{OPENAI_API_KEY}} (bắt buộc khi dùng OpenAI)
  - OPENAI_MODEL=gpt-4o-mini (mặc định)
  - OPENAI_CONNECT_TIMEOUT, OPENAI_READ_TIMEOUT, OPENAI_MAX_RETRIES, OPENAI_RETRY_BACKOFF
- Ghi chú bảo mật: Quản lý khóa qua ENV, không echo/log giá trị khóa. Không commit khóa vào repo.

Citations [n]
- Backend yêu cầu LLM chèn [n] tương ứng với [CTX n] khi trả lời.
- UI sẽ parse các marker [1], [2], … và hiển thị “Citations panel” gồm nguồn (source) và chunk.
- Non-stream: API /api/query trả về metadatas[] cùng answer để render citations.
- Streaming: server gửi header đặc biệt ở đầu stream: [[CTXJSON]]{json}\n chứa { contexts, metadatas, db } để client render sớm; phần answer stream nối tiếp sau đó.

Citations Export (API nhanh)
- Theo chat:
  - JSON: GET /api/citations/chat/{chat_id}?db=<DB>&format=json
  - CSV:  GET /api/citations/chat/{chat_id}?db=<DB>&format=csv
  - MD:   GET /api/citations/chat/{chat_id}?db=<DB>&format=md
- Toàn DB (ZIP nhiều file):
  - JSON: GET /api/citations/db?db=<DB>&format=json
  - CSV:  GET /api/citations/db?db=<DB>&format=csv
  - MD:   GET /api/citations/db?db=<DB>&format=md
- Lọc nâng cao: thêm query params (dấu phẩy = nhiều giá trị)
  - sources=a.txt,b.txt (substring match trên metadata.source)
  - versions=v1,v2 (match chính xác)
  - languages=vi,en (match chính xác)
- Ví dụ (PowerShell, JSON per chat):
  - curl "http://127.0.0.1:8001/api/citations/chat/$($env:CHAT_ID)?db=default&format=json&sources=a.txt&versions=v1&languages=vi"

Query Rewrite (UI + API)
- UI: bật “Rewrite” và đặt n (1..5). Mặc định tắt để tránh tăng chi phí CPU.
- Hành vi: sinh n biến thể truy vấn, hợp nhất kết quả retrieval bằng RRF trước khi rerank/sinh câu trả lời.
- API:
  - /api/query, /api/stream_query body có các trường:
    rewrite_enable: boolean, rewrite_n: number
  - Ví dụ body:
```
{
  "query": "Bitsness là gì?",
  "method": "hybrid",
  "k": 5,
  "rewrite_enable": true,
  "rewrite_n": 2
}
```

Multi-hop nâng cao (budget_ms, fanout_first_hop)
- UI: khi bật Multi-hop sẽ hiện thêm các tham số:
  - Depth, Fanout (mặc định 2)
  - Fanout-1st: fanout riêng cho hop đầu (1..5)
  - Budget(ms): giới hạn thời gian (ước lượng) cho toàn bộ quá trình decompose + retrieve; nếu sắp hết budget có thể cắt bớt sub-questions.
- API:
  - /api/multihop_query, /api/stream_multihop_query body chấp nhận:
    fanout_first_hop: number, budget_ms: number
  - Ví dụ body:
```
{
  "query": "Giải thích A liên quan B",
  "method": "hybrid",
  "k": 5,
  "depth": 2,
  "fanout": 2,
  "fanout_first_hop": 1,
  "budget_ms": 200
}
```

Cấu hình (.env):
- PROVIDER=ollama|openai (mặc định ollama)
- OLLAMA_BASE_URL=http://localhost:11434
- LLM_MODEL=llama3.1:8b
- EMBED_MODEL=nomic-embed-text
- CHUNK_SIZE=800, CHUNK_OVERLAP=120
- OLLAMA_CONNECT_TIMEOUT=5, OLLAMA_READ_TIMEOUT=180, OLLAMA_MAX_RETRIES=3, OLLAMA_RETRY_BACKOFF=0.6
- OLLAMA_NUM_THREAD, OLLAMA_NUM_CTX, OLLAMA_NUM_GPU (tinh chỉnh hiệu năng)
- OPENAI_BASE_URL=https://api.openai.com/v1, OPENAI_MODEL=gpt-4o-mini, OPENAI_API_KEY={{OPENAI_API_KEY}}
- PERSIST_DIR (ví dụ data/chroma) hoặc PERSIST_ROOT=data/kb + DB_NAME=default
- ORT_INTRA_OP_THREADS, ORT_INTER_OP_THREADS
