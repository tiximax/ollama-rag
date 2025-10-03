# Kiến trúc (Architecture)

Tài liệu này mô tả kiến trúc hệ thống, các thành phần chính và luồng dữ liệu của Ollama RAG App.

Tổng quan thành phần
- FastAPI (app/main.py): Cổng HTTP, endpoints REST/stream, CORS, bảo mật headers, rate limit
- RagEngine (app/rag_engine.py): Quản lý tri thức (Chroma/FAISS), retrieve, rerank, generate, multihop, cache
- Stores: ChatStore (lưu hội thoại), FeedbackStore (phản hồi), ExperimentLogger (logs JSONL)
- Clients: OllamaClient, OpenAIClient
- Web UI (web/): index.html, app.js, styles.css

Luồng xử lý Query (non-stream)
1) Client POST /api/query với tham số (method, k, bm25_weight, rerank, rewrite, filters, provider...)
2) RagEngine:
   - retrieve_aggregate hoặc retrieve/retrieve_bm25/retrieve_hybrid
   - optional rerank (BGE ONNX hoặc embedding) → cắt top K
   - build_prompt và gọi generate (Ollama/OpenAI)
3) Server trả về answer + contexts + metadatas + db
4) Tuỳ chọn lưu chat và ghi log (latency, contexts, nguồn)

Luồng xử lý Query (stream)
- /api/stream_query: gửi header [[CTXJSON]]{json}\n trước, sau đó stream tokens
- Nếu có rerank/rewrite sẽ thực hiện trước khi stream
- Lưu chat sớm (trả lời rỗng) để phục vụ analytics

Multihop
- answer_multihop(depth, fanout, budget, fanout_first_hop) trả về contexts/metadatas (skip_answer=True), có fallback sang single-hop
- /api/stream_multihop_query hoạt động tương tự stream_query nhưng khởi tạo contexts từ multihop

Lưu trữ tri thức
- ChromaDB PersistentClient tại data/kb/<DB>
- VECTOR_BACKEND=faiss cho phép truy vấn nhanh bằng FAISS (tuỳ chọn)
- Chunking: CHUNK_SIZE/CHUNK_OVERLAP, lưu metadata (source, chunk, version, language)

Cache sinh (Generation Cache)
- GenCache tại data/kb/<DB>/gen_cache, bật/tắt qua GEN_CACHE_ENABLE, TTL=GEN_CACHE_TTL
- Invalidate khi corpus stamp thay đổi (ingest/delete)

Error handling & Rate limit
- Custom exceptions và handler → JSON lỗi nhất quán
- SlowAPI limiter cho /api/query, /api/upload, /api/ingest
- Security headers và loại bỏ Server header

Bảo trì & Dọn dẹp
- GenCache/BM25/Filters cache được reset khi đổi DB/ingest/delete
- __del__/cleanup xử lý dọn dẹp an toàn
