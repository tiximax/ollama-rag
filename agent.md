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
- Desktop shell: PyQt6 + QWebEngineView (desktop/main.py)
  - Cấu hình URL/Host/Port, Start/Stop server trong app, tự động reconnect
  - Lưu cấu hình tại %USERPROFILE%\.ollama_rag_desktop.json
- Ingest: TXT, PDF (pypdf), DOCX (python-docx) – thêm file vào data/docs rồi gọi /api/ingest
- Retrieval: Vector | BM25 | Hybrid (trọng số BM25)
- Reranker: BGE v2 m3 (ONNX) hoặc fallback cosine-embedding
- Multi-DB: tách DB theo thư mục data/kb/{db_name}/ và chuyển DB từ UI
- Multi-hop: decompose → retrieve → synthesize (API + streaming), có fallback single-hop khi không có context
- Chat Sessions: lưu theo DB (data/kb/{db}/chats/{id}.json), CRUD API, auto-save Q/A từ query/stream, UI chọn/tạo/đổi tên/xóa, bật/tắt lưu
- Provider switch: Ollama/OpenAI (mặc định Ollama). Embeddings luôn dùng Ollama/local.
- Tính năng UI: nhập câu hỏi, đặt số CTX k, bật Streaming; hiển thị các CTX; chọn phương pháp, reranker, multi-hop, DB
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
6) Tối ưu hiệu năng local và thêm “chế độ nhẹ” cho e2e

## Tasks
- [x] Khởi tạo FastAPI + UI web + Chroma + Ollama client
- [x] Ingest TXT/PDF/DOCX, chunking và lưu index
- [x] Streaming + chọn top-k trên UI
- [x] Tài liệu + file triển khai Cloudflare Tunnel (Docker + native)
- [x] Test e2e Playwright tối thiểu (MCP theo rule người dùng)
- [x] Hybrid Search (FAISS+BM25) + tham số hóa
- [x] Tích hợp Reranker BGE v2 (INT8) (ưu tiên ONNX; fallback cosine embedding)
- [x] Multi-DB cơ bản (API + UI)
- [x] Desktop shell PyQt6 (khung, nhúng UI, cấu hình server, Start/Stop)
- [x] Multi-hop Retrieval (engine + API + UI) + fallback single-hop
- [x] Tối ưu hiệu năng local + thêm test:e2e:light (bỏ qua @heavy)
- [x] Chat Sessions (per-DB) + auto-save Q/A + UI quản lý
- [x] Provider switch (Ollama/OpenAI) + API /api/provider + UI chọn provider

## Hướng dẫn sử dụng nhanh
- Kéo models:
  - ollama pull llama3.1:8b (hoặc tinyllama cho chế độ nhẹ)
  - ollama pull nomic-embed-text
- Chạy server (PowerShell):
  - PowerShell -ExecutionPolicy Bypass -File .\\scripts\\run_server.ps1
  - Mở http://127.0.0.1:8000
- Ingest dữ liệu:
  - Thả file .txt/.pdf/.docx vào data/docs, bấm “Index tài liệu mẫu” hoặc:
  - python .\\scripts\\ingest.py

### Chạy Playwright e2e (chế độ nhẹ khuyến nghị khi dev)

#### Chat Sessions (API nhanh)
- List: GET /api/chats?db=<DB>
- Create: POST /api/chats { db?, name? }
- Get: GET /api/chats/{id}?db=<DB>
- Rename: PATCH /api/chats/{id}?db=<DB> { name }
- Delete: DELETE /api/chats/{id}?db=<DB>
- Lưu tự động: gửi chat_id và save_chat=true trong body /api/query, /api/stream_query, /api/multihop_query, /api/stream_multihop_query

#### Chat advanced (Search / Export / Delete All)
- UI: thanh Chat có ô tìm kiếm, các nút Export JSON/MD, Delete All (theo DB hiện tại)
- API nhanh:
  - Tìm: GET /api/chats/search?db=<DB>&q=<keyword>
  - Export JSON: GET /api/chats/{id}/export?db=<DB>&format=json
  - Export MD: GET /api/chats/{id}/export?db=<DB>&format=md
  - Xóa toàn bộ: DELETE /api/chats?db=<DB>

#### Provider switch (Ollama/OpenAI)
- UI: chọn Provider ở thanh điều khiển; mặc định Ollama. Embeddings luôn dùng Ollama/local để đảm bảo private & không re-index.
- API nhanh:
  - GET /api/provider → { provider }
  - POST /api/provider { name: "ollama" | "openai" }
  - Per-request: gửi provider trong body của /api/query, /api/stream_query, /api/multihop_query, /api/stream_multihop_query
- ENV:
  - PROVIDER=ollama|openai (mặc định ollama)
  - OPENAI_API_KEY, OPENAI_MODEL, OPENAI_* timeout/retry
