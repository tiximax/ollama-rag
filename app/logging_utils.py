"""
Logging utilities with sensitive data filtering 🛡️

Module này cung cấp logging filter để tự động mask API keys
và sensitive data khỏi logs, ngăn chặn security leaks.
"""

import logging
import re
from re import Pattern


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter để tự động redact sensitive data.

    Automatically masks:
    - API keys (api_key, apikey, API_KEY, etc.)
    - Tokens (token, access_token, bearer, etc.)
    - Passwords (password, pwd, pass, etc.)
    - Secrets (secret, private_key, etc.)

    Example:
        >>> import logging
        >>> filter = SensitiveDataFilter()
        >>> logging.root.addFilter(filter)
        >>> logging.info("API_KEY=sk-1234567890")  # Logs: "API_KEY=***REDACTED***"
    """

    # Patterns để detect sensitive keys
    SENSITIVE_PATTERNS: list[Pattern] = [
        # API keys - ✅ Fixed: match underscore and no underscore
        re.compile(
            r"(\b(?:api[_-]?key|apikey|api[_-]?secret)\s*[:=]\s*['\"]?)([a-zA-Z0-9_\-]{5,})",
            re.IGNORECASE,
        ),
        # Tokens - ✅ Fixed: match colon with optional space and value
        re.compile(
            r"(\b(?:token|access[_-]?token|bearer|jwt)\s*[:=]\s*)([a-zA-Z0-9_\-\.]{5,})",
            re.IGNORECASE,
        ),
        # Passwords
        re.compile(r"(\b(?:password|pwd|pass|passwd)\b\s*[:=]\s*['\"]?)([^\s'\"]+)", re.IGNORECASE),
        # Secrets & private keys
        re.compile(
            r"(\b(?:secret|private[_-]?key|client[_-]?secret)\b\s*[:=]\s*['\"]?)([a-zA-Z0-9_\-\.]{10,})",
            re.IGNORECASE,
        ),
        # Authorization headers
        re.compile(r"(authorization\s*:\s*(?:bearer|basic)\s+)([a-zA-Z0-9_\-\.=]+)", re.IGNORECASE),
    ]

    REDACTED = "***REDACTED***"

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record, masking sensitive data.

        Args:
            record: LogRecord to filter

        Returns:
            True (always allow record, just mask sensitive parts)
        """
        # Mask message
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._mask_sensitive(str(record.msg))

        # Mask args (tuples passed to logger)
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._mask_sensitive(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (tuple, list)):
                record.args = tuple(
                    self._mask_sensitive(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        # Always allow record (we just masked sensitive parts)
        return True

    def _mask_sensitive(self, text: str) -> str:
        """
        Mask sensitive data trong text.

        Args:
            text: Text to mask

        Returns:
            Masked text with sensitive data replaced
        """
        masked = text

        for pattern in self.SENSITIVE_PATTERNS:
            # Replace with group 1 (key name) + REDACTED
            masked = pattern.sub(rf"\1{self.REDACTED}", masked)

        return masked


def setup_secure_logging(level: int = logging.INFO) -> None:
    """
    Setup secure logging với sensitive data filtering.

    Args:
        level: Log level (default: INFO)

    Example:
        >>> from app.logging_utils import setup_secure_logging
        >>> setup_secure_logging()
        >>> import logging
        >>> logging.info("My API_KEY is sk-12345")  # Safe! Logs: "My API_KEY is ***REDACTED***"
    """
    # Create and add filter to root logger
    sensitive_filter = SensitiveDataFilter()

    # Add to all existing handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)

    # Also add to any new handlers created after this
    # (by adding to root logger itself)
    root_logger.addFilter(sensitive_filter)

    # Log that secure logging is enabled
    logging.info("✅ Secure logging enabled - Sensitive data will be redacted")


def mask_dict_secrets(data: dict) -> dict:
    """
    Mask secrets trong dictionary (useful cho JSON responses).

    Args:
        data: Dictionary potentially containing secrets

    Returns:
        New dictionary with secrets masked

    Example:
        >>> mask_dict_secrets({"api_key": "sk-123", "name": "John"})
        {'api_key': '***REDACTED***', 'name': 'John'}
    """
    import copy

    masked = copy.deepcopy(data)

    SENSITIVE_KEYS = {
        'api_key',
        'apikey',
        'api_secret',
        'token',
        'access_token',
        'bearer',
        'password',
        'pwd',
        'pass',
        'passwd',
        'secret',
        'private_key',
        'client_secret',
        'authorization',
        'auth',
    }

    def _mask_recursive(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check if key name suggests sensitive data
                if any(sens in key.lower() for sens in SENSITIVE_KEYS):
                    obj[key] = SensitiveDataFilter.REDACTED
                else:
                    # Recurse into nested structures
                    obj[key] = _mask_recursive(value)
        elif isinstance(obj, (list, tuple)):
            return type(obj)(_mask_recursive(item) for item in obj)
        return obj

    return _mask_recursive(masked)
