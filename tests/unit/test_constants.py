"""
Unit tests for constants module aligned with current app/constants.py.
"""
import re
import pytest
from app.constants import (
    # Chunking
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    MIN_CHUNK_SIZE,
    MAX_CHUNK_SIZE,
    
    # Retrieval
    DEFAULT_TOP_K,
    MIN_TOP_K,
    MAX_TOP_K,

    # RRF
    RRF_ENABLE_DEFAULT,
    RRF_K_DEFAULT,

    # Reranker
    RERANKER_DEFAULT_BATCH_SIZE,
    RERANKER_MIN_BATCH_SIZE,
    RERANKER_MAX_BATCH_SIZE,

    # BM25
    BM25_DEFAULT_WEIGHT,
    BM25_MIN_WEIGHT,
    BM25_MAX_WEIGHT,

    # Multi-hop
    MULTIHOP_DEFAULT_DEPTH,
    MULTIHOP_MAX_DEPTH,
    MULTIHOP_DEFAULT_FANOUT,
    MULTIHOP_MAX_FANOUT,
    MULTIHOP_DEFAULT_BUDGET_MS,

    # Query rewrite
    REWRITE_MIN_N,
    REWRITE_MAX_N,
    REWRITE_DEFAULT_N,

    # Cache
    FILTERS_CACHE_TTL_SECONDS,
    GEN_CACHE_DEFAULT_TTL,

    # Database
    DB_NAME_MIN_LENGTH,
    DB_NAME_MAX_LENGTH,
    DEFAULT_DB_NAME,
    DEFAULT_PERSIST_ROOT,
    DEFAULT_COLLECTION_NAME,

    # File Upload
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
    MAX_UPLOAD_SIZE_BYTES,

    # Rate limits
    RATE_LIMIT_QUERY,
    RATE_LIMIT_INGEST,
    RATE_LIMIT_UPLOAD,

    # Timeouts / retries
    OLLAMA_CONNECT_TIMEOUT,
    OLLAMA_READ_TIMEOUT,
    OLLAMA_MAX_RETRIES,
    OLLAMA_RETRY_BACKOFF,
    FILE_LOCK_TIMEOUT,

    # Pagination
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,

    # Versions
    APP_VERSION,
    API_VERSION,

    # CORS
    DEFAULT_CORS_ORIGINS,

    # Thread Pool
    DEFAULT_NUM_THREADS,
    MAX_NUM_THREADS,

    # Logging
    LOG_MAX_MESSAGE_LENGTH,
    LOG_DATE_FORMAT,

    # Validation
    VERSION_STRING_MAX_LENGTH,
    PATH_MAX_LENGTH,
    STRING_SANITIZE_MAX_LENGTH,

    # HTTP Codes
    HTTP_OK,
    HTTP_BAD_REQUEST,
    HTTP_UNAUTHORIZED,
    HTTP_NOT_FOUND,
    HTTP_REQUEST_TOO_LARGE,
    HTTP_RATE_LIMIT,
    HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE,
)


class TestVersions:
    def test_app_version_semver(self):
        assert isinstance(APP_VERSION, str)
        assert re.match(r"^\d+\.\d+\.\d+$", APP_VERSION)

    def test_api_version_non_empty(self):
        assert isinstance(API_VERSION, str)
        assert len(API_VERSION) > 0


class TestChunking:
    def test_chunk_size_range(self):
        assert MIN_CHUNK_SIZE < DEFAULT_CHUNK_SIZE < MAX_CHUNK_SIZE
        assert MIN_CHUNK_SIZE > 0
        assert MAX_CHUNK_SIZE <= 10000

    def test_chunk_overlap_less_than_size(self):
        assert 0 <= DEFAULT_CHUNK_OVERLAP < DEFAULT_CHUNK_SIZE


class TestRetrieval:
    def test_top_k_within_bounds(self):
        assert MIN_TOP_K <= DEFAULT_TOP_K <= MAX_TOP_K


class TestRRF:
    def test_rrf_defaults(self):
        assert isinstance(RRF_ENABLE_DEFAULT, bool)
        assert isinstance(RRF_K_DEFAULT, int)
        assert RRF_K_DEFAULT > 0


class TestReranker:
    def test_reranker_batch_bounds(self):
        assert RERANKER_MIN_BATCH_SIZE <= RERANKER_DEFAULT_BATCH_SIZE <= RERANKER_MAX_BATCH_SIZE
        assert RERANKER_MIN_BATCH_SIZE >= 1
        assert RERANKER_MAX_BATCH_SIZE <= 128


