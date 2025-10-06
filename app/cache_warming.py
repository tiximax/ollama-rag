"""
🔥 Cache Warming - Pre-load popular queries vào cache khi khởi động

Thay vì đợi users query lần đầu (chậm), ta sẽ "warm" cache bằng cách
pre-compute embeddings và results cho các queries phổ biến!

Benefits:
- ✅ Faster first-time user experience
- ✅ Reduced cold-start latency
- ✅ Better cache hit rates from the start
- ✅ Smoother performance under load
"""

import json
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    🔥 Cache Warmer - Làm nóng cache với popular queries!

    Strategies:
    1. **Static warming**: Load từ file config (queries.json)
    2. **Analytics-based**: Load từ query logs (most frequent)
    3. **Embeddings-only**: Chỉ pre-compute embeddings, không query LLM
    """

    def __init__(
        self,
        popular_queries_file: str | None = None,
        analytics_log_dir: str | None = None,
        max_queries: int = 50,
    ):
        """
        Args:
            popular_queries_file: Path to JSON file with popular queries
            analytics_log_dir: Directory containing query logs
            max_queries: Maximum number of queries to warm
        """
        self.popular_queries_file = popular_queries_file
        self.analytics_log_dir = analytics_log_dir
        self.max_queries = max_queries

    def load_popular_queries(self) -> list[str]:
        """
        Load popular queries từ nhiều sources.

        Returns:
            List of popular query strings
        """
        queries: list[str] = []

        # 1. Load from static config file
        if self.popular_queries_file and os.path.exists(self.popular_queries_file):
            try:
                with open(self.popular_queries_file, encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        queries.extend(data)
                    elif isinstance(data, dict) and 'queries' in data:
                        queries.extend(data['queries'])
                logger.info(f"✅ Loaded {len(queries)} queries from config file")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load queries from {self.popular_queries_file}: {e}")

        # 2. Load from analytics logs (most frequent queries)
        if self.analytics_log_dir and os.path.exists(self.analytics_log_dir):
            try:
                log_queries = self._extract_popular_from_logs()
                queries.extend(log_queries)
                logger.info(f"✅ Loaded {len(log_queries)} queries from analytics logs")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load queries from logs: {e}")

        # 3. Fallback: Default popular queries
        if not queries:
            queries = self._get_default_queries()
            logger.info(f"ℹ️ Using {len(queries)} default popular queries")

        # Deduplicate and limit
        queries = list(dict.fromkeys(queries))  # Remove duplicates while preserving order
        return queries[: self.max_queries]

    def _extract_popular_from_logs(self) -> list[str]:
        """Extract most frequent queries from analytics logs."""
        query_counts: dict[str, int] = {}

        log_dir = Path(self.analytics_log_dir)
        for log_file in log_dir.glob("*.jsonl"):
            try:
                with open(log_file, encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            query = entry.get('query', '').strip()
                            if query and len(query) > 5:  # Skip trivial queries
                                query_counts[query] = query_counts.get(query, 0) + 1
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.debug(f"Skipping log file {log_file}: {e}")

        # Sort by frequency and return top queries
        sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
        return [q for q, _ in sorted_queries[: self.max_queries]]

    def _get_default_queries(self) -> list[str]:
        """Default popular queries cho RAG systems."""
        return [
            # General RAG queries
            "What is RAG?",
            "How does Retrieval Augmented Generation work?",
            "What are the benefits of using RAG?",
            # Technical queries
            "How do I configure the system?",
            "What are the API endpoints?",
            "How to upload documents?",
            "How to ingest data?",
            # Performance queries
            "How to improve query performance?",
            "What is the response time?",
            "How many documents can it handle?",
            # Troubleshooting
            "Why is my query slow?",
            "How to fix errors?",
            "Connection issues",
            # Features
            "What models are supported?",
            "Can I use custom embeddings?",
            "How to enable caching?",
        ]

    async def warm_cache_async(
        self,
        cache: Any,
        embedder: Callable,
        query_fn: Callable | None = None,
        embeddings_only: bool = False,
    ) -> dict[str, Any]:
        """
        Asynchronously warm cache with popular queries.

        Args:
            cache: Cache object with get/set methods
            embedder: Function to generate embeddings
            query_fn: Optional function to execute full queries
            embeddings_only: If True, only pre-compute embeddings, skip full query

        Returns:
            Dict with warming statistics
        """
        import asyncio

        start_time = time.time()
        queries = self.load_popular_queries()

        logger.info(f"🔥 Starting cache warming for {len(queries)} queries...")

        stats = {
            "total_queries": len(queries),
            "embeddings_cached": 0,
            "full_queries_cached": 0,
            "errors": 0,
            "duration_seconds": 0.0,
        }

        tasks = []
        for query in queries:
            tasks.append(
                self._warm_single_query_async(query, cache, embedder, query_fn, embeddings_only)
            )

        # Execute in parallel with concurrency limit
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect statistics
        for result in results:
            if isinstance(result, Exception):
                stats["errors"] += 1
                logger.debug(f"Warming error: {result}")
            elif result:
                if result.get("embedding_cached"):
                    stats["embeddings_cached"] += 1
                if result.get("full_query_cached"):
                    stats["full_queries_cached"] += 1

        stats["duration_seconds"] = time.time() - start_time

        logger.info(
            f"✅ Cache warming complete! "
            f"Embeddings: {stats['embeddings_cached']}/{stats['total_queries']}, "
            f"Full queries: {stats['full_queries_cached']}/{stats['total_queries']}, "
            f"Errors: {stats['errors']}, "
            f"Duration: {stats['duration_seconds']:.2f}s"
        )

        return stats

    async def _warm_single_query_async(
        self,
        query: str,
        cache: Any,
        embedder: Callable,
        query_fn: Callable | None,
        embeddings_only: bool,
    ) -> dict[str, bool]:
        """Warm a single query asynchronously."""
        import asyncio

        result = {"embedding_cached": False, "full_query_cached": False}

        try:
            # Check if already cached
            cached_result = cache.get(query, embedder)
            if cached_result is not None:
                return result  # Already cached, skip

            if embeddings_only:
                # Just pre-compute embedding and cache empty result
                dummy_result = {"embeddings_preloaded": True}
                cache.set(query, dummy_result, embedder)
                result["embedding_cached"] = True
            else:
                # Execute full query and cache result
                if query_fn:
                    query_result = await asyncio.to_thread(query_fn, query)
                    cache.set(query, query_result, embedder)
                    result["full_query_cached"] = True
                else:
                    # Fallback: Just cache embeddings
                    dummy_result = {"embeddings_preloaded": True}
                    cache.set(query, dummy_result, embedder)
                    result["embedding_cached"] = True

        except Exception as e:
            logger.debug(f"Failed to warm query '{query}': {e}")
            raise

        return result

    def warm_cache_sync(
        self,
        cache: Any,
        embedder: Callable,
        query_fn: Callable | None = None,
        embeddings_only: bool = True,
    ) -> dict[str, Any]:
        """
        Synchronously warm cache (blocking).

        Use this for startup warming when you can afford blocking.
        """
        start_time = time.time()
        queries = self.load_popular_queries()

        logger.info(f"🔥 Starting cache warming for {len(queries)} queries (sync)...")

        stats = {
            "total_queries": len(queries),
            "embeddings_cached": 0,
            "full_queries_cached": 0,
            "errors": 0,
            "duration_seconds": 0.0,
        }

        for query in queries:
            try:
                # Check if already cached
                cached_result = cache.get(query, embedder)
                if cached_result is not None:
                    continue  # Already cached

                if embeddings_only:
                    # Just pre-compute embedding
                    dummy_result = {"embeddings_preloaded": True}
                    cache.set(query, dummy_result, embedder)
                    stats["embeddings_cached"] += 1
                else:
                    # Execute full query
                    if query_fn:
                        query_result = query_fn(query)
                        cache.set(query, query_result, embedder)
                        stats["full_queries_cached"] += 1
                    else:
                        dummy_result = {"embeddings_preloaded": True}
                        cache.set(query, dummy_result, embedder)
                        stats["embeddings_cached"] += 1

            except Exception as e:
                stats["errors"] += 1
                logger.debug(f"Failed to warm query '{query}': {e}")

        stats["duration_seconds"] = time.time() - start_time

        logger.info(
            f"✅ Cache warming complete! "
            f"Embeddings: {stats['embeddings_cached']}/{stats['total_queries']}, "
            f"Full queries: {stats['full_queries_cached']}/{stats['total_queries']}, "
            f"Errors: {stats['errors']}, "
            f"Duration: {stats['duration_seconds']:.2f}s"
        )

        return stats


# Example usage
if __name__ == "__main__":
    # Mock cache and embedder for testing
    class MockCache:
        def __init__(self):
            self.data = {}

        def get(self, query, embedder):
            return self.data.get(query)

        def set(self, query, result, embedder):
            self.data[query] = result

    class MockEmbedder:
        def __call__(self, queries):
            return [[0.1] * 128 for _ in queries]

    logging.basicConfig(level=logging.INFO)

    cache = MockCache()
    embedder = MockEmbedder()
    warmer = CacheWarmer(max_queries=10)

    print("🧪 Testing Cache Warmer...")
    stats = warmer.warm_cache_sync(cache, embedder, embeddings_only=True)

    print("\n📊 Warming Statistics:")
    print(f"  - Total queries: {stats['total_queries']}")
    print(f"  - Cached: {stats['embeddings_cached']}")
    print(f"  - Errors: {stats['errors']}")
    print(f"  - Duration: {stats['duration_seconds']:.2f}s")
    print(f"  - Cache size: {len(cache.data)}")

    print("\n✅ Cache Warmer test completed!")
