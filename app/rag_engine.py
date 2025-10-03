import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
import threading
import time
import uuid
from collections.abc import Sequence
from typing import Any

import numpy as _np  # for FAISS cosine and array building
from chromadb import PersistentClient
from chromadb.api.types import Documents, Embeddings, IDs, Metadatas
from chromadb.config import Settings
from dotenv import load_dotenv

from .cache_utils import LRUCacheWithTTL
from .exceptions import IngestError
from .file_utils import read_file_by_extension
from .gen_cache import GenCache
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient  # type: ignore
from .reranker import BgeOnnxReranker, SimpleEmbedReranker

try:
    from rank_bm25 import BM25Okapi  # type: ignore
except Exception:  # pragma: no cover
    BM25Okapi = None  # fallback if package not installed

try:
    import langid  # type: ignore
except Exception:  # pragma: no cover
    langid = None  # optional dependency

load_dotenv()
# Optional FAISS (install via: pip install faiss-cpu). Import lazily.
try:
    import faiss as _faiss  # type: ignore
except Exception:  # pragma: no cover
    _faiss = None  # type: ignore

# Giảm nhiễu log/telemetry từ chromadb trong test/CI
for _name in ("chromadb", "chromadb.telemetry", "chromadb.telemetry.posthog"):
    try:
        logging.getLogger(_name).setLevel(logging.CRITICAL)
    except Exception:
        pass

DEFAULT_PERSIST = os.getenv("PERSIST_DIR")
PERSIST_ROOT = os.getenv("PERSIST_ROOT", "data/kb")
DEFAULT_DB = os.getenv("DB_NAME", "default")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

# Vector backend: chroma | faiss
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "chroma").lower().strip()

# Generation cache
GEN_CACHE_ENABLE = os.getenv("GEN_CACHE_ENABLE", "1").strip() not in ("0", "false", "False")
GEN_CACHE_TTL = int(os.getenv("GEN_CACHE_TTL", "86400"))

