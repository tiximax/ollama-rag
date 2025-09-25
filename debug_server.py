#!/usr/bin/env python3
"""
🔍 Debug server để catch mọi exception có thể! 
Detective mode ON! 🕵️‍♂️
"""

import uvicorn
import traceback
import sys
import threading
import time
from contextlib import contextmanager

# Monkey patch để catch hidden exceptions
original_excepthook = sys.excepthook

def debug_excepthook(exc_type, exc_value, exc_traceback):
    """Catch tất cả uncaught exceptions"""
    print(f"\n🚨 UNCAUGHT EXCEPTION DETECTED! 🚨")
    print(f"Type: {exc_type}")
    print(f"Value: {exc_value}")
    print(f"Traceback:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("=" * 50)
    
    # Call original handler
    original_excepthook(exc_type, exc_value, exc_traceback)

sys.excepthook = debug_excepthook

@contextmanager
def debug_context(name):
    """Context manager để track execution"""
    try:
        print(f"🟢 ENTERING: {name}")
        yield
        print(f"✅ COMPLETED: {name}")
    except Exception as e:
        print(f"🔴 ERROR in {name}: {e}")
        traceback.print_exc()
        raise

def test_imports():
    """Test tất cả imports trước"""
    print("🧪 Testing imports...")
    
    with debug_context("FastAPI import"):
        from fastapi import FastAPI
        
    with debug_context("App imports"):
        from app.rag_engine import RagEngine
        from app.chat_store import ChatStore  
        from app.feedback_store import FeedbackStore
        from app.exp_logger import ExperimentLogger
        
    print("✅ All imports OK!")

def create_debug_app():
    """Tạo app với debug info chi tiết"""
    print("🏗️ Creating FastAPI app...")
    
    with debug_context("FastAPI creation"):
        from fastapi import FastAPI
        app = FastAPI(title="Debug Ollama RAG")
        
    with debug_context("Basic routes"):
        @app.get("/")
        def root():
            return {"status": "alive", "message": "Debug server running!"}
            
        @app.get("/health")
        def health():
            import os
            return {"status": "healthy", "pid": os.getpid()}
    
    print("✅ App created successfully!")
    return app

def run_debug_server():
    """Chạy server với full debug"""
    print("=" * 60)
    print("🔍 DEBUG SERVER MODE - DETECTIVE EDITION 🔍")
    print("=" * 60)
    
    try:
        test_imports()
        app = create_debug_app()
        
        print("🚀 Starting uvicorn server...")
        print("📊 Server config:")
        print("   - Host: 127.0.0.1")
        print("   - Port: 8006")  
        print("   - Reload: False")
        print("   - Debug: True")
        
        # Keep alive thread
        def keep_alive():
            """Thread để keep server alive"""
            print("💓 Keep-alive thread started")
            for i in range(60):  # 60 seconds
                time.sleep(1)
                if i % 10 == 0:
                    print(f"💗 Heartbeat {i//10 + 1}/6")
            print("💤 Keep-alive thread ending")
        
        threading.Thread(target=keep_alive, daemon=True).start()
        
        uvicorn.run(
            app,
            host="127.0.0.1", 
            port=8006,
            log_level="debug",
            reload=False
        )
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import os
    run_debug_server()