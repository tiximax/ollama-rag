import numpy as np

from app.semantic_cache import SemanticQueryCache


class MockEmbedder:
    """Deterministic embedder for testing.

    - Base query maps to unit vector e1.
    - Similar query maps to a vector with controllable cosine similarity.
    - All other texts map to orthogonal e2.
    """

    def __init__(self, mapping: dict[str, np.ndarray] | None = None):
        self.mapping = mapping or {}

    def __call__(self, queries):
        out = []
        for q in queries:
            if q in self.mapping:
                v = self.mapping[q]
            else:
                # default orthogonal vector
                v = np.array([0.0, 1.0], dtype=float)
            out.append(v.tolist())
        return out


def test_exact_hit():
    cache = SemanticQueryCache(similarity_threshold=0.95, max_size=10, ttl=10.0)
    emb = MockEmbedder({"q1": np.array([1.0, 0.0])})

    # MISS then SET
    assert cache.get("q1", emb) is None
    cache.set("q1", {"answer": "A1"}, emb)

    # EXACT HIT
    res = cache.get("q1", emb)
    assert res is not None
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["exact_hits"] == 1


def test_semantic_hit_above_threshold():
    # Cosine sim between [1,0] and [0.95, 0.3122499] ~ 0.95 (normalized)
    base = np.array([1.0, 0.0])
    similar = np.array([0.95, 0.3122499])

    cache = SemanticQueryCache(similarity_threshold=0.90, max_size=10, ttl=10.0)
    emb = MockEmbedder({"base": base, "similar": similar})

    # Seed cache
    assert cache.get("base", emb) is None
    cache.set("base", {"answer": "A-base"}, emb)

    # Semantic HIT
    res = cache.get("similar", emb)
    assert res is not None
    st = cache.stats()
    assert st["semantic_hits"] == 1


def test_semantic_miss_below_threshold():
    base = np.array([1.0, 0.0])
    # cosine sim ~ 0.7
    near = np.array([0.7, 0.71414284])

    cache = SemanticQueryCache(similarity_threshold=0.90, max_size=10, ttl=10.0)
    emb = MockEmbedder({"base": base, "near": near})

    cache.set("base", {"answer": "A"}, emb)
    res = cache.get("near", emb)
    assert res is None
    st = cache.stats()
    assert st["misses"] >= 1


def test_ttl_expiration():
    cache = SemanticQueryCache(similarity_threshold=0.95, max_size=10, ttl=1e-6)
    emb = MockEmbedder({"q": np.array([1.0, 0.0])})
    cache.set("q", {"answer": "A"}, emb)

    # Manually age the entry by modifying timestamp
    key = cache._compute_key("q")
    entry = cache._cache[key]
    entry.timestamp -= 1.0  # ensure expired

    assert cache.get("q", emb) is None  # should expire and miss


def test_lru_eviction():
    cache = SemanticQueryCache(similarity_threshold=0.95, max_size=2, ttl=10.0)
    emb = MockEmbedder(
        {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0]), "c": np.array([1.0, 1.0])}
    )

    cache.set("a", {"answer": "A"}, emb)
    cache.set("b", {"answer": "B"}, emb)
    # Cause eviction
    cache.set("c", {"answer": "C"}, emb)

    # Oldest (a) should be evicted
    assert cache.get("a", emb) is None
    assert cache.get("b", emb) is not None
    assert cache.get("c", emb) is not None


def test_stats_structure():
    cache = SemanticQueryCache(similarity_threshold=0.95, max_size=2, ttl=10.0)
    emb = MockEmbedder({"a": np.array([1.0, 0.0])})
    cache.set("a", {"answer": "A"}, emb)
    _ = cache.get("a", emb)
    stats = cache.stats()
    for key in [
        "hits",
        "misses",
        "exact_hits",
        "semantic_hits",
        "total_requests",
        "hit_rate",
        "semantic_hit_rate",
        "size",
        "max_size",
        "fill_ratio",
        "similarity_threshold",
        "ttl",
    ]:
        assert key in stats


def test_namespace_isolation():
    cache = SemanticQueryCache(similarity_threshold=0.90, max_size=10, ttl=10.0)
    emb = MockEmbedder({"q": np.array([1.0, 0.0])})

    # Seed in namespace A
    cache.set("q", {"answer": "A"}, emb, namespace="DB1:stamp1")

    # Exact get in different namespace should MISS
    assert cache.get("q", emb, namespace="DB2:stampX") is None

    # Semantic get in different namespace should MISS too (even same embedding)
    assert cache.get("q", emb, namespace="DB3:stampY") is None

    # Exact get in same namespace should HIT
    assert cache.get("q", emb, namespace="DB1:stamp1") is not None
    cache = SemanticQueryCache(similarity_threshold=0.95, max_size=2, ttl=10.0)
    emb = MockEmbedder({"a": np.array([1.0, 0.0])})
    cache.set("a", {"answer": "A"}, emb)
    _ = cache.get("a", emb)
    stats = cache.stats()
    for key in [
        "hits",
        "misses",
        "exact_hits",
        "semantic_hits",
        "total_requests",
        "hit_rate",
        "semantic_hit_rate",
        "size",
        "max_size",
        "fill_ratio",
        "similarity_threshold",
        "ttl",
    ]:
        assert key in stats
