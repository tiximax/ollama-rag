"""
Input validation module cho Ollama RAG.

Module này cung cấp các hàm validation an toàn để:
- Ngăn chặn path traversal attacks
- Validate DB names
- Validate file uploads
- Sanitize inputs
"""

import os
import platform
import re
from pathlib import Path

from .constants import (
    ALLOWED_EXTENSIONS,
    DB_NAME_MAX_LENGTH,
    DB_NAME_MIN_LENGTH,
    STRING_SANITIZE_MAX_LENGTH,
    VERSION_STRING_MAX_LENGTH,
)

# ✅ FIX BUG #2: Default absolute base directory (không dùng CWD có thể thay đổi)
_DEFAULT_BASE_DIR = Path(os.path.abspath(os.path.join(__file__, "../.."))).resolve()


def validate_safe_path(path: str, base_dir: Path | None = None) -> Path:
    """
    Validate path không escape khỏi base directory.

    ✅ FIX BUG #2: Enhanced security với:
    - Absolute base directory (không dùng CWD)
    - Symlink validation (ngăn symlink ra ngoài base)
    - Cross-platform path normalization (Windows case-insensitive)

    Args:
        path: Đường dẫn cần validate
        base_dir: Base directory (default: project root)

    Returns:
        Resolved Path object nếu an toàn

    Raises:
        ValueError: Nếu path cố gắng escape khỏi base_dir (path traversal)

    Example:
        >>> validate_safe_path("data/docs/test.txt")
        Path('C:/project/data/docs/test.txt')
        >>> validate_safe_path("../../etc/passwd")  # Raises ValueError!
        >>> validate_safe_path("/tmp/symlink")  # Raises if points outside
    """
    # Use absolute base directory (không dùng CWD)
    if base_dir is None:
        base_dir = _DEFAULT_BASE_DIR
    else:
        base_dir = base_dir.resolve()  # Always resolve base_dir

    # Resolve absolute path
    try:
        resolved = Path(path).resolve(strict=False)  # strict=False để cho phép path chưa tồn tại
    except Exception as e:
        raise ValueError(f"Invalid path format: {path}") from e

    # ✅ Cross-platform validation (Windows case-insensitive)
    if platform.system() == "Windows":
        # Normalize paths to lowercase for comparison
        resolved_str = str(resolved).lower()
        base_str = str(base_dir).lower()

        # Check if resolved path starts with base_dir
        if not resolved_str.startswith(base_str):
            raise ValueError(f"Path traversal detected: {path} attempts to escape {base_dir}")
    else:
        # Unix-like systems - case-sensitive
        try:
            resolved.relative_to(base_dir)
        except ValueError:
            raise ValueError(f"Path traversal detected: {path} attempts to escape {base_dir}")

    # ✅ Additional symlink check (ngăn symlinks ra ngoài base_dir)
    if resolved.is_symlink():
        try:
            # Get real target of symlink
            real_target = resolved.readlink()

            # If relative, resolve from parent directory
            if not real_target.is_absolute():
                real_target = (resolved.parent / real_target).resolve()
            else:
                real_target = real_target.resolve()

            # Check if target is within base_dir
            if platform.system() == "Windows":
                target_str = str(real_target).lower()
                base_str = str(base_dir).lower()
                if not target_str.startswith(base_str):
                    raise ValueError(
                        f"Symlink {path} targets outside base directory: {real_target}"
                    )
            else:
                try:
                    real_target.relative_to(base_dir)
                except ValueError:
                    raise ValueError(
                        f"Symlink {path} targets outside base directory: {real_target}"
                    )
        except (OSError, RuntimeError) as e:
            # Broken symlink or permission error
            raise ValueError(f"Cannot validate symlink {path}: {e}") from e

    return resolved


def validate_db_name(name: str) -> bool:
    """
    Validate DB name theo quy tắc an toàn.

    ✅ FIX BUG #10: Trên Windows, DB names không phân biệt hoa/thường!
    Để tránh duplicate DBs ("MyDB" vs "mydb"), normalize về lowercase.

    Rules:
    - Chỉ chứa: A-Z, a-z, 0-9, _, -, .
    - Độ dài: 1-64 ký tự
    - Không được chứa: /, \\, .., ký tự đặc biệt
    - Windows: Case-insensitive (normalize về lowercase)

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


def normalize_db_name(name: str) -> str:
    """
    Normalize DB name cho cross-platform consistency.

    ✅ FIX BUG #10: Trên Windows filesystem case-insensitive,
    normalize DB names về lowercase để tránh "MyDB" != "mydb" bugs!

    Args:
        name: DB name cần normalize

    Returns:
        Normalized DB name (lowercase trên Windows, unchanged trên Unix)

    Example:
        >>> normalize_db_name("MyDB")  # Windows
        "mydb"
        >>> normalize_db_name("MyDB")  # Unix
        "MyDB"
    """
    if platform.system() == "Windows":
        # Windows: case-insensitive filesystem → normalize về lowercase
        return name.lower()
    else:
        # Unix-like: case-sensitive → giữ nguyên
        return name


def validate_file_extension(filename: str, allowed_extensions: list[str] | None = None) -> bool:
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
