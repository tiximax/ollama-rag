"""
Cache utilities with LRU eviction and TTL - Ngăn memory leaks 🧹

Module này cung cấp LRU cache với TTL và size limit để
tự động cleanup expired entries, ngăn memory leaks.
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Generic, TypeVar

T = TypeVar('T')


class LRUCacheWithTTL(Generic[T]):
    """
    LRU Cache với TTL (Time-To-Live) và size limit.

    Features:
    - ✅ LRU eviction (Least Recently Used)
    - ✅ TTL expiration (auto-cleanup)
    - ✅ Size limit (prevent unbounded growth)
    - ✅ Thread-safe operations
    - ✅ Automatic periodic cleanup

    Example:
        >>> cache = LRUCacheWithTTL[list](max_size=100, ttl=300)
        >>> cache.set("key", ["value1", "value2"])
        >>> cache.get("key")  # ['value1', 'value2']
        >>> # After 300 seconds...
        >>> cache.get("key")  # None (expired)
    """

    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items (default: 100)
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if ttl < 1:
            raise ValueError("ttl must be >= 1")

        self.max_size = max_size
        self.ttl = ttl

        # OrderedDict maintains insertion order for LRU
        self._cache: OrderedDict[str, T] = OrderedDict()
        self._timestamps: dict[str, float] = {}
        self._lock = threading.RLock()  # Reentrant lock

        # Stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> T | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, else None
        """
        with self._lock:
            # Check if key exists
            if key not in self._cache:
                self._misses += 1
                return None

            # Check if expired
            timestamp = self._timestamps.get(key, 0)
            if time.time() - timestamp >= self.ttl:
                # Expired - remove and return None
                del self._cache[key]
                del self._timestamps[key]
                self._misses += 1
                return None

            # Hit! Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def set(self, key: str, value: T) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # If key exists, update and move to end
            if key in self._cache:
                self._cache[key] = value
                self._timestamps[key] = time.time()
                self._cache.move_to_end(key)
                return

            # Check if cache is full
            if len(self._cache) >= self.max_size:
                # Evict least recently used (first item)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
                self._evictions += 1

            # Add new item
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired items.

        Returns:
            Number of items removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [key for key, ts in self._timestamps.items() if now - ts >= self.ttl]

            for key in expired_keys:
                del self._cache[key]
                del self._timestamps[key]

            return len(expired_keys)

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with stats (hits, misses, hit_rate, etc.)
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "evictions": self._evictions,
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def __repr__(self) -> str:
        """String representation."""
        stats = self.stats()
        return (
            f"LRUCacheWithTTL(size={stats['size']}/{stats['max_size']}, "
            f"ttl={stats['ttl']}s, hit_rate={stats['hit_rate']}%)"
        )


class PeriodicCleanupCache(LRUCacheWithTTL[T]):
    """
    LRU Cache với automatic periodic cleanup.

    Extends LRUCacheWithTTL với background thread để
    tự động cleanup expired entries định kỳ.

    Example:
        >>> cache = PeriodicCleanupCache[str](max_size=100, ttl=300, cleanup_interval=60)
        >>> cache.set("key", "value")
        >>> # Cache tự động cleanup expired entries mỗi 60 giây
    """

    def __init__(self, max_size: int = 100, ttl: int = 300, cleanup_interval: int = 60):
        """
        Initialize cache với periodic cleanup.

        Args:
            max_size: Maximum cache size
            ttl: Time-to-live in seconds
            cleanup_interval: Cleanup interval in seconds (default: 60)
        """
        super().__init__(max_size, ttl)

        self.cleanup_interval = cleanup_interval
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()

        # Start cleanup thread
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread."""

        def cleanup_loop():
            while not self._stop_cleanup.is_set():
                # Wait for interval or stop event
                if self._stop_cleanup.wait(self.cleanup_interval):
                    break  # Stop requested

                # Cleanup expired entries
                try:
                    removed = self.cleanup_expired()
                    if removed > 0:
                        import logging

                        logging.debug(f"Cache cleanup: removed {removed} expired entries")
                except Exception as e:
                    import logging

                    logging.error(f"Cache cleanup error: {e}")

        self._cleanup_thread = threading.Thread(
            target=cleanup_loop,
            daemon=True,  # Don't block app shutdown
            name="CacheCleanupThread",
        )
        self._cleanup_thread.start()

    def stop_cleanup(self) -> None:
        """Stop the cleanup thread."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=2.0)

    def __del__(self) -> None:
        """Destructor - stop cleanup thread."""
        try:
            self.stop_cleanup()
        except Exception:
            pass
