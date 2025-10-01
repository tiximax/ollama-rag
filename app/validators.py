"""
Input validation module cho Ollama RAG.

Module này cung cấp các hàm validation an toàn để:
- Ngăn chặn path traversal attacks
- Validate DB names
- Validate file uploads
- Sanitize inputs
"""
from pathlib import Path
from typing import List, Optional
import re
from .constants import (
    DB_NAME_MIN_LENGTH,
    DB_NAME_MAX_LENGTH,
    VERSION_STRING_MAX_LENGTH,
    STRING_SANITIZE_MAX_LENGTH,
    ALLOWED_EXTENSIONS
)


def validate_safe_path(path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Validate path không escape khỏi base directory.
    
    Args:
        path: Đường dẫn cần validate
        base_dir: Base directory (default: cwd)
        
    Returns:
        Resolved Path object nếu an toàn
        
    Raises:
        ValueError: Nếu path cố gắng escape khỏi base_dir (path traversal)
        
    Example:
        >>> validate_safe_path("data/docs/test.txt")
        Path('C:/project/data/docs/test.txt')
        >>> validate_safe_path("../../etc/passwd")  # Raises ValueError!
    """
    if base_dir is None:
        base_dir = Path.cwd()
    
    # Resolve absolute path
    try:
        resolved = Path(path).resolve()
    except Exception as e:
        raise ValueError(f"Invalid path format: {path}") from e
    
    # Check if resolved path is within base_dir
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Path traversal detected: {path} attempts to escape {base_dir}")
    
    return resolved


def validate_db_name(name: str) -> bool:
    """
    Validate DB name theo quy tắc an toàn.
    
    Rules:
    - Chỉ chứa: A-Z, a-z, 0-9, _, -, .
    - Độ dài: 1-64 ký tự
    - Không được chứa: /, \\, .., ký tự đặc biệt
    
    Args:
        name: DB name cần validate
        
    Returns:
        True nếu hợp lệ, False nếu không
        
    Example:
        >>> validate_db_name("my_db_v1")
        True
        >>> validate_db_name("../etc/passwd")
        False
    """
    if not isinstance(name, str):
        return False
    
    if not (DB_NAME_MIN_LENGTH <= len(name) <= DB_NAME_MAX_LENGTH):
        return False
    
    # Chỉ cho phép alphanumeric, underscore, dash, dot
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        return False
    
    # Không cho phép các patterns nguy hiểm
    dangerous_patterns = ["..", "/", "\\", "~"]
    for pattern in dangerous_patterns:
        if pattern in name:
            return False
    
    return True


def validate_file_extension(filename: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    Validate file extension.
    
    Args:
        filename: Tên file cần kiểm tra
        allowed_extensions: List extensions cho phép (default: ['.txt', '.pdf', '.docx'])
        
    Returns:
        True nếu extension hợp lệ
        
    Example:
        >>> validate_file_extension("doc.txt")
        True
        >>> validate_file_extension("script.exe")
        False
    """
    if allowed_extensions is None:
        allowed_extensions = list(ALLOWED_EXTENSIONS)
    
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def sanitize_string(s: str, max_length: int = STRING_SANITIZE_MAX_LENGTH) -> str:
    """
    Sanitize string input để tránh injection.
    
    Args:
        s: String cần sanitize
        max_length: Độ dài tối đa cho phép
        
    Returns:
        Sanitized string
        
    Example:
        >>> sanitize_string("Hello<script>alert(1)</script>")
        "Helloscriptalert1script"
    """
    if not isinstance(s, str):
        return ""
    
    # Truncate to max length
    s = s[:max_length]
    
    # Remove control characters và một số ký tự nguy hiểm
    # Keep alphanumeric, spaces, và các ký tự thông dụng
    dangerous_chars = ["<", ">", "&", ";", "|", "$", "`"]
    for char in dangerous_chars:
        s = s.replace(char, "")
    
    return s.strip()


def validate_version_string(version: str) -> bool:
    """
    Validate version string format.
    
    Args:
        version: Version string (e.g., "v1.0", "2023-12-01", hash)
        
    Returns:
        True nếu format hợp lệ
        
    Example:
        >>> validate_version_string("v1.0.2")
        True
        >>> validate_version_string("../bad")
        False
    """
    if not isinstance(version, str):
        return False
    
    if not (1 <= len(version) <= VERSION_STRING_MAX_LENGTH):
        return False
    
    # Allow alphanumeric, dash, underscore, dot
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", version):
        return False
    
    # Check for dangerous patterns
    if ".." in version or "/" in version or "\\" in version:
        return False
    
    return True
