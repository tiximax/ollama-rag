# 📝 TASKS CHI TIẾT - OLLAMA RAG IMPROVEMENTS

**Generated:** 2025-10-01  
**Status Tracking:** [ ] TODO | [🔄] IN PROGRESS | [✅] DONE

---

## 🚨 PHASE 1: CRITICAL FIXES (Week 1-2)

### Task 1.1: Type Safety & Input Validation
**Priority:** 🔥🔥🔥 CRITICAL  
**Estimated Time:** 2-3 days  
**Difficulty:** Medium

#### Subtasks:
- [ ] **1.1.1** Tạo validators module
  ```bash
  # Tạo file mới
  touch app/validators.py
  ```
  
- [ ] **1.1.2** Implement path validation
  ```python
  # app/validators.py
  from pathlib import Path
  from typing import List
  
  def validate_safe_path(path: str, base_dir: Path = Path.cwd()) -> Path:
      """Validate path không escape khỏi base_dir."""
      resolved = Path(path).resolve()
      if not str(resolved).startswith(str(base_dir)):
          raise ValueError(f"Path traversal detected: {path}")
      return resolved
  ```

- [ ] **1.1.3** Add Pydantic validators cho IngestRequest
  ```python
  # app/main.py
  from pydantic import field_validator
  
  class IngestRequest(BaseModel):
      paths: List[str] = ["data/docs"]
      db: Optional[str] = None
      version: Optional[str] = None
      
      @field_validator('paths')
      def validate_paths(cls, v):
          from .validators import validate_safe_path
          for p in v:
              validate_safe_path(p)
          return v
      
      @field_validator('db')
      def validate_db_name(cls, v):
          if v and not RagEngine._valid_db_name(v):
              raise ValueError(f"Invalid DB name: {v}")
          return v
  ```

- [ ] **1.1.4** Add request size limits
  ```python
  # app/main.py (thêm vào top)
  from fastapi.middleware.trustedhost import TrustedHostMiddleware
  from fastapi import Request
  from starlette.middleware.base import BaseHTTPMiddleware
  
  class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
      def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB
          super().__init__(app)
          self.max_size = max_size
      
      async def dispatch(self, request: Request, call_next):
          if request.headers.get('content-length'):
              if int(request.headers['content-length']) > self.max_size:
                  return Response(status_code=413, content="Request too large")
          return await call_next(request)
  
  app.add_middleware(RequestSizeLimitMiddleware)
  ```

- [ ] **1.1.5** Test validation với malicious inputs
  ```python
  # tests/unit/test_validators.py (NEW)
  import pytest
  from app.validators import validate_safe_path
  
  def test_path_traversal_blocked():
      with pytest.raises(ValueError):
          validate_safe_path("../../../etc/passwd")
  ```

**Files Changed:**
- `app/validators.py` (NEW)
- `app/main.py` (MODIFY)
- `tests/unit/test_validators.py` (NEW)

**Testing:**
```bash
pytest tests/unit/test_validators.py -v
```

---

### Task 1.2: Fix Resource Leaks
**Priority:** 🔥🔥 HIGH  
**Estimated Time:** 1-2 days  
**Difficulty:** Medium

#### Subtasks:
- [ ] **1.2.1** Wrap FAISS SQLite connection
  ```python
  # app/rag_engine.py
  import contextlib
  
  @contextlib.contextmanager
  def _faiss_connection(self):
      """Context manager cho FAISS map connection."""
      conn = None
      try:
          conn = _sqlite3.connect(self._faiss_map_path())
          yield conn
      finally:
          if conn:
              conn.close()
  ```

- [ ] **1.2.2** Update tất cả usages của _faiss_map_conn
  ```python
  # Thay thế:
  # OLD: self._faiss_map_conn = _sqlite3.connect(...)
  # NEW:
  with self._faiss_connection() as conn:
      cur = conn.cursor()
      # ... operations
  ```

