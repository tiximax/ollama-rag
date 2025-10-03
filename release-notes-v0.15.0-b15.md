# B15 — Upload & Ingest (v0.15.0-b15)

Ngày phát hành: 2025-09-23
Tag: v0.15.0-b15

Nội dung chính:
- Backend: thêm /api/upload (multipart/form-data) nhận nhiều file (.txt/.pdf/.docx), lưu vào data/docs/uploads và gọi ingest_paths.
- UI: bổ sung input multiple + nút "Upload & Ingest"; sau khi ingest xong, refresh Filters (languages/versions).
- Dependencies: thêm python-multipart (bắt buộc cho FastAPI khi xử lý multipart uploads).
- Tests: ổn định tests/e2e/upload_ingest.spec.js
  - Loại bỏ cú pháp TypeScript 'as any' trong file .js
  - Dùng mảng cho setInputFiles và assert input files > 0
  - Target #btn-upload để tránh strict-mode ambiguity
  - Chờ POST /api/upload và assert payload (data.saved.length > 0)
- Docs: cập nhật agent.md với tiến trình B15.

Ghi chú:
- Đã đảm bảo server chạy trong .venv có python-multipart.
- Test e2e upload/ingest PASS trên môi trường Windows + Playwright.
