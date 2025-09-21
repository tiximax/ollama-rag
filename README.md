# Ollama RAG App

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
- Ollama đã cài và đang chạy (http://localhost:11434)

Cài đặt:
1) Cài Python packages
   pip install -r requirements.txt

2) Cài Playwright (tùy chọn, để test e2e)
   npm install
   npm run playwright:install

3) Kéo model Ollama (mặc định):
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text

4) Ingest mẫu:
   python scripts/ingest.py

5) Chạy server (khuyến nghị dùng script PowerShell trên Windows):
   PowerShell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1
   (hoặc dùng uvicorn: uvicorn app.main:app --host 127.0.0.1 --port 8000)

6) Mở UI:
   http://127.0.0.1:8000

Triển khai qua Cloudflare Tunnel (tùy chọn)
- Xem deploy/README.md
- Docker compose: deploy/docker/docker-compose.yml (cần CF_TUNNEL_TOKEN)
- cloudflared native trên Windows: deploy/cloudflared/config.yml.example + start-local.ps1

Chạy Playwright e2e
- Cài đặt một lần: npm install && npm run playwright:install
- Chế độ nhẹ (khuyến nghị khi dev, giảm CPU):
  PowerShell:
    $env:LLM_MODEL="tinyllama"; $env:OLLAMA_NUM_THREAD="2"; $env:OLLAMA_NUM_CTX="1024"; $env:OLLAMA_NUM_GPU="0"; $env:ORT_INTRA_OP_THREADS="1"; $env:ORT_INTER_OP_THREADS="1"; $env:UVICORN_RELOAD="0";
    npm run test:e2e:light
- Chạy full (gồm Multi-hop, Reranker):
    npm run test:e2e

UI — các điều khiển chính
- Provider: Ollama | OpenAI (generate/stream dùng provider đã chọn; Embeddings luôn dùng Ollama/local)
- Phương pháp: vector | bm25 | hybrid (+ w BM25)
- Reranker: bật/tắt + Top-N
- Multi-hop: bật/tắt + Depth + Fanout
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
- UI: chọn Provider ở thanh điều khiển (mặc định: Ollama). Embeddings luôn chạy bằng Ollama để đảm bảo local & không cần re-index.
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

Cấu hình (tùy chọn .env):
- OLLAMA_BASE_URL=http://localhost:11434
- LLM_MODEL=llama3.1:8b
- EMBED_MODEL=nomic-embed-text
- CHUNK_SIZE=800
- CHUNK_OVERLAP=120
- OLLAMA_CONNECT_TIMEOUT=5, OLLAMA_READ_TIMEOUT=180, OLLAMA_MAX_RETRIES=3, OLLAMA_RETRY_BACKOFF=0.6
- OLLAMA_NUM_THREAD, OLLAMA_NUM_CTX, OLLAMA_NUM_GPU (tinh chỉnh hiệu năng)
- ORT_INTRA_OP_THREADS, ORT_INTER_OP_THREADS (giới hạn luồng ONNXRuntime)
