# Cloud deployment via Cloudflare Tunnel (Docker or native cloudflared)

Có 2 cách chạy:

A) Docker Compose (khuyến nghị)
- rag2app (FastAPI) chạy cổng 8000 trong container
- cloudflared là container chạy Tunnel bằng Token
- Ollama vẫn chạy ở máy local (Windows) hoặc container khác

B) cloudflared chạy trực tiếp trên Windows (không cần Docker cho cloudflared)
- Tunnel trỏ domain → http://localhost:8000

Yêu cầu chung
- Đã cài Ollama và kéo model cần thiết
- App đã chạy tốt local
- Có domain trên Cloudflare và tạo Tunnel (Zero Trust)

Bảo mật
- KHÔNG public 11434 (Ollama). Cloudflare Tunnel chỉ trỏ vào cổng 8000 (FastAPI UI/API).
- Nên bật Cloudflare Access (SAML/OTP) trước UI.

---

A) Docker Compose

1) Tạo biến môi trường cho Tunnel Token (KHÔNG commit vào repo)
- PowerShell (Windows):
  $env:CF_TUNNEL_TOKEN="{{CF_TUNNEL_TOKEN}}"

2) Build & up
- Chạy:
  docker compose -f deploy/docker/docker-compose.yml build
  docker compose -f deploy/docker/docker-compose.yml up -d

3) Kiểm tra
- Mở https://<domain-tunnel-của-bạn> → UI hiển thị

4) Dừng
- docker compose -f deploy/docker/docker-compose.yml down

---

B) cloudflared native trên Windows

Smoke test (Windows)
- Native:
  - npm run smoke:tunnel:native
  - Kiểm tra cloudflared binary, phiên bản, và file config mặc định
- Docker Compose:
  - npm run smoke:tunnel:docker
  - Kiểm tra docker compose, biến CF_TUNNEL_TOKEN (không in giá trị), và validate file compose

1) Cài cloudflared và đăng nhập:
- winget install Cloudflare.cloudflared
- cloudflared tunnel login  # mở trình duyệt xác thực

2) Tạo tunnel và lấy TUNNEL_ID + file credentials
- cloudflared tunnel create rag2app

3) Tạo file cấu hình (xem config.yml.example) và chạy:
- cloudflared tunnel run <TUNNEL_ID>

Hoặc dùng script PowerShell trong thư mục này (start-local.ps1).

---

Lưu ý khi dùng Docker + Ollama local
- App trong container gọi Ollama qua http://host.docker.internal:11434
- Bản Windows và Docker Desktop hỗ trợ host.docker.internal mặc định.

Streaming/SSE
- Endpoint /api/stream_query dùng chunked responses; Cloudflare Tunnel hỗ trợ.

Upload lớn
- Cloudflare có giới hạn kích thước HTTP body; khuyến nghị ingest theo đường dẫn local hoặc crawl URL thay vì upload file cực lớn qua Internet.
