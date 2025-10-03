"""
CORS validation utilities - Ngăn chặn CORS misconfiguration 🛡️

Module này cung cấp validation an toàn cho CORS origins,
ngăn chặn wildcard attacks và validate URL format.
"""

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def validate_cors_origins(origins_str: str) -> list[str]:
    """
    Parse và validate CORS origins an toàn.

    Args:
        origins_str: Comma-separated list of origins

    Returns:
        List of validated origin URLs

    Raises:
        ValueError: If origins contain wildcard or invalid URLs

    Example:
        >>> validate_cors_origins("http://localhost:8000,https://app.com")
        ['http://localhost:8000', 'https://app.com']

        >>> validate_cors_origins("*")  # Raises ValueError!

    Security Rules:
        - ❌ NO wildcard "*" allowed
        - ✅ Must be valid http/https URLs
        - ✅ Must have scheme and netloc
    """
    if not origins_str or not origins_str.strip():
        raise ValueError("CORS_ORIGINS cannot be empty")

    # Split and clean
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]

    if not origins:
        raise ValueError("No valid CORS origins provided")

    # 🔴 CRITICAL: Reject wildcard "*"
    if "*" in origins:
        raise ValueError(
            "CORS wildcard '*' is NOT allowed for security reasons! "
            "Please specify exact origins (e.g., http://localhost:8000,https://app.example.com)"
        )

    # Validate each origin
    validated: list[str] = []

    for origin in origins:
        # Check for wildcard patterns
        if "*" in origin:
            raise ValueError(
                f"Wildcard patterns not allowed in CORS origin: {origin}. " "Use exact URLs only."
            )

        # Parse URL
        try:
            parsed = urlparse(origin)
        except Exception as e:
            raise ValueError(f"Invalid URL format for origin '{origin}': {e}")

        # Validate scheme and netloc
        if not parsed.scheme:
            raise ValueError(f"Origin must include scheme (http:// or https://): {origin}")

        if not parsed.netloc:
            raise ValueError(f"Origin must include domain/host: {origin}")

        # Only allow http/https
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Origin must use http or https scheme, got '{parsed.scheme}': {origin}"
            )

        # Reconstruct clean origin (scheme + netloc only)
        clean_origin = f"{parsed.scheme}://{parsed.netloc}"

        if clean_origin != origin:
            logger.warning(f"CORS origin normalized: '{origin}' → '{clean_origin}'")

        validated.append(clean_origin)

    # Remove duplicates while preserving order
    seen = set()
    unique_origins = []
    for o in validated:
        if o not in seen:
            seen.add(o)
            unique_origins.append(o)

    logger.info(f"Validated CORS origins: {unique_origins}")
    return unique_origins


def parse_cors_origins_safe(env_value: str, default_origins: str) -> list[str]:
    """
    Parse CORS origins với fallback an toàn nếu invalid.

    Args:
        env_value: CORS_ORIGINS from environment
        default_origins: Default origins to use as fallback

    Returns:
        List of validated origins

    Example:
        >>> parse_cors_origins_safe("*", "http://localhost:8000")
        ['http://localhost:8000']  # Fallback to default
    """
    try:
        return validate_cors_origins(env_value)
    except ValueError as e:
        logger.error(
            f"Invalid CORS configuration: {e}. "
            f"Falling back to default origins: {default_origins}"
        )
        # Fallback to defaults
        try:
            return validate_cors_origins(default_origins)
        except ValueError as e2:
            # Default also invalid → use localhost only as last resort
            logger.critical(
                f"Default CORS origins also invalid: {e2}. "
                "Using localhost:8000 only as fallback!"
            )
            return ["http://localhost:8000", "http://127.0.0.1:8000"]
