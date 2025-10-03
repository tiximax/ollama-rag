# Cài đặt (Installation)

Tài liệu này hướng dẫn thiết lập môi trường và chạy Ollama RAG App trên Windows/macOS/Linux với mức độ chi tiết, ổn định và ít lỗi nhất.

Yêu cầu chung
- Python 3.10+
- Windows/macOS/Linux
- Ollama đã cài và chạy tại http://localhost:11434 hoặc dùng OpenAI API (tuỳ chọn)
- Node.js + npm (tuỳ chọn, chỉ khi chạy e2e bằng Playwright)

Khuyến nghị chung
- Dùng virtualenv để cách ly môi trường Python
- Không commit khoá bí mật; quản lý qua biến môi trường (.env)
- Với máy cấu hình thấp, dùng tinyllama và giảm số luồng để đỡ tải CPU

Windows (PowerShell)
1) Sao chép file cấu hình mẫu
   copy .env.example .env

2) Cài đặt nhanh (khuyến nghị)
   PowerShell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
   - Tuỳ chọn e2e: thêm tham số -WithE2E

   Hoặc cài thủ công:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -U pip
   pip install -r requirements.txt

3) Kéo models Ollama (khi dùng Ollama)
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text

4) Chạy server
   PowerShell -ExecutionPolicy Bypass -File .\start_server.ps1
   Hoặc: py -m uvicorn app.main:app --host 127.0.0.1 --port 8001

5) Mở UI
   http://127.0.0.1:8001

macOS/Linux (bash/zsh)
1) Sao chép cấu hình mẫu
   cp .env.example .env

2) Tạo và kích hoạt venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -r requirements.txt

3) Kéo models Ollama (nếu dùng Ollama)
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text

4) Chạy server
   uvicorn app.main:app --host 127.0.0.1 --port 8001

5) Mở UI
   http://127.0.0.1:8001

Tuỳ chọn: Thiết lập E2E (Playwright)
- npm install
- npm run playwright:install
- Chạy chế độ nhẹ (khuyến nghị khi dev)
  Windows PowerShell:
    $env:LLM_MODEL="tinyllama"; $env:OLLAMA_NUM_THREAD="2"; $env:OLLAMA_NUM_CTX="1024"; $env:OLLAMA_NUM_GPU="0"; $env:ORT_INTRA_OP_THREADS="1"; $env:ORT_INTER_OP_THREADS="1"; $env:UVICORN_RELOAD="0";
    npm run test:e2e:light

Mẹo nâng cao độ ổn định
- Đảm bảo Ollama sẵn sàng: curl http://localhost:11434/api/tags
- Không bật reload khi chạy benchmark/tests
- Giới hạn threads (ONNXRuntime và Ollama) để tránh quá tải CPU
