"""
🚀 Parallel Retrieval - Execute multiple retrieval methods concurrently!

Thay vì chạy sequential (vector → BM25 → hybrid), chạy song song để giảm latency!

Benefits:
- ✅ -30% to -50% retrieval latency
- ✅ Better resource utilization
- ✅ Smoother user experience
- ✅ Backward compatible (same API)

Example:
    Sequential:  Vector (200ms) → BM25 (100ms) → Hybrid (300ms) = 600ms total
    Parallel:    All concurrent = 300ms total (slowest one) 🚀
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievalResult:
    """Result from a single retrieval method."""

    method: str
    documents: list[str]
    metadatas: list[dict[str, Any]]
    scores: list[float] | None = None
    duration_ms: float = 0.0
    error: str | None = None


class ParallelRetriever:
    """
    🚀 Parallel Retriever - Run multiple retrieval methods concurrently!

    Supports:
    - Vector search
    - BM25 search
    - Hybrid search (RRF)
    - Custom retrieval functions

    Usage:
        >>> retriever = ParallelRetriever(engine)
        >>>
        >>> # Sequential (slow)
        >>> vector = engine.retrieve(query, top_k=10)
        >>> bm25 = engine.retrieve_bm25(query, top_k=10)
        >>> # Total: vector_time + bm25_time
        >>>
        >>> # Parallel (fast!)
        >>> results = await retriever.retrieve_parallel(
        ...     query,
        ...     methods=["vector", "bm25"],
        ...     top_k=10
        ... )
        >>> # Total: max(vector_time, bm25_time) ⚡
    """

    def __init__(self, engine: Any, max_workers: int = 3):
        """
        Args:
            engine: RagEngine instance with retrieval methods
            max_workers: Max parallel workers (default 3 = vector + bm25 + hybrid)
        """
        self.engine = engine
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def retrieve_parallel(
        self,
        query: str,
        methods: list[str] | None = None,
        top_k: int = 10,
        **kwargs,
    ) -> dict[str, RetrievalResult]:
        """
        Retrieve from multiple methods in parallel.

        Args:
            query: Query string
            methods: List of methods to run ["vector", "bm25", "hybrid"]
            top_k: Number of documents to retrieve
            **kwargs: Additional args passed to retrieval methods
                     (bm25_weight, rrf_enable, rrf_k, etc.)

        Returns:
            Dict mapping method name to RetrievalResult
        """
        # Default methods if not specified
        if methods is None:
            methods = ["vector", "bm25"]

        # Create tasks for each method
        tasks = []
        for method in methods:
            tasks.append(self._retrieve_single_async(query, method, top_k, **kwargs))

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert to dict
        results_dict = {}
        for i, method in enumerate(methods):
            if isinstance(results[i], Exception):
                # Error occurred
                results_dict[method] = RetrievalResult(
                    method=method,
                    documents=[],
                    metadatas=[],
                    error=str(results[i]),
                )
            else:
                results_dict[method] = results[i]

        return results_dict

    async def _retrieve_single_async(
        self,
        query: str,
        method: str,
        top_k: int,
        **kwargs,
    ) -> RetrievalResult:
        """
        Execute a single retrieval method asynchronously.

        Wraps synchronous engine methods in asyncio.to_thread for true parallelism.
        """
        start_time = time.time()

        try:
            # Execute in thread pool (engine methods are sync)
            if method == "vector":
                raw_result = await asyncio.to_thread(
                    self.engine.retrieve,
                    query,
                    top_k=top_k,
                    languages=kwargs.get("languages"),
                    versions=kwargs.get("versions"),
                )

            elif method == "bm25":
                raw_result = await asyncio.to_thread(
                    self.engine.retrieve_bm25,
                    query,
                    top_k=top_k,
                    languages=kwargs.get("languages"),
                    versions=kwargs.get("versions"),
                )

            elif method == "hybrid":
                raw_result = await asyncio.to_thread(
                    self.engine.retrieve_hybrid,
                    query,
                    top_k=top_k,
                    bm25_weight=kwargs.get("bm25_weight", 0.5),
                    rrf_enable=kwargs.get("rrf_enable", True),
                    rrf_k=kwargs.get("rrf_k", 60),
                    languages=kwargs.get("languages"),
                    versions=kwargs.get("versions"),
                )

            else:
                raise ValueError(f"Unknown method: {method}")

            duration_ms = (time.time() - start_time) * 1000

            return RetrievalResult(
                method=method,
                documents=raw_result.get("documents", []),
                metadatas=raw_result.get("metadatas", []),
                scores=raw_result.get("scores"),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return RetrievalResult(
                method=method,
                documents=[],
                metadatas=[],
                duration_ms=duration_ms,
                error=str(e),
            )

    def merge_results(
        self,
        results: dict[str, RetrievalResult],
        strategy: str = "rrf",
        top_k: int = 10,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Merge results from multiple retrieval methods.

        Args:
            results: Dict of RetrievalResult from retrieve_parallel
            strategy: Merging strategy ["rrf", "concatenate", "vote"]
            top_k: Final number of documents after merging
            **kwargs: Strategy-specific parameters (e.g., rrf_k)

        Returns:
            Merged result dict with documents and metadatas
        """
        if strategy == "rrf":
            return self._merge_rrf(results, top_k, kwargs.get("rrf_k", 60))
        elif strategy == "concatenate":
            return self._merge_concatenate(results, top_k)
        elif strategy == "vote":
            return self._merge_vote(results, top_k)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")

    def _merge_rrf(
        self,
        results: dict[str, RetrievalResult],
        top_k: int,
        rrf_k: int = 60,
    ) -> dict[str, Any]:
        """
        Merge using Reciprocal Rank Fusion (RRF).

        RRF Score = Σ 1/(k + rank_i) for each retrieval method i
        """
        # Collect all unique documents with their RRF scores
        doc_scores: dict[str, float] = {}
        doc_metas: dict[str, dict[str, Any]] = {}

        for method, result in results.items():
            if result.error:
                continue  # Skip failed retrievals

            for rank, (doc, meta) in enumerate(
                zip(result.documents, result.metadatas, strict=False)
            ):
                # RRF score: 1 / (k + rank)
                rrf_score = 1.0 / (rrf_k + rank + 1)

                # Use doc content as key (or could use ID if available)
                doc_key = doc[:100]  # Use first 100 chars as key

                # Accumulate scores from different methods
                doc_scores[doc_key] = doc_scores.get(doc_key, 0.0) + rrf_score

                # Keep metadata (use first occurrence)
                if doc_key not in doc_metas:
                    doc_metas[doc_key] = {
                        "doc": doc,
                        "meta": meta,
                    }

        # Sort by RRF score (descending)
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        # Extract documents and metadatas
        final_docs = [doc_metas[doc_key]["doc"] for doc_key, _ in sorted_docs]
        final_metas = [doc_metas[doc_key]["meta"] for doc_key, _ in sorted_docs]
        final_scores = [score for _, score in sorted_docs]

        return {
            "documents": final_docs,
            "metadatas": final_metas,
            "scores": final_scores,
            "merge_strategy": "rrf",
        }

    def _merge_concatenate(
        self,
        results: dict[str, RetrievalResult],
        top_k: int,
    ) -> dict[str, Any]:
        """
        Simple concatenation of results (preserve order).
        """
        all_docs = []
        all_metas = []

        for method, result in results.items():
            if result.error:
                continue
            all_docs.extend(result.documents)
            all_metas.extend(result.metadatas)

        # Deduplicate while preserving order
        seen = set()
        unique_docs = []
        unique_metas = []

        for doc, meta in zip(all_docs, all_metas, strict=False):
            doc_key = doc[:100]
            if doc_key not in seen:
                seen.add(doc_key)
                unique_docs.append(doc)
                unique_metas.append(meta)

        return {
            "documents": unique_docs[:top_k],
            "metadatas": unique_metas[:top_k],
            "merge_strategy": "concatenate",
        }

    def _merge_vote(
        self,
        results: dict[str, RetrievalResult],
        top_k: int,
    ) -> dict[str, Any]:
        """
        Voting-based merge (documents appearing in more methods rank higher).
        """
        doc_votes: dict[str, int] = {}
        doc_metas: dict[str, dict[str, Any]] = {}

        for method, result in results.items():
            if result.error:
                continue

            for doc, meta in zip(result.documents, result.metadatas, strict=False):
                doc_key = doc[:100]
                doc_votes[doc_key] = doc_votes.get(doc_key, 0) + 1

                if doc_key not in doc_metas:
                    doc_metas[doc_key] = {"doc": doc, "meta": meta}

        # Sort by vote count
        sorted_docs = sorted(
            doc_votes.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        final_docs = [doc_metas[doc_key]["doc"] for doc_key, _ in sorted_docs]
        final_metas = [doc_metas[doc_key]["meta"] for doc_key, _ in sorted_docs]
        final_votes = [votes for _, votes in sorted_docs]

        return {
            "documents": final_docs,
            "metadatas": final_metas,
            "votes": final_votes,
            "merge_strategy": "vote",
        }

    def close(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=True)


# Example usage and benchmarking
if __name__ == "__main__":
    print("🧪 Testing Parallel Retrieval...")
    print("Note: This requires a real RagEngine instance to test properly.\n")

    # Mock engine for demonstration
    class MockEngine:
        def retrieve(self, query, top_k=10, **kwargs):
            import random
            import time

            time.sleep(0.2 + random.random() * 0.1)  # Simulate 200-300ms
            return {
                "documents": [f"vector_doc_{i}" for i in range(top_k)],
                "metadatas": [{"source": f"vector_{i}"} for i in range(top_k)],
            }

        def retrieve_bm25(self, query, top_k=10, **kwargs):
            import random
            import time

            time.sleep(0.1 + random.random() * 0.05)  # Simulate 100-150ms
            return {
                "documents": [f"bm25_doc_{i}" for i in range(top_k)],
                "metadatas": [{"source": f"bm25_{i}"} for i in range(top_k)],
            }

        def retrieve_hybrid(self, query, top_k=10, **kwargs):
            import random
            import time

            time.sleep(0.3 + random.random() * 0.1)  # Simulate 300-400ms
            return {
                "documents": [f"hybrid_doc_{i}" for i in range(top_k)],
                "metadatas": [{"source": f"hybrid_{i}"} for i in range(top_k)],
            }

    engine = MockEngine()
    retriever = ParallelRetriever(engine)

    async def test_parallel():
        query = "What is RAG?"

        # Test sequential (baseline)
        print("🐢 Sequential Retrieval:")
        start = time.time()
        vector = engine.retrieve(query, top_k=5)
        bm25 = engine.retrieve_bm25(query, top_k=5)
        sequential_time = (time.time() - start) * 1000
        print(f"   Vector: {len(vector['documents'])} docs")
        print(f"   BM25: {len(bm25['documents'])} docs")
        print(f"   Total Time: {sequential_time:.0f}ms\n")

        # Test parallel
        print("🚀 Parallel Retrieval:")
        start = time.time()
        results = await retriever.retrieve_parallel(
            query,
            methods=["vector", "bm25"],
            top_k=5,
        )
        parallel_time = (time.time() - start) * 1000

        for method, result in results.items():
            status = "✅" if not result.error else "❌"
            print(
                f"   {status} {method}: {len(result.documents)} docs ({result.duration_ms:.0f}ms)"
            )
        print(f"   Total Time: {parallel_time:.0f}ms")
        print(f"   Speedup: {sequential_time/parallel_time:.2f}x faster! 🚀\n")

        # Test merge
        print("🔗 Merging Results (RRF):")
        merged = retriever.merge_results(results, strategy="rrf", top_k=5)
        print(f"   Merged: {len(merged['documents'])} docs")
        print(f"   Strategy: {merged['merge_strategy']}")

    # Run async test
    asyncio.run(test_parallel())
    retriever.close()

    print("\n✅ Parallel Retrieval test completed!")
