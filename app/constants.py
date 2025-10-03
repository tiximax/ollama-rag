"""
Application constants và configuration defaults.

Module này chứa tất cả magic numbers và configuration values
được sử dụng xuyên suốt ứng dụng.
"""

# ===== Chunking =====
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 2000

# ===== Retrieval =====
DEFAULT_TOP_K = 5
MIN_TOP_K = 1
MAX_TOP_K = 50

# ===== RRF (Reciprocal Rank Fusion) =====
RRF_ENABLE_DEFAULT = True
RRF_K_DEFAULT = 60

# ===== Reranker =====
RERANKER_DEFAULT_BATCH_SIZE = 32
RERANKER_MIN_BATCH_SIZE = 1
RERANKER_MAX_BATCH_SIZE = 128

# ===== BM25 =====
BM25_DEFAULT_WEIGHT = 0.5
BM25_MIN_WEIGHT = 0.0
BM25_MAX_WEIGHT = 1.0

# ===== Multi-hop =====
MULTIHOP_DEFAULT_DEPTH = 2
MULTIHOP_MAX_DEPTH = 5
MULTIHOP_DEFAULT_FANOUT = 2
MULTIHOP_MAX_FANOUT = 5
MULTIHOP_DEFAULT_BUDGET_MS = 0  # 0 = no limit

# ===== Query Rewrite =====
REWRITE_MIN_N = 1
REWRITE_MAX_N = 5
REWRITE_DEFAULT_N = 2

# ===== Cache =====
FILTERS_CACHE_TTL_SECONDS = 300  # 5 minutes
GEN_CACHE_DEFAULT_TTL = 86400  # 24 hours

# ===== Database =====
DB_NAME_MIN_LENGTH = 1
DB_NAME_MAX_LENGTH = 64
DEFAULT_DB_NAME = "default"
DEFAULT_PERSIST_ROOT = "data/kb"
DEFAULT_COLLECTION_NAME = "docs"

# ===== File Upload =====
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}
MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# ===== Rate Limiting =====
RATE_LIMIT_QUERY = "30/minute"
RATE_LIMIT_INGEST = "10/hour"
RATE_LIMIT_UPLOAD = "10/hour"

# ===== Timeouts =====
OLLAMA_CONNECT_TIMEOUT = 5  # seconds
OLLAMA_READ_TIMEOUT = 180  # seconds
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_BACKOFF = 0.6  # seconds

FILE_LOCK_TIMEOUT = 5  # seconds

# ===== Pagination =====
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ===== API Versions =====
APP_VERSION = "0.15.0"
API_VERSION = "v1"

# ===== CORS =====
DEFAULT_CORS_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000"

# ===== Thread Pool =====
DEFAULT_NUM_THREADS = 1
MAX_NUM_THREADS = 16

# ===== Logging =====
LOG_MAX_MESSAGE_LENGTH = 10000
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ===== Validation =====
VERSION_STRING_MAX_LENGTH = 64
PATH_MAX_LENGTH = 1000
STRING_SANITIZE_MAX_LENGTH = 1000

# ===== HTTP Status Codes =====
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_REQUEST_TOO_LARGE = 413
HTTP_RATE_LIMIT = 429
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503
