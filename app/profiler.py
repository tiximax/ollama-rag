"""
⚡ Query Performance Profiler - Phân tích bottlenecks trong RAG pipeline

Profiler này giúp identify chính xác phần nào của query pipeline chậm nhất:
- Embedding generation
- Vector search
- BM25 search
- Reranking
- LLM generation
- Total end-to-end time

Features:
- ✅ Detailed timing breakdown
- ✅ Memory usage tracking
- ✅ Automatic bottleneck detection
- ✅ Performance recommendations
- ✅ Export to JSON/CSV
- ✅ Real-time visualization ready
"""

import json
import time
import tracemalloc
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

import psutil


@dataclass
class ProfileStep:
    """Single step trong query execution."""

    name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_delta_mb: float = 0.0
    cpu_percent: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self) -> None:
        """Mark step as finished and calculate metrics."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class ProfileResult:
    """Full profiling result cho 1 query."""

    query: str
    total_duration_ms: float
    steps: list[ProfileStep]
    bottlenecks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    total_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def analyze(self) -> None:
        """Analyze profile and generate insights."""
        if not self.steps:
            return

        # Calculate total memory and CPU
        self.total_memory_mb = sum(s.memory_delta_mb for s in self.steps)
        self.peak_memory_mb = max(s.memory_after_mb for s in self.steps)
        self.avg_cpu_percent = sum(s.cpu_percent for s in self.steps) / len(self.steps)

        # Find bottlenecks (steps taking > 30% of total time)
        threshold_ms = self.total_duration_ms * 0.3
        self.bottlenecks = [
            f"{s.name}: {s.duration_ms:.0f}ms ({s.duration_ms/self.total_duration_ms*100:.1f}%)"
            for s in self.steps
            if s.duration_ms > threshold_ms
        ]

        # Generate recommendations
        self._generate_recommendations()

    def _generate_recommendations(self) -> None:
        """Generate performance recommendations based on profiling."""
        for step in self.steps:
            pct = (step.duration_ms / self.total_duration_ms) * 100

            # Embedding too slow
            if "embedding" in step.name.lower() and step.duration_ms > 500:
                self.recommendations.append(
                    f"🔧 Embedding generation slow ({step.duration_ms:.0f}ms). "
                    f"Consider: batch embeddings, use faster model, or enable caching"
                )

            # Vector search slow
            if "vector" in step.name.lower() and step.duration_ms > 1000:
                self.recommendations.append(
                    f"🔧 Vector search slow ({step.duration_ms:.0f}ms). "
                    f"Consider: reduce index size, use FAISS, or lower top_k"
                )

            # BM25 slow
            if "bm25" in step.name.lower() and step.duration_ms > 500:
                self.recommendations.append(
                    f"🔧 BM25 search slow ({step.duration_ms:.0f}ms). "
                    f"Consider: reduce corpus size or cache tokenization"
                )

            # Reranking slow
            if "rerank" in step.name.lower() and step.duration_ms > 2000:
                self.recommendations.append(
                    f"🔧 Reranking slow ({step.duration_ms:.0f}ms). "
                    f"Consider: reduce batch size, disable reranking, or use faster model"
                )

            # LLM generation slow
            if "llm" in step.name.lower() or "generate" in step.name.lower():
                if step.duration_ms > 30000:  # > 30s
                    self.recommendations.append(
                        f"🔧 LLM generation very slow ({step.duration_ms/1000:.1f}s). "
                        f"Consider: use smaller model, reduce context length, or enable streaming"
                    )

            # High memory usage
            if step.memory_delta_mb > 100:
                self.recommendations.append(
                    f"💾 High memory usage in {step.name} (+{step.memory_delta_mb:.0f}MB). "
                    f"Consider: batch processing or memory optimization"
                )

        # Total time too long
        if self.total_duration_ms > 60000:  # > 1 minute
            self.recommendations.append(
                "⚠️ Total query time > 1min. Consider: parallel retrieval, "
                "caching, or async processing"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "query": self.query,
            "total_duration_ms": self.total_duration_ms,
            "total_memory_mb": self.total_memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_cpu_percent": self.avg_cpu_percent,
            "steps": [s.to_dict() for s in self.steps],
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }

    def print_summary(self) -> None:
        """Print human-readable summary."""
        print(f"\n{'='*80}")
        print("⚡ Query Performance Profile")
        print(f"{'='*80}")
        print(f"Query: {self.query[:60]}...")
        print(
            f"Total Duration: {self.total_duration_ms:.0f}ms ({self.total_duration_ms/1000:.2f}s)"
        )
        print(f"Peak Memory: {self.peak_memory_mb:.1f}MB")
        print(f"Avg CPU: {self.avg_cpu_percent:.1f}%")

        print("\n📊 Step Breakdown:")
        print(f"{'Step':<30} {'Duration':<15} {'%':<8} {'Memory':<12}")
        print(f"{'-'*70}")
        for step in self.steps:
            pct = (step.duration_ms / self.total_duration_ms) * 100
            mem_str = f"+{step.memory_delta_mb:.1f}MB" if step.memory_delta_mb > 0 else "0MB"
            print(f"{step.name:<30} {step.duration_ms:>8.0f}ms      {pct:>5.1f}%   {mem_str:>10}")

        if self.bottlenecks:
            print("\n🔥 Bottlenecks Detected:")
            for bottleneck in self.bottlenecks:
                print(f"  - {bottleneck}")

        if self.recommendations:
            print("\n💡 Recommendations:")
            for rec in self.recommendations:
                print(f"  - {rec}")

        print(f"{'='*80}\n")


class QueryProfiler:
    """
    ⚡ Query Profiler - Profile query performance và detect bottlenecks!

    Usage:
        >>> profiler = QueryProfiler()
        >>>
        >>> with profiler.profile_query("What is RAG?") as p:
        ...     with p.step("embedding"):
        ...         embeddings = embedder(query)
        ...
        ...     with p.step("vector_search"):
        ...         results = vector_search(embeddings)
        ...
        ...     with p.step("llm_generation"):
        ...         answer = llm.generate(context)
        >>>
        >>> result = profiler.get_last_result()
        >>> result.print_summary()
    """

    def __init__(self, enable_memory_tracking: bool = True):
        """
        Args:
            enable_memory_tracking: Track memory usage (slight overhead)
        """
        self.enable_memory_tracking = enable_memory_tracking
        self._results: list[ProfileResult] = []
        self._current_profile: _ProfileContext | None = None

    def profile_query(self, query: str) -> '_ProfileContext':
        """
        Start profiling a query.

        Returns:
            Context manager for profiling
        """
        context = _ProfileContext(query, self, self.enable_memory_tracking)
        self._current_profile = context
        return context

    def add_result(self, result: ProfileResult) -> None:
        """Add a completed profile result."""
        self._results.append(result)

    def get_last_result(self) -> ProfileResult | None:
        """Get the most recent profile result."""
        return self._results[-1] if self._results else None

    def get_all_results(self) -> list[ProfileResult]:
        """Get all profile results."""
        return self._results

    def get_aggregate_stats(self) -> dict[str, Any]:
        """
        Get aggregate statistics across all profiled queries.

        Returns:
            Dict with aggregate metrics
        """
        if not self._results:
            return {}

        total_queries = len(self._results)
        avg_duration = sum(r.total_duration_ms for r in self._results) / total_queries
        avg_memory = sum(r.total_memory_mb for r in self._results) / total_queries

        # Step statistics
        step_stats = defaultdict(lambda: {"count": 0, "total_ms": 0.0})
        for result in self._results:
            for step in result.steps:
                step_stats[step.name]["count"] += 1
                step_stats[step.name]["total_ms"] += step.duration_ms

        step_averages = {
            name: stats["total_ms"] / stats["count"] for name, stats in step_stats.items()
        }

        return {
            "total_queries": total_queries,
            "avg_duration_ms": avg_duration,
            "avg_memory_mb": avg_memory,
            "step_averages_ms": step_averages,
            "slowest_query_ms": max(r.total_duration_ms for r in self._results),
            "fastest_query_ms": min(r.total_duration_ms for r in self._results),
        }

    def export_json(self, filepath: str) -> None:
        """Export all results to JSON."""
        data = {
            "results": [r.to_dict() for r in self._results],
            "aggregate_stats": self.get_aggregate_stats(),
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def clear_results(self) -> None:
        """Clear all stored results."""
        self._results.clear()


class _ProfileContext:
    """Context manager for profiling a single query."""

    def __init__(self, query: str, profiler: QueryProfiler, track_memory: bool):
        self.query = query
        self.profiler = profiler
        self.track_memory = track_memory
        self.steps: list[ProfileStep] = []
        self.start_time = 0.0
        self._process = psutil.Process()

    def __enter__(self) -> '_ProfileContext':
        """Start profiling."""
        self.start_time = time.time()
        if self.track_memory:
            tracemalloc.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish profiling and analyze."""
        total_duration_ms = (time.time() - self.start_time) * 1000

        # Create result
        result = ProfileResult(
            query=self.query,
            total_duration_ms=total_duration_ms,
            steps=self.steps,
        )
        result.analyze()

        # Add to profiler
        self.profiler.add_result(result)

        # Stop memory tracking
        if self.track_memory:
            tracemalloc.stop()

        return False  # Don't suppress exceptions

    def step(self, name: str, **metadata) -> '_StepContext':
        """Profile a single step in the query."""
        return _StepContext(self, name, metadata)


