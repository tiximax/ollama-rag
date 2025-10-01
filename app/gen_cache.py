import os
import time
import sqlite3
from typing import Optional


class GenCache:
    """SQLite-based cache for generated LLM answers.

    Key design:
    - Each DB (persist_dir) has its own cache file: persist_dir/gen_cache.sqlite
    - TTL-based reads; no background GC (simple and robust)
    - Thread-safe enough for single-process use (FastAPI default). For heavy concurrency, tune pragmas.
    """

    def __init__(self, db_dir: str, enabled: bool = True, ttl_sec: int = 86400) -> None:
        self.enabled = bool(enabled)
        self.ttl = int(ttl_sec) if ttl_sec is not None else 0
        self.path = os.path.join(db_dir, "gen_cache.sqlite")
        self._ensure()

    def _ensure(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with sqlite3.connect(self.path) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS gen_cache (key TEXT PRIMARY KEY, value TEXT, ts INTEGER)"
                )
                # basic index on ts for optional cleanup
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_gen_cache_ts ON gen_cache(ts)"
                )
        except Exception:
            # If cache initialization fails, disable to avoid breaking request path
            self.enabled = False

    def get(self, key: str) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            now = int(time.time())
            with sqlite3.connect(self.path) as conn:
                row = conn.execute(
                    "SELECT value, ts FROM gen_cache WHERE key=?", (key,)
                ).fetchone()
                if not row:
                    return None
                val, ts = row[0], int(row[1] or 0)
                if self.ttl > 0 and (now - ts) > self.ttl:
                    return None
                return str(val)
        except Exception:
            return None

    def set(self, key: str, value: str) -> None:
        if not self.enabled:
            return
        try:
            now = int(time.time())
            with sqlite3.connect(self.path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO gen_cache(key, value, ts) VALUES(?,?,?)",
                    (key, value, now),
                )
        except Exception:
            # best-effort; ignore failures
            return