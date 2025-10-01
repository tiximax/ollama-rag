# Quy trình phát hành (Release Process)

Tài liệu mô tả cách phát hành phiên bản mới ổn định.

Phiên bản & Changelog
- Tuân thủ SemVer khi có thể
- Cập nhật CHANGELOG.md với mục Added/Changed/Fixed/Removed

Chuẩn bị
- Chạy lint/format: scripts/lint.ps1, scripts/fmt.ps1
- Chạy unit + e2e (light): npm run test:e2e:light
- Cập nhật docs nếu có thay đổi API/flags

Tạo Release
- Tag git: vX.Y.Z
- Tạo release notes (tham khảo release-notes-*.md)
- Đẩy tag và branch lên origin

Sau phát hành
- Mở issue cho các cải tiến/bug phát hiện trong quá trình triển khai
- Cập nhật ROADMAP nếu cần