- [ ] **1.2.3** Add cleanup method cho RagEngine
  ```python
  # app/rag_engine.py
  def cleanup(self):
      """Cleanup resources."""
      if hasattr(self, '_faiss_map_conn') and self._faiss_map_conn:
          try:
              self._faiss_map_conn.close()
          except:
              pass
      # Clear caches
      self._bm25 = None
      self._filters_cache.clear()
  
  def __del__(self):
      """Destructor."""
      self.cleanup()
  ```

- [ ] **1.2.4** Fix file handles trong chat_store
  ```python
  # app/chat_store.py
  # Ensure all file opens use context manager
  # OLD: f = open(path, 'w')
  # NEW: with open(path, 'w') as f:
  ```

- [ ] **1.2.5** Memory profiling test
  ```bash
  pip install memory_profiler
  python -m memory_profiler app/main.py
  ```

**Files Changed:**
- `app/rag_engine.py` (MODIFY)
- `app/chat_store.py` (MODIFY)

**Testing:**
```bash
# Run memory profiler trước và sau fix
python -m memory_profiler scripts/memory_test.py
```

---

### Task 1.3: Concurrency Safety
**Priority:** 🔥🔥 HIGH  
**Estimated Time:** 2 days  
**Difficulty:** Medium-Hard

#### Subtasks:
- [ ] **1.3.1** Install filelock dependency
  ```bash
  pip install filelock
  # Add to requirements.txt
  echo "filelock>=3.12" >> requirements.txt
  ```

- [ ] **1.3.2** Add threading lock cho BM25
  ```python
  # app/rag_engine.py
  import threading
  
  class RagEngine:
      def __init__(self, ...):
          # ... existing code
          self._bm25_lock = threading.RLock()  # Reentrant lock
      
      def _build_bm25_from_collection(self):
          with self._bm25_lock:
              # ... existing logic
      
      def retrieve_bm25(self, ...):
          if not self._ensure_bm25():
              return {"documents": [], "metadatas": [], "scores": []}
          
          with self._bm25_lock:
              # ... existing logic
  ```

- [ ] **1.3.3** Add file locking cho chat operations
  ```python
  # app/chat_store.py
  from filelock import FileLock
  
  class ChatStore:
      def _lock_path(self, db: str) -> str:
          return os.path.join(self._db_dir(db), ".lock")
      
      def append_pair(self, db: str, chat_id: str, ...):
          lock_file = self._lock_path(db)
          with FileLock(lock_file, timeout=5):
              # ... existing write logic
      
      def delete(self, db: str, chat_id: str):
          lock_file = self._lock_path(db)
          with FileLock(lock_file, timeout=5):
              # ... existing delete logic
  ```

- [ ] **1.3.4** Add lock cho filters cache
  ```python
  # app/rag_engine.py
  def __init__(self, ...):
      # ...
      self._filters_lock = threading.Lock()
  
  def get_filters(self):
      with self._filters_lock:
          # ... existing logic
  ```

- [ ] **1.3.5** Test concurrent operations
  ```javascript
  // tests/e2e/concurrency.spec.js (NEW)
  test('concurrent queries should not corrupt data', async ({ page }) => {
      // Gửi 10 requests đồng thời
      const promises = Array(10).fill(0).map(() => 
          fetch('http://localhost:8000/api/query', {
              method: 'POST',
              body: JSON.stringify({query: 'test', k: 5})
          })
      );
      const results = await Promise.all(promises);
      // Assert tất cả succeed
      results.forEach(r => expect(r.ok).toBeTruthy());
  });
  ```

**Files Changed:**
- `requirements.txt` (ADD filelock)
- `app/rag_engine.py` (MODIFY)
- `app/chat_store.py` (MODIFY)
- `tests/e2e/concurrency.spec.js` (NEW)

**Testing:**
```bash
npm run test:e2e -- concurrency.spec.js
```

---

## ⚡ PHASE 2: IMPORTANT IMPROVEMENTS (Week 3-4)

