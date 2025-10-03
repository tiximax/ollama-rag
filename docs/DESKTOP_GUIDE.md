# Hướng dẫn Desktop (Desktop Guide)

Chạy ứng dụng Desktop ở chế độ phát triển hoặc đóng gói thành bản phân phối một thư mục.

Chạy Dev
- PowerShell -ExecutionPolicy Bypass -File .\scripts\run_desktop.ps1

Build gói Desktop (one-folder, kèm server nhúng)
- PowerShell -ExecutionPolicy Bypass -File .\scripts\build_desktop.ps1
- File chạy sau build: .\dist\OllamaRAGDesktop\OllamaRAGDesktop.exe

Ghi chú
- Khi build, đảm bảo Python runtime và dependencies đã được cài
- Không hardcode đường dẫn; dùng path tương đối để đảm bảo hoạt động cross-machine
- Kiểm tra lại quyền truy cập network cục bộ (127.0.0.1)
