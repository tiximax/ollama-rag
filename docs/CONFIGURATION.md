# Cấu hình (Configuration)

Tài liệu này mô tả chi tiết các biến môi trường, tuỳ chọn cấu hình, và tinh chỉnh hiệu năng.

Tệp .env
- Tạo từ .env.example và sửa theo nhu cầu

Biến môi trường chính
- PROVIDER=ollama|openai (mặc định ollama)
- OLLAMA_BASE_URL=http://localhost:11434
- LLM_MODEL=llama3.1:8b
- EMBED_MODEL=nomic-embed-text
- CHUNK_SIZE=800, CHUNK_OVERLAP=120
- OLLAMA_CONNECT_TIMEOUT=5, OLLAMA_READ_TIMEOUT=180, OLLAMA_MAX_RETRIES=3, OLLAMA_RETRY_BACKOFF=0.6
- OLLAMA_NUM_THREAD, OLLAMA_NUM_CTX, OLLAMA_NUM_GPU (tinh chỉnh hiệu năng)
- OPENAI_BASE_URL=https://api.openai.com/v1, OPENAI_MODEL=gpt-4o-mini, OPENAI_API_KEY={{OPENAI_API_KEY}}
- PERSIST_DIR (ví dụ data/chroma) hoặc PERSIST_ROOT=data/kb + DB_NAME=default
- ORT_INTRA_OP_THREADS, ORT_INTER_OP_THREADS (giới hạn luồng ONNXRuntime)
- VECTOR_BACKEND=chroma|faiss (mặc định chroma). Dùng faiss: pip install faiss-cpu
- GEN_CACHE_ENABLE=1, GEN_CACHE_TTL=86400 (bộ nhớ đệm trả lời để giảm chi phí)
- RRF_ENABLE=1, RRF_K=60 (thiết lập Reciprocal Rank Fusion)

CORS
- CORS_ORIGINS: danh sách domain, ngăn cách bằng dấu phẩy (mặc định cho phép localhost)

Giới hạn tải lên
- MAX_UPLOAD_SIZE_BYTES: mặc định 10MB (đặt trong constants)

Logging/Analytics
- Logs JSONL nằm tại data/kb/<DB>/logs/
- Có thể bật/tắt ghi logs qua API /api/logs/enable

An toàn bí mật
- Không echo/log giá trị khoá
- Lưu khoá dưới dạng biến môi trường hoặc secret manager ngoài