# RRF config
RRF_ENABLE_DEFAULT = os.getenv("RRF_ENABLE", "1").strip() not in ("0", "false", "False")
RRF_K_DEFAULT = int(os.getenv("RRF_K", "60"))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.replace("\r\n", "\n")
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def extract_text_from_pdf(path: str) -> str:
    """Extract text from PDF with proper error handling."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise IngestError("pypdf not installed. Run: pip install pypdf") from e

    try:
        reader = PdfReader(path)
        texts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t:
                texts.append(t)
        return "\n\n".join(texts)
    except Exception as e:
        # Log error but return empty string for graceful degradation
        import logging

        logging.warning(f"Failed to extract PDF {path}: {e}")
        return ""


def extract_text_from_docx(path: str) -> str:
    """Extract text from DOCX with proper error handling."""
    try:
        from docx import Document
    except ImportError as e:
        raise IngestError("python-docx not installed. Run: pip install python-docx") from e

    try:
        doc = Document(path)
        paras = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paras)
    except Exception as e:
        # Log error but return empty string for graceful degradation
        import logging

        logging.warning(f"Failed to extract DOCX {path}: {e}")
        return ""


class OllamaEmbeddingFunction:
    """Embedding function wrapper để dùng với ChromaDB."""

    def __init__(self, client: OllamaClient):
        self.client = client

    def __call__(self, input: Sequence[str]) -> Embeddings:
        return self.client.embed(list(input))


class RagEngine:
    def __init__(
        self,
        persist_dir: str | None = DEFAULT_PERSIST,
        collection_name: str = "docs",
        persist_root: str | None = None,
        db_name: str | None = None,
    ):
        # Determine persist_root and db_name
        if persist_dir:
            root = os.path.dirname(persist_dir)
            base = os.path.basename(persist_dir)
            self.persist_root = root if root else (persist_root or PERSIST_ROOT)
            self.db_name = base if base else (db_name or DEFAULT_DB)
        else:
            self.persist_root = persist_root or PERSIST_ROOT
            self.db_name = db_name or DEFAULT_DB
        self.collection_name = collection_name

        self.ollama = OllamaClient()
        self._openai: OpenAIClient | None = None
        self.default_provider = os.getenv("PROVIDER", "ollama").lower()
        self.vector_backend = VECTOR_BACKEND if _faiss is not None else "chroma"
        # Initialize storage and client
        self._init_client()

        # Generation cache per DB
        self.gen_cache = GenCache(self.persist_dir, enabled=GEN_CACHE_ENABLE, ttl_sec=GEN_CACHE_TTL)

        # BM25 state (in-memory)
        self._bm25 = None  # type: ignore
        self._bm25_docs: list[str] = []
        self._bm25_metas: list[dict[str, Any]] = []
        self._bm25_tokens: list[list[str]] = []
        self._bm25_lock = threading.RLock()  # Reentrant lock for BM25 operations

        # Reranker
        self._bge_rr: BgeOnnxReranker | None = None
        self._embed_rr: SimpleEmbedReranker | None = None

        # ✅ FIX BUG #7: Dùng LRU cache với TTL và size limit - Ngăn memory leak 🧹
        self._filters_cache = LRUCacheWithTTL[list[str]](max_size=100, ttl=300)

    # ===== Multi-DB =====
    @property
    def persist_dir(self) -> str:
        return os.path.join(self.persist_root, self.db_name)

    def _init_client(self) -> None:
        os.makedirs(self.persist_dir, exist_ok=True)
        # Ensure corpus stamp exists
        self._ensure_corpus_stamp()
        try:
            self.client = PersistentClient(
                path=self.persist_dir, settings=Settings(anonymized_telemetry=False)
            )
        except Exception:
            # Fallback nếu phiên bản chromadb không hỗ trợ Settings
            self.client = PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=OllamaEmbeddingFunction(self.ollama),
        )
        # Optional FAISS init
        self._faiss_index = None
        self._faiss_map_conn = None
        if self.vector_backend == "faiss" and _faiss is not None:
            self._init_faiss()
        # invalidate bm25 on (re)init
        self._bm25 = None

    def _stamp_path(self) -> str:
        return os.path.join(self.persist_dir, ".corpus_stamp")

    def _ensure_corpus_stamp(self) -> None:
        try:
            p = self._stamp_path()
            if not os.path.isfile(p):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(str(int(time.time())))
            with open(p, encoding="utf-8") as f:
                self._corpus_stamp = f.read().strip()
        except Exception:
            self._corpus_stamp = "0"

    def _bump_corpus_stamp(self) -> None:
        try:
            p = self._stamp_path()
            with open(p, "w", encoding="utf-8") as f:
                f.write(str(int(time.time())))
            self._corpus_stamp = str(int(time.time()))
        except Exception:
            pass

    # ===== FAISS helpers =====
    def _faiss_map_path(self) -> str:
        return os.path.join(self.persist_dir, "faiss_map.sqlite")

    def _faiss_index_path(self) -> str:
        return os.path.join(self.persist_dir, "faiss.index")

    @contextlib.contextmanager
    def _faiss_connection(self):
        """
        Context manager cho FAISS SQLite connection.

        ✅ FIX BUG #5: Proper error handling và logging thay vì silent fail
        """
        import sqlite3 as _sqlite3

        conn = None
        try:
            # ✅ Add timeout để tránh deadlock
            conn = _sqlite3.connect(
                self._faiss_map_path(),
                timeout=5.0,  # 5 seconds timeout
                check_same_thread=False,  # Allow multi-thread (use carefully!)
            )
            yield conn
        except _sqlite3.Error as e:
            logging.error(f"FAISS SQLite connection error: {e}")
            raise  # ✅ Re-raise thay vì silent fail
        except Exception as e:
            logging.error(f"Unexpected FAISS connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    # ✅ Log warning but don't raise (avoid masking original exception)
                    logging.warning(f"Failed to close FAISS connection: {e}")

    def _init_faiss(self) -> None:
        """Initialize FAISS index with proper resource management."""
        try:
            # Create tables using context manager
            with self._faiss_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS map (idx INTEGER PRIMARY KEY, id TEXT UNIQUE)"
                )
                cur.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
                conn.commit()

            # Keep _faiss_map_conn = None, use context manager for queries
            self._faiss_map_conn = None

            # load index if exists
            idx_path = self._faiss_index_path()
            if os.path.isfile(idx_path):
                self._faiss_index = _faiss.read_index(idx_path)  # type: ignore[attr-defined]
            else:
                self._faiss_index = None
        except Exception:
            self._faiss_index = None
            self._faiss_map_conn = None
            # fail soft: will fallback to chroma

    def _faiss_map_get_idx(self, idv: str) -> int | None:
        """Get index for ID using context manager."""
        try:
            with self._faiss_connection() as conn:
                cur = conn.cursor()
                row = cur.execute("SELECT idx FROM map WHERE id=?", (idv,)).fetchone()
                return int(row[0]) if row else None
        except Exception:
            return None

    def _faiss_map_add_many(self, ids: list[str], start_idx: int) -> None:
        """Add many IDs using context manager."""
        try:
            with self._faiss_connection() as conn:
                cur = conn.cursor()
                for i, idv in enumerate(ids):
                    cur.execute(
                        "INSERT OR IGNORE INTO map(idx,id) VALUES(?,?)", (start_idx + i, idv)
                    )
                conn.commit()
        except Exception:
            pass

    def _faiss_id_by_idx(self, idxs: list[int]) -> list[str | None]:
        """Get IDs by indexes using context manager."""
        try:
            with self._faiss_connection() as conn:
                cur = conn.cursor()
                out: list[str | None] = []
                for i in idxs:
                    row = cur.execute("SELECT id FROM map WHERE idx=?", (int(i),)).fetchone()
                    out.append(str(row[0]) if row else None)
                return out
        except Exception:
            return [None for _ in idxs]

    @staticmethod
    def _l2_normalize(mat: _np.ndarray) -> _np.ndarray:
        norm = _np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
        return mat / norm

    def _faiss_add(self, embeddings: list[list[float]], ids: list[str]) -> None:
        if _faiss is None or not embeddings or not ids:
            return
        try:
            d = len(embeddings[0])
            X = _np.array(embeddings, dtype=_np.float32)
            X = self._l2_normalize(X)
            if self._faiss_index is None:
                # Inner Product on normalized vectors ~ cosine similarity
                self._faiss_index = _faiss.IndexFlatIP(d)  # type: ignore[attr-defined]
            start = int(self._faiss_index.ntotal)  # type: ignore[union-attr]
            self._faiss_index.add(X)  # type: ignore[union-attr]
            self._faiss_map_add_many(ids, start)
            _faiss.write_index(self._faiss_index, self._faiss_index_path())  # type: ignore[attr-defined]
        except Exception:
            # fail soft
            pass

    def _faiss_query(self, embedding: list[float], top_k: int) -> tuple[list[str], list[float]]:
        if _faiss is None or self._faiss_index is None:
            return [], []
        try:
            q = _np.array([embedding], dtype=_np.float32)
            q = self._l2_normalize(q)
            scores, idxs = self._faiss_index.search(q, max(1, int(top_k)))  # type: ignore[union-attr]
            idx_list = [int(i) for i in idxs[0]]
            score_list = [float(s) for s in scores[0]]
            ids = self._faiss_id_by_idx(idx_list)
            out_ids: list[str] = []
            aligned_scores: list[float] = []
            for maybe_id, sc in zip(ids, score_list, strict=False):
                if maybe_id is not None:
                    out_ids.append(maybe_id)
                    aligned_scores.append(sc)
            return out_ids, aligned_scores
        except Exception:
            return [], []

    def list_dbs(self) -> list[str]:
        if not os.path.isdir(self.persist_root):
            return []
        names = []
        for entry in os.listdir(self.persist_root):
            p = os.path.join(self.persist_root, entry)
            if os.path.isdir(p):
                names.append(entry)
        names.sort()
        return names

    @staticmethod
    def _valid_db_name(name: str) -> bool:
        """Allow only safe names to avoid path traversal or invalid folders.
        Accept [A-Za-z0-9_.-], length 1..64.
        """
        if not isinstance(name, str):
            return False
        if not (1 <= len(name) <= 64):
            return False
        return re.fullmatch(r"[A-Za-z0-9_.-]+", name) is not None

    def use_db(self, name: str) -> str:
        """Switch to different DB. ✅ FIX BUG #10: Normalize name on Windows! 🎊"""
        if not self._valid_db_name(name):
            raise ValueError("Invalid db name")

        # ✅ Normalize DB name for Windows case-insensitivity
        from .validators import normalize_db_name

        normalized_name = normalize_db_name(name)

        if normalized_name == self.db_name:
            return self.db_name

        self.db_name = normalized_name
        self._init_client()
        # Reset cache handle to new DB path
        self.gen_cache = GenCache(self.persist_dir, enabled=GEN_CACHE_ENABLE, ttl_sec=GEN_CACHE_TTL)
        return self.db_name

    def create_db(self, name: str) -> str:
        """Create new DB. ✅ FIX BUG #10: Normalize name to avoid duplicates!"""
        if not self._valid_db_name(name):
            raise ValueError("Invalid db name")

        # ✅ Normalize DB name for Windows case-insensitivity
        from .validators import normalize_db_name

        normalized_name = normalize_db_name(name)

        p = os.path.join(self.persist_root, normalized_name)
        if os.path.exists(p):
            raise FileExistsError(f"DB '{normalized_name}' already exists")
        os.makedirs(p, exist_ok=False)
        return normalized_name

    def delete_db(self, name: str) -> None:
        """Delete DB. ✅ FIX BUG #10: Normalize name for consistent deletion!"""
        if not self._valid_db_name(name):
            raise ValueError("Invalid db name")

        # ✅ Normalize DB name for Windows case-insensitivity
        from .validators import normalize_db_name

        normalized_name = normalize_db_name(name)

        p = os.path.join(self.persist_root, normalized_name)
        if not os.path.exists(p):
            return
        # If deleting current DB, switch to DEFAULT_DB (create if needed)
        deleting_current = normalized_name == self.db_name
        shutil.rmtree(p, ignore_errors=True)
        if deleting_current:
            self.db_name = DEFAULT_DB
            self._init_client()
            self.gen_cache = GenCache(
                self.persist_dir, enabled=GEN_CACHE_ENABLE, ttl_sec=GEN_CACHE_TTL
            )

    def cleanup(self) -> None:
        """Cleanup resources (call before shutdown)."""
        # Clear caches
        self._bm25 = None
        self._filters_cache.clear()

        # Note: _faiss_map_conn is always None now (using context manager)
        # FAISS index will be garbage collected
        self._faiss_index = None

        # Gen cache cleanup if needed
        if hasattr(self, 'gen_cache'):
            try:
                del self.gen_cache
            except Exception:
                pass

    def __del__(self) -> None:
        """Destructor - cleanup resources."""
        try:
            self.cleanup()
        except Exception:
            pass

    # ===== Ingest =====
    def _detect_lang(self, text: str) -> str | None:
        try:
            if langid is None:
                return None
            code, _ = langid.classify(text)
            return code
        except Exception:
            return None

    def ingest_texts(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        version: str | None = None,
    ) -> int:
        ids: IDs = []
        docs: Documents = []
        mds: Metadatas = []

        for i, t in enumerate(texts):
            # Version cho cả tài liệu này (áp cho tất cả chunks)
