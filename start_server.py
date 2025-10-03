#!/usr/bin/env python3
"""
🚀 Script khởi động server siêu ổn định như kim cương! 💎
Không sợ crash, không sợ reload conflict!
"""

import os
import sys

import uvicorn


def start_production_server():
    """Khởi động server production mode - ổn định tuyệt đối! 🏔️"""
    print("🚀 Khởi động Ollama RAG Server (Production Mode)...")
    print("💎 Mode: Ổn định như kim cương!")
    print("🔥 No reload, no crash, pure performance!")

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=False,  # Không dùng reload để tránh conflict
        log_level="info",
        access_log=True,
    )


def start_development_server():
    """Khởi động server development mode - có hot reload! 🔄"""
    print("🚀 Khởi động Ollama RAG Server (Development Mode)...")
    print("🔄 Mode: Hot reload enabled!")
    print("⚡ Changes sẽ auto restart server!")

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=["app"],  # Chỉ watch thư mục app
        reload_excludes=["*.pyc", "__pycache__", "*.log"],
        log_level="info",
    )


if __name__ == "__main__":
    print("=" * 60)
    print("🛠️  OLLAMA RAG SERVER LAUNCHER 🛠️")
    print("=" * 60)

    # Kiểm tra environment
    mode = os.getenv("MODE", "prod").lower()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    if mode in ["dev", "development"]:
        start_development_server()
    else:
        start_production_server()
