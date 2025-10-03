import json
import os
import signal
import subprocess
import sys
import threading
import time

import requests
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QToolBar,
)

SERVER_URL = os.getenv("APP_URL", "http://127.0.0.1:8000")
HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", "8000"))
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".ollama_rag_desktop.json")


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


def start_server(host: str, port: int) -> subprocess.Popen | None:
    py = find_python_exe()
    env = os.environ.copy()
    cmd = [
        py,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


# -------- Embedded server (for packaged builds) --------
_embed_thread: threading.Thread | None = None
_embed_server_obj = None


def start_server_embedded(host: str, port: int) -> bool:
    """Start uvicorn server in-process in a background thread.
    Used when running as a packaged executable (PyInstaller), where spawning
    "python -m uvicorn" is not available.
    """
    global _embed_thread, _embed_server_obj
    if _embed_thread is not None:
        return True
    try:
        import uvicorn

        # Import lazily to avoid heavy imports before needed
        from app.main import app as _app

        config = uvicorn.Config(_app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        _embed_server_obj = server

        def _run():
            try:
                server.run()
            except Exception:
                pass

        t = threading.Thread(target=_run, name="uvicorn-embedded", daemon=True)
        t.start()
        _embed_thread = t
        # wait briefly to allow startup
        for _ in range(60):
            if is_server_up(f"http://{host}:{port}", timeout_sec=0.3):
                return True
            time.sleep(0.5)
        return False
    except Exception:
        _embed_thread = None
        _embed_server_obj = None
        return False


def stop_server_embedded():
    global _embed_thread, _embed_server_obj
    try:
        if _embed_server_obj is not None:
            # signal the server to exit
            try:
                _embed_server_obj.should_exit = True  # type: ignore[attr-defined]
            except Exception:
                pass
        # give it a moment
        time.sleep(0.5)
    except Exception:
        pass
    _embed_thread = None
    _embed_server_obj = None


def start_server_if_needed(url: str, host: str, port: int) -> subprocess.Popen | None:
    if is_server_up(url):
        return None
    proc = start_server(host, port)
    if wait_server(url, total_timeout=60.0):
        return proc
    try:
        proc.terminate()
    except Exception:
        pass
    return None


def load_config() -> tuple[str, str, int]:
    url = SERVER_URL
    host = HOST
    port = PORT
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
                url = str(data.get("url", url))
                host = str(data.get("host", host))
                port = int(data.get("port", port))
    except Exception:
        pass
    return url, host, port


def save_config(url: str, host: str, port: int) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"url": url, "host": host, "port": port}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class MainWindow(QMainWindow):
    def __init__(
        self,
        server_proc: subprocess.Popen | None,
        url: str,
        host: str,
        port: int,
        embedded: bool = False,
    ):
        super().__init__()
        self.server_proc = server_proc
        self.embedded = embedded
        self.setWindowTitle("Ollama RAG Desktop")
        self.resize(1200, 800)

        self.current_url = url
        self.host = host
        self.port = port

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Menus & toolbar
        self._build_actions()
        self._build_menus()
        self._build_toolbar()

        # Trì hoãn 100ms rồi load URL để chắc chắn server đã sẵn sàng
        QTimer.singleShot(100, self.load_url)

        # Poll server định kỳ để auto-reconnect nếu server rớt rồi lên lại
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_server)
        self.poll_timer.start(2000)

    # ----- UI helpers -----
    def _build_actions(self):
        self.act_back = QAction("Back", self)
        self.act_back.setShortcut("Alt+Left")
        self.act_back.triggered.connect(self.view.back)

        self.act_forward = QAction("Forward", self)
        self.act_forward.setShortcut("Alt+Right")
        self.act_forward.triggered.connect(self.view.forward)

        self.act_reload = QAction("Reload", self)
        self.act_reload.setShortcut("Ctrl+R")
        self.act_reload.triggered.connect(self.view.reload)

        self.act_set_url = QAction("Set URL...", self)
        self.act_set_url.triggered.connect(self.prompt_set_url)

        self.act_exit = QAction("Exit", self)
        self.act_exit.setShortcut("Ctrl+Q")
        self.act_exit.triggered.connect(self.close)

        self.act_start_server = QAction("Start Server", self)
        self.act_start_server.triggered.connect(self.menu_start_server)

        self.act_stop_server = QAction("Stop Server", self)
        self.act_stop_server.triggered.connect(self.menu_stop_server)

        self.act_config = QAction("Configure Server...", self)
        self.act_config.triggered.connect(self.menu_configure)

        self.act_about = QAction("About", self)
        self.act_about.triggered.connect(self.show_about)

    def _build_menus(self):
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        m_file.addAction(self.act_reload)
        m_file.addAction(self.act_set_url)
        m_file.addSeparator()
        m_file.addAction(self.act_start_server)
        m_file.addAction(self.act_stop_server)
        m_file.addAction(self.act_config)
        m_file.addSeparator()
        m_file.addAction(self.act_exit)

        m_view = mb.addMenu("&View")
        m_view.addAction(self.act_back)
        m_view.addAction(self.act_forward)
        m_view.addAction(self.act_reload)

        m_help = mb.addMenu("&Help")
        m_help.addAction(self.act_about)

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        tb.addAction(self.act_back)
        tb.addAction(self.act_forward)
        tb.addAction(self.act_reload)
        self.addToolBar(tb)

    # ----- Behaviors -----
    def load_url(self):
        self.view.setUrl(QUrl(self.current_url))
        self.statusBar().showMessage(f"Loading {self.current_url}...")

    def prompt_set_url(self):
        text, ok = QInputDialog.getText(self, "Set URL", "Enter app URL:", text=self.current_url)
        if ok and text:
            self.current_url = text
            save_config(self.current_url, self.host, self.port)
            self.load_url()

    def show_about(self):
        QMessageBox.information(
            self,
            "About",
            "Ollama RAG Desktop\nPyQt6 + QWebEngineView\n" f"URL: {self.current_url}",
        )

    def poll_server(self):
        if is_server_up(self.current_url, timeout_sec=0.7):
            self.statusBar().showMessage("Server is up", 1500)
            if self.view.url().toString() not in (self.current_url, self.current_url + "/"):
                self.view.setUrl(QUrl(self.current_url))
        else:
            self.statusBar().showMessage("Waiting for server...", 1500)

    def closeEvent(self, event):
        self.stop_server()
        return super().closeEvent(event)

    # ----- Server controls -----
    def stop_server(self):
        if self.embedded:
            try:
                stop_server_embedded()
            except Exception:
                pass
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
            self.server_proc = None

    def menu_start_server(self):
        if self.server_proc is not None:
            QMessageBox.information(
                self, "Server", "Server is already running (started by Desktop)."
            )
            return
        self.server_proc = start_server(self.host, self.port)
        if wait_server(self.current_url, total_timeout=30.0):
            self.statusBar().showMessage("Server started", 1500)
            self.load_url()
        else:
            self.stop_server()
            QMessageBox.warning(self, "Server", "Failed to start server.")

    def menu_stop_server(self):
        if self.server_proc is None:
            QMessageBox.information(self, "Server", "No server process owned by Desktop.")
            return
        self.stop_server()
        self.statusBar().showMessage("Server stopped", 1500)

    def menu_configure(self):
        dlg = SettingsDialog(self.current_url, self.host, self.port, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            url, host, port = dlg.values()
            self.current_url, self.host, self.port = url, host, port
            save_config(self.current_url, self.host, self.port)
            # Hỏi khởi động lại server nếu Desktop đang giữ server
            if self.server_proc is not None:
                self.stop_server()
                self.menu_start_server()
            else:
                # Không giữ server → chỉ reload UI
                self.load_url()


def main():
    # Load config (hoặc ENV mặc định)
    url, host, port = load_config()

    # Khi chạy dạng packaged (PyInstaller), chạy server embedded để tránh phụ thuộc python.exe ngoài
    is_frozen = bool(getattr(sys, "frozen", False))

    server_proc: subprocess.Popen | None = None
    embedded = False
    if is_frozen or os.getenv("DESKTOP_EMBED_SERVER", "0").strip() in ("1", "true", "True"):
        # Try embedded
        if not is_server_up(url):
            ok = start_server_embedded(host, port)
            embedded = ok
    else:
        # Nếu server chưa chạy, khởi động server nền trước
        server_proc = start_server_if_needed(url, host, port)

    app = QApplication(sys.argv)
    win = MainWindow(server_proc, url, host, port, embedded=embedded)
    win.show()
    sys.exit(app.exec())


class SettingsDialog(QDialog):
    def __init__(self, url: str, host: str, port: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Server")
        self.url_edit = QLineEdit(url, self)
        self.host_edit = QLineEdit(host, self)
        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(port))

        form = QFormLayout(self)
        form.addRow("App URL:", self.url_edit)
        form.addRow("Host:", self.host_edit)
        form.addRow("Port:", self.port_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

    def values(self) -> tuple[str, str, int]:
        return (
            self.url_edit.text().strip(),
            self.host_edit.text().strip(),
            int(self.port_spin.value()),
        )


if __name__ == "__main__":
    main()
