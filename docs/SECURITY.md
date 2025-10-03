# Bảo mật (Security)

Chính sách và khuyến nghị bảo mật cho Ollama RAG App.

Nguyên tắc chung
- Không lưu trữ khoá bí mật trong code hoặc repo
- Dùng biến môi trường .env hoặc secret manager bên ngoài
- Không echo/log giá trị khoá (ví dụ OPENAI_API_KEY)

Headers bảo mật
- X-Content-Type-Options=nosniff
- X-Frame-Options=DENY
- X-XSS-Protection=1; mode=block
- Strict-Transport-Security=max-age=31536000; includeSubDomains

Rate limiting
- SlowAPI hạn chế tần suất các route tốn tài nguyên (/api/query, /api/upload, /api/ingest)

CORS
- Chỉ bật nguồn tin cậy qua CORS_ORIGINS khi triển khai

Xử lý input và upload
- Giới hạn kích thước upload (mặc định 10MB)
- Chỉ cho phép đuôi .txt/.pdf/.docx
- Kiểm tra path an toàn để tránh path traversal

Lộ trình lộ thông tin
- Xoá header Server khỏi response
- Trả lỗi với thông tin tối thiểu, định dạng thống nhất

Khuyến nghị bổ sung (tuỳ chọn)
- Chạy sau reverse proxy có TLS (Nginx, Caddy)
- Bật xác thực (basic/bearer) nếu public
- Bật logging bảo mật có kiểm soát và redaction
