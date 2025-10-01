# Hướng dẫn Web UI (Web UI Guide)

Phần này mô tả giao diện web, các nút điều khiển và phím tắt để sử dụng hiệu quả.

Điều khiển chính
- Provider: Ollama | OpenAI (Embeddings luôn dùng Ollama/local)
- Phương pháp: vector | bm25 | hybrid (+ w BM25)
- Reranker: bật/tắt + Top-N; nâng cao: rr_provider, rr_max_k, rr_batch_size, rr_num_threads
- Rewrite: bật/tắt + n (sinh biến thể truy vấn, hợp nhất RRF trước rerank)
- Multi-hop: bật/tắt + Depth, Fanout, Fanout-1st, Budget(ms)
- Top-K: số lượng ngữ cảnh
- Stream: bật/tắt
- DB: chọn/tạo/xoá DB
- Chat: chọn session, New/Rename/Delete, Export JSON/MD, Delete All

Bảng kết quả
- Answer: câu trả lời từ LLM
- Contexts: các đoạn văn liên quan từ KB
- Citations: chú thích [n] ánh xạ sang nguồn (source/version/language/chunk)

Phím tắt
- Ctrl/Cmd + Enter: gửi truy vấn khi con trỏ ở ô nhập
- Ctrl/Cmd + K: focus ô tìm kiếm
- Escape: xoá nhanh kết quả và citations

Toast & Loading
- Thông báo dạng toast (thành công, cảnh báo, lỗi)
- Overlay loading khi thao tác ingest/upload/lệnh tốn thời gian

Tìm kiếm & Xuất chats
- Tìm trong DB theo nội dung messages
- Xuất hội thoại (chat hiện tại) dưới dạng JSON/Markdown
- Xuất toàn DB (ZIP) gồm citations theo định dạng JSON/CSV/MD

Trạng thái Backend
- Chip "Backend" hiển thị trạng thái /api/health
- Khi backend chưa OK, nút Ingest/Gửi sẽ bị vô hiệu hoá tạm thời