class _StepContext:
    """Context manager for profiling a single step."""

    def __init__(self, profile_ctx: _ProfileContext, name: str, metadata: dict[str, Any]):
        self.profile_ctx = profile_ctx
        self.name = name
        self.metadata = metadata
        self.step: ProfileStep | None = None

    def __enter__(self) -> ProfileStep:
        """Start step timing."""
        # Get memory before
        memory_before_mb = 0.0
        if self.profile_ctx.track_memory:
            try:
                mem_info = self.profile_ctx._process.memory_info()
                memory_before_mb = mem_info.rss / (1024 * 1024)  # Convert to MB
            except Exception:
                pass

        # Create step
        self.step = ProfileStep(
            name=self.name,
            start_time=time.time(),
            memory_before_mb=memory_before_mb,
            metadata=self.metadata,
        )

        return self.step

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish step timing."""
        if self.step:
            self.step.finish()

            # Get memory after
            if self.profile_ctx.track_memory:
                try:
                    mem_info = self.profile_ctx._process.memory_info()
                    self.step.memory_after_mb = mem_info.rss / (1024 * 1024)
                    self.step.memory_delta_mb = (
                        self.step.memory_after_mb - self.step.memory_before_mb
                    )

                    # Get CPU percent
                    self.step.cpu_percent = self.profile_ctx._process.cpu_percent()
                except Exception:
                    pass

            # Add to profile
            self.profile_ctx.steps.append(self.step)

        return False  # Don't suppress exceptions


# Example usage
if __name__ == "__main__":
    import random

    print("🧪 Testing Query Profiler...")

    profiler = QueryProfiler()

    # Simulate a query
    with profiler.profile_query("What is RAG?") as p:
        # Simulate embedding
        with p.step("embedding_generation", model="nomic-embed"):
            time.sleep(0.1 + random.random() * 0.1)

        # Simulate vector search
        with p.step("vector_search", top_k=10):
            time.sleep(0.2 + random.random() * 0.2)

        # Simulate BM25
        with p.step("bm25_search", top_k=10):
            time.sleep(0.05 + random.random() * 0.05)

        # Simulate reranking
        with p.step("reranking", model="bge-reranker"):
            time.sleep(0.5 + random.random() * 0.3)

        # Simulate LLM generation
        with p.step("llm_generation", model="llama3.2", tokens=500):
            time.sleep(1.0 + random.random() * 0.5)

    # Get and print result
    result = profiler.get_last_result()
    if result:
        result.print_summary()

    # Aggregate stats
    print("📊 Aggregate Statistics:")
    stats = profiler.get_aggregate_stats()
    print(json.dumps(stats, indent=2))

    # Export
    profiler.export_json("profile_results.json")
    print("\n✅ Results exported to profile_results.json")

    print("\n✅ Query Profiler test completed!")