### Task 2.1: Error Handling Standards
**Priority:** 🟡 MEDIUM  
**Estimated Time:** 3 days  
**Difficulty:** Medium

#### Subtasks:
- [ ] **2.1.1** Tạo custom exceptions
  ```python
  # app/exceptions.py (NEW)
  """Custom exceptions cho Ollama RAG."""
  
  class OllamaRAGException(Exception):
      """Base exception."""
      pass
  
  class IngestError(OllamaRAGException):
      """Lỗi khi ingest tài liệu."""
      pass
  
  class RetrievalError(OllamaRAGException):
      """Lỗi khi retrieve."""
      pass
  
  class GenerationError(OllamaRAGException):
      """Lỗi khi generate answer."""
      pass
  
  class ConfigError(OllamaRAGException):
      """Lỗi config."""
      pass
  ```

- [ ] **2.1.2** Replace generic Exception catches
  ```python
  # app/rag_engine.py - Example refactor
  # OLD:
  try:
      text = extract_text_from_pdf(path)
  except Exception:
      return ""
  
  # NEW:
  from .exceptions import IngestError
  try:
      from pypdf import PdfReader
      text = extract_text_from_pdf(path)
  except ImportError as e:
      logger.error("PyPDF not installed", exc_info=e)
      raise IngestError("PDF support not available") from e
  except Exception as e:
      logger.error(f"PDF extraction failed: {path}", exc_info=e)
      return ""  # Graceful degradation cho extract
  ```

- [ ] **2.1.3** Add structured logging
  ```bash
  pip install structlog
  echo "structlog>=23.1" >> requirements.txt
  ```
  
  ```python
  # app/logging_config.py (NEW)
  import structlog
  
  def setup_logging():
      structlog.configure(
          processors=[
              structlog.stdlib.add_log_level,
              structlog.stdlib.add_logger_name,
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.processors.StackInfoRenderer(),
              structlog.processors.format_exc_info,
              structlog.processors.JSONRenderer()
          ],
          wrapper_class=structlog.stdlib.BoundLogger,
          context_class=dict,
          logger_factory=structlog.stdlib.LoggerFactory(),
      )
  
  logger = structlog.get_logger()
  ```

- [ ] **2.1.4** Standardize error responses
  ```python
  # app/main.py
  from fastapi.responses import JSONResponse
  
  @app.exception_handler(OllamaRAGException)
  async def rag_exception_handler(request, exc):
      return JSONResponse(
          status_code=500,
          content={
              "error": exc.__class__.__name__,
              "message": str(exc),
              "detail": getattr(exc, 'detail', None)
          }
      )
  ```

- [ ] **2.1.5** Update all modules
  - Scan toàn bộ `app/*.py`
  - Replace `except Exception` phù hợp
  - Add logging statements

**Files Changed:**
- `app/exceptions.py` (NEW)
- `app/logging_config.py` (NEW)
- `app/main.py` (MODIFY)
- `app/rag_engine.py` (MODIFY - multiple spots)
- `app/chat_store.py` (MODIFY)
- `requirements.txt` (ADD structlog)

---

### Task 2.2: Performance Optimization
**Priority:** 🟡 MEDIUM  
**Estimated Time:** 3 days  
**Difficulty:** Medium

#### Subtasks:
- [ ] **2.2.1** Cache filters với TTL
  ```python
  # app/rag_engine.py
  from datetime import datetime, timedelta
  
  def __init__(self, ...):
      # ...
      self._filters_cache_data = None
      self._filters_cache_time = None
      self._filters_cache_ttl = 300  # 5 mins
  
  def get_filters(self):
      now = datetime.now()
      if (self._filters_cache_data and self._filters_cache_time and 
          (now - self._filters_cache_time).total_seconds() < self._filters_cache_ttl):
          return self._filters_cache_data
      
      # Rebuild...
      with self._filters_lock:
          result = self._build_filters()
          self._filters_cache_data = result
          self._filters_cache_time = now
          return result
  ```

