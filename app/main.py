import json
import os
import time
import uuid
from typing import Any

# ✅ Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()  # Load .env before any other imports that use os.getenv()

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from . import metrics
from .chat_store import ChatStore
from .constants import (
    APP_VERSION,
    DEFAULT_CORS_ORIGINS,
    MAX_UPLOAD_SIZE_BYTES,
    RATE_LIMIT_INGEST,
    RATE_LIMIT_QUERY,
    RATE_LIMIT_UPLOAD,
)
from .cors_utils import parse_cors_origins_safe
from .exceptions import OllamaRAGException, get_http_status_code
from .exp_logger import ExperimentLogger
from .feedback_store import FeedbackStore
from .logging_utils import setup_secure_logging
from .rag_engine import RagEngine
from .semantic_cache import SemanticQueryCache
from .validators import validate_db_name, validate_safe_path, validate_version_string

# ✅ FIX BUG #1: Setup secure logging để tự động mask API keys
setup_secure_logging()

app = FastAPI(
    title="Ollama RAG API",
    version=APP_VERSION,
    description="Production-ready RAG application with Ollama LLM",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ✅ Prometheus metrics instrumentation 📊
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,  # Always enable
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Middleware cho request size limit (10MB)
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = MAX_UPLOAD_SIZE_BYTES):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.headers.get('content-length'):
            content_length = int(request.headers['content-length'])
            if content_length > self.max_size:
                return Response(
                    status_code=413,
                    content=json.dumps(
                        {
                            "error": "Request too large",
                            "max_size_mb": self.max_size // (1024 * 1024),
                        }
                    ),
                    media_type="application/json",
                )
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)


# Request ID middleware - Track every request with unique ID 🆔
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


# Response Time middleware - Track API performance ⏱️
class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response


app.add_middleware(ResponseTimeMiddleware)

# CORS middleware - Secure validation 🛡️
# ✅ FIX BUG #3: No wildcard allowed, validate URL format
allowed_origins = parse_cors_origins_safe(
    os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS), DEFAULT_CORS_ORIGINS
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Remove server header for security
        if 'Server' in response.headers:
            del response.headers['Server']
        return response


app.add_middleware(SecurityHeadersMiddleware)


