"""
Unit tests cho validators module.

Test coverage cho:
- Path validation (security)
- DB name validation
- File extension validation
- String sanitization
- Version string validation
"""

from pathlib import Path

import pytest

from app.validators import (
    sanitize_string,
    validate_db_name,
    validate_file_extension,
    validate_safe_path,
    validate_version_string,
)


class TestValidateSafePath:
    """Tests cho validate_safe_path function."""

    def test_valid_relative_path(self):
        """Test path hợp lệ trong current directory."""
        result = validate_safe_path("data/docs/test.txt")
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_path_traversal_blocked(self):
        """Test path traversal attack bị block."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_safe_path("../../../etc/passwd")

    def test_path_traversal_with_dots(self):
        """Test path với .. bị block."""
        with pytest.raises(ValueError, match="Path traversal"):
            validate_safe_path("data/../../../etc/hosts")

    def test_absolute_path_outside_basedir(self):
        """Test absolute path ngoài base dir bị block."""
        with pytest.raises(ValueError):
            validate_safe_path("/etc/passwd", base_dir=Path.cwd())

    def test_valid_with_custom_basedir(self):
        """Test với custom base directory."""
        base = Path.cwd() / "data"
        result = validate_safe_path("data/test.txt", base_dir=base)
        assert result.is_relative_to(base)


class TestValidateDbName:
    """Tests cho validate_db_name function."""

    def test_valid_simple_name(self):
        """Test DB name đơn giản hợp lệ."""
        assert validate_db_name("my_database") is True
        assert validate_db_name("test-db") is True
        assert validate_db_name("db.v1") is True

    def test_alphanumeric_with_special(self):
        """Test alphanumeric với ký tự đặc biệt cho phép."""
        assert validate_db_name("db_test_123") is True
        assert validate_db_name("prod-2024") is True

    def test_path_traversal_blocked(self):
        """Test path traversal trong DB name bị block."""
        assert validate_db_name("../etc/passwd") is False
        assert validate_db_name("..") is False
        assert validate_db_name("test/../bad") is False

    def test_invalid_characters(self):
        """Test ký tự không hợp lệ bị reject."""
        assert validate_db_name("db/test") is False
        assert validate_db_name("db\\test") is False
        assert validate_db_name("db~test") is False
        assert validate_db_name("db@test") is False

    def test_length_limits(self):
        """Test giới hạn độ dài."""
        assert validate_db_name("") is False  # Too short
        assert validate_db_name("a" * 64) is True  # Max length
        assert validate_db_name("a" * 65) is False  # Too long

    def test_non_string_input(self):
        """Test input không phải string."""
        assert validate_db_name(123) is False
        assert validate_db_name(None) is False
        assert validate_db_name([]) is False


class TestValidateFileExtension:
    """Tests cho validate_file_extension function."""

    def test_allowed_extensions_default(self):
        """Test extensions mặc định cho phép."""
        assert validate_file_extension("document.txt") is True
        assert validate_file_extension("file.pdf") is True
        assert validate_file_extension("doc.docx") is True

    def test_disallowed_extensions(self):
        """Test extensions không cho phép."""
        assert validate_file_extension("script.exe") is False
        assert validate_file_extension("file.sh") is False
        assert validate_file_extension("app.bat") is False

    def test_case_insensitive(self):
        """Test extension không phân biệt hoa thường."""
        assert validate_file_extension("FILE.TXT") is True
        assert validate_file_extension("Doc.PDF") is True

    def test_custom_allowed_extensions(self):
        """Test với custom allowed extensions."""
        custom = [".md", ".json"]
        assert validate_file_extension("readme.md", custom) is True
        assert validate_file_extension("data.json", custom) is True
        assert validate_file_extension("file.txt", custom) is False


class TestSanitizeString:
    """Tests cho sanitize_string function."""

    def test_remove_dangerous_chars(self):
        """Test loại bỏ ký tự nguy hiểm."""
        result = sanitize_string("Hello<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result
        assert "script" in result  # Text giữ lại

    def test_max_length_truncation(self):
        """Test truncate string quá dài."""
        long_string = "a" * 2000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100

    def test_remove_shell_chars(self):
        """Test loại bỏ shell injection chars."""
        result = sanitize_string("test; rm -rf /")
        assert ";" not in result
        assert "|" not in result
        assert "$" not in result

    def test_non_string_input(self):
        """Test input không phải string."""
        assert sanitize_string(123) == ""
        assert sanitize_string(None) == ""

    def test_whitespace_strip(self):
        """Test strip whitespace."""
        result = sanitize_string("  hello world  ")
        assert result == "hello world"


class TestValidateVersionString:
    """Tests cho validate_version_string function."""

    def test_valid_semver(self):
        """Test semantic versioning hợp lệ."""
        assert validate_version_string("v1.0.0") is True
        assert validate_version_string("2.3.1") is True

    def test_valid_date_version(self):
        """Test date-based version."""
        assert validate_version_string("2024-01-15") is True
        assert validate_version_string("20240115") is True

    def test_valid_hash(self):
        """Test hash-based version."""
        assert validate_version_string("abc123def") is True

    def test_path_traversal_blocked(self):
        """Test path traversal bị block."""
        assert validate_version_string("../bad") is False
        assert validate_version_string("v1/../v2") is False

    def test_invalid_characters(self):
        """Test ký tự không hợp lệ."""
        assert validate_version_string("v1.0/beta") is False
        assert validate_version_string("v1.0\\test") is False

    def test_length_limits(self):
        """Test giới hạn độ dài."""
        assert validate_version_string("") is False
        assert validate_version_string("a" * 64) is True
        assert validate_version_string("a" * 65) is False

    def test_non_string_input(self):
        """Test input không phải string."""
        assert validate_version_string(123) is False
        assert validate_version_string(None) is False


# Integration tests
class TestValidationIntegration:
    """Integration tests cho validators."""

    def test_path_and_db_name_together(self):
        """Test validation path và DB name cùng lúc."""
        # Valid case
        db_name = "test_db"
        path = "data/docs/file.txt"
        assert validate_db_name(db_name) is True
        assert validate_safe_path(path)

        # Invalid case
        bad_db = "../etc"
        bad_path = "../../etc/passwd"
        assert validate_db_name(bad_db) is False
        with pytest.raises(ValueError):
            validate_safe_path(bad_path)
