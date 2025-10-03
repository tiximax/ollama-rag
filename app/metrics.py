"""
Custom Prometheus metrics cho Ollama RAG application.
Track LLM operations, query performance, và system health.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional
import time
from functools import wraps

# ===== Request Counters =====
query_counter = Counter(
    'ollama_rag_queries_total',
    'Total number of RAG queries',
    ['method', 'provider', 'db']
)

query_error_counter = Counter(
    'ollama_rag_query_errors_total',
    'Total number of query errors',
    ['method', 'provider', 'error_type']
)

# ===== LLM Metrics =====
llm_response_time = Histogram(
    'ollama_rag_llm_response_seconds',
    'Time taken for LLM to generate response',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_token_count = Histogram(
    'ollama_rag_llm_tokens',
    'Number of tokens in LLM response',
    ['provider'],
    buckets=[10, 50, 100, 250, 500, 1000, 2000, 5000]
)

# ===== Retrieval Metrics =====
retrieval_time = Histogram(
    'ollama_rag_retrieval_seconds',
    'Time taken for document retrieval',
    ['method', 'db'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

retrieved_docs_count = Histogram(
    'ollama_rag_retrieved_docs',
    'Number of documents retrieved',
    ['method'],
    buckets=[1, 3, 5, 10, 20, 50, 100]
)

# ===== Ingestion Metrics =====
ingestion_counter = Counter(
    'ollama_rag_documents_ingested_total',
    'Total documents ingested',
    ['db', 'source_type']
)

ingestion_chunks_counter = Counter(
    'ollama_rag_chunks_created_total',
    'Total chunks created from documents',
    ['db']
)

ingestion_time = Histogram(
    'ollama_rag_ingestion_seconds',
    'Time taken to ingest documents',
    ['db'],
    buckets=[0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# ===== System Metrics =====
database_size = Gauge(
    'ollama_rag_database_documents',
    'Number of documents in database',
    ['db']
)

active_chats = Gauge(
    'ollama_rag_active_chats',
    'Number of active chat sessions',
    ['db']
)

ollama_health = Gauge(
    'ollama_rag_ollama_healthy',
    'Ollama service health (1=healthy, 0=unhealthy)'
)

# ===== System Info =====
app_info = Info(
    'ollama_rag_app',
    'Application information'
)

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

def set_app_info(version: str, db_type: str = "chromadb"):
    """Set application info."""
    app_info.info({
        'version': version,
        'db_type': db_type,
        'app_name': 'ollama-rag'
    })
