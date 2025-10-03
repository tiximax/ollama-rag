# Triển khai (Deployment)

Tài liệu này mô tả triển khai thông qua Cloudflare Tunnel và Docker Compose.

Cloudflare Tunnel (tuỳ chọn)
- Xem deploy/README.md
- Cấu hình: deploy/cloudflared/config.yml.example
- Chạy local: deploy/cloudflared/start-local.ps1
- Cần CF_TUNNEL_TOKEN (không commit vào repo). Thiết lập thông qua biến môi trường/secret manager.

Docker Compose
- file: deploy/docker/docker-compose.yml
- env mẫu: deploy/docker/.env.example
- Biến quan trọng:
  - CF_TUNNEL_TOKEN
  - PROVIDER, OLLAMA_BASE_URL hoặc OPENAI_API_KEY

Bảo mật khi triển khai
- Giới hạn nguồn CORS qua CORS_ORIGINS
- Đặt reverse proxy với HTTPS (HSTS đã bật trong headers)
- Không log khoá bí mật
- Xem thêm docs/SECURITY.md
