"""
Unit tests for exceptions module.
"""
import pytest
from app.exceptions import (
    OllamaRAGException,
    ValidationError,
    IngestError,
    RetrievalError,
    GenerationError,
    ConfigError,
    DatabaseError,
    ChatError,
    ConnectionError,
    RateLimitError,
    AuthenticationError,
    get_http_status_code,
    ERROR_CODE_MAP
)


class TestCustomExceptions:
    """Tests cho custom exception classes."""
    
    def test_base_exception(self):
        """Test base OllamaRAGException."""
        exc = OllamaRAGException("test error")
        assert str(exc) == "test error"
        assert isinstance(exc, Exception)
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("invalid input")
        assert isinstance(exc, OllamaRAGException)
        assert str(exc) == "invalid input"
    
    def test_ingest_error(self):
        """Test IngestError."""
        exc = IngestError("failed to ingest")
        assert isinstance(exc, OllamaRAGException)
    
    def test_retrieval_error(self):
        """Test RetrievalError."""
        exc = RetrievalError("retrieval failed")
        assert isinstance(exc, OllamaRAGException)
    
    def test_generation_error(self):
        """Test GenerationError."""
        exc = GenerationError("generation failed")
        assert isinstance(exc, OllamaRAGException)
    
    def test_config_error(self):
        """Test ConfigError."""
        exc = ConfigError("invalid config")
        assert isinstance(exc, OllamaRAGException)
    
    def test_database_error(self):
        """Test DatabaseError."""
        exc = DatabaseError("db error")
        assert isinstance(exc, OllamaRAGException)
    
    def test_chat_error(self):
        """Test ChatError."""
        exc = ChatError("chat not found")
        assert isinstance(exc, OllamaRAGException)
    
    def test_connection_error(self):
        """Test ConnectionError."""
        exc = ConnectionError("connection failed")
        assert isinstance(exc, OllamaRAGException)
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        exc = RateLimitError("too many requests")
        assert isinstance(exc, OllamaRAGException)
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError("invalid token")
        assert isinstance(exc, OllamaRAGException)


class TestHttpStatusCodes:
    """Tests cho HTTP status code mapping."""
    
    def test_validation_error_code(self):
        """ValidationError maps to 400."""
        exc = ValidationError("test")
        code = get_http_status_code(exc)
        assert code == 400
    
    def test_chat_error_code(self):
        """ChatError maps to 404."""
        exc = ChatError("test")
        code = get_http_status_code(exc)
        assert code == 404
    
    def test_rate_limit_error_code(self):
        """RateLimitError maps to 429."""
        exc = RateLimitError("test")
        code = get_http_status_code(exc)
        assert code == 429
    
    def test_connection_error_code(self):
        """ConnectionError maps to 503."""
        exc = ConnectionError("test")
        code = get_http_status_code(exc)
        assert code == 503
    
    def test_authentication_error_code(self):
        """AuthenticationError maps to 401."""
        exc = AuthenticationError("test")
        code = get_http_status_code(exc)
        assert code == 401
    
    def test_generic_error_defaults_to_500(self):
        """Generic exceptions default to 500."""
        exc = OllamaRAGException("test")
        code = get_http_status_code(exc)
        assert code == 500
    
    def test_unknown_exception_defaults_to_500(self):
        """Unknown exceptions default to 500."""
        exc = ValueError("test")
        code = get_http_status_code(exc)
        assert code == 500
    
    def test_error_code_map_completeness(self):
        """Verify all custom exceptions are in ERROR_CODE_MAP."""
        assert ValidationError in ERROR_CODE_MAP
        assert IngestError in ERROR_CODE_MAP
        assert RetrievalError in ERROR_CODE_MAP
        assert GenerationError in ERROR_CODE_MAP
        assert ConfigError in ERROR_CODE_MAP
        assert DatabaseError in ERROR_CODE_MAP
        assert ChatError in ERROR_CODE_MAP
        assert ConnectionError in ERROR_CODE_MAP
        assert RateLimitError in ERROR_CODE_MAP
        assert AuthenticationError in ERROR_CODE_MAP
        assert OllamaRAGException in ERROR_CODE_MAP


class TestExceptionInheritance:
    """Tests cho exception inheritance hierarchy."""
    
    def test_all_inherit_from_base(self):
        """All custom exceptions inherit from OllamaRAGException."""
        exceptions = [
            ValidationError,
            IngestError,
            RetrievalError,
            GenerationError,
            ConfigError,
            DatabaseError,
            ChatError,
            ConnectionError,
            RateLimitError,
            AuthenticationError
        ]
        
        for exc_class in exceptions:
            exc = exc_class("test")
            assert isinstance(exc, OllamaRAGException)
            assert isinstance(exc, Exception)
    
    def test_exception_can_be_caught_generically(self):
        """Custom exceptions can be caught with base class."""
        try:
            raise ValidationError("test")
        except OllamaRAGException:
            pass  # Should catch
        else:
            pytest.fail("Should have caught ValidationError")
    
    def test_exception_can_be_caught_specifically(self):
        """Custom exceptions can be caught specifically."""
        caught = False
        try:
            raise RateLimitError("test")
        except RateLimitError:
            caught = True
        
        assert caught
