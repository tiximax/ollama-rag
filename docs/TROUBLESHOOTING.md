# Xử lý sự cố (Troubleshooting)

Các lỗi phổ biến và cách khắc phục.

Kết nối Ollama thất bại (Connection refused)
- Chạy: ollama serve
- Kiểm tra: http://localhost:11434/api/tags
- Đảm bảo OLLAMA_BASE_URL đúng

Thiếu models
- ollama pull nomic-embed-text
- ollama pull llama3.1:8b

OpenAI chưa cấu hình
- Đặt OPENAI_API_KEY vào .env hoặc biến môi trường hệ thống
- Đổi Provider sang OpenAI: POST /api/provider { name: "openai" }

UI không cập nhật
- Hard refresh (Ctrl+F5)

Timeout/Hiệu năng thấp
- Giảm OLLAMA_NUM_THREAD, ORT_INTRA_OP_THREADS, ORT_INTER_OP_THREADS
- Tắt stream khi không cần
- Dùng BM25 cho query ngắn, Hybrid cho bối cảnh hỗn hợp

Ingest không thấy dữ liệu
- Kiểm tra pattern đường dẫn (hỗ trợ thư mục + *.txt/*.pdf/*.docx)
- Kiểm tra quyền đọc file

Lỗi tải lên (413)
- File quá lớn → nén hoặc tách nhỏ
- Giới hạn tuỳ biến bằng MAX_UPLOAD_SIZE_BYTES

Logs/Analytics rỗng
- Bật logs: POST /api/logs/enable { enabled: true }
- Kiểm tra quyền ghi vào data/kb/<DB>/logs/