- Bảo mật: Quản lý secret qua ENV, không log/echo giá trị.
- Thiết lập biến môi trường trước khi chạy test (pwsh/Windows):
  - $env:LLM_MODEL = "tinyllama"
  - $env:OLLAMA_NUM_THREAD = "2"
  - $env:OLLAMA_NUM_CTX = "1024"
  - $env:OLLAMA_NUM_GPU = "0"
  - $env:ORT_INTRA_OP_THREADS = "1"
  - $env:ORT_INTER_OP_THREADS = "1"
  - $env:UVICORN_RELOAD = "0"
- Chạy test nhẹ (bỏ qua @heavy):
  - npm run test:e2e:light
- Chạy full (gồm Multi-hop, Reranker):
  - npm run test:e2e

## Triển khai Cloudflare Tunnel
- Docker Compose: dùng deploy/docker/docker-compose.yml (cần đặt biến CF_TUNNEL_TOKEN)
  - $env:CF_TUNNEL_TOKEN="{{CF_TUNNEL_TOKEN}}"
  - PowerShell -ExecutionPolicy Bypass -File .\deploy\docker\compose-up.ps1 -Build
- cloudflared native (Windows):
  - winget install Cloudflare.cloudflared
  - cloudflared tunnel login → create → cập nhật C:\Users\pc\.cloudflared\config.yml
  - PowerShell -ExecutionPolicy Bypass -File .\deploy\cloudflared\start-local.ps1 -TunnelId <TUNNEL_ID>

## Tiến trình gần nhất
- 2025-09-21: Thêm Provider switch (OpenAI/Ollama), UI dropdown, API /api/provider; giữ Embeddings bằng Ollama. Test e2e (light) không hồi quy.

## Kế hoạch R&D (Học thuật)
Mục tiêu: độ phủ tri thức & suy luận đa bước (multi-step), trích dẫn đa tài liệu, hỗ trợ đa ngôn ngữ và phiên bản hóa.

1) Pipeline truy vấn
- Hybrid + RRF (Rank Fusion):
  - Lấy top-N (vector) và top-M (BM25), hợp nhất bằng RRF: score = Σ 1/(k + rank_i).
  - Giữ chế độ normalize-weight làm tùy chọn; mặc định RRF.
- Rerank bắt buộc:
  - Rerank top-K' (K' ≥ k) bằng BGE-ONNX; fallback cosine-embed (đã có). Mặc định bật.
- Query rewrite/decompose:
  - Rewrite 2–3 biến thể truy vấn (đa ngôn ngữ), hợp nhất bằng RRF trước rerank.
  - Multi-hop (đã có): thêm tham số fanout_first_hop, budget_time_ms và max_hops để giới hạn chi phí.
- Trích nguồn đa tài liệu + citations:
  - Mỗi context kèm metadata {source, version, language, chunk}. Prompt yêu cầu chèn [n].
  - Trả về citations: [{n, source, version, chunk}] cho UI render footnotes.

2) Dữ liệu
- Tài liệu dài: chunking 1000–1500 tokens, overlap 150–250; ưu tiên cắt theo tiêu đề/mục lục.
- Phiên bản hóa: field version cho mỗi chunk; UI/Lọc theo version (hoặc dùng DB như version).
- Đa ngôn ngữ: langid cho mỗi doc; BM25 tokenizer tùy ngôn ngữ; embedding đa ngôn ngữ (nomic-embed-text/bge-m3).

3) Đo lường & đánh giá
- Recall@k cho retrieval (pre/post-rerank) trên tập dev (q, gold_doc_ids).
- Faithfulness: LLM-judge (local/OpenAI) đối chiếu answer với contexts; hoặc heuristic n-gram overlap (tham khảo).
- Usefulness: UI feedback (thumbs/score/comment) + lưu vào /api/feedback.
- Logging thực nghiệm JSONL: {ts, query, rewrites[], retrieve_sets, rrf_scores, rerank_scores, answer, citations, metrics?, provider, db, version}.

4) UI/UX
- Panel “Advanced R&D”: bật RRF, bắt buộc Reranker, Rewrite(n), Multi-hop(depth/fanout), budget time.
- Bộ lọc version & language; hiển thị citations [n] → expand ngữ cảnh + metadata.
- Nút Evaluate: chạy pilot set → hiện Recall@k, ước lượng faithfulness, bảng truy vấn.

5) API
- /api/query, /api/stream_query: thêm options rrf_enable, rrf_k, rewrite_enable, rewrite_n, hop_depth, hop_fanout, hop_budget_ms, version, language_filter, citations_format.
- /api/eval/offline: nhận JSONL devset → trả Recall@k, latency, fail cases.
- /api/feedback: lưu đánh giá người dùng (score/comment) kèm truy vấn/answer/citations.

