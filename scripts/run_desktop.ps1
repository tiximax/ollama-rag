# Chạy Desktop shell (PyQt6)
$ErrorActionPreference = "Stop"

# Ưu tiên dùng Python của .venv
$venvPy = ".\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
  $python = $venvPy
} else {
  $python = "python"
}

Write-Host "Using Python: $python" -ForegroundColor Yellow

# (Tuỳ chọn) Tắt sandbox nếu gặp lỗi WebEngine (thường cho Linux; Windows đa số không cần)
# $env:QTWEBENGINE_DISABLE_SANDBOX = "1"

# Đặt APP_URL nếu muốn đổi host/port
# $env:APP_URL = "http://127.0.0.1:8000"

Write-Host "Starting Desktop shell..." -ForegroundColor Green
& $python "desktop/main.py"