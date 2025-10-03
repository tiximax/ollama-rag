"""
File reading utilities với proper error handling 📄

Module này cung cấp functions đểread files an toàn với:
- File size limits
- Encoding fallback
- Specific error types
- Error tracking
"""

import logging
import os
from pathlib import Path

from .exceptions import IngestError

logger = logging.getLogger(__name__)


# File size limits
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def check_file_size(filepath: str, max_size: int = MAX_FILE_SIZE_BYTES) -> None:
    """
    Check if file size is within limits.

    Args:
        filepath: Path to file
        max_size: Maximum size in bytes

    Raises:
        IngestError: If file too large
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    file_size = os.path.getsize(filepath)
    if file_size > max_size:
        raise IngestError(
            f"File too large: {filepath} "
            f"({file_size / 1024 / 1024:.1f}MB > {max_size / 1024 / 1024:.1f}MB limit)"
        )


def read_text_file_safe(filepath: str) -> str:
    """
    Read text file với encoding fallback.

    ✅ FIX BUG #6: Proper error handling + encoding fallback

    Args:
        filepath: Path to text file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IngestError: If file too large or other read errors
    """
    # Check file size first
    check_file_size(filepath)

    # Try UTF-8 first
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        logger.warning(f"UTF-8 decode failed for {filepath}, trying latin-1")
        try:
            with open(filepath, encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            raise IngestError(f"Failed to read {filepath} with latin-1: {e}") from e
    except OSError as e:
        raise IngestError(f"I/O error reading {filepath}: {e}") from e
    except Exception as e:
        raise IngestError(f"Unexpected error reading {filepath}: {e}") from e


def extract_text_from_pdf_safe(filepath: str) -> str:
    """
    Extract text from PDF với proper error handling.

    Args:
        filepath: Path to PDF file

    Returns:
        Extracted text (empty string if extraction fails)
    """
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise IngestError("pypdf not installed. Run: pip install pypdf") from e

    # Check file size
    try:
        check_file_size(filepath)
    except IngestError as e:
        logger.warning(f"PDF file too large, skipping: {e}")
        return ""

    try:
        reader = PdfReader(filepath)
        texts = []
        for page_num, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text() or ""
                if text:
                    texts.append(text)
            except Exception as e:
                logger.warning(f"Failed to extract page {page_num} from {filepath}: {e}")
                continue

        return "\n\n".join(texts)
    except Exception as e:
        logger.error(f"Failed to extract PDF {filepath}: {e}")
        return ""  # Graceful degradation


def extract_text_from_docx_safe(filepath: str) -> str:
    """
    Extract text from DOCX với proper error handling.

    Args:
        filepath: Path to DOCX file

    Returns:
        Extracted text (empty string if extraction fails)
    """
    try:
        from docx import Document
    except ImportError as e:
        raise IngestError("python-docx not installed. Run: pip install python-docx") from e

    # Check file size
    try:
        check_file_size(filepath)
    except IngestError as e:
        logger.warning(f"DOCX file too large, skipping: {e}")
        return ""

    try:
        doc = Document(filepath)
        paras = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paras)
    except Exception as e:
        logger.error(f"Failed to extract DOCX {filepath}: {e}")
        return ""  # Graceful degradation


def read_file_by_extension(filepath: str) -> tuple[str | None, str | None]:
    """
    Read file based on extension với comprehensive error handling.

    ✅ FIX BUG #6: Specific exceptions, proper error tracking

    Args:
        filepath: Path to file

    Returns:
        Tuple of (content, error_message)
        - If successful: (text_content, None)
        - If failed: (None, error_message)
    """
    ext = Path(filepath).suffix.lower()

    try:
        if ext == ".txt":
            content = read_text_file_safe(filepath)
            return (content, None)
        elif ext == ".pdf":
            content = extract_text_from_pdf_safe(filepath)
            if not content:
                return (None, "PDF extraction returned empty content")
            return (content, None)
        elif ext == ".docx":
            content = extract_text_from_docx_safe(filepath)
            if not content:
                return (None, "DOCX extraction returned empty content")
            return (content, None)
        else:
            return (None, f"Unsupported file extension: {ext}")

    except FileNotFoundError as e:
        return (None, f"File not found: {e}")
    except IngestError as e:
        return (None, str(e))
    except OSError as e:
        return (None, f"I/O error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading {filepath}: {e}", exc_info=True)
        return (None, f"Unexpected error: {e}")
