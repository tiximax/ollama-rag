"""
Custom Prometheus metrics cho Ollama RAG application.
Track LLM operations, query performance, và system health.
"""

import time

from prometheus_client import Counter, Gauge, Histogram, Info

# ===== Request Counters =====
query_counter = Counter(
    'ollama_rag_queries_total', 'Total number of RAG queries', ['method', 'provider', 'db']
)

query_error_counter = Counter(
    'ollama_rag_query_errors_total',
    'Total number of query errors',
    ['method', 'provider', 'error_type'],
)

# ===== LLM Metrics =====
llm_response_time = Histogram(
    'ollama_rag_llm_response_seconds',
    'Time taken for LLM to generate response',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_token_count = Histogram(
    'ollama_rag_llm_tokens',
    'Number of tokens in LLM response',
    ['provider'],
    buckets=[10, 50, 100, 250, 500, 1000, 2000, 5000],
)

# ===== Retrieval Metrics =====
retrieval_time = Histogram(
    'ollama_rag_retrieval_seconds',
    'Time taken for document retrieval',
    ['method', 'db'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)

retrieved_docs_count = Histogram(
    'ollama_rag_retrieved_docs',
    'Number of documents retrieved',
    ['method'],
    buckets=[1, 3, 5, 10, 20, 50, 100],
)

# ===== Ingestion Metrics =====
ingestion_counter = Counter(
    'ollama_rag_documents_ingested_total', 'Total documents ingested', ['db', 'source_type']
)

ingestion_chunks_counter = Counter(
    'ollama_rag_chunks_created_total', 'Total chunks created from documents', ['db']
)

ingestion_time = Histogram(
    'ollama_rag_ingestion_seconds',
    'Time taken to ingest documents',
    ['db'],
    buckets=[0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ===== System Metrics =====
database_size = Gauge('ollama_rag_database_documents', 'Number of documents in database', ['db'])

active_chats = Gauge('ollama_rag_active_chats', 'Number of active chat sessions', ['db'])

ollama_health = Gauge('ollama_rag_ollama_healthy', 'Ollama service health (1=healthy, 0=unhealthy)')

# ===== Semantic Cache Metrics =====
semcache_hits = Counter(
    'ollama_rag_semcache_hits_total',
    'Total semantic cache hits',
    ['type'],  # type: exact|semantic
)
semcache_misses = Counter('ollama_rag_semcache_misses_total', 'Total semantic cache misses')
semcache_size = Gauge('ollama_rag_semcache_size', 'Semantic cache current size')
semcache_fill_ratio = Gauge(
    'ollama_rag_semcache_fill_ratio', 'Semantic cache fill ratio (size/max_size)'
)

# ===== Circuit Breaker Metrics =====
# Metrics siêu thông minh cho Circuit Breaker như siêu anh hùng! 🦸‍♂️

circuit_breaker_state = Gauge(
    'ollama_rag_circuit_breaker_state',
    'Current circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)',
    ['breaker_name'],
)

circuit_breaker_calls_total = Counter(
    'ollama_rag_circuit_breaker_calls_total',
    'Total calls through circuit breaker',
    ['breaker_name', 'status'],  # status: success|failure|rejected
)

circuit_breaker_state_transitions = Counter(
    'ollama_rag_circuit_breaker_transitions_total',
    'Total circuit breaker state transitions',
    ['breaker_name', 'from_state', 'to_state'],
)

circuit_breaker_consecutive_failures = Gauge(
    'ollama_rag_circuit_breaker_consecutive_failures',
    'Current consecutive failure count',
    ['breaker_name'],
)

circuit_breaker_last_state_change = Gauge(
    'ollama_rag_circuit_breaker_last_state_change_timestamp',
    'Timestamp of last state change (Unix time)',
    ['breaker_name'],
)

# ===== System Info =====
app_info = Info('ollama_rag_app', 'Application information')

# ===== Helper Functions =====


def track_query(method: str, provider: str, db: str):
    """Increment query counter."""
    query_counter.labels(method=method, provider=provider, db=db).inc()


def track_query_error(method: str, provider: str, error_type: str):
    """Increment query error counter."""
    query_error_counter.labels(method=method, provider=provider, error_type=error_type).inc()


def track_retrieval_time(method: str, db: str):
    """Context manager to track retrieval time."""

    class RetrievalTimer:
        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            duration = time.time() - self.start
            retrieval_time.labels(method=method, db=db).observe(duration)

    return RetrievalTimer()


def track_llm_response(provider: str, model: str = "unknown"):
    """Context manager to track LLM response time."""

    class LLMTimer:
        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            duration = time.time() - self.start
            llm_response_time.labels(provider=provider, model=model).observe(duration)

    return LLMTimer()


def track_ingestion(db: str):
    """Context manager to track ingestion time."""

    class IngestionTimer:
        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            duration = time.time() - self.start
            ingestion_time.labels(db=db).observe(duration)

    return IngestionTimer()


def update_database_size(db: str, count: int):
    """Update database size gauge."""
    database_size.labels(db=db).set(count)


def update_active_chats(db: str, count: int):
    """Update active chats gauge."""
    active_chats.labels(db=db).set(count)


def update_ollama_health(is_healthy: bool):
    """Update Ollama health status."""
    ollama_health.set(1 if is_healthy else 0)


# ===== Semantic Cache Helpers =====


def semcache_hit(hit_type: str) -> None:
    """Increment semantic cache hit counter.

    Args:
        hit_type: 'exact' or 'semantic'
    """
    try:
        semcache_hits.labels(type=hit_type).inc()
    except Exception:
        pass


def semcache_miss() -> None:
    """Increment semantic cache miss counter."""
    try:
        semcache_misses.inc()
    except Exception:
        pass


def update_semcache_size(size: int, max_size: int) -> None:
    """Update semantic cache size and fill ratio gauges."""
    try:
        semcache_size.set(size)
        if max_size > 0:
            semcache_fill_ratio.set(size / max_size)
    except Exception:
        pass


def set_app_info(version: str, db_type: str = "chromadb"):
    """Set application info."""
    app_info.info({'version': version, 'db_type': db_type, 'app_name': 'ollama-rag'})


# ===== Circuit Breaker Helpers =====


def record_circuit_breaker_call(
    breaker_name: str,
    status: str,  # 'success' | 'failure' | 'rejected'
) -> None:
    """Record circuit breaker call - tracking như rockstar! 🎸

    Args:
        breaker_name: Tên của circuit breaker
        status: 'success', 'failure', hoặc 'rejected'
    """
    try:
        circuit_breaker_calls_total.labels(breaker_name=breaker_name, status=status).inc()
    except Exception:
        pass  # Never crash on metrics!


def update_circuit_breaker_state(
    breaker_name: str,
    state: str,  # 'closed' | 'open' | 'half_open'
) -> None:
    """Update circuit breaker state - real-time như chớp nát! ⚡

    Args:
        breaker_name: Tên của circuit breaker
        state: 'closed', 'open', hoặc 'half_open'
    """
    try:
        state_mapping = {'closed': 0, 'open': 1, 'half_open': 2}
        circuit_breaker_state.labels(breaker_name=breaker_name).set(state_mapping.get(state, 0))
    except Exception:
        pass


def record_circuit_breaker_transition(breaker_name: str, from_state: str, to_state: str) -> None:
    """Record state transition - theo dõi chuyển đổi! 🔄

    Args:
        breaker_name: Tên của circuit breaker
        from_state: State ban đầu
        to_state: State mới
    """
    try:
        import time

        circuit_breaker_state_transitions.labels(
            breaker_name=breaker_name, from_state=from_state, to_state=to_state
        ).inc()
        # Update timestamp
        circuit_breaker_last_state_change.labels(breaker_name=breaker_name).set(time.time())
    except Exception:
        pass


def update_circuit_breaker_failures(breaker_name: str, consecutive_failures: int) -> None:
    """Update consecutive failures count - đếm lỗi chính xác! 🎯

    Args:
        breaker_name: Tên của circuit breaker
        consecutive_failures: Số lỗi liên tiếp hiện tại
    """
    try:
        circuit_breaker_consecutive_failures.labels(breaker_name=breaker_name).set(
            consecutive_failures
        )
    except Exception:
        pass