- [ ] **2.2.2** Lazy BM25 loading
  ```python
  # Already có _ensure_bm25(), chỉ cần verify
  # Không build BM25 trong __init__
  ```

- [ ] **2.2.3** Optimize reranker batch size
  ```python
  # app/reranker.py
  # Tăng default batch size
  DEFAULT_BATCH_SIZE = 32  # Was 16
  ```

- [ ] **2.2.4** Add pagination support
  ```python
  # app/main.py - NEW endpoint
  @app.get("/api/chats/paginated")
  def api_chats_paginated(
      db: Optional[str] = None, 
      page: int = 0, 
      size: int = 20
  ):
      # Implement pagination logic
      pass
  ```

- [ ] **2.2.5** Benchmark tests
  ```bash
  pip install pytest-benchmark
  # Create tests/perf/test_benchmark.py
  ```

**Testing:**
```bash
pytest tests/perf/ --benchmark-only
```

---

### Task 2.3: Security Hardening
**Priority:** 🟡 MEDIUM-HIGH  
**Estimated Time:** 2 days  
**Difficulty:** Medium

#### Subtasks:
- [ ] **2.3.1** Add rate limiting
  ```bash
  pip install slowapi
  echo "slowapi>=0.1.8" >> requirements.txt
  ```
  
  ```python
  # app/main.py
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded
  
  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
  
  @app.post("/api/query")
  @limiter.limit("30/minute")  # 30 queries per minute
  async def api_query(req: QueryRequest, request: Request):
      # ... existing logic
  ```

- [ ] **2.3.2** Sanitize secrets trong logs
  ```python
  # app/logging_config.py
  def sanitize_log(event_dict):
      """Remove sensitive data from logs."""
      sensitive_keys = ['api_key', 'password', 'token', 'secret']
      for key in sensitive_keys:
          if key in event_dict:
              event_dict[key] = '***REDACTED***'
      return event_dict
  
  # Add to processors
  structlog.processors.add_log_level,
  sanitize_log,  # <- Add this
  ```

- [ ] **2.3.3** Content-type validation cho uploads
  ```bash
  pip install python-magic
  ```
  
  ```python
  # app/main.py - trong api_upload
  import magic
  
  async def api_upload(...):
      for f in files:
          data = await f.read()
          mime = magic.from_buffer(data, mime=True)
          
          # Validate MIME type
          allowed_mimes = ['text/plain', 'application/pdf', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
          if mime not in allowed_mimes:
              continue  # Skip invalid files
  ```

- [ ] **2.3.4** CORS configuration
  ```python
  # app/main.py
  from fastapi.middleware.cors import CORSMiddleware
  
  app.add_middleware(
      CORSMiddleware,
      allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:8000").split(","),
      allow_credentials=True,
      allow_methods=["GET", "POST", "PATCH", "DELETE"],
      allow_headers=["*"],
  )
  ```

- [ ] **2.3.5** Security headers
  ```python
  # app/main.py
  from starlette.middleware.base import BaseHTTPMiddleware
  
  class SecurityHeadersMiddleware(BaseHTTPMiddleware):
      async def dispatch(self, request, call_next):
          response = await call_next(request)
          response.headers['X-Content-Type-Options'] = 'nosniff'
          response.headers['X-Frame-Options'] = 'DENY'
          response.headers['X-XSS-Protection'] = '1; mode=block'
          response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
          return response
  
  app.add_middleware(SecurityHeadersMiddleware)
  ```

- [ ] **2.3.6** Run security scan
  ```bash
  pip install bandit safety
  bandit -r app/
  safety check
  ```

**Files Changed:**
- `requirements.txt` (ADD slowapi, python-magic, bandit, safety)
- `app/main.py` (MODIFY - middlewares, rate limits)
- `app/logging_config.py` (MODIFY - sanitization)

