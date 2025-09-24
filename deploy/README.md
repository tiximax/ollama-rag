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

Healthcheck và non-root user
- Dockerfile chạy dưới user không phải root (appuser) để tăng an toàn.
- docker-compose có healthcheck cho rag2app: kiểm tra HTTP 127.0.0.1:8000 trong container bằng Python stdlib.

Smoke test Docker (không cần Tunnel)
- PowerShell: scripts/smoke/app_smoke.ps1
  - Build image từ deploy/docker/Dockerfile
  - Chạy container, đợi / trả 200, rồi dọn container

Cloudflare Access (khuyến nghị trước UI)
- Dùng Cloudflare Zero Trust Access để bảo vệ domain Tunnel trước khi vào UI 8000.
- Bước cơ bản:
  1) Tạo/đăng nhập Zero Trust; bật Access.
  2) Tạo Application → "Self-hosted" trỏ tới hostname của Tunnel (route đó).
  3) Thiết lập Policy (e.g., email domain, One-time PIN, SSO SAML/OIDC).
  4) Áp policy vào route 8000; kiểm tra truy cập yêu cầu xác thực.
- Lưu ý: Không public cổng 11434 (Ollama). Chỉ expose 8000 (FastAPI UI/API).

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
- Header đầu stream có JSON đánh dấu contexts & metadatas (dạng [[CTXJSON]]{json}\n), UI sẽ render "Citations panel" dựa trên metadatas + các marker [n] trong câu trả lời.

Tính năng nâng cao (không cần cấu hình riêng cho Tunnel)
- Citations [n]: model chèn [n] theo [CTX n]; UI hiển thị footnotes nguồn/chunk. Không yêu cầu cấu hình Cloudflare đặc biệt.
- Query Rewrite: bật/tắt bằng rewrite_enable và rewrite_n trong body /api/query hoặc /api/stream_query; mặc định tắt để tiết kiệm tài nguyên.
- Multi-hop nâng cao: /api/multihop_query và /api/stream_multihop_query hỗ trợ fanout_first_hop và budget_ms để kiểm soát chi phí; không cần thay đổi cấu hình Tunnel.

Ví dụ (curl, minh hoạ):
```
# Rewrite
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Bitsness là gì?",
    "method": "hybrid",
    "k": 5,
    "rewrite_enable": true,
    "rewrite_n": 2
  }'

# Multi-hop advanced
curl -X POST http://127.0.0.1:8000/api/multihop_query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Giải thích A liên quan B",
    "method": "hybrid",
    "k": 5,
    "depth": 2,
    "fanout": 2,
    "fanout_first_hop": 1,
    "budget_ms": 200
  }'
```

Upload lớn
- Cloudflare có giới hạn kích thước HTTP body; khuyến nghị ingest theo đường dẫn local hoặc crawl URL thay vì upload file cực lớn qua Internet.
