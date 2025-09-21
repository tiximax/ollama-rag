# Agent Notes — ollama-rag

Thời gian: 2025-09-21T04:21:19Z
Vị trí dự án: C:\Users\pc\Downloads\ollama-rag (Windows)

## Mục tiêu
Xây dựng ứng dụng RAG dùng Ollama (local) với UI web đơn giản, hỗ trợ ingest đa định dạng, tìm kiếm theo ngữ nghĩa, và triển khai qua Cloudflare Tunnel. Làm nền tảng để tiến tới RAG 2.0 (Hybrid Search, Reranker, Multi-hop, Multi-DB, Desktop shell PyQt6) theo yêu cầu.

## Đặc tả hiện tại (đã triển khai)
- Backend: FastAPI (app/main.py)
- Vector store: ChromaDB PersistentClient (data/chroma)
- LLM: Ollama (mặc định llama3.1:8b), streaming qua /api/stream_query
- Embedding: Ollama nomic-embed-text (client gọi /api/embeddings)
- UI: web (web/index.html, app.js, styles.css)
- Ingest: TXT, PDF (pypdf), DOCX (python-docx) – thêm file vào data/docs rồi gọi /api/ingest
- Tính năng UI: nhập câu hỏi, đặt số CTX k, bật Streaming; hiển thị các CTX
- Script: scripts/ingest.py, scripts/run_server.ps1, scripts/pull_models.ps1
- Deploy: Cloudflare Tunnel (deploy/README.md)
  - Docker Compose: deploy/docker/Dockerfile, docker-compose.yml, compose-up.ps1, compose-down.ps1
  - cloudflared native (Windows): deploy/cloudflared/config.yml.example, start-local.ps1

## Spec mở rộng (RAG 2.0 – mục tiêu kế tiếp)
- Hybrid Search: FAISS + BM25 (RRF/trọng số)
- Reranker: BAAI/bge-reranker-v2-m3 (INT8) trên top-N
- Multi-hop Retrieval: decompose → retrieve → synthesize, giới hạn depth/steps
- Multi-DB: tách DB theo thư mục data/kb/{db_name}/, chats riêng theo DB
- Desktop shell: PyQt6 + QWebEngineView (nhúng web UI)
- Chat & quản trị hội thoại: rename/export/xóa, tìm kiếm lịch sử
- Provider switch: Ollama/OpenAI (bật tắt an toàn dữ liệu)

## Plan (ngắn hạn)
1) Viết và chạy test e2e Playwright cơ bản (ingest → hỏi → có ctx, streaming)
2) Bổ sung Hybrid Search (FAISS + BM25) với tham số hóa k, weight
3) Thêm Reranker BGE v2 (INT8) vào pipeline
4) (Tuỳ chọn) Multi-DB cơ bản: tạo/xóa/list DB, chọn DB từ UI
5) Chuẩn bị Desktop shell PyQt6 nhúng UI (khung cơ bản)

## Tasks
- [x] Khởi tạo FastAPI + UI web + Chroma + Ollama client
- [x] Ingest TXT/PDF/DOCX, chunking và lưu index
- [x] Streaming + chọn top-k trên UI
- [x] Tài liệu + file triển khai Cloudflare Tunnel (Docker + native)
- [ ] Test e2e Playwright tối thiểu (MCP theo rule người dùng)
- [ ] Hybrid Search (FAISS+BM25) + tham số hóa
- [ ] Tích hợp Reranker BGE v2 (INT8)
- [ ] Multi-DB cơ bản (API + UI)
- [ ] Desktop shell PyQt6 (khung, nhúng UI)

## Hướng dẫn sử dụng nhanh
- Kéo models:
  - ollama pull llama3.1:8b
  - ollama pull nomic-embed-text
- Chạy server (PowerShell):
  - PowerShell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1
  - Mở http://127.0.0.1:8000
- Ingest dữ liệu:
  - Thả file .txt/.pdf/.docx vào data/docs, bấm “Index tài liệu mẫu” hoặc:
  - python .\scripts\ingest.py

## Triển khai Cloudflare Tunnel
- Docker Compose: dùng deploy/docker/docker-compose.yml (cần đặt biến CF_TUNNEL_TOKEN)
  - $env:CF_TUNNEL_TOKEN="{{CF_TUNNEL_TOKEN}}"
  - PowerShell -ExecutionPolicy Bypass -File .\deploy\docker\compose-up.ps1 -Build
- cloudflared native (Windows):
  - winget install Cloudflare.cloudflared
  - cloudflared tunnel login → create → cập nhật C:\Users\pc\.cloudflared\config.yml
  - PowerShell -ExecutionPolicy Bypass -File .\deploy\cloudflared\start-local.ps1 -TunnelId <TUNNEL_ID>

## Tiến trình gần nhất
- 2025-09-21: Hoàn tất bản web app cơ bản chạy với Ollama, ingest TXT/PDF/DOCX, streaming, top-k.
- 2025-09-21: Thêm bộ file triển khai Cloudflare Tunnel (Docker Compose + native) và hướng dẫn.
- 2025-09-21: Server local hoạt động tại http://127.0.0.1:8000; sẵn sàng chạy tunnel nếu có CF_TUNNEL_TOKEN.

## Ghi chú
- Khi thêm tính năng mới, theo rule: chạy test automation (MCP Playwright) và sửa cho đến khi pass.
- Không commit khóa/token; đặt trong biến môi trường.
