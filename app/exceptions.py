"""
Custom exceptions cho Ollama RAG.

Module này định nghĩa tất cả các exception types được sử dụng trong app,
giúp error handling rõ ràng và nhất quán hơn.
"""


class OllamaRAGException(Exception):
    """
    Base exception cho tất cả Ollama RAG errors.
    
    Tất cả custom exceptions khác nên inherit từ class này.
    """
    pass


class ValidationError(OllamaRAGException):
    """
    Lỗi khi validate input data.
    
    Ví dụ: invalid path, invalid DB name, invalid version string.
    """
    pass


class IngestError(OllamaRAGException):
    """
    Lỗi khi ingest tài liệu.
    
    Có thể xảy ra khi:
    - Không thể đọc file
    - Không thể extract text từ PDF/DOCX
    - Không thể chunk text
    - Không thể embed chunks
    """
    pass


class RetrievalError(OllamaRAGException):
    """
    Lỗi khi retrieve documents.
    
    Có thể xảy ra khi:
    - Vector search fails
    - BM25 search fails
    - Reranker fails
    """
    pass


class GenerationError(OllamaRAGException):
    """
    Lỗi khi generate answer với LLM.
    
    Có thể xảy ra khi:
    - Ollama connection fails
    - LLM generation fails
    - Streaming fails
    """
    pass


class ConfigError(OllamaRAGException):
    """
    Lỗi liên quan đến configuration.
    
    Có thể xảy ra khi:
    - Missing required environment variables
    - Invalid configuration values
    - Database config issues
    """
    pass


class DatabaseError(OllamaRAGException):
    """
    Lỗi liên quan đến database operations.
    
    Có thể xảy ra khi:
    - DB không tồn tại
    - Không thể tạo/xóa DB
    - ChromaDB errors
    - FAISS errors
    """
    pass


class ChatError(OllamaRAGException):
    """
    Lỗi liên quan đến chat operations.
    
    Có thể xảy ra khi:
    - Chat không tồn tại
    - Không thể lưu chat
    - Không thể export chat
    """
    pass


class ConnectionError(OllamaRAGException):
    """
    Lỗi kết nối với external services.
    
    Có thể xảy ra khi:
    - Ollama service không available
    - OpenAI API fails
    - Network timeout
    """
    pass


class RateLimitError(OllamaRAGException):
    """
    Lỗi khi vượt quá rate limit.
    
    Client nên retry sau một khoảng thời gian.
    """
    pass


class AuthenticationError(OllamaRAGException):
    """
    Lỗi authentication.
    
    Có thể xảy ra khi:
    - Invalid API key
    - Expired token
    - Insufficient permissions
    """
    pass


# Error codes mapping for HTTP responses
ERROR_CODE_MAP = {
    ValidationError: 400,
    IngestError: 500,
    RetrievalError: 500,
    GenerationError: 500,
    ConfigError: 500,
    DatabaseError: 500,
    ChatError: 404,
    ConnectionError: 503,
    RateLimitError: 429,
    AuthenticationError: 401,
    OllamaRAGException: 500,  # Default
}


def get_http_status_code(exc: Exception) -> int:
    """
    Get HTTP status code cho exception.
    
    Args:
        exc: Exception instance
        
    Returns:
        HTTP status code (int)
        
    Example:
        >>> get_http_status_code(ValidationError("Invalid input"))
        400
        >>> get_http_status_code(RateLimitError("Too many requests"))
        429
    """
    exc_type = type(exc)
    return ERROR_CODE_MAP.get(exc_type, 500)
