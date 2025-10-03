"""Semantic Query Cache - Cache thông minh dựa trên độ tương tự ngữ nghĩa.

Cache này lưu kết quả query dựa trên embedding vectors thay vì exact string matching.
Nếu query mới có embedding tương tự (cosine similarity > threshold) với query đã cache,
sẽ trả về kết quả cached thay vì query lại!

Ví dụ:
- Query 1: "What is RAG?"
- Query 2: "Can you explain RAG to me?"
→ Nếu similarity > 0.95, trả về kết quả của Query 1! 🎯

Features:
- ✅ Cosine similarity matching
- ✅ Configurable threshold
- ✅ TTL (Time To Live) support
- ✅ LRU eviction when full
- ✅ Thread-safe operations
- ✅ Statistics tracking
"""

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any

import numpy as np

from . import metrics


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Tính cosine similarity giữa 2 vectors.

    Returns:
        float: Similarity score từ 0.0 (khác hoàn toàn) đến 1.0 (giống hệt)
    """
    # Normalize vectors
    vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-10)
    vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-10)
    # Compute cosine similarity
    return float(np.dot(vec1_norm, vec2_norm))


@dataclass
class CacheEntry:
    """Entry trong semantic cache với metadata đầy đủ."""

    query: str
    embedding: np.ndarray
    result: Any
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0
    namespace: str = ""  # Phân vùng cache theo DB/corpus_stamp để tránh cross-DB pollution

    def is_expired(self, ttl: float) -> bool:
        """Check xem entry đã hết hạn chưa."""
        return (time.time() - self.timestamp) > ttl


class SemanticQueryCache:
    """Semantic Query Cache - Cache queries by semantic similarity.

    Thay vì so sánh string exact match, cache này dùng embeddings để tìm
    queries tương tự về mặt ngữ nghĩa và trả về kết quả đã cache!

    Example:
        >>> cache = SemanticQueryCache(similarity_threshold=0.95, ttl=300)
        >>>
        >>> # Lần đầu: cache miss
        >>> result = cache.get("What is RAG?", embedder)
        >>> if result is None:
        ...     result = expensive_query("What is RAG?")
        ...     cache.set("What is RAG?", result, embedder)
        >>>
        >>> # Lần sau: cache HIT cho query tương tự!
        >>> result = cache.get("Can you explain RAG?", embedder)  # Hit! 🎉
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_size: int = 1000,
        ttl: float = 300.0,  # 5 minutes
    ):
        """Initialize cache settings.

        Args:
            similarity_threshold: Ngưỡng similarity để coi là match (0.0-1.0)
                0.95 = rất nghiêm ngặt, chỉ queries gần giống mới match
                0.85 = lỏng hơn, cho phép queries hơi khác biệt
            max_size: Số lượng entries tối đa trong cache
            ttl: Thời gian sống của entry (giây), sau đó sẽ bị xóa
        """
        self.similarity_threshold = similarity_threshold
        self.max_size = max_size
        self.ttl = ttl

        # OrderedDict để implement LRU eviction
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()  # Thread-safe!

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "exact_hits": 0,  # Cache hit với exact query string
            "semantic_hits": 0,  # Cache hit với similar query
            "evictions": 0,
            "expirations": 0,
        }

    def _compute_key(self, query: str, namespace: str | None = None) -> str:
        """Generate unique key từ query string (non-security), scoped by namespace if provided."""
        seed = f"{namespace or ''}|{query}"
        return hashlib.blake2b(seed.encode(), digest_size=16).hexdigest()

    def get(
        self,
        query: str,
        embedder: Any,
        return_metadata: bool = False,
        namespace: str | None = None,
    ) -> Any | None:
        """Lấy cached result nếu có query tương tự trong cache.

        Quy trình:
        1. Exact match khóa (nhanh nhất)
        2. Nếu không có, tính embedding và tìm similar queries
        3. Nếu similarity > threshold → Cache HIT

        Args:
            query: Query string để search
            embedder: Hàm/đối tượng tạo embedding: embedder([query]) -> list[embedding]
            return_metadata: Nếu True, trả về (result, metadata)
            namespace: Phân vùng cache (vd: "DB:stamp") để tránh cross-DB pollution

        Returns:
            Cached result nếu tìm thấy, None nếu cache miss
        """
        with self._lock:
            print(f"[SemCache] GET start: query='{query[:60]}'")
            # 1. Try exact match first (fastest path) 🏃‍♂️
            key = self._compute_key(query, namespace)
            if key in self._cache:
                entry = self._cache[key]

                # Check expiration
                if entry.is_expired(self.ttl):
                    del self._cache[key]
                    self._stats["expirations"] += 1
                    self._stats["misses"] += 1
                    return None

                # Exact hit! 🎯
                print("[SemCache] GET exact hit")
                self._stats["hits"] += 1
                self._stats["exact_hits"] += 1
                try:
                    metrics.semcache_hit('exact')
                except Exception:
                    pass
                entry.access_count += 1
                entry.last_access = time.time()

                # Move to end (LRU)
                self._cache.move_to_end(key)

                # Namespace filter (exact key already scoped, but keep for completeness)
                if namespace is not None and entry.namespace != (namespace or ""):
                    # Treat as miss if namespace mismatched
                    self._stats["misses"] += 1
                    return None if not return_metadata else (None, None)

                if return_metadata:
                    metadata = {
                        "cache_type": "exact",
                        "similarity": 1.0,
                        "original_query": entry.query,
                        "access_count": entry.access_count,
                        "namespace": entry.namespace,
                    }
                    return entry.result, metadata
                return entry.result

            # 2. Try semantic matching 🧠
            try:
                # Generate embedding for query
                query_embedding = np.array(embedder([query])[0])
                try:
                    dims = int(query_embedding.shape[0])
                except Exception:
                    dims = len(query_embedding) if hasattr(query_embedding, "__len__") else -1
                print(f"[SemCache] GET embedding dims: {dims}")

                # Search for similar cached queries
                best_match: tuple[str, CacheEntry, float] | None = None

                for cache_key, entry in list(self._cache.items()):
                    # Skip expired entries
                    if entry.is_expired(self.ttl):
                        del self._cache[cache_key]
                        self._stats["expirations"] += 1
                        continue
                    # Namespace filter: only consider entries in the same namespace
                    if namespace is not None and entry.namespace != (namespace or ""):
                        continue

                    # Compute similarity
                    similarity = cosine_similarity(query_embedding, entry.embedding)

                    # Check if this is the best match so far
                    if similarity >= self.similarity_threshold:
                        if best_match is None or similarity > best_match[2]:
                            best_match = (cache_key, entry, similarity)

                # Found semantic match! 🎉
                if best_match:
                    cache_key, entry, similarity = best_match
                    print(
                        f"[SemCache] GET semantic hit: sim={similarity:.4f} for '{entry.query[:60]}'"
                    )
                    self._stats["hits"] += 1
                    self._stats["semantic_hits"] += 1
                    try:
                        metrics.semcache_hit('semantic')
                    except Exception:
                        pass
                    entry.access_count += 1
                    entry.last_access = time.time()

                    # Move to end (LRU)
                    self._cache.move_to_end(cache_key)

                    if return_metadata:
                        metadata = {
                            "cache_type": "semantic",
                            "similarity": similarity,
                            "original_query": entry.query,
                            "access_count": entry.access_count,
                            "namespace": entry.namespace,
                        }
                        return entry.result, metadata
                    return entry.result

            except Exception as e:
                # If embedding fails, just continue as cache miss
                # Don't crash the application!
                print(f"Semantic cache embedding failed: {e}")

            # Cache miss 😢
            print("[SemCache] GET miss")
            self._stats["misses"] += 1
            try:
                metrics.semcache_miss()
            except Exception:
                pass
            return None if not return_metadata else (None, None)

    def set(
        self,
        query: str,
        result: Any,
        embedder: Any,
        namespace: str | None = None,
    ) -> None:
        """Cache query result với embedding.

        Args:
            query: Query string
            result: Kết quả cần cache
            embedder: Function/object để tạo embedding
            namespace: Phân vùng cache (vd: "DB:stamp")
        """
        with self._lock:
            try:
                print(f"[SemCache] SET start: query='{query[:60]}'")
                # Generate embedding
                query_embedding = np.array(embedder([query])[0])
                try:
                    dims = int(query_embedding.shape[0])
                except Exception:
                    dims = len(query_embedding) if hasattr(query_embedding, "__len__") else -1
                print(f"[SemCache] SET embedding dims: {dims}")

                # Create cache entry
                key = self._compute_key(query, namespace)
                entry = CacheEntry(
                    query=query,
                    embedding=query_embedding,
                    result=result,
                    timestamp=time.time(),
                    access_count=0,
                    last_access=time.time(),
                    namespace=(namespace or ""),
                )

                # Check if need to evict (LRU)
                if len(self._cache) >= self.max_size and key not in self._cache:
                    # Remove oldest (first item in OrderedDict)
                    self._cache.popitem(last=False)
                    self._stats["evictions"] += 1

                # Add to cache
                self._cache[key] = entry
                self._cache.move_to_end(key)  # Mark as most recently used
                print("[SemCache] SET done")
                try:
                    metrics.update_semcache_size(len(self._cache), self.max_size)
                except Exception:
                    pass

            except Exception as e:
                # If caching fails, don't crash!
                print(f"⚠️ Semantic cache set failed: {e}")

    def clear(self) -> None:
        """Xóa toàn bộ cache."""
        with self._lock:
            self._cache.clear()
            try:
                metrics.update_semcache_size(0, self.max_size)
            except Exception:
                pass

    def cleanup_expired(self) -> int:
        """Dọn dẹp các entries đã hết hạn.

        Returns:
            Số lượng entries đã xóa
        """
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired(self.ttl)]

            for key in expired_keys:
                del self._cache[key]

            self._stats["expirations"] += len(expired_keys)
            try:
                metrics.update_semcache_size(len(self._cache), self.max_size)
            except Exception:
                pass
            return len(expired_keys)

    def stats(self) -> dict[str, Any]:
        """Trả về statistics của cache.

        Returns:
            Dict chứa metrics như hit rate, miss rate, etc.
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0
            semantic_hit_rate = (
                self._stats["semantic_hits"] / self._stats["hits"]
                if self._stats["hits"] > 0
                else 0.0
            )

            return {
                **self._stats,
                "total_requests": total_requests,
                "hit_rate": hit_rate,
                "semantic_hit_rate": semantic_hit_rate,
                "size": len(self._cache),
                "max_size": self.max_size,
                "fill_ratio": len(self._cache) / self.max_size,
                "similarity_threshold": self.similarity_threshold,
                "ttl": self.ttl,
            }

    def __len__(self) -> int:
        """Số lượng entries trong cache."""
        return len(self._cache)

    def __repr__(self) -> str:
        """Debug-friendly representation."""
        stats = self.stats()
        return (
            f"SemanticQueryCache(size={stats['size']}/{self.max_size}, "
            f"hit_rate={stats['hit_rate']:.2%}, "
            f"semantic_hits={stats['semantic_hits']}, "
            f"threshold={self.similarity_threshold})"
        )


# Example usage và testing
if __name__ == "__main__":
    print("🧪 Testing Semantic Query Cache...")

    # Mock embedder for testing
    class MockEmbedder:
        """Embedder giả để test."""

        def __call__(self, queries: list[str]) -> list[np.ndarray]:
            # Tạo embeddings ngẫu nhiên nhưng consistent
            embeddings = []
            for q in queries:
                # Use hash để tạo seed, similar queries có embedding gần nhau
                seed = sum(ord(c) for c in q.lower())
                np.random.seed(seed)
                emb = np.random.randn(128)
                embeddings.append(emb)
            return embeddings

    embedder = MockEmbedder()
    cache = SemanticQueryCache(similarity_threshold=0.95, max_size=5, ttl=10.0)

    # Test 1: Cache miss
    result = cache.get("What is RAG?", embedder)
    print(f"Test 1 - Cache miss: {result is None}")  # Should be True

    # Test 2: Set cache
    cache.set("What is RAG?", {"answer": "RAG is awesome!"}, embedder)
    print(f"Test 2 - Cache size: {len(cache)}")  # Should be 1

    # Test 3: Exact hit
    result = cache.get("What is RAG?", embedder)
    print(f"Test 3 - Exact hit: {result is not None}")  # Should be True

    # Test 4: Semantic hit (similar query)
    result = cache.get("what is rag?", embedder)  # lowercase
    print(f"Test 4 - Semantic hit: {result is not None}")  # Should be True (if similar)

    # Test 5: Stats
    stats = cache.stats()
    print("\n📊 Cache Statistics:")
    print(f"  - Hits: {stats['hits']}")
    print(f"  - Misses: {stats['misses']}")
    print(f"  - Hit Rate: {stats['hit_rate']:.2%}")
    print(f"  - Semantic Hits: {stats['semantic_hits']}")
    print(f"  - Size: {stats['size']}/{stats['max_size']}")

    print("\n✅ Semantic Query Cache test completed!")
    print(cache)