6) Kế hoạch triển khai (ưu tiên)
- B1: Thêm RRF vào retrieve_hybrid (mặc định bật). e2e: contexts ổn định + citations stub.
- B5: Citations [n] + map metadata → UI footnotes. e2e: kiểm tra [1][2] xuất hiện và map đúng.
- B3: Query rewrite (n=2) + RRF hợp nhất. e2e: đa dạng hóa contexts (không đánh giá nội dung).
- B4: Multi-hop nâng cao: budget + fanout_first_hop. e2e: multi-hop nhẹ pass.
- B6: Phiên bản hóa + lọc ngôn ngữ. e2e: 2 phiên bản/DB.
- B7: Eval offline (Recall@k; optional faithfulness bằng provider). Smoke-only (tránh tốn CPU trong CI).
- B8: UI feedback + /api/feedback + log JSONL.

7) ENV khuyến nghị (Windows/CPU)
- RRF_ENABLE=1, RRF_K=60
- REWRITE_N=2, HOP_DEPTH=2, HOP_FANOUT=2, HOP_BUDGET_MS=4000
- LOG_EXPERIMENTS=1 (ghi logs/exp-*.jsonl)
- Vẫn giữ “chế độ nhẹ” khi dev; @heavy chạy khi tăng tài nguyên hoặc dùng OpenAI provider.
- 2025-09-21: Hoàn tất bản web app cơ bản chạy với Ollama, ingest TXT/PDF/DOCX, streaming, top-k.
- 2025-09-21: Thêm bộ file triển khai Cloudflare Tunnel (Docker Compose + native) và hướng dẫn.
- 2025-09-21: Server local hoạt động tại http://127.0.0.1:8000; sẵn sàng chạy tunnel nếu có CF_TUNNEL_TOKEN.
- 2025-09-21: Thiết lập khung test e2e Playwright (globalSetup khởi động Ollama; webServer khởi động FastAPI). Chạy test thành công (5 cases pass, gồm Hybrid + Reranker).
- 2025-09-21: Thêm Desktop shell PyQt6 khung cơ bản (desktop/main.py) + script chạy (scripts/run_desktop.ps1); Desktop shell tự khởi động server nếu chưa chạy và nhúng UI web.
- 2025-09-21: Nâng cấp Desktop shell: hộp thoại cấu hình (URL/Host/Port), Start/Stop server trong app, tự động reconnect; cấu hình lưu ở %USERPROFILE%\\.ollama_rag_desktop.json.
- 2025-09-21: Ổn định gọi Ollama: thêm retry + backoff và timeout cho embeddings/generate (app/ollama_client.py). Biến môi trường: OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT, OLLAMA_MAX_RETRIES, OLLAMA_RETRY_BACKOFF. Toàn bộ e2e tests PASS (6/6).
- 2025-09-21: Thêm Multi-hop Retrieval (engine+API+UI) + fallback single-hop; thêm endpoints /api/multihop_query và /api/stream_multihop_query.
- 2025-09-21: Gắn nhãn @heavy cho Multi-hop & Reranker; thêm script npm run test:e2e:light (bỏ qua @heavy). Hướng dẫn “chế độ nhẹ” bằng biến môi trường (LLM_MODEL=tinyllama, OLLAMA_NUM_THREAD=2, ...).
- 2025-09-21: Thêm Chat Sessions (per-DB), CRUD API, auto-save Q/A trong query/stream; UI quản lý. Test e2e (light) PASS 5/5.
- 2025-09-21: Hoàn thiện RRF Fusion trong hybrid retrieval (B1), cấu hình RRF_ENABLE/RRF_K, expose tham số qua API. E2E (light) PASS.
- 2025-09-21: B5 — Citations [n] trong prompt + UI render footnotes từ metadata; sửa lỗi cú pháp JS (xóa token thừa, loại else trùng) → e2e light PASS 7/7.
- 2025-09-21: Bổ sung khối citations vào index.html và thêm e2e test (mock /api/query) kiểm tra UI citations; sửa thiếu gọi renderCitations ở nhánh non-stream /api/query → e2e light PASS 8/8.
- 2025-09-21: Tinh chỉnh prompt backend (build_prompt) yêu cầu LLM chèn citations [n] khớp với [CTX n]; chạy lại e2e (light) PASS 8/8.
- 2025-09-21: Giảm nhiễu log/telemetry Chroma trong test: tắt anonymized_telemetry (Settings), hạ mức logger chromadb/* xuống CRITICAL; e2e (light) PASS 8/8, log sạch hơn.
- 2025-09-21: Thêm smoke test Cloudflare Tunnel (native + Docker), bổ sung scripts npm và cập nhật deploy/README.md.

## Ghi chú
- Khi thêm tính năng mới, theo rule: chạy test automation (MCP Playwright) và sửa cho đến khi pass.
- Reranker dùng BGE v2 m3 ONNX nếu tải được model; nếu không, fallback cosine embedding từ Ollama embeddings.
- Không commit khóa/token; đặt trong biến môi trường.