class TestBM25:
    def test_bm25_weights(self):
        assert 0.0 <= BM25_MIN_WEIGHT <= BM25_DEFAULT_WEIGHT <= BM25_MAX_WEIGHT <= 1.0


class TestMultihop:
    def test_multihop_limits(self):
        assert 1 <= MULTIHOP_DEFAULT_DEPTH <= MULTIHOP_MAX_DEPTH
        assert 1 <= MULTIHOP_DEFAULT_FANOUT <= MULTIHOP_MAX_FANOUT
        assert MULTIHOP_DEFAULT_BUDGET_MS >= 0


class TestRewrite:
    def test_rewrite_n_bounds(self):
        assert REWRITE_MIN_N <= REWRITE_DEFAULT_N <= REWRITE_MAX_N
        assert REWRITE_MIN_N >= 1
        assert REWRITE_MAX_N <= 10


class TestCache:
    def test_cache_ttls(self):
        assert FILTERS_CACHE_TTL_SECONDS > 0
        assert FILTERS_CACHE_TTL_SECONDS <= 3600
        assert GEN_CACHE_DEFAULT_TTL > 0


class TestDatabase:
    def test_db_name_constraints(self):
        assert DB_NAME_MIN_LENGTH >= 1
        assert DB_NAME_MAX_LENGTH >= DB_NAME_MIN_LENGTH
        assert isinstance(DEFAULT_DB_NAME, str) and len(DEFAULT_DB_NAME) >= DB_NAME_MIN_LENGTH
        assert isinstance(DEFAULT_COLLECTION_NAME, str) and len(DEFAULT_COLLECTION_NAME) > 0
        assert isinstance(DEFAULT_PERSIST_ROOT, str) and len(DEFAULT_PERSIST_ROOT) > 0


class TestUpload:
    def test_allowed_extensions(self):
        assert isinstance(ALLOWED_EXTENSIONS, set)
        assert ".txt" in ALLOWED_EXTENSIONS
        assert ".pdf" in ALLOWED_EXTENSIONS

    def test_upload_sizes(self):
        assert MAX_UPLOAD_SIZE_MB > 0
        assert MAX_UPLOAD_SIZE_BYTES == MAX_UPLOAD_SIZE_MB * 1024 * 1024


class TestRateLimits:
    def test_rate_limit_format(self):
        for rate in [RATE_LIMIT_QUERY, RATE_LIMIT_INGEST, RATE_LIMIT_UPLOAD]:
            assert isinstance(rate, str)
            assert "/" in rate


class TestTimeouts:
    def test_timeouts_and_retries(self):
        assert OLLAMA_CONNECT_TIMEOUT > 0
        assert OLLAMA_READ_TIMEOUT > 0
        assert OLLAMA_MAX_RETRIES >= 0
        assert OLLAMA_RETRY_BACKOFF >= 0
        assert FILE_LOCK_TIMEOUT > 0


class TestPagination:
    def test_page_sizes(self):
        assert DEFAULT_PAGE_SIZE > 0
        assert DEFAULT_PAGE_SIZE <= MAX_PAGE_SIZE


class TestCORS:
    def test_default_cors_origins_string(self):
        assert isinstance(DEFAULT_CORS_ORIGINS, str)
        assert len(DEFAULT_CORS_ORIGINS) > 0


class TestThreads:
    def test_threads_bounds(self):
        assert 1 <= DEFAULT_NUM_THREADS <= MAX_NUM_THREADS
        assert MAX_NUM_THREADS <= 1024


class TestLogging:
    def test_logging_constants(self):
        assert isinstance(LOG_MAX_MESSAGE_LENGTH, int)
        assert LOG_MAX_MESSAGE_LENGTH > 0
        assert isinstance(LOG_DATE_FORMAT, str)
        assert "%Y" in LOG_DATE_FORMAT


class TestValidation:
    def test_validation_constants(self):
        assert VERSION_STRING_MAX_LENGTH > 0
        assert PATH_MAX_LENGTH > 0
        assert STRING_SANITIZE_MAX_LENGTH > 0


class TestHttpCodes:
    def test_http_constants_values(self):
        assert HTTP_OK == 200
        assert HTTP_BAD_REQUEST == 400
        assert HTTP_UNAUTHORIZED == 401
        assert HTTP_NOT_FOUND == 404
        assert HTTP_REQUEST_TOO_LARGE == 413
        assert HTTP_RATE_LIMIT == 429
        assert HTTP_INTERNAL_ERROR == 500
        assert HTTP_SERVICE_UNAVAILABLE == 503