ver = version or (hashlib.blake2b(t.encode("utf-8"), digest_size=16).hexdigest()[:8])
            src_val = metadatas[i].get("source") if metadatas else f"text_{i}"
            for j, chunk in enumerate(chunk_text(t)):
                ids.append(str(uuid.uuid4()))
                docs.append(chunk)
                lang = self._detect_lang(chunk) or "unknown"
                meta = {
                    "source": src_val,
                    "chunk": j,
                    "version": ver,
                    "language": lang,
                }
                mds.append(meta)
        self.collection.add(ids=ids, documents=docs, metadatas=mds)
        # Optional: add to FAISS
        if self.vector_backend == "faiss" and _faiss is not None:
            try:
                # recompute embeddings locally for FAISS index
                embs = self.ollama.embed(list(docs))
                self._faiss_add(embs, list(ids))
            except Exception:
                pass
        # invalidate bm25 to rebuild on next query
        self._bm25 = None
        # clear filters cache
        self._filters_cache.clear()
        # bump corpus stamp to invalidate gen-cache for new knowledge
        self._bump_corpus_stamp()
        return len(docs)

    def ingest_paths(self, paths: list[str], version: str | None = None) -> int:
        """
        Ingest files from paths với proper error handling.

        ✅ FIX BUG #6: Specific exceptions, error tracking, file size limits

        Returns:
            Number of chunks indexed
        """
        import glob

        contents: list[str] = []
        metas: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []  # ✅ Track errors

        for p in paths:
            for file in glob.glob(p, recursive=True):
                if os.path.isdir(file):
                    # Ingest *.txt, *.pdf, *.docx recursively
                    for pattern in ("*.txt", "*.pdf", "*.docx"):
                        for f2 in glob.glob(os.path.join(file, "**", pattern), recursive=True):
                            # ✅ Use safe file reading with error tracking
                            content, error = read_file_by_extension(f2)
                            if content:
                                contents.append(content)
                                metas.append({"source": f2})
                            elif error:
                                logging.warning(f"Skipping {f2}: {error}")
                                errors.append({"file": f2, "error": error})
                else:
                    # ✅ Use safe file reading
                    content, error = read_file_by_extension(file)
                    if content:
                        contents.append(content)
                        metas.append({"source": file})
                    elif error:
                        logging.warning(f"Skipping {file}: {error}")
                        errors.append({"file": file, "error": error})

        # ✅ Log summary
        if errors:
            logging.warning(
                f"Ingest completed with {len(errors)} errors: {len(contents)} files processed"
            )

        if not contents:
            if errors:
                raise IngestError(
                    f"No files ingested successfully. {len(errors)} file(s) failed. "
                    f"First error: {errors[0]['error']}"
                )
            return 0

        return self.ingest_texts(contents, metas, version=version)

    # ===== Docs listing/deletion =====
    def list_sources(self) -> list[dict[str, Any]]:
        """Return a list of unique sources with their chunk counts.
        Safe across ChromaDB versions by using .get(include=["metadatas"]) with fallback.
        """
        try:
            results = self.collection.get(include=["metadatas"])  # type: ignore[arg-type]
            metas = results.get("metadatas", [])
        except Exception:
            results = self.collection.get()
            metas = results.get("metadatas", [])
        counts: dict[str, int] = {}
        for md in metas:
            try:
                src = str((md or {}).get("source") or "")
            except Exception:
                src = ""
            if not src:
                continue
            counts[src] = counts.get(src, 0) + 1
        items = [{"source": s, "chunks": c} for s, c in sorted(counts.items(), key=lambda x: x[0])]
        return items

    def delete_sources(self, sources: list[str]) -> int:
        """Delete all chunks whose metadata.source is in the provided list.
        Returns the number of source entries attempted (not exact chunk count).
        """
        if not sources:
            return 0
        deleted = 0
        for s in sources:
            if not s:
                continue
            try:
                # Preferred path (supported in newer chromadb):
                self.collection.delete(where={"source": s})  # type: ignore[arg-type]
                deleted += 1
                continue
            except Exception:
                pass
            # Fallback: try to fetch IDs then delete by ids
            try:
                ids: list[str] = []
                try:
                    res = self.collection.get(where={"source": s}, include=["ids"])  # type: ignore[arg-type]
                    raw_ids = res.get("ids", [])
                except Exception:
                    res = self.collection.get()
                    raw_ids = res.get("ids", [])
                # raw_ids may be nested list depending on API; flatten safely
                if isinstance(raw_ids, list):
                    for item in raw_ids:
                        if isinstance(item, list):
                            ids.extend([str(x) for x in item])
                        elif item is not None:
                            ids.append(str(item))
                if ids:
                    self.collection.delete(ids=ids)
                    deleted += 1
            except Exception:
                # Ignore errors per-source to be robust
                pass
        # Invalidate caches
        self._bm25 = None
        self._filters_cache.clear()
        return deleted

    # ===== Tokenize & BM25 =====
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", (text or "").lower())

    def _build_bm25_from_collection(self) -> None:
        """Build BM25 index with thread safety."""
        with self._bm25_lock:
            if BM25Okapi is None:
                self._bm25 = None
                self._bm25_docs = []
                self._bm25_metas = []
                self._bm25_tokens = []
                return
        try:
            # Try new API with include
            results = self.collection.get(include=["documents", "metadatas"])  # type: ignore[arg-type]
            docs: list[str] = results.get("documents", [])  # type: ignore[assignment]
            metas: list[dict[str, Any]] = results.get("metadatas", [])  # type: ignore[assignment]
        except Exception:
            # Fallback without include
            results = self.collection.get()
            docs = results.get("documents", [])  # type: ignore[assignment]
            metas = results.get("metadatas", [])  # type: ignore[assignment]
        # Filter empties keeping alignment
        new_docs: list[str] = []
        new_metas: list[dict[str, Any]] = []
        new_tokens: list[list[str]] = []
        for d, m in zip(docs, metas, strict=False):
            if d and d.strip():
                new_docs.append(d)
                new_metas.append(m)
                new_tokens.append(self._tokenize(d))
        if not new_docs:
            self._bm25 = None
            self._bm25_docs = []
            self._bm25_metas = []
            self._bm25_tokens = []
            return
        self._bm25 = BM25Okapi(new_tokens)  # type: ignore[operator]
        self._bm25_docs = new_docs
        self._bm25_metas = new_metas
        self._bm25_tokens = new_tokens
        # clear filters cache as corpus changed
        self._filters_cache.clear()

    def _ensure_bm25(self) -> bool:
        """
        Ensure BM25 index exists - THREAD-SAFE VERSION 🔒

        Uses double-checked locking pattern to prevent race conditions:
        1. Check if _bm25 exists (fast path, no lock)
        2. If None, acquire lock
        3. Re-check if _bm25 exists (another thread may have initialized it)
        4. Build if still None

        ✅ FIX BUG #4: Prevents multiple threads from rebuilding BM25 simultaneously
        """
        # Fast path: BM25 already exists
        if self._bm25 is not None:
            return True

        # Slow path: Need to build BM25
        with self._bm25_lock:
            # Double-check after acquiring lock
            # (another thread may have built it while we waited for lock)
            if self._bm25 is None:
                self._build_bm25_from_collection()

            return self._bm25 is not None

    # ===== Retrieval =====
    def _meta_match(
        self, meta: dict[str, Any], languages: list[str] | None, versions: list[str] | None
    ) -> bool:
        """
        Check if metadata matches filter criteria.

        ✅ FIX BUG #11: Robust null/empty handling:
        - None filters → no filtering (match all)
        - Empty list [] → no filtering (match all)
        - Non-empty list → filter to matches only
        - Handle None metadata values gracefully
        """
        # ✅ Check if meta is None or empty dict
        if meta is None:
            meta = {}

        # ✅ Languages filter - handle None, empty list, and None values
        if languages is not None and len(languages) > 0:
            lang = meta.get("language")
            # Skip docs with None/missing language if filter is active
            if lang is None:
                return False
            # Check if language matches any in filter list
            if str(lang) not in set(languages):
                return False

        # ✅ Versions filter - handle None, empty list, and None values
        if versions is not None and len(versions) > 0:
            ver = meta.get("version")
            # Skip docs with None/missing version if filter is active
            if ver is None:
                return False
            # Check if version matches any in filter list
            if str(ver) not in set(versions):
                return False

        return True

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        *,
        languages: list[str] | None = None,
        versions: list[str] | None = None,
    ) -> dict[str, Any]:
        # If FAISS backend is enabled and available, use it and map IDs back from Chroma
        if self.vector_backend == "faiss" and _faiss is not None and self._faiss_index is not None:
            try:
                q_emb = self.ollama.embed([query])[0]
                ids, scores = self._faiss_query(q_emb, max(top_k * 5, 25))
                if ids:
                    # Fetch documents/metas for these ids from Chroma
                    try:
                        results = self.collection.get(ids=ids, include=["documents", "metadatas"])  # type: ignore[arg-type]
                        docs_all: list[str] = results.get("documents", [])
                        metas_all: list[dict[str, Any]] = results.get("metadatas", [])
                    except Exception:
                        results = self.collection.get(ids=ids)
                        docs_all = results.get("documents", [])
                        metas_all = results.get("metadatas", [])
                    # Build dict by id to preserve FAISS order
                    id_to_doc = {}
                    id_to_meta = {}
                    # results may return lists aligned with ids param
                    for i, idv in enumerate(ids):
                        if i < len(docs_all):
                            id_to_doc[idv] = docs_all[i]
                        if i < len(metas_all):
                            id_to_meta[idv] = metas_all[i]
                    # Filter and keep order
                    filt_docs: list[str] = []
                    filt_metas: list[dict[str, Any]] = []
                    filt_dists: list[float] = []
                    for idv, s in zip(ids, scores, strict=False):
                        d = id_to_doc.get(idv)
                        m = id_to_meta.get(idv, {})
                        if not d:
                            continue
                        if self._meta_match(m or {}, languages, versions):
                            filt_docs.append(d)
                            filt_metas.append(m)
                            # Convert cosine sim ~ inner product to pseudo distance
                            dist = max(0.0, 1.0 - float(s))
                            filt_dists.append(dist)
                        if len(filt_docs) >= top_k:
                            break
                    return {
                        "documents": filt_docs[:top_k],
                        "metadatas": filt_metas[:top_k],
                        "distances": filt_dists[:top_k],
                        "ids": ids[: len(filt_docs)],
                    }
            except Exception:
                # fallback to chroma below
                pass
        # Default: Chroma vector query
        n_fetch = max(top_k * 5, 25)
        n_fetch = min(n_fetch, 200)
        results = self.collection.query(query_texts=[query], n_results=n_fetch)
        docs_all: list[str] = results.get("documents", [[]])[0]
        metas_all: list[dict[str, Any]] = results.get("metadatas", [[]])[0]
        dists_all: list[float] = results.get("distances", [[]])[0]
        ids_all = results.get("ids", [[]])[0] if "ids" in results else []
        # Lọc theo metadata và giữ thứ tự
        filt_docs: list[str] = []
        filt_metas: list[dict[str, Any]] = []
        filt_dists: list[float] = []
        filt_ids: list[str] = []
        for d, m, dist, idv in zip(
            docs_all, metas_all, dists_all, ids_all or [None] * len(docs_all), strict=False
        ):
            if self._meta_match(m or {}, languages, versions):
                filt_docs.append(d)
                filt_metas.append(m)
                filt_dists.append(dist)
                if ids_all:
                    filt_ids.append(idv)  # type: ignore[arg-type]
            if len(filt_docs) >= top_k:
                break
        return {
            "documents": filt_docs[:top_k],
            "metadatas": filt_metas[:top_k],
            "distances": filt_dists[:top_k],
            "ids": filt_ids[:top_k] if filt_ids else [],
        }

    def retrieve_bm25(
        self,
        query: str,
        top_k: int = 5,
        *,
        languages: list[str] | None = None,
        versions: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self._ensure_bm25():
            return {"documents": [], "metadatas": [], "scores": []}

        with self._bm25_lock:
            q_tokens = self._tokenize(query)
            scores_list = list(self._bm25.get_scores(q_tokens))  # type: ignore[union-attr]
        # chỉ lấy các chỉ số khớp filter theo thứ tự điểm giảm dần
        idxs_sorted = sorted(range(len(scores_list)), key=lambda i: scores_list[i], reverse=True)
        sel: list[int] = []
        for i in idxs_sorted:
            if self._meta_match(self._bm25_metas[i] or {}, languages, versions):
                sel.append(i)
                if len(sel) >= top_k:
                    break
        docs = [self._bm25_docs[i] for i in sel]
        metas = [self._bm25_metas[i] for i in sel]
        scores = [scores_list[i] for i in sel]
        return {"documents": docs, "metadatas": metas, "scores": scores}

    @staticmethod
    def _to_similarity(distances: list[float]) -> list[float]:
        """
        Convert distances to similarities.

        ✅ FIX BUG #12: Handle NaN/Inf gracefully để tránh propagate lỗi!
        """
        sims = []
        for d in distances:
            try:
                # ✅ Safe conversion với NaN/Inf check
                val = float(d)
                if _np.isnan(val) or _np.isinf(val):
                    # Fallback: Inf distance → 0 similarity, NaN → 0
                    sims.append(0.0)
                else:
                    sims.append(1.0 / (1.0 + val))
            except (TypeError, ValueError, ZeroDivisionError):
                # Fallback for any conversion errors
                sims.append(0.0)
        return sims

    @staticmethod
    def _min_max(values: list[float]) -> list[float]:
        """
        Min-max normalization to [0, 1] range.

        ✅ FIX BUG #12: Safe division with edge cases:
        - Empty list → return empty
        - All same values → return all 1.0 (avoid division by zero)
        - NaN/Inf values → filter out gracefully
        """
        if not values:
            return []

        # ✅ Filter out NaN/Inf values để tránh lỗi tính toán
        clean_values = []
        for v in values:
            try:
                val = float(v)
                if not (_np.isnan(val) or _np.isinf(val)):
                    clean_values.append(val)
                else:
                    clean_values.append(0.0)  # Replace NaN/Inf with 0
            except (TypeError, ValueError):
                clean_values.append(0.0)  # Fallback for conversion errors

        if not clean_values:
            return [0.0 for _ in values]

        vmin = min(clean_values)
        vmax = max(clean_values)

        # ✅ Check for division by zero (all values same)
        if abs(vmax - vmin) <= 1e-12:
            return [1.0 for _ in values]

        # ✅ Safe normalization
        return [(v - vmin) / (vmax - vmin) for v in clean_values]

    @staticmethod
    def _make_key(doc: str, meta: dict[str, Any]) -> tuple[str, Any, Any]:
        return (meta.get("source", ""), meta.get("chunk", -1), len(doc))

    def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 5,
        bm25_weight: float = 0.5,
        rrf_enable: bool | None = None,
        rrf_k: int | None = None,
        *,
        languages: list[str] | None = None,
        versions: list[str] | None = None,
    ) -> dict[str, Any]:
        # Fetch candidates
        vec = self.retrieve(query, top_k=top_k, languages=languages, versions=versions)
        bm = self.retrieve_bm25(
            query, top_k=max(top_k, 10), languages=languages, versions=versions
        )  # get a bit more for better merge

        v_docs: list[str] = vec.get("documents", [])
        v_metas: list[dict[str, Any]] = vec.get("metadatas", [])
        v_dists: list[float] = vec.get("distances", [])
        v_sims = self._to_similarity(v_dists)
        v_norm = self._min_max(v_sims)

        b_docs: list[str] = bm.get("documents", [])
        b_metas: list[dict[str, Any]] = bm.get("metadatas", [])
        b_scores: list[float] = bm.get("scores", [])
        b_norm = self._min_max(b_scores)

        # Decide fusion strategy
        use_rrf = RRF_ENABLE_DEFAULT if rrf_enable is None else bool(rrf_enable)
        rrf_k_val = RRF_K_DEFAULT if rrf_k is None else int(rrf_k)

        if use_rrf:
            # Build ranks
            ranks_vec: dict[tuple[str, Any, Any], int] = {}
            for idx, (doc, meta) in enumerate(zip(v_docs, v_metas, strict=False), start=1):
                ranks_vec[self._make_key(doc, meta)] = idx
            ranks_bm: dict[tuple[str, Any, Any], int] = {}
            for idx, (doc, meta) in enumerate(zip(b_docs, b_metas, strict=False), start=1):
                ranks_bm[self._make_key(doc, meta)] = idx
            # Union keys
            keys = set(ranks_vec.keys()) | set(ranks_bm.keys())
            combined = []
            for key in keys:
                r1 = ranks_vec.get(key)
                r2 = ranks_bm.get(key)
                score = 0.0
                if r1 is not None:
                    score += 1.0 / (rrf_k_val + r1)
                if r2 is not None:
                    score += 1.0 / (rrf_k_val + r2)
                # pick representative doc/meta (prefer vector side if available)
                if key in ranks_vec:
                    i = r1 - 1  # type: ignore
                    doc = v_docs[i]
                    meta = v_metas[i]
                else:
                    i = r2 - 1  # type: ignore
                    doc = b_docs[i]
                    meta = b_metas[i]
                combined.append((score, doc, meta))
            combined.sort(key=lambda x: x[0], reverse=True)
            docs = [d for _, d, _ in combined[:top_k]]
            metas = [m for _, _, m in combined[:top_k]]
            return {"documents": docs, "metadatas": metas}
        else:
            # Weighted normalization merge (legacy)
            cand: dict[tuple[str, Any, Any], dict[str, Any]] = {}
            for doc, meta, s in zip(v_docs, v_metas, v_norm, strict=False):
                key = self._make_key(doc, meta)
                cand[key] = {"doc": doc, "meta": meta, "v": s, "b": 0.0}
            for doc, meta, s in zip(b_docs, b_metas, b_norm, strict=False):
                key = self._make_key(doc, meta)
                if key in cand:
                    cand[key]["b"] = s
                else:
                    cand[key] = {"doc": doc, "meta": meta, "v": 0.0, "b": s}
            combined = []
            w = max(0.0, min(1.0, float(bm25_weight)))
            for item in cand.values():
                score = (1.0 - w) * item["v"] + w * item["b"]
                combined.append((score, item["doc"], item["meta"]))
            combined.sort(key=lambda x: x[0], reverse=True)
            docs = [d for _, d, _ in combined[:top_k]]
            metas = [m for _, _, m in combined[:top_k]]
            return {"documents": docs, "metadatas": metas}

    # ===== Prompt & Answer =====
    def build_prompt(self, question: str, context_docs: list[str]) -> str:
        context_block = "\n\n".join([f"[CTX {i+1}]\n{c}" for i, c in enumerate(context_docs)])
        # Hướng dẫn rõ ràng về citations [n] khớp với [CTX n]
        system = (
            "Bạn là trợ lý AI tiếng Việt, trả lời ngắn gọn, chính xác và chỉ dựa trên phần 'Ngữ cảnh' được cung cấp. "
            "Khi sử dụng thông tin từ một CTX, hãy chèn citation dạng [n] với n là số thứ tự CTX tương ứng (ví dụ [1], [2]). "
            "Có thể chèn nhiều [n] nếu nhiều nguồn liên quan. Không tạo citation nếu không có căn cứ trong ngữ cảnh. "
            "Nếu không đủ thông tin để trả lời, hãy nói bạn không chắc thay vì suy đoán."
        )
        prompt = (
            f"{system}\n\n"
            f"Ngữ cảnh:\n{context_block}\n\n"
            f"Câu hỏi: {question}\n\n"
            f"Trả lời (tiếng Việt), nhớ chèn [n] khi trích dẫn CTX phù hợp:"
        )
        return prompt

    def _ensure_rerankers(self) -> None:
        if self._bge_rr is None:
            try:
                self._bge_rr = BgeOnnxReranker()
            except Exception:
                self._bge_rr = None
        if self._embed_rr is None:
            self._embed_rr = SimpleEmbedReranker(self.ollama.embed)

    def _apply_rerank(
        self,
        question: str,
        docs: list[str],
        metas: list[dict[str, Any]],
        top_k: int,
        rr_provider: str | None = None,
        rr_max_k: int | None = None,
        rr_batch_size: int | None = None,
        rr_num_threads: int | None = None,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        # Giới hạn số lượng doc cần rerank (tiết kiệm chi phí)
        maxk = int(rr_max_k) if rr_max_k is not None else len(docs)
        if maxk <= 0:
            maxk = len(docs)
        docs_in = docs[:maxk]
        metas_in = metas[:maxk]

        provider = (rr_provider or "auto").lower()
        # Cập nhật threads cho ONNX nếu được yêu cầu (tạo lại session để áp dụng)
        if rr_num_threads is not None and rr_num_threads > 0:
            try:
                os.environ["ORT_INTRA_OP_THREADS"] = str(int(rr_num_threads))
                os.environ["ORT_INTER_OP_THREADS"] = str(int(rr_num_threads))
            except Exception:
                pass

        self._ensure_rerankers()
        use_bge = False
        if provider in ("auto", "bge") and self._bge_rr and self._bge_rr.available():
            use_bge = True
        elif provider == "bge":
            use_bge = False  # cưỡng bức bge nhưng không available → fallback

        if use_bge and self._bge_rr:
            try:
                bs = (
                    int(rr_batch_size) if rr_batch_size else 32
                )  # Increased from 16 to 32 for better throughput
                return self._bge_rr.rerank(question, docs_in, metas_in, top_k, batch_size=bs)
            except Exception:
                pass
        # Fallback embed
        assert self._embed_rr is not None
        return self._embed_rr.rerank(question, docs_in, metas_in, top_k)

    def _get_llm(self, provider: str | None = None):
        name = (provider or self.default_provider or "ollama").lower()
        if name == "openai":
            if self._openai is None:
                try:
                    self._openai = OpenAIClient()
                except Exception:
                    self._openai = None
            return self._openai or self.ollama
        return self.ollama

    def _gen_cache_key(self, prompt: str, provider: str | None) -> str:
        prov = (provider or self.default_provider or "ollama").lower()
        seed = json.dumps(
            {
                "prov": prov,
                "stamp": getattr(self, "_corpus_stamp", "0"),
                "prompt": prompt,
                "model": os.getenv("LLM_MODEL", "llama3.1:8b"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        try:
            return hashlib.sha256(seed.encode("utf-8")).hexdigest()
        except Exception:
            return str(abs(hash(seed)))

    def generate_text(self, prompt: str, provider: str | None = None) -> str:
        # Cache layer
        key = self._gen_cache_key(prompt, provider)
        cached = self.gen_cache.get(key)
        if cached is not None and cached.strip():
            return cached
        llm = self._get_llm(provider)
        out = llm.generate(prompt)
        try:
            if out and out.strip():
                self.gen_cache.set(key, out)
        except Exception:
            pass
        return out

    def generate_stream(self, prompt: str, provider: str | None = None):
        # If cached, stream from cache to preserve API contract
        key = self._gen_cache_key(prompt, provider)
        cached = self.gen_cache.get(key)
        if cached is not None and cached.strip():
            chunk = 1024

            def _gen():
                s = cached
                for i in range(0, len(s), chunk):
                    yield s[i : i + chunk]

            return _gen()
        llm = self._get_llm(provider)
        return llm.generate_stream(prompt)

    # ===== Rewrite & Aggregate Retrieval =====
    def _rewrite_queries(self, question: str, n: int = 2, provider: str | None = None) -> list[str]:
        n = max(1, min(int(n or 1), 5))
        sys = (
            "Bạn là công cụ rewrite truy vấn. Trả về MẢNG JSON gồm vài biến thể truy vấn ngắn gọn (tiếng Việt), "
            "giữ nguyên ý nghĩa, tối đa N phần tử. Chỉ in JSON, không giải thích."
        )
        ins = (
            f"N={n}. Câu hỏi gốc: {question}\n"
            "Yêu cầu đầu ra: một mảng JSON thuần, ví dụ: [\"câu hỏi 1\", \"câu hỏi 2\"]."
        )
        prompt = f"[SYSTEM]\n{sys}\n[/SYSTEM]\n{ins}"
        try:
            llm = self._get_llm(provider)
            raw = llm.generate(prompt)
            s = raw
            if not s:
                return []
            start = s.find('[')
            end = s.rfind(']')
            if start != -1 and end != -1 and end > start:
                arr_txt = s[start : end + 1]
                data = json.loads(arr_txt)
                outs = [str(x) for x in data if isinstance(x, (str, int, float))]
                outs = [o for o in outs if o.strip()]
                return outs[:n]
        except Exception:
            return []
        return []

    def retrieve_aggregate(
        self,
        question: str,
        *,
        top_k: int = 5,
        method: str = "vector",
        bm25_weight: float = 0.5,
        rrf_enable: bool | None = None,
        rrf_k: int | None = None,
        rewrite_enable: bool = False,
        rewrite_n: int = 2,
        provider: str | None = None,
        languages: list[str] | None = None,
        versions: list[str] | None = None,
    ) -> dict[str, Any]:
        method = (method or "vector").lower()
        queries: list[str] = [question]
        if rewrite_enable:
            try:
                rewrites = self._rewrite_queries(question, n=rewrite_n, provider=provider)
                for rw in rewrites:
                    if rw and rw.strip() and rw.strip() not in queries:
                        queries.append(rw.strip())
            except Exception:
                pass
        # Thu thập kết quả cho từng query
        per_query: list[tuple[list[str], list[dict[str, Any]]]] = []
        for q in queries:
            if method == "bm25":
                r = self.retrieve_bm25(q, top_k=top_k, languages=languages, versions=versions)
            elif method == "hybrid":
                r = self.retrieve_hybrid(
                    q,
                    top_k=top_k,
                    bm25_weight=bm25_weight,
                    rrf_enable=rrf_enable,
                    rrf_k=rrf_k,
                    languages=languages,
                    versions=versions,
                )
            else:
                r = self.retrieve(q, top_k=top_k, languages=languages, versions=versions)
            per_query.append((r.get("documents", []), r.get("metadatas", [])))
        # RRF fuse across rewrites
        if len(per_query) == 1:
            docs, metas = per_query[0]
            return {"documents": docs[:top_k], "metadatas": metas[:top_k]}
        rrf_k_val = RRF_K_DEFAULT if rrf_k is None else int(rrf_k)
        score_map: dict[tuple[str, Any, Any], tuple[float, str, dict[str, Any]]] = {}
        for docs, metas in per_query:
            for idx, (d, m) in enumerate(zip(docs, metas, strict=False), start=1):
                key = self._make_key(d, m)
                inc = 1.0 / (rrf_k_val + idx)
                if key in score_map:
                    cur = score_map[key]
                    score_map[key] = (cur[0] + inc, cur[1], cur[2])
                else:
                    score_map[key] = (inc, d, m)
        combined = sorted(score_map.values(), key=lambda x: x[0], reverse=True)
        out_docs = [d for _, d, _ in combined[:top_k]]
        out_metas = [m for _, _, m in combined[:top_k]]
        return {"documents": out_docs, "metadatas": out_metas}

    def answer(
        self,
        question: str,
        top_k: int = 5,
        method: str = "vector",
        bm25_weight: float = 0.5,
        rerank_enable: bool = False,
        rerank_top_n: int = 10,
        provider: str | None = None,
        rrf_enable: bool | None = None,
        rrf_k: int | None = None,
        rewrite_enable: bool = False,
        rewrite_n: int = 2,
        languages: list[str] | None = None,
        versions: list[str] | None = None,
        rr_provider: str | None = None,
        rr_max_k: int | None = None,
        rr_batch_size: int | None = None,
        rr_num_threads: int | None = None,
    ) -> dict[str, Any]:
        method = (method or "vector").lower()
        base_k = max(top_k, rerank_top_n if rerank_enable else top_k)
        retrieved = self.retrieve_aggregate(
            question,
            top_k=base_k,
            method=method,
            bm25_weight=bm25_weight,
            rrf_enable=rrf_enable,
            rrf_k=rrf_k,
            rewrite_enable=rewrite_enable,
            rewrite_n=rewrite_n,
            provider=provider,
            languages=languages,
            versions=versions,
        )
        docs = retrieved.get("documents", [])
        metas = retrieved.get("metadatas", [])
        if rerank_enable and docs:
            docs, metas = self._apply_rerank(
                question,
                docs,
                metas,
                top_k,
                rr_provider=rr_provider,
                rr_max_k=rr_max_k,
                rr_batch_size=rr_batch_size,
                rr_num_threads=rr_num_threads,
            )
        else:
            docs = docs[:top_k]
            metas = metas[:top_k]
        prompt = self.build_prompt(question, docs)
        reply = self.generate_text(prompt, provider=provider)
        return {
            "answer": reply,
            "contexts": docs,
            "metadatas": metas,
            "method": method,
            "bm25_weight": bm25_weight,
            "rerank_enable": rerank_enable,
            "rerank_top_n": rerank_top_n,
        }

    # ===== Multi-hop =====
    def _decompose(self, question: str, fanout: int = 2) -> list[str]:
        """Dùng LLM để đề xuất một số câu hỏi con ngắn gọn (JSON array).
        An toàn: ép model phải trả về JSON duy nhất; nếu parse thất bại, fallback 1 subquestion = original.
        """
        fanout = max(1, min(int(fanout or 1), 5))
        sys = (
            "Bạn là công cụ phân rã câu hỏi. Hãy trả về mảng JSON các câu hỏi con ngắn gọn (tiếng Việt), "
            "tối đa N phần tử. Chỉ in JSON, không thêm giải thích."
        )
        ins = (
            f"N={fanout}. Câu hỏi gốc: {question}\n"
            "Yêu cầu đầu ra: một mảng JSON thuần, ví dụ: [\"câu hỏi 1\", \"câu hỏi 2\"]."
        )
        prompt = f"[SYSTEM]\n{sys}\n[/SYSTEM]\n{ins}"
        try:
            raw = self.ollama.generate(prompt)
            # Tìm khối JSON array đầu tiên
            start = raw.find('[')
            end = raw.rfind(']')
            if start != -1 and end != -1 and end > start:
                arr_txt = raw[start : end + 1]
                data = json.loads(arr_txt)
                subqs = [str(x) for x in data if isinstance(x, (str, int, float))]
                subqs = [s for s in subqs if s.strip()]
                if subqs:
                    return subqs[:fanout]
        except Exception:
            pass
        return [question]

    def answer_multihop(
        self,
        question: str,
        *,
        depth: int = 2,
        fanout: int = 2,
        top_k: int = 5,
        method: str = "hybrid",
        bm25_weight: float = 0.5,
        rerank_enable: bool = False,
        rerank_top_n: int = 10,
        skip_answer: bool = False,
        rrf_enable: bool | None = None,
        rrf_k: int | None = None,
        fanout_first_hop: int | None = None,
        budget_ms: int | None = None,
        languages: list[str] | None = None,
        versions: list[str] | None = None,
    ) -> dict[str, Any]:
        depth = max(1, min(int(depth or 1), 3))
        fanout = max(1, min(int(fanout or 1), 3))
        if fanout_first_hop is not None:
            try:
                fanout_first_hop = max(1, min(int(fanout_first_hop), 5))
            except Exception:
                fanout_first_hop = None
        budget_ms = int(budget_ms or 0)
        start_ms = int(time.time() * 1000)

        def time_left_ok() -> bool:
            if budget_ms <= 0:
                return True
            return (int(time.time() * 1000) - start_ms) < budget_ms

        agg_docs: list[str] = []
        agg_metas: list[dict[str, Any]] = []
        seen_keys = set()
        subquestions_all: list[str] = []
        cur_questions = [question]
        # Duyệt theo tầng
        for hop_idx in range(depth):
            if not time_left_ok():
                break
            next_questions: list[str] = []
            # Chọn fanout cho hop này
            this_fanout = fanout_first_hop if (hop_idx == 0 and fanout_first_hop) else fanout
            # Decompose mỗi câu hỏi hiện tại
            for q in cur_questions:
                if not time_left_ok():
                    break
                subs = self._decompose(q, fanout=this_fanout)
                subquestions_all.extend(subs)
                # Nếu sát budget, cắt bớt subs
                if budget_ms > 0 and len(subs) > 1 and not time_left_ok():
                    subs = subs[:1]
                next_questions.extend(subs)
            # Retrieve cho tất cả sub-qs của tầng này
            for sq in next_questions:
                if not time_left_ok():
                    break
                base_k = max(top_k, rerank_top_n if rerank_enable else top_k)
                if method == "bm25":
                    retrieved = self.retrieve_bm25(
                        sq, top_k=base_k, languages=languages, versions=versions
                    )
                elif method == "hybrid":
                    retrieved = self.retrieve_hybrid(
                        sq,
                        top_k=base_k,
                        bm25_weight=bm25_weight,
                        rrf_enable=rrf_enable,
                        rrf_k=rrf_k,
                        languages=languages,
                        versions=versions,
                    )
                else:
                    retrieved = self.retrieve(
                        sq, top_k=base_k, languages=languages, versions=versions
                    )
                docs = retrieved.get("documents", [])
                metas = retrieved.get("metadatas", [])
                for d, m in zip(docs, metas, strict=False):
                    key = self._make_key(d, m)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    agg_docs.append(d)
                    agg_metas.append(m)
            cur_questions = next_questions
        # Fallback: nếu không thu được context nào qua multi-hop, thử single-hop trên câu hỏi gốc
        if not agg_docs:
            base_k = max(top_k, rerank_top_n if rerank_enable else top_k)
            if method == "bm25":
                retrieved = self.retrieve_bm25(
                    question, top_k=base_k, languages=languages, versions=versions
                )
            elif method == "hybrid":
                retrieved = self.retrieve_hybrid(
                    question,
                    top_k=base_k,
                    bm25_weight=bm25_weight,
                    languages=languages,
                    versions=versions,
                )
            else:
                retrieved = self.retrieve(
                    question, top_k=base_k, languages=languages, versions=versions
                )
            agg_docs = retrieved.get("documents", [])
            agg_metas = retrieved.get("metadatas", [])

        # Rerank/giới hạn top_k
        if rerank_enable and agg_docs:
            sel_docs, sel_metas = self._apply_rerank(question, agg_docs, agg_metas, top_k)
        else:
            sel_docs = agg_docs[:top_k]
            sel_metas = agg_metas[:top_k]
        prompt = self.build_prompt(question, sel_docs)
        reply = "" if skip_answer else self.generate_text(prompt, provider=None)
        return {
            "answer": reply,
            "contexts": sel_docs,
            "metadatas": sel_metas,
            "method": method,
            "bm25_weight": bm25_weight,
            "rerank_enable": rerank_enable,
            "rerank_top_n": rerank_top_n,
            "depth": depth,
            "fanout": fanout,
            "fanout_first_hop": fanout_first_hop,
            "budget_ms": budget_ms,
            "subquestions": subquestions_all,
        }

    # ===== Filters =====
    def get_filters(self) -> dict[str, list[str]]:
        """
        Get available filters với LRU caching.

        ✅ FIX BUG #7: Dùng LRU cache với TTL để ngăn memory leak
        """
        # Cache key by collection (db)
        cache_key = f"{self.persist_dir}:{self.collection_name}"

        # Try to get from cache
        cached = self._filters_cache.get(cache_key)
        if cached is not None:
            # Cache hit!
            return {"languages": cached[0], "versions": cached[1]}

        # Cache miss - query database
        try:
            results = self.collection.get(include=["metadatas"])  # type: ignore[arg-type]
        except Exception:
            results = self.collection.get()

        metas: list[dict[str, Any]] = results.get("metadatas", [])  # type: ignore[assignment]
        langs_set = set()
        vers_set = set()

        for m in metas:
            v = m.get("version")
            if isinstance(v, str) and v.strip():
                vers_set.add(v.strip())
            l = m.get("language")
            if isinstance(l, str) and l.strip():
                langs_set.add(l.strip())

        langs = sorted(langs_set)
        vers = sorted(vers_set)

        # Store in LRU cache as tuple
        self._filters_cache.set(cache_key, (langs, vers))

        return {"languages": langs, "versions": vers}
