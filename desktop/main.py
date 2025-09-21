import os
import sys
import subprocess
import time
import signal
from typing import Optional

import requests

from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView


SERVER_URL = os.getenv("APP_URL", "http://127.0.0.1:8000")
HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", "8000"))


def find_python_exe() -> str:
    # Ưu tiên .venv\Scripts\python.exe trên Windows
    venv_py = os.path.join(".venv", "Scripts", "python.exe")
    if os.name == "nt" and os.path.isfile(venv_py):
        return venv_py
    return sys.executable


def is_server_up(url: str, timeout_sec: float = 1.0) -> bool:
    try:
        r = requests.get(url, timeout=timeout_sec)
        return r.status_code < 500
    except Exception:
        return False


def wait_server(url: str, total_timeout: float = 30.0) -> bool:
    start = time.time()
    while time.time() - start < total_timeout:
        if is_server_up(url):
            return True
        time.sleep(0.5)
    return False


def start_server_if_needed() -> Optional[subprocess.Popen]:
    if is_server_up(SERVER_URL):
        return None
    py = find_python_exe()
    env = os.environ.copy()
    # Tùy chọn: giảm sandbox nếu gặp lỗi WebEngine (chủ yếu Linux). Trên Windows thường không cần.
    # env["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    cmd = [
        py,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if wait_server(SERVER_URL, total_timeout=60.0):
        return proc
    # Không khởi động được
    try:
        proc.terminate()
    except Exception:
        pass
    return None


class MainWindow(QMainWindow):
    def __init__(self, server_proc: Optional[subprocess.Popen] = None):
        super().__init__()
        self.server_proc = server_proc
        self.setWindowTitle("Ollama RAG Desktop")
        self.resize(1200, 800)

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        # Trì hoãn 100ms rồi load URL để chắc chắn server đã sẵn sàng
        QTimer.singleShot(100, self.load_url)

    def load_url(self):
        self.view.setUrl(QUrl(SERVER_URL))

    def closeEvent(self, event):
        # Đóng server nếu do Desktop shell khởi tạo
        if self.server_proc is not None:
            try:
                if os.name == "nt":
                    self.server_proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                self.server_proc.terminate()
            except Exception:
                try:
                    self.server_proc.kill()
                except Exception:
                    pass
        return super().closeEvent(event)


def main():
    # Nếu server chưa chạy, khởi động server nền trước
    server_proc = start_server_if_needed()

    app = QApplication(sys.argv)
    win = MainWindow(server_proc)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