# Exception handlers
@app.exception_handler(OllamaRAGException)
async def ollama_rag_exception_handler(request: Request, exc: OllamaRAGException):
    """Handle custom Ollama RAG exceptions."""
    status_code = get_http_status_code(exc)
    request_id = getattr(request.state, 'request_id', 'unknown')
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "detail": getattr(exc, 'detail', None),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError from validators."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    return JSONResponse(
        status_code=400,
        content={"error": "ValidationError", "message": str(exc), "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


# Khởi tạo engine với thiết lập Multi-DB (tương thích ngược)
# Nếu PERSIST_DIR được set (ví dụ data/chroma) sẽ dùng như db mặc định trong root của nó
# Nếu không, mặc định PERSIST_ROOT=data/kb và DB_NAME=default
engine = RagEngine(persist_dir=os.path.join("data", "chroma"))
chat_store = ChatStore(engine.persist_root)
feedback_store = FeedbackStore(engine.persist_root)
exp_logger = ExperimentLogger(engine.persist_root)

# ✅ Initialize application metrics 📊
metrics.set_app_info(version=APP_VERSION, db_type="chromadb")


# ✅ Startup event - Initialize Semantic Cache 🧠
# Last updated: 2025-10-03 - Force reload to load .env via dotenv
@app.on_event("startup")
async def startup_event():
    """Initialize application resources on startup."""
    # Initialize Semantic Query Cache
    semantic_cache_enabled = os.getenv("USE_SEMANTIC_CACHE", "true").lower() == "true"
    if semantic_cache_enabled:
        app.state.semantic_cache = SemanticQueryCache(
            similarity_threshold=float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95")),
            max_size=int(os.getenv("SEMANTIC_CACHE_SIZE", "1000")),
            ttl=float(os.getenv("SEMANTIC_CACHE_TTL", "3600")),  # 1 hour default
        )
        print(
            f"[SEMANTIC CACHE] ENABLED: threshold={app.state.semantic_cache.similarity_threshold}, max_size={app.state.semantic_cache.max_size}, ttl={app.state.semantic_cache.ttl}s"
        )
    else:
        app.state.semantic_cache = None
        print("[SEMANTIC CACHE] DISABLED. Set USE_SEMANTIC_CACHE=true to enable.")


@app.get("/", tags=["Web UI"])
def root():
    return FileResponse("web/index.html")


@app.get("/metrics", tags=["Monitoring"])
def get_metrics():
    """✅ Prometheus metrics endpoint for monitoring."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/debug/cache-state", tags=["Debug"])
def debug_cache_state():
    """🔍 Debug endpoint to check semantic cache state."""
    return {
        "has_semantic_cache_attr": hasattr(app.state, 'semantic_cache'),
        "semantic_cache_is_none": (
            app.state.semantic_cache is None if hasattr(app.state, 'semantic_cache') else "N/A"
        ),
        "semantic_cache_type": (
            str(type(app.state.semantic_cache)) if hasattr(app.state, 'semantic_cache') else "N/A"
        ),
        "env_USE_SEMANTIC_CACHE": os.getenv("USE_SEMANTIC_CACHE"),
        "env_SEMANTIC_CACHE_THRESHOLD": os.getenv("SEMANTIC_CACHE_THRESHOLD"),
        "env_SEMANTIC_CACHE_SIZE": os.getenv("SEMANTIC_CACHE_SIZE"),
        "env_SEMANTIC_CACHE_TTL": os.getenv("SEMANTIC_CACHE_TTL"),
    }


@app.get("/api/cache-stats", tags=["Monitoring"])
def get_cache_stats():
    """📊 Cache statistics endpoint - View cache performance metrics.

    Returns:
        Cache hit rates, sizes, and performance stats for all caches
    """
    try:
        # Get filters cache stats from engine
        filters_cache_stats = (
            engine._filters_cache.stats() if hasattr(engine, '_filters_cache') else {}
        )

        # Check if generation cache is enabled
        gen_cache_enabled = os.getenv("GEN_CACHE_ENABLE", "0") == "1"
        gen_cache_info = {
            "enabled": gen_cache_enabled,
            "path": (
                os.path.join(engine.persist_root, "gen_cache.db") if gen_cache_enabled else None
            ),
        }

        # Get semantic cache stats 🧠
        semantic_cache_stats = None
        if hasattr(app.state, 'semantic_cache') and (app.state.semantic_cache is not None):
            semantic_cache_stats = app.state.semantic_cache.stats()

        # Get database info
        db_info = {
            "current_db": engine.db_name,
            "persist_root": engine.persist_root,
            "available_dbs": engine.list_dbs() if hasattr(engine, 'list_dbs') else [],
        }

        return {
            "filters_cache": filters_cache_stats,
            "generation_cache": gen_cache_info,
            "semantic_cache": semantic_cache_stats,
            "database": db_info,
            "timestamp": time.time(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve cache stats", "detail": str(e)},
        )


@app.get("/health", tags=["System"])
def health_check():
    """✅ Enhanced health check endpoint with detailed metrics.

    Returns comprehensive health status including:
    - Overall health status (healthy/degraded/unhealthy)
    - Service health (Ollama, Database, Chats)
    - System resources (CPU, Memory, Disk)
    - Uptime and version info
    """
    from datetime import datetime

    import psutil

    # ✅ Check Ollama service health
    try:
        ollama_healthy = engine.ollama.health_check()
    except Exception:
        ollama_healthy = False

    # ✅ Check database health
    try:
        db_healthy = os.path.exists(engine.persist_dir)
    except Exception:
        db_healthy = False

    # ✅ Update Ollama health metric
    metrics.update_ollama_health(ollama_healthy)

    # ✅ Get database stats with error handling
    try:
        db_count = engine.collection.count()
        metrics.update_database_size(engine.db_name, db_count)
    except Exception:
        db_count = 0

    # ✅ Get chat stats with error handling
    try:
        chats = chat_store.list(engine.db_name)
        chat_count = len(chats)
        metrics.update_active_chats(engine.db_name, chat_count)
    except Exception:
        chat_count = 0

    # ✅ System resource stats with graceful fallback
    system_stats = None
    try:
        mem = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage(os.path.dirname(engine.persist_dir))

        system_stats = {
            "memory_used_percent": mem.percent,
            "memory_available_gb": round(mem.available / (1024**3), 2),
            "cpu_percent": cpu_percent,
            "disk_used_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
        }
    except Exception:
        pass  # Graceful degradation if psutil fails

    # ✅ Determine overall status
    if ollama_healthy and db_healthy:
        status = "healthy"
    elif ollama_healthy or db_healthy:
        status = "degraded"  # Partial health
    else:
        status = "unhealthy"  # Critical failure

    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
        "services": {
            "ollama": {
                "healthy": ollama_healthy,
                "url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            },
            "database": {
                "healthy": db_healthy,
                "name": engine.db_name,
                "path": engine.persist_dir,
                "document_count": db_count,
            },
            "chats": {"count": chat_count},
        },
        "system": system_stats,
    }


@app.get("/health/live", tags=["System"])
def liveness_probe():
    """🚀 Kubernetes liveness probe - lightweight check.

    Returns 200 if application is running.
    This should ONLY check if the process is alive, not if dependencies work.
    Used by K8s to restart pods if they become unresponsive.
    """
    return {"status": "alive", "timestamp": time.time()}


@app.get("/health/ready", tags=["System"])
def readiness_probe():
    """🚀 Kubernetes readiness probe - check if ready to serve traffic.

    Returns 200 only if:
    - Ollama service is reachable
    - Database is accessible

    Used by K8s to determine if pod should receive traffic.
    """
    from datetime import datetime

    # ✅ Quick checks without heavy operations
    ollama_ready = False
    db_ready = False

    try:
        ollama_ready = engine.ollama.health_check()
    except Exception:
        pass

    try:
        db_ready = os.path.exists(engine.persist_dir) and engine.collection is not None
    except Exception:
        pass

    is_ready = ollama_ready and db_ready

    if not is_ready:
        return JSONResponse(
            status_code=503,  # Service Unavailable
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "checks": {"ollama": ollama_ready, "database": db_ready},
            },
        )

    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {"ollama": True, "database": True},
    }


class IngestRequest(BaseModel):
    paths: list[str] = ["data/docs"]
    db: str | None = None
    version: str | None = None

    @field_validator('paths')
    @classmethod
    def validate_paths(cls, v):
        """Validate paths để ngăn path traversal."""
        if not v:
            raise ValueError("Paths list cannot be empty")
        for p in v:
            try:
                # Validate path an toàn
                validate_safe_path(p)
            except ValueError as e:
                raise ValueError(f"Invalid path '{p}': {str(e)}") from e
        return v

    @field_validator('db')
    @classmethod
    def validate_db_name_field(cls, v):
        """Validate DB name."""
        if v is not None and not validate_db_name(v):
            raise ValueError(
                f"Invalid DB name: {v}. Must be alphanumeric with _, -, . only (1-64 chars)"
            )
        return v

    @field_validator('version')
    @classmethod
    def validate_version_field(cls, v):
        """Validate version string."""
        if v is not None and not validate_version_string(v):
            raise ValueError(f"Invalid version: {v}. Must be alphanumeric with _, -, . only")
        return v


@app.post("/api/ingest", tags=["Ingestion"])
@limiter.limit(RATE_LIMIT_INGEST)
def api_ingest(req: IngestRequest, request: Request):
    try:
        if req.db:
            engine.use_db(req.db)
        count = engine.ingest_paths(req.paths, version=req.version)
        return {"status": "ok", "chunks_indexed": count, "db": engine.db_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Upload & Ingest =====
@app.post("/api/upload", tags=["Ingestion"])
@limiter.limit(RATE_LIMIT_UPLOAD)
async def api_upload(
    request: Request,
    files: list[UploadFile] = File(...),
    db: str | None = Form(None),
    version: str | None = Form(None),
):
    """Upload files. ✅ FIX BUG #9: Async file I/O to avoid blocking event loop! 🚀"""
    try:
        if db:
            engine.use_db(db)
        save_dir = os.path.join("data", "docs", "uploads")
        os.makedirs(save_dir, exist_ok=True)
        saved_paths: list[str] = []
        allowed = {".txt", ".pdf", ".docx"}

        # ✅ Import aiofiles để ghi file không đồng bộ
        import aiofiles

        for f in files:
            name = f.filename or ""
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed:
                continue
            data = await f.read()
            new_name = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(save_dir, new_name)

            # ✅ Ghi file bằng aiofiles.open() thay vì blocking open()
            async with aiofiles.open(path, "wb") as out:
                await out.write(data)

            saved_paths.append(path)
        count = engine.ingest_paths(saved_paths, version=version) if saved_paths else 0
        return {
            "status": "ok",
            "saved": [os.path.basename(p) for p in saved_paths],
            "chunks_indexed": count,
            "db": engine.db_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    query: str
    k: int = 5
    method: str = "vector"  # vector | bm25 | hybrid
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10
    rrf_enable: bool | None = None
    rrf_k: int | None = None
    rewrite_enable: bool = False
    rewrite_n: int = 2
    provider: str | None = None
    chat_id: str | None = None
    save_chat: bool = True
    db: str | None = None
    languages: list[str] | None = None
    versions: list[str] | None = None
    rr_provider: str | None = None  # auto|bge|embed
    rr_max_k: int | None = None
    rr_batch_size: int | None = None
    rr_num_threads: int | None = None


class MultiHopQueryRequest(BaseModel):
    query: str
    k: int = 5
    method: str = "hybrid"
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10
    depth: int = 2
    fanout: int = 2
    fanout_first_hop: int | None = None
    budget_ms: int | None = None
    rrf_enable: bool | None = None
    rrf_k: int | None = None
    provider: str | None = None
    chat_id: str | None = None
    save_chat: bool = True
    db: str | None = None
    languages: list[str] | None = None
    versions: list[str] | None = None
    rr_provider: str | None = None
    rr_max_k: int | None = None
    rr_batch_size: int | None = None
    rr_num_threads: int | None = None


@app.post("/api/query", tags=["RAG Query"])
@limiter.limit(RATE_LIMIT_QUERY)
def api_query(req: QueryRequest, request: Request):
    try:
        if req.db:
            engine.use_db(req.db)

        # ✅ Track query metrics
        provider = req.provider or engine.default_provider
        metrics.track_query(req.method, provider, engine.db_name)

        import time as _t

        t0 = int(_t.time() * 1000)

        # 🧠 Check semantic cache first (if enabled)
        cached_result = None
        cache_metadata = None
        if hasattr(app.state, 'semantic_cache') and (app.state.semantic_cache is not None):
            try:
                cached_result, cache_metadata = app.state.semantic_cache.get(
                    req.query, engine.ollama.embed, return_metadata=True
                )
                if cached_result:
                    # Cache HIT! 🎉 Return immediately
                    print(
                        f"🔥 Semantic Cache HIT! Type: {cache_metadata['cache_type']}, Similarity: {cache_metadata['similarity']:.4f}"
                    )
                    # Add cache metadata to result
                    cached_result["cache_hit"] = True
                    cached_result["cache_metadata"] = cache_metadata
                    cached_result["db"] = engine.db_name
                    return cached_result
            except Exception as e:
                # If cache check fails, just continue with normal query
                print(f"⚠️ Semantic cache check failed: {e}")

        # Cache MISS or cache disabled - Execute normal query
        result = engine.answer(
            req.query,
            top_k=req.k,
            method=req.method,
            bm25_weight=req.bm25_weight,
            rerank_enable=req.rerank_enable,
            rerank_top_n=req.rerank_top_n,
            provider=req.provider,
            rrf_enable=req.rrf_enable,
            rrf_k=req.rrf_k,
            rewrite_enable=req.rewrite_enable,
            rewrite_n=req.rewrite_n,
            languages=req.languages,
            versions=req.versions,
            rr_provider=req.rr_provider,
            rr_max_k=req.rr_max_k,
            rr_batch_size=req.rr_batch_size,
            rr_num_threads=req.rr_num_threads,
        )
        # Lưu chat nếu cần
        if req.save_chat and req.chat_id:
            try:
                chat_store.append_pair(
                    engine.db_name,
                    req.chat_id,
                    req.query,
                    result.get("answer", ""),
                    {"metas": result.get("metadatas", []), "contexts": result.get("contexts", [])},
                )
            except Exception:
                pass
        result["db"] = engine.db_name
        result["cache_hit"] = False  # Mark as fresh query

        # 🧠 Cache the result (if semantic cache enabled)
        if hasattr(app.state, 'semantic_cache') and (app.state.semantic_cache is not None):
            try:
                app.state.semantic_cache.set(req.query, result, engine.ollama.embed)
                print(f"Query cached: {req.query[:50]}...")
            except Exception as e:
                print(f"Failed to cache query: {e}")

        # Log
        try:
            t1 = int(_t.time() * 1000)
            exp_logger.log(
                engine.db_name,
                {
                    "ts": t1,
                    "latency_ms": t1 - t0,
                    "route": "/api/query",
                    "db": engine.db_name,
                    "provider": req.provider or engine.default_provider,
                    "method": req.method,
                    "k": req.k,
                    "bm25_weight": req.bm25_weight,
                    "rerank_enable": req.rerank_enable,
                    "rerank_top_n": req.rerank_top_n,
                    "rrf_enable": req.rrf_enable,
                    "rrf_k": req.rrf_k,
                    "rewrite_enable": req.rewrite_enable,
                    "rewrite_n": req.rewrite_n,
                    "languages": req.languages,
                    "versions": req.versions,
                    "query": req.query,
                    "answer_len": len(result.get("answer", "")),
                    "contexts_count": len(result.get("contexts", [])),
                    "contexts_sources": [
                        (m or {}).get("source", "") for m in result.get("metadatas", [])
                    ],
                    "cache_hit": False,
                },
            )
        except Exception:
            pass
        return result
    except Exception as e:
        # ✅ Track query error
        provider = req.provider or engine.default_provider
        error_type = type(e).__name__
        metrics.track_query_error(req.method, provider, error_type)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream_query", tags=["RAG Query"])
@limiter.limit(RATE_LIMIT_QUERY)
def api_stream_query(req: QueryRequest, request: Request):
    try:

        def gen():
            import time as _t

            t0 = int(_t.time() * 1000)
            saved_early = False
            if req.db:
                engine.use_db(req.db)
            # Lấy contexts theo method đã chọn, có thể áp dụng reranker trước khi stream
            base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
            if req.rewrite_enable:
                retrieved = engine.retrieve_aggregate(
                    req.query,
                    top_k=base_k,
                    method=req.method,
                    bm25_weight=req.bm25_weight,
                    rrf_enable=req.rrf_enable,
                    rrf_k=req.rrf_k,
                    rewrite_enable=True,
                    rewrite_n=req.rewrite_n,
                    provider=req.provider,
                    languages=req.languages,
                    versions=req.versions,
                )
            else:
                if req.method == "bm25":
                    retrieved = engine.retrieve_bm25(
                        req.query, top_k=base_k, languages=req.languages, versions=req.versions
                    )
                elif req.method == "hybrid":
                    retrieved = engine.retrieve_hybrid(
                        req.query,
                        top_k=base_k,
                        bm25_weight=req.bm25_weight,
                        rrf_enable=req.rrf_enable,
                        rrf_k=req.rrf_k,
                        languages=req.languages,
                        versions=req.versions,
                    )
                else:
                    retrieved = engine.retrieve(
                        req.query, top_k=base_k, languages=req.languages, versions=req.versions
                    )
            ctx_docs = retrieved["documents"]
            metas = retrieved["metadatas"]
            # Fallback nếu không có contexts
            if not ctx_docs:
                try:
                    base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
                    # Ưu tiên BM25 fallback
                    fb = engine.retrieve_bm25(req.query, top_k=base_k)
                    ctx_docs = fb.get("documents", [])
                    metas = fb.get("metadatas", [])
                    if not ctx_docs:
                        # Thử vector
                        fb2 = engine.retrieve(req.query, top_k=base_k)
                        ctx_docs = fb2.get("documents", [])
                        metas = fb2.get("metadatas", [])
                    if not ctx_docs:
                        # Lấy ít nhất 1 doc bất kỳ từ collection để hiển thị
                        try:
                            results = engine.collection.get(include=["documents", "metadatas"])  # type: ignore[arg-type]
                            docs_any = results.get("documents", [])
                            metas_any = results.get("metadatas", [])
                            if docs_any:
                                ctx_docs = [docs_any[0]]
                                metas = [metas_any[0] if metas_any else {}]
                        except Exception:
                            pass
                except Exception:
                    pass
            if req.rerank_enable and ctx_docs:
                # dùng hàm private trong engine để giữ logic nhất quán
                ctx_docs, metas = engine._apply_rerank(
                    req.query,
                    ctx_docs,
                    metas,
                    req.k,
                    rr_provider=req.rr_provider,
                    rr_max_k=req.rr_max_k,
                    rr_batch_size=req.rr_batch_size,
                    rr_num_threads=req.rr_num_threads,
                )  # type: ignore[attr-defined]
            else:
                ctx_docs = ctx_docs[: req.k]
                metas = metas[: req.k]
            # Gửi contexts trước dưới dạng JSON đánh dấu
            header = {"contexts": ctx_docs, "metadatas": metas, "db": engine.db_name}
            yield "[[CTXJSON]]" + json.dumps(header) + "\n"
            # Lưu chat sớm (trả lời rỗng) ngay sau khi có contexts (giúp analytics và test nhanh)
            if req.save_chat and req.chat_id and not saved_early:
                try:
                    chat_store.append_pair(
                        engine.db_name, req.chat_id, req.query, "", {"metas": metas}
                    )
                    saved_early = True
                except Exception:
                    saved_early = False
            # Log sớm ngay sau khi có contexts để export logs không phải đợi sinh câu trả lời
            try:
                exp_logger.log(
                    engine.db_name,
                    {
                        "ts": int(__import__('time').time() * 1000),
                        "latency_ms": 0,
                        "route": "/api/stream_query",
                        "db": engine.db_name,
                        "provider": req.provider or engine.default_provider,
                        "method": req.method,
                        "k": req.k,
                        "bm25_weight": req.bm25_weight,
                        "rerank_enable": req.rerank_enable,
                        "rerank_top_n": req.rerank_top_n,
                        "rrf_enable": req.rrf_enable,
                        "rrf_k": req.rrf_k,
                        "rewrite_enable": req.rewrite_enable,
                        "rewrite_n": req.rewrite_n,
                        "languages": req.languages,
                        "versions": req.versions,
                        "query": req.query,
                        "answer_len": 0,
                        "contexts_count": len(ctx_docs or []),
                        "contexts_sources": [(m or {}).get("source", "") for m in metas or []],
                    },
                )
            except Exception:
                pass
            prompt = engine.build_prompt(req.query, ctx_docs)
            answer_buf = []
            try:
                for chunk in engine.generate_stream(prompt, provider=req.provider):
                    answer_buf.append(chunk)
                    yield chunk
            except Exception:
                return
            finally:
                # Lưu chat nếu cần (nếu chưa lưu sớm)
                if req.save_chat and req.chat_id and not saved_early:
                    try:
                        chat_store.append_pair(
                            engine.db_name,
                            req.chat_id,
                            req.query,
                            "".join(answer_buf),
                            {"metas": metas, "contexts": ctx_docs},
                        )
                    except Exception:
                        pass
                # Log
                try:
                    t1 = int(_t.time() * 1000)
                    exp_logger.log(
                        engine.db_name,
                        {
                            "ts": t1,
                            "latency_ms": t1 - t0,
                            "route": "/api/stream_query",
                            "db": engine.db_name,
                            "provider": req.provider or engine.default_provider,
                            "method": req.method,
                            "k": req.k,
                            "bm25_weight": req.bm25_weight,
                            "rerank_enable": req.rerank_enable,
                            "rerank_top_n": req.rerank_top_n,
                            "rrf_enable": req.rrf_enable,
                            "rrf_k": req.rrf_k,
                            "rewrite_enable": req.rewrite_enable,
                            "rewrite_n": req.rewrite_n,
                            "languages": req.languages,
                            "versions": req.versions,
                            "query": req.query,
                            "answer_len": len("".join(answer_buf)),
                            "contexts_count": len(ctx_docs or []),
                            "contexts_sources": [(m or {}).get("source", "") for m in metas or []],
                        },
                    )
                except Exception:
                    pass

        return StreamingResponse(gen(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/multihop_query", tags=["RAG Query"])
def api_multihop_query(req: MultiHopQueryRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        import time as _t

        t0 = int(_t.time() * 1000)
        result = engine.answer_multihop(
            req.query,
            depth=req.depth,
            fanout=req.fanout,
            top_k=req.k,
            method=req.method,
            bm25_weight=req.bm25_weight,
            rerank_enable=req.rerank_enable,
            rerank_top_n=req.rerank_top_n,
            skip_answer=True,
            rrf_enable=req.rrf_enable,
            rrf_k=req.rrf_k,
            fanout_first_hop=req.fanout_first_hop,
            budget_ms=req.budget_ms,
            languages=req.languages,
            versions=req.versions,
        )
        if req.save_chat and req.chat_id:
            try:
                chat_store.append_pair(
                    engine.db_name,
                    req.chat_id,
                    req.query,
                    result.get("answer", ""),
                    {"metas": result.get("metadatas", []), "contexts": result.get("contexts", [])},
                )
            except Exception:
                pass
        result["db"] = engine.db_name
        # Log
        try:
            t1 = int(_t.time() * 1000)
            result_metas = result.get("metadatas", [])
            exp_logger.log(
                engine.db_name,
                {
                    "ts": t1,
                    "latency_ms": t1 - t0,
                    "route": "/api/multihop_query",
                    "db": engine.db_name,
                    "provider": req.provider or engine.default_provider,
                    "method": req.method,
                    "k": req.k,
                    "bm25_weight": req.bm25_weight,
                    "rerank_enable": req.rerank_enable,
                    "rerank_top_n": req.rerank_top_n,
                    "rrf_enable": req.rrf_enable,
                    "rrf_k": req.rrf_k,
                    "depth": req.depth,
                    "fanout": req.fanout,
                    "fanout_first_hop": req.fanout_first_hop,
                    "budget_ms": req.budget_ms,
                    "languages": req.languages,
                    "versions": req.versions,
                    "query": req.query,
                    "answer_len": len(result.get("answer", "")),
                    "contexts_count": len(result.get("contexts", [])),
                    "contexts_sources": [(m or {}).get("source", "") for m in result_metas],
                },
            )
        except Exception:
            pass
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream_multihop_query", tags=["RAG Query"])
def api_stream_multihop_query(req: MultiHopQueryRequest):
    try:

        def gen():
            import time as _t

            t0 = int(_t.time() * 1000)
            if req.db:
                engine.use_db(req.db)
            # Chuẩn bị contexts qua multi-hop (không stream decomposition để đơn giản)
            mh = engine.answer_multihop(
                req.query,
                depth=req.depth,
                fanout=req.fanout,
                top_k=req.k,
                method=req.method,
                bm25_weight=req.bm25_weight,
                rerank_enable=req.rerank_enable,
                rerank_top_n=req.rerank_top_n,
                skip_answer=True,
                fanout_first_hop=req.fanout_first_hop,
                budget_ms=req.budget_ms,
                languages=req.languages,
                versions=req.versions,
            )
            ctx_docs = mh.get("contexts", [])
            metas = mh.get("metadatas", [])
            # Nếu multi-hop không thu được contexts, fallback về single-hop theo method
            if not ctx_docs:
                base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
                if req.method == "bm25":
                    retrieved = engine.retrieve_bm25(req.query, top_k=base_k)
                elif req.method == "hybrid":
                    retrieved = engine.retrieve_hybrid(
                        req.query,
                        top_k=base_k,
                        bm25_weight=req.bm25_weight,
                        rrf_enable=req.rrf_enable,
                        rrf_k=req.rrf_k,
                    )
                else:
                    retrieved = engine.retrieve(req.query, top_k=base_k)
                ctx_docs = retrieved.get("documents", [])
                metas = retrieved.get("metadatas", [])
                if req.rerank_enable and ctx_docs:
                    ctx_docs, metas = engine._apply_rerank(
                        req.query,
                        ctx_docs,
                        metas,
                        req.k,
                        rr_provider=req.rr_provider,
                        rr_max_k=req.rr_max_k,
                        rr_batch_size=req.rr_batch_size,
                        rr_num_threads=req.rr_num_threads,
                    )  # type: ignore[attr-defined]
                else:
                    ctx_docs = ctx_docs[: req.k]
                    metas = metas[: req.k]
            header = {"contexts": ctx_docs, "metadatas": metas, "db": engine.db_name}
            yield "[[CTXJSON]]" + json.dumps(header) + "\n"
            # Stream phần trả lời chính thức dựa trên prompt đã dùng
            prompt = engine.build_prompt(req.query, ctx_docs)
            answer_buf = []
            try:
                for chunk in engine.generate_stream(prompt, provider=req.provider):
                    answer_buf.append(chunk)
                    yield chunk
            except Exception:
                return
            finally:
                if req.save_chat and req.chat_id:
                    try:
                        chat_store.append_pair(
                            engine.db_name,
                            req.chat_id,
                            req.query,
                            "".join(answer_buf),
                            {"metas": metas, "contexts": ctx_docs},
                        )
                    except Exception:
                        pass
                # Log
                try:
                    t1 = int(_t.time() * 1000)
                    exp_logger.log(
                        engine.db_name,
                        {
                            "ts": t1,
                            "latency_ms": t1 - t0,
                            "route": "/api/stream_multihop_query",
                            "db": engine.db_name,
                            "provider": req.provider or engine.default_provider,
                            "method": req.method,
                            "k": req.k,
                            "bm25_weight": req.bm25_weight,
                            "rerank_enable": req.rerank_enable,
                            "rerank_top_n": req.rerank_top_n,
                            "depth": req.depth,
                            "fanout": req.fanout,
                            "fanout_first_hop": req.fanout_first_hop,
                            "budget_ms": req.budget_ms,
                            "query": req.query,
                            "answer_len": len("".join(answer_buf)),
                            "contexts_count": len(ctx_docs or []),
                            "contexts_sources": [(m or {}).get("source", "") for m in metas or []],
                        },
                    )
                except Exception:
                    pass

        return StreamingResponse(gen(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Chat APIs =====
class ChatCreate(BaseModel):
    db: str | None = None
    name: str | None = None


class ChatRename(BaseModel):
    name: str


@app.get("/api/chats", tags=["Chat Management"])
def api_chats_list(db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        return {"db": engine.db_name, "chats": chat_store.list(engine.db_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chats", tags=["Chat Management"])
def api_chats_create(req: ChatCreate):
    try:
        if req.db:
            engine.use_db(req.db)
        data = chat_store.create(engine.db_name, name=req.name)
        return {"db": engine.db_name, "chat": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Define search BEFORE dynamic {chat_id} routes to avoid conflicts
@app.get("/api/chats/search", tags=["Chat Management"])
def api_chats_search(q: str, db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        return {"db": engine.db_name, "results": chat_store.search(engine.db_name, q)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats/export_db", tags=["Chat Management"])
def api_chats_export_db(format: str = "json", db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.export_db_zip(engine.db_name, fmt=format)
        from datetime import datetime

        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"{engine.db_name}-chats-{ts}.zip"
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats/{chat_id}", tags=["Chat Management"])
def api_chats_get(chat_id: str, db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.get(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/chats/{chat_id}", tags=["Chat Management"])
def api_chats_rename(chat_id: str, req: ChatRename, db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.rename(engine.db_name, chat_id, req.name)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chats/{chat_id}", tags=["Chat Management"])
def api_chats_delete(chat_id: str, db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        chat_store.delete(engine.db_name, chat_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chats", tags=["Chat Management"])
def api_chats_delete_all(db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        cnt = chat_store.delete_all(engine.db_name)
        return {"status": "ok", "deleted": cnt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats/{chat_id}/export", tags=["Chat Management"])
def api_chats_export(chat_id: str, format: str = "json", db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        fmt = (format or "json").lower()
        if fmt == "md" or fmt == "markdown":
            md = chat_store.export_markdown(engine.db_name, chat_id)
            if md is None:
                raise HTTPException(status_code=404, detail="Chat not found")
            return Response(content=md, media_type="text/markdown")
        # default json
        data = chat_store.export_json(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Provider APIs =====
class ProviderName(BaseModel):
    name: str


# ===== Filters API =====
@app.get("/api/filters", tags=["System"])
def api_get_filters(db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        return engine.get_filters()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Docs APIs =====
class DocsDeleteRequest(BaseModel):
    sources: list[str]
    db: str | None = None


@app.get("/api/docs", tags=["Document Management"])
def api_docs_list(db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        return {"db": engine.db_name, "docs": engine.list_sources()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/docs", tags=["Document Management"])
def api_docs_delete(req: DocsDeleteRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        n = engine.delete_sources(req.sources or [])
        return {"status": "ok", "deleted_sources": n, "db": engine.db_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Offline Evaluation API =====
class EvalQueryItem(BaseModel):
    query: str
    expected_sources: list[str] | None = None  # match by substring in metadata.source
    expected_substrings: list[str] | None = None  # match by substring in retrieved docs
    languages: list[str] | None = None
    versions: list[str] | None = None


class EvalRequest(BaseModel):
    queries: list[EvalQueryItem]
    k: int = 5
    method: str = "bm25"
    bm25_weight: float = 0.5
    rerank_enable: bool = False
    rerank_top_n: int = 10
    rrf_enable: bool | None = None
    rrf_k: int | None = None
    rewrite_enable: bool = False
    rewrite_n: int = 2
    provider: str | None = None
    db: str | None = None
    # defaults for all items if not provided per-item
    languages: list[str] | None = None
    versions: list[str] | None = None


@app.post("/api/eval/offline", tags=["Evaluation"])
def api_eval_offline(req: EvalRequest):
    try:
        if req.db:
            engine.use_db(req.db)
        total = len(req.queries or [])
        hits = 0
        details: list[dict[str, Any]] = []
        for item in req.queries:
            langs = item.languages if item.languages is not None else req.languages
            vers = item.versions if item.versions is not None else req.versions
            base_k = max(req.k, req.rerank_top_n if req.rerank_enable else req.k)
            retrieved = engine.retrieve_aggregate(
                item.query,
                top_k=base_k,
                method=req.method,
                bm25_weight=req.bm25_weight,
                rrf_enable=req.rrf_enable,
                rrf_k=req.rrf_k,
                rewrite_enable=req.rewrite_enable,
                rewrite_n=req.rewrite_n,
                provider=req.provider,
                languages=langs,
                versions=vers,
            )
            docs = retrieved.get("documents", [])
            metas = retrieved.get("metadatas", [])
            if req.rerank_enable and docs:
                docs, metas = engine._apply_rerank(item.query, docs, metas, req.k)  # type: ignore[attr-defined]
            else:
                docs = docs[: req.k]
                metas = metas[: req.k]
            # Prepare for matching
            srcs: list[str] = []
            for m in metas:
                try:
                    s = str(m.get("source", ""))
                except Exception:
                    s = ""
                srcs.append(s)
            matched_srcs: list[str] = []
            matched_subs: list[str] = []
            # Match sources by substring anywhere in path
            if item.expected_sources:
                for exp in item.expected_sources:
                    exp = (exp or "").strip()
                    if not exp:
                        continue
                    if any(exp in s for s in srcs):
                        matched_srcs.append(exp)
            # Match expected substrings in any retrieved doc
            if item.expected_substrings:
                for exp in item.expected_substrings:
                    exp = (exp or "").strip()
                    if not exp:
                        continue
                    if any(exp.lower() in (d or "").lower() for d in docs):
                        matched_subs.append(exp)
            matched = bool(matched_srcs or matched_subs)
            if matched:
                hits += 1
            details.append(
                {
                    "query": item.query,
                    "matched": matched,
                    "matched_sources": matched_srcs,
                    "matched_substrings": matched_subs,
                    "retrieved_sources": srcs,
                }
            )
        recall = (hits / total) if total > 0 else 0.0
        return {
            "db": engine.db_name,
            "n": total,
            "hits": hits,
            "recall_at_k": recall,
            "details": details,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Logs APIs =====
class LogsEnableReq(BaseModel):
    db: str | None = None
    enabled: bool


@app.get("/api/logs/info", tags=["Logs"])
def api_logs_info(db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        return exp_logger.info(engine.db_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs/enable", tags=["Logs"])
def api_logs_enable(req: LogsEnableReq):
    try:
        if req.db:
            engine.use_db(req.db)
        return exp_logger.enable(engine.db_name, req.enabled)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/export", tags=["Logs"])
def api_logs_export(db: str | None = None, since: str | None = None, until: str | None = None):
    try:
        if db:
            engine.use_db(db)
        content = exp_logger.export(engine.db_name, since=since, until=until)
        from datetime import datetime as _dt
        from datetime import timezone as _tz

        ts = _dt.now(_tz.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"logs-{engine.db_name}-{ts}.jsonl"
        return Response(
            content=content,
            media_type="application/jsonl",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/logs", tags=["Logs"])
def api_logs_clear(db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        cnt = exp_logger.clear(engine.db_name)
        return {"status": "ok", "deleted_files": cnt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/summary", tags=["Logs"])
def api_logs_summary(db: str | None = None, since: str | None = None, until: str | None = None):
    """Tóm tắt nhanh logs JSONL: tổng số, median latency, contexts_rate, phân bố theo route/provider/method."""
    try:
        if db:
            engine.use_db(db)
        raw = exp_logger.export(engine.db_name, since=since, until=until)
        import json
        import statistics as stats

        total = 0
        latencies: list[float] = []
        with_ctx = 0
        by_route: dict[str, int] = {}
        by_provider: dict[str, int] = {}
        by_method: dict[str, int] = {}
        first_ts = None
        last_ts = None
        for line in raw.splitlines():
            try:
                e = json.loads(line)
            except Exception:
                continue
            total += 1
            try:
                lat = float(e.get('latency_ms') or 0)
                if lat > 0:
                    latencies.append(lat)
            except Exception:
                pass
            try:
                if (e.get('contexts_count') or 0) > 0:
                    with_ctx += 1
            except Exception:
                pass
            r = str(e.get('route') or '')
            if r:
                by_route[r] = by_route.get(r, 0) + 1
            p = str(e.get('provider') or '')
            if p:
                by_provider[p] = by_provider.get(p, 0) + 1
            m = str(e.get('method') or '')
            if m:
                by_method[m] = by_method.get(m, 0) + 1
            ts = e.get('ts')
            if isinstance(ts, (int, float)):
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts
        median = float(stats.median(latencies)) if latencies else 0.0
        rate = (with_ctx / total) if total > 0 else 0.0

        def top_k(d: dict[str, int], k: int = 5):
            return sorted(
                [{'key': k_, 'count': v_} for k_, v_ in d.items()],
                key=lambda x: x['count'],
                reverse=True,
            )[:k]

        return {
            'db': engine.db_name,
            'total': total,
            'median_latency_ms': median,
            'contexts_rate': rate,
            'by_route': top_k(by_route),
            'by_provider': top_k(by_provider),
            'by_method': top_k(by_method),
            'first_ts': first_ts,
            'last_ts': last_ts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Citations Export APIs =====
@app.get("/api/citations/chat/{chat_id}", tags=["Citations"])
def api_citations_chat(
    chat_id: str,
    format: str = "json",
    db: str | None = None,
    sources: str | None = None,
    versions: str | None = None,
    languages: str | None = None,
):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.get(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        # build citations from assistant messages
        import re

        citations = []
        last_user = None
        for m in data.get('messages', []):
            role = m.get('role')
            if role == 'user':
                last_user = m.get('content')
                continue
            if role != 'assistant':
                continue
            ans = m.get('content') or ''
            metas = (m.get('meta') or {}).get('metas') or []
            ctxs = (m.get('meta') or {}).get('contexts') or []
            seen = set()
            for match in re.finditer(r"\[(\d+)\]", ans):
                try:
                    n = int(match.group(1))
                except Exception:
                    continue
                if n in seen or n <= 0 or n > len(metas):
                    continue
                seen.add(n)
                md = metas[n - 1] or {}
                citations.append(
                    {
                        'n': n,
                        'source': md.get('source'),
                        'version': md.get('version'),
                        'language': md.get('language'),
                        'chunk': md.get('chunk'),
                        'excerpt': (ctxs[n - 1] if 0 <= (n - 1) < len(ctxs) else None),
                        'question': last_user,
                        'ts': m.get('ts'),
                    }
                )

        # apply filters
        def parse_csv(s: str | None):
            if not s:
                return []
            return [x.strip() for x in s.split(',') if x.strip()]

        src_filters = parse_csv(sources)
        ver_filters = parse_csv(versions)
        lang_filters = parse_csv(languages)

        def keep(c):
            if src_filters:
                src = str(c.get('source') or '')
                if not any(f in src for f in src_filters):
                    return False
            if ver_filters:
                if str(c.get('version') or '') not in ver_filters:
                    return False
            if lang_filters:
                if str(c.get('language') or '') not in lang_filters:
                    return False
            return True

        citations = [c for c in citations if keep(c)]
        fmt = (format or 'json').lower()
        if fmt == 'csv':
            import csv
            import io

            buf = io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=[
                    'n',
                    'source',
                    'version',
                    'language',
                    'chunk',
                    'question',
                    'excerpt',
                    'ts',
                ],
            )
            writer.writeheader()
            for row in citations:
                writer.writerow(row)
            return Response(
                content=buf.getvalue(),
                media_type='text/csv',
                headers={'Content-Disposition': f'attachment; filename=citations-{chat_id}.csv'},
            )
        if fmt == 'md' or fmt == 'markdown':
            lines = ['# Citations']
            for c in citations:
                lines.append(
                    f"- [{c.get('n')}] {c.get('source')} v={c.get('version')} lang={c.get('language')} chunk={c.get('chunk')}"
                )
            md = "\n".join(lines)
            return Response(content=md, media_type='text/markdown')
        # default json
        return citations
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/db", tags=["Citations"])
def api_citations_db(
    format: str = 'json',
    db: str | None = None,
    sources: str | None = None,
    versions: str | None = None,
    languages: str | None = None,
):
    try:
        if db:
            engine.use_db(db)
        # Build per-chat files and zip strictly from JSON citations for consistency
        import io
        import json
        import zipfile

        mem = io.BytesIO()
        fmt = (format or 'json').lower()
        with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for ch in chat_store.list(engine.db_name):
                cid = ch.get('id')
                if not cid:
                    continue
                # Always get JSON rows first, then render per requested format
                rows = api_citations_chat(
                    cid,
                    format='json',
                    db=engine.db_name,
                    sources=sources,
                    versions=versions,
                    languages=languages,
                )  # type: ignore[arg-type]
                rows = rows if isinstance(rows, list) else []
                fname_base = ch.get('name') or cid
                if fmt == 'csv':
                    import csv
                    from io import StringIO

                    s = StringIO()
                    w = csv.DictWriter(
                        s,
                        fieldnames=[
                            'n',
                            'source',
                            'version',
                            'language',
                            'chunk',
                            'question',
                            'excerpt',
                            'ts',
                        ],
                    )
                    w.writeheader()
                    for r in rows:
                        w.writerow(r)
                    zf.writestr(f"{fname_base}-citations.csv", s.getvalue())
                elif fmt in ('md', 'markdown'):
                    lines = ['# Citations']
                    for c in rows:
                        lines.append(
                            f"- [{c.get('n')}] {c.get('source')} v={c.get('version')} lang={c.get('language')} chunk={c.get('chunk')}"
                        )
                    zf.writestr(f"{fname_base}-citations.md", "\n".join(lines))
                else:
                    zf.writestr(
                        f"{fname_base}-citations.json",
                        json.dumps(rows, ensure_ascii=False, indent=2),
                    )
        mem.seek(0)
        return Response(
            content=mem.read(),
            media_type='application/zip',
            headers={'Content-Disposition': f'attachment; filename={engine.db_name}-citations.zip'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Analytics APIs =====
class AnalyticsSummary(BaseModel):
    chats: int
    qa_pairs: int
    answered: int
    with_contexts: int
    answer_len_avg: float
    answer_len_median: float
    top_sources: list[dict[str, Any]]
    top_versions: list[dict[str, Any]]
    top_languages: list[dict[str, Any]]
    first_ts: str | None = None
    last_ts: str | None = None


def _compute_chat_summary(chat: dict[str, Any]) -> dict[str, Any]:
    msgs = chat.get('messages', []) or []
    qa = 0
    answered = 0
    with_ctx = 0
    ans_lens: list[int] = []  # type: ignore[name-defined]
    src_counts: dict[str, int] = {}
    ver_counts: dict[str, int] = {}
    lang_counts: dict[str, int] = {}
    first_ts: str | None = None
    last_ts: str | None = None
    for m in msgs:
        ts = m.get('ts')
        if isinstance(ts, str):
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
        if m.get('role') == 'assistant':
            qa += 1
            a = m.get('content') or ''
            if a.strip():
                answered += 1
                ans_lens.append(len(a))
            meta = m.get('meta') or {}
            metas = meta.get('metas') or []
            if isinstance(metas, list) and metas:
                with_ctx += 1
                for md in metas:
                    src = str((md or {}).get('source', '') or '')
                    if src:
                        src_counts[src] = src_counts.get(src, 0) + 1
                    ver = str((md or {}).get('version', '') or '')
                    if ver:
                        ver_counts[ver] = ver_counts.get(ver, 0) + 1
                    lang = str((md or {}).get('language', '') or '')
                    if lang:
                        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    import statistics as stats  # type: ignore

    avg = float(sum(ans_lens) / len(ans_lens)) if ans_lens else 0.0
    med = float(stats.median(ans_lens)) if ans_lens else 0.0

    def top_k(d: dict[str, int], k: int = 5) -> list[dict[str, Any]]:
        items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]
        return [{'value': k_, 'count': v_} for (k_, v_) in items]

    return {
        'qa_pairs': qa,
        'answered': answered,
        'with_contexts': with_ctx,
        'answer_len_avg': avg,
        'answer_len_median': med,
        'top_sources': top_k(src_counts),
        'top_versions': top_k(ver_counts),
        'top_languages': top_k(lang_counts),
        'first_ts': first_ts,
        'last_ts': last_ts,
    }


@app.get("/api/analytics/db", tags=["Analytics"])
def api_analytics_db(db: str | None = None):
    """Analytics for entire DB. ✅ FIX BUG #8: Bulk fetch chats to avoid N+1 queries! ⚡"""
    try:
        if db:
            engine.use_db(db)
        # Get all chat IDs
        chats = chat_store.list(engine.db_name)
        chat_ids = [ch.get('id') for ch in chats if ch.get('id')]

        # ✅ Bulk fetch all chats at once (1 query thay vì N queries)! 🚀
        chats_data = chat_store.get_many(engine.db_name, chat_ids)

        merged = {
            'chats': len(chats),
            'qa_pairs': 0,
            'answered': 0,
            'with_contexts': 0,
            'answer_len_sum': 0.0,
            'answer_len_count': 0,
            'all_lens': [],
            'src': {},
            'ver': {},
            'lang': {},
            'first_ts': None,
            'last_ts': None,
        }

        # Aggregate từ bulk data
        for chat_id, data in chats_data.items():
            s = _compute_chat_summary(data)
            merged['qa_pairs'] += s['qa_pairs']
            merged['answered'] += s['answered']
            merged['with_contexts'] += s['with_contexts']
            if s['answer_len_avg'] and s['answered']:
                merged['answer_len_sum'] += s['answer_len_avg'] * s['answered']
                merged['answer_len_count'] += s['answered']
            merged['all_lens'].extend([0] * 0)  # placeholder
            for item in s['top_sources']:
                v = item['value']
                c = int(item['count'])
                merged['src'][v] = merged['src'].get(v, 0) + c
            for item in s['top_versions']:
                v = item['value']
                c = int(item['count'])
                merged['ver'][v] = merged['ver'].get(v, 0) + c
            for item in s['top_languages']:
                v = item['value']
                c = int(item['count'])
                merged['lang'][v] = merged['lang'].get(v, 0) + c
            ft = s.get('first_ts')
            lt = s.get('last_ts')
            if ft and (merged['first_ts'] is None or ft < merged['first_ts']):
                merged['first_ts'] = ft
            if lt and (merged['last_ts'] is None or lt > merged['last_ts']):
                merged['last_ts'] = lt

        avg = (
            (merged['answer_len_sum'] / merged['answer_len_count'])
            if merged['answer_len_count']
            else 0.0
        )

        def top_k(d: dict[str, int], k: int = 5) -> list[dict[str, Any]]:
            items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:k]
            return [{'value': k_, 'count': v_} for (k_, v_) in items]

        return {
            'db': engine.db_name,
            'chats': merged['chats'],
            'qa_pairs': merged['qa_pairs'],
            'answered': merged['answered'],
            'with_contexts': merged['with_contexts'],
            'answer_len_avg': float(avg),
            'answer_len_median': None,  # không tính median gộp
            'top_sources': top_k(merged['src']),
            'top_versions': top_k(merged['ver']),
            'top_languages': top_k(merged['lang']),
            'first_ts': merged['first_ts'],
            'last_ts': merged['last_ts'],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/chat/{chat_id}", tags=["Analytics"])
def api_analytics_chat(chat_id: str, db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        data = chat_store.get(engine.db_name, chat_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        s = _compute_chat_summary(data)
        out = {'db': engine.db_name, 'chat_id': chat_id}
        out.update(s)
        return out
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/provider", tags=["System"])
def api_get_provider():
    try:
        return {"provider": engine.default_provider}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/provider", tags=["System"])
def api_set_provider(req: ProviderName):
    try:
        name = (req.name or "ollama").lower()
        if name not in ("ollama", "openai"):
            raise HTTPException(status_code=400, detail="Invalid provider")
        engine.default_provider = name
        return {"provider": engine.default_provider}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Health API =====
@app.get("/api/health", tags=["System"])
def api_health():
    """Trả trạng thái backend mở rộng: Ollama/OpenAI, models, và gợi ý khắc phục."""
    try:
        import os as _os

        import requests  # type: ignore

        from .ollama_client import EMBED_MODEL, LLM_MODEL, OLLAMA_BASE_URL  # type: ignore

        status = {
            "provider": engine.default_provider,
            "db": engine.db_name,
            "overall_status": "unknown",  # ok, warning, error
            "message": "",
            "suggestions": [],
            "test_mode": bool((_os.getenv("TEST_MODE") or "").strip()),
            "ollama": {
                "base_url": OLLAMA_BASE_URL,
                "ok": False,
                "error": None,
                "models": {"available": [], "required": [LLM_MODEL, EMBED_MODEL], "missing": []},
            },
            "openai": {"configured": False, "ok": False, "error": None},
        }

        # Check Ollama
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if r.ok:
                status["ollama"]["ok"] = True
                try:
                    tags_data = r.json()
                    available_models = [
                        m.get("name", "").split(":")[0] for m in tags_data.get("models", [])
                    ]
                    status["ollama"]["models"]["available"] = list(set(available_models))

                    # Check required models
                    required = [LLM_MODEL.split(":")[0], EMBED_MODEL.split(":")[0]]
                    missing = [m for m in required if m not in available_models]
                    status["ollama"]["models"]["missing"] = missing

                    if missing:
                        status["ollama"]["error"] = f"Thiếu models: {', '.join(missing)}"
                        status["ollama"]["ok"] = False
                except Exception:
                    status["ollama"]["error"] = "Không đọc được danh sách models"
                    status["ollama"]["ok"] = False
            else:
                status["ollama"]["error"] = f"HTTP {r.status_code}"
        except Exception as e:
            status["ollama"]["error"] = str(e)

        # Check OpenAI config
        if (_os.getenv("OPENAI_API_KEY") or "").strip():
            status["openai"]["configured"] = True
            status["openai"]["ok"] = True

        # Determine overall status and suggestions
        provider = status["provider"].lower()
        if provider == "ollama":
            if status["ollama"]["ok"]:
                status["overall_status"] = "ok"
                status["message"] = "Ollama sẵn sàng"
            elif "Thiếu models" in (status["ollama"].get("error") or ""):
                status["overall_status"] = "warning"
                status["message"] = "Ollama thiếu models"
                missing = status["ollama"]["models"]["missing"]
                status["suggestions"] = [f"Chạy: ollama pull {m}" for m in missing]
            else:
                status["overall_status"] = "error"
                status["message"] = "Ollama không khả dụng"
                status["suggestions"] = ["Chạy: ollama serve", "Hoặc đổi Provider sang OpenAI"]
        elif provider == "openai":
            if status["openai"]["ok"]:
                status["overall_status"] = "ok"
                status["message"] = "OpenAI sẵn sàng"
            else:
                status["overall_status"] = "error"
                status["message"] = "OpenAI chưa cấu hình"
                status["suggestions"] = [
                    "Set biến môi trường OPENAI_API_KEY",
                    "Hoặc đổi Provider sang Ollama",
                ]
        else:
            status["overall_status"] = "error"
            status["message"] = "Provider không hợp lệ"
            status["suggestions"] = ["Chọn Provider: Ollama hoặc OpenAI"]

        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Feedback APIs =====
class FeedbackItem(BaseModel):
    db: str | None = None
    chat_id: str | None = None
    query: str | None = None
    answer: str | None = None
    score: int  # -1 | 0 | 1
    comment: str | None = None
    provider: str | None = None
    method: str | None = None
    k: int | None = None
    languages: list[str] | None = None
    versions: list[str] | None = None
    sources: list[str] | None = None


@app.post("/api/feedback", tags=["Feedback"])
def api_feedback_add(item: FeedbackItem):
    try:
        if item.db:
            engine.use_db(item.db)
        data = item.model_dump()
        data["db"] = engine.db_name
        feedback_store.append(engine.db_name, data)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback", tags=["Feedback"])
def api_feedback_list(db: str | None = None, limit: int = 50):
    try:
        if db:
            engine.use_db(db)
        items = feedback_store.list(engine.db_name, limit=limit)
        return {"db": engine.db_name, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/feedback", tags=["Feedback"])
def api_feedback_clear(db: str | None = None):
    try:
        if db:
            engine.use_db(db)
        cnt = feedback_store.clear(engine.db_name)
        return {"status": "ok", "deleted": cnt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Multi-DB APIs =====
class DbName(BaseModel):
    name: str


@app.get("/api/dbs", tags=["Database"])
def api_list_dbs():
    try:
        return {"current": engine.db_name, "dbs": engine.list_dbs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dbs/use", tags=["Database"])
def api_use_db(req: DbName):
    try:
        current = engine.use_db(req.name)
        return {"current": current, "dbs": engine.list_dbs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dbs/create", tags=["Database"])
def api_create_db(req: DbName):
    try:
        engine.create_db(req.name)
        return {"status": "ok", "current": engine.db_name, "dbs": engine.list_dbs()}
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/dbs/{name}", tags=["Database"])
def api_delete_db(name: str):
    try:
        engine.delete_db(name)
        return {"status": "ok", "current": engine.db_name, "dbs": engine.list_dbs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Mount static files at the end to not override API routes
app.mount("/static", StaticFiles(directory="web"), name="static")