---

## 🎨 PHASE 3: CODE QUALITY (Week 5)

### Task 3.1: Refactoring
**Priority:** 🟢 LOW-MEDIUM  
**Estimated Time:** 4 days

#### Subtasks:
- [ ] **3.1.1** Extract constants
- [ ] **3.1.2** Break large functions
- [ ] **3.1.3** Add docstrings
- [ ] **3.1.4** Type hints với mypy

### ✅ Task 3.2: Unit Tests
**Priority:** 🟢 MEDIUM  
**Estimated Time:** 4 days  
**Status:** DONE ✅  
**Completed:** 2025-01-XX

#### Subtasks:
- [x] **3.2.1** Setup pytest-cov
- [x] **3.2.2** Write unit tests cho core modules
  - Created `tests/unit/test_exceptions.py` (22 tests)
  - Created `tests/unit/test_constants.py` (22 tests)  
  - Existing `tests/unit/test_validators.py` (28 tests)
- [x] **3.2.3** Coverage report generated
  - **Total unit tests:** 72 tests, all passing ✅
  - **Coverage for tested modules:**
    - `app/constants.py`: 100%
    - `app/exceptions.py`: 100%
    - `app/validators.py`: 94%

**Notes:**
- Unit tests cover all utility/helper modules completely
- Main application modules (main.py, rag_engine.py) require integration tests
- Coverage report generated with `pytest-cov`
- All tests pass successfully

### ✅ Task 3.3: UI/UX Polish
**Priority:** 🟢 LOW-MEDIUM  
**Estimated Time:** 2 days  
**Status:** DONE ✅  
**Completed:** 2025-01-XX

#### Subtasks:
- [x] **3.3.1** Loading spinners
  - Added inline spinners for buttons during operations
  - Created full-screen loading overlay with text
  - Integrated into all long-running operations (ingest, upload, query)
- [x] **3.3.2** Toast notifications
  - Created toast notification system (success, error, warning, info)
  - Replaced all alert() calls with toast notifications
  - Auto-dismiss after 4 seconds with manual close option
  - Smooth slide-in/out animations
- [x] **3.3.3** Responsive improvements
  - Added media queries for mobile (< 768px) and small mobile (< 480px)
  - Made query input and buttons stack vertically on mobile
  - Improved context grid layout for smaller screens
  - Toast notifications adapt to screen width
- [x] **3.3.4** Keyboard shortcuts
  - **Ctrl/Cmd + Enter**: Submit query from input
  - **Escape**: Clear results and contexts
  - **Ctrl/Cmd + K**: Focus search input

**Notes:**
- All CSS animations use hardware acceleration
- Focus states improved with visible borders
- Button hover/active states added for better UX
- Loading states disable buttons to prevent double-submission

---

## 🚀 QUICK WIN TASKS (Có thể làm ngay)

### Quick Win 1: Add Health Check Endpoint
**Time:** 30 mins
```python
# app/main.py
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "db": engine.db_name,
        "ollama": engine.ollama.health_check(),  # Add method
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Quick Win 2: Pin All Dependencies
**Time:** 15 mins
```bash
pip freeze > requirements-lock.txt
```

### Quick Win 3: Add .gitignore Improvements
**Time:** 10 mins
```
# Add to .gitignore
*.pyc
__pycache__/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.env
*.log
```

### Quick Win 4: Add Pre-commit Hooks
**Time:** 1 hour
```bash
pip install pre-commit
# Create .pre-commit-config.yaml
pre-commit install
```

---

## 📊 PROGRESS TRACKING

Use this format to track:
```
[✅] 1.1.1 - Tạo validators module (2025-10-02)
[🔄] 1.1.2 - Implement path validation (Started 2025-10-02)
[ ] 1.1.3 - Add Pydantic validators
```

---

**Báo cáo này cung cấp roadmap chi tiết để cải thiện Ollama RAG từng bước một! 🚀💎**
