# Đóng góp (Contributing)

Chào mừng đóng góp! Vui lòng đọc kỹ để giữ chất lượng và ổn định.

Thiết lập môi trường dev
- python -m venv .venv && activate
- pip install -r requirements.txt
- (tuỳ chọn) npm install && npm run playwright:install

Chạy kiểm tra
- Unit: py -m unittest -q
- E2E (light): npm run test:e2e:light

Lint/Format
- Windows: scripts\lint.ps1, scripts\fmt.ps1

Phong cách code
- Python: PEP8, type hints, docstrings
- Không lạm dụng global state, tránh side-effects
- Xử lý lỗi toàn diện (try/except rõ ràng)

PR Checklist
- [ ] Mô tả thay đổi rõ ràng
- [ ] Có test phù hợp (unit/e2e)
- [ ] Cập nhật docs nếu thay đổi API/CLI/ENV
- [ ] Pass CI

Bảo mật
- Không đưa khoá vào code/commit
- Nếu cần secret trong ví dụ, dùng {{SECRET_NAME}}
