# Tài liệu API (API Reference)

Tài liệu này mô tả các endpoints chính. Trừ khi ghi chú khác, tất cả response là JSON; stream endpoints trả về text/plain và bắt đầu bằng header [[CTXJSON]]{json}\n.

Sức khỏe & Thông tin
- GET /health → Thông tin mức "app" (healthy/degraded, db, version)
- GET /api/health → Thông tin chi tiết backend (provider, Ollama/OpenAI, gợi ý khắc phục)
- GET /api/provider → { provider }
- POST /api/provider { name: "ollama" | "openai" } → set provider

Ingest & Upload
- POST /api/ingest
  body: { paths: string[], db?: string, version?: string }
  resp: { status, chunks_indexed, db }
- POST /api/upload (multipart/form-data)
  fields: files[] (.txt|.pdf|.docx), db?, version?
  resp: { status, saved: string[], chunks_indexed, db }

Truy vấn (Single-hop)
- POST /api/query
  body: {
    query: string, k?: number=5, method?: "vector"|"bm25"|"hybrid",
    bm25_weight?: number=0.5,
    rerank_enable?: boolean, rerank_top_n?: number=10,
    rrf_enable?: boolean, rrf_k?: number,
    rewrite_enable?: boolean, rewrite_n?: number=2,
    provider?: "ollama"|"openai",
    chat_id?: string, save_chat?: boolean=true,
    db?: string, languages?: string[], versions?: string[],
    rr_provider?: "auto"|"bge"|"embed", rr_max_k?: number, rr_batch_size?: number, rr_num_threads?: number
  }
  resp: { answer, contexts: string[], metadatas: any[], db }

- POST /api/stream_query
  body: giống /api/query
  stream: dòng đầu là [[CTXJSON]]{ contexts, metadatas, db }\n; sau đó stream tokens trả lời

Truy vấn Multi-hop
- POST /api/multihop_query
  body: như QueryRequest + { depth?: number=2, fanout?: number=2, fanout_first_hop?: number, budget_ms?: number }
  resp: { answer?, contexts, metadatas, db }
- POST /api/stream_multihop_query
  body: như MultiHopQueryRequest
  stream: dòng đầu [[CTXJSON]] rồi tokens trả lời

Chat APIs
- GET /api/chats?db=<db>
- POST /api/chats { db?, name? }
- GET /api/chats/{id}?db=<db>
- PATCH /api/chats/{id}?db=<db> { name }
- DELETE /api/chats/{id}?db=<db>
- DELETE /api/chats?db=<db> (xoá tất cả)
- GET /api/chats/search?q=keyword&db=<db>
- GET /api/chats/{id}/export?format=json|md&db=<db>
- GET /api/chats/export_db?format=json|md|csv&db=<db> → ZIP tổng

Docs (Knowledge Base)
- GET /api/docs?db=<db> → danh sách nguồn { source, chunks }
- DELETE /api/docs { sources: string[], db? } → xoá theo source

Filters
- GET /api/filters?db=<db> → danh sách filters (languages, versions, sources... nếu có)

Offline Evaluation
- POST /api/eval/offline { queries: { query, expected_sources?, expected_substrings?, languages?, versions? }[], ... }
  resp: { db, n, hits, recall_at_k, details[] }

Logs & Analytics
- GET /api/logs/info?db=<db>
- POST /api/logs/enable { db?, enabled: bool }
- GET /api/logs/export?db=<db>&since=...&until=... → JSONL download
- DELETE /api/logs?db=<db>
- GET /api/logs/summary?db=<db>&since=...&until=... → stats tóm tắt
- GET /api/analytics/db?db=<db>
- GET /api/analytics/chat/{chat_id}?db=<db>

Citations Export
- GET /api/citations/chat/{chat_id}?format=json|csv|md&db=<db>&sources=a,b&versions=...&languages=...
- GET /api/citations/db?format=json|csv|md&db=<db>&sources=... → ZIP nhiều file theo chat

Multi-DB
- GET /api/dbs → { current, dbs }
- POST /api/dbs/use { name }
- POST /api/dbs/create { name }
- DELETE /api/dbs/{name }

Chuẩn lỗi
- 400: ValidationError hoặc tham số sai
- 404: Không tìm thấy tài nguyên (chat)
- 409: DB trùng khi create
- 413: Upload quá lớn
- 429: Rate limit
- 500: Lỗi nội bộ (chi tiết trong field detail)

Bảo mật & Rate limit
- Rate limit cho /api/query, /api/ingest, /api/upload (thiết lập trong constants)
- Security headers (X-Frame-Options, X-Content-Type-Options, HSTS) được set tự động
