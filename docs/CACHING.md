# 🧠 Caching Strategies Guide

Comprehensive guide to caching in Ollama RAG for optimal performance.

---

## Cache Types

### 1. **Filters Cache** (Built-in ✅)
**Location:** `app/cache_utils.py` → `RagEngine._filters_cache`  
**Purpose:** Cache filter results (language/version filtering)  
**Config:**
- Max size: 100 entries
- TTL: 300s (5 minutes)
- Type: LRU with TTL

**Stats:** Check via `/api/cache-stats`

---

### 2. **Generation Cache** (Built-in ✅)
**Location:** `app/gen_cache.py`  
**Purpose:** Cache LLM generations (expensive!)  
**Config:**
```bash
GEN_CACHE_ENABLE=1  # Enable (default: 1)
GEN_CACHE_TTL=86400  # 24 hours
```

**Storage:** SQLite per database (`<db_path>/gen_cache.db`)

---

### 3. **Semantic Query Cache** (New! 🆕)
**Location:** `app/semantic_cache.py`  
**Purpose:** Cache by semantic similarity, not exact match

**Features:**
- Matches similar queries (e.g., "What is RAG?" ≈ "Can you explain RAG?")
- Cosine similarity threshold: 0.95 (configurable)
- LRU eviction + TTL
- Thread-safe

**Usage:**
```python
from app.semantic_cache import SemanticQueryCache

# Initialize
cache = SemanticQueryCache(
    similarity_threshold=0.95,  # 0.85-0.98 recommended
    max_size=1000,
    ttl=300.0,  # 5 minutes
)

# Get
result = cache.get(query, embedder=engine.ollama.embed)
if result is None:
    # Cache miss - execute query
    result = engine.query(...)
    cache.set(query, result, embedder=engine.ollama.embed)
```

**Performance:**
- Exact match: <1ms
- Semantic search: ~50ms (100 entries)
- Memory: ~10KB/entry (128-dim embeddings)

---

### 4. **Cache Warming** (New! 🆕)
**Location:** `app/cache_warming.py`  
**Purpose:** Pre-load popular queries on startup

**Strategies:**
1. Static: Load from `popular_queries.json`
2. Analytics: Extract from query logs
3. Embeddings-only: Fast startup (recommended)

**Usage:**
```python
from app.cache_warming import CacheWarmer

warmer = CacheWarmer(
    popular_queries_file="config/popular_queries.json",
    analytics_log_dir="data/kb/default/exp_logs",
    max_queries=50,
)

# Sync (blocking)
stats = warmer.warm_cache_sync(
    cache=semantic_cache,
    embedder=engine.ollama.embed,
    embeddings_only=True,  # Fast!
)

# Async (non-blocking)
await warmer.warm_cache_async(
    cache=semantic_cache,
    embedder=engine.ollama.embed,
    embeddings_only=True,
)
```

**Performance:**
- 10 queries: ~0.5s (embeddings only)
- 50 queries: ~2.5s (embeddings only)

---

## Configuration Guide

### Recommended Settings

**Development:**
```env
GEN_CACHE_ENABLE=1
GEN_CACHE_TTL=3600  # 1 hour (short for testing)
```

**Production:**
```env
GEN_CACHE_ENABLE=1
GEN_CACHE_TTL=86400  # 24 hours
```

**High-Traffic Production:**
- Enable Semantic Cache
- Enable Cache Warming
- Consider Redis for distributed caching (future)

---

## Best Practices

### 1. **Cache Invalidation**
```python
# Clear generation cache
engine.gen_cache.clear()

# Clear semantic cache
semantic_cache.clear()

# Clear filters cache
engine._filters_cache.clear()
```

### 2. **Monitoring Cache Performance**
```bash
# Check cache stats
curl http://localhost:8000/api/cache-stats

# Example response:
{
  "filters_cache": {
    "hits": 42,
    "misses": 10,
    "hit_rate": 0.807,
    "size": 15,
    "max_size": 100
  },
  "generation_cache": {
    "enabled": true,
    "path": "data/kb/default/gen_cache.db"
  }
}
```

### 3. **Tuning Similarity Threshold**
- **0.98**: Very strict (almost exact match)
- **0.95**: Strict (recommended default)
- **0.90**: Moderate (more cache hits, less precision)
- **0.85**: Loose (high hit rate, may be too lenient)

**Test before deploying:**
```python
# A/B test different thresholds
thresholds = [0.85, 0.90, 0.95, 0.98]
for t in thresholds:
    cache = SemanticQueryCache(similarity_threshold=t)
    # Test with your queries
```

### 4. **Memory Management**
- Semantic cache: ~10MB per 1000 entries
- Generation cache: ~1KB per entry (depends on answer length)
- Filters cache: ~1KB per entry

**Adjust max_size based on available RAM:**
```python
# For 100MB cache budget:
semantic_cache = SemanticQueryCache(max_size=10000)  # ~100MB
```

---

## Troubleshooting

### High Memory Usage
```python
# Check cache sizes
stats = semantic_cache.stats()
print(f"Size: {stats['size']}/{stats['max_size']}")
print(f"Fill ratio: {stats['fill_ratio']:.2%}")

# Solution: Reduce max_size or TTL
semantic_cache = SemanticQueryCache(max_size=500, ttl=180)
```

### Low Hit Rate
```python
stats = semantic_cache.stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Semantic hits: {stats['semantic_hits']}")

# Solutions:
# 1. Lower similarity threshold (0.90 instead of 0.95)
# 2. Enable cache warming
# 3. Increase TTL (queries expire too quickly)
```

### Cache Warming Too Slow
```python
# Solution 1: Use embeddings_only=True
warmer.warm_cache_sync(cache, embedder, embeddings_only=True)

# Solution 2: Reduce max_queries
warmer = CacheWarmer(max_queries=20)

# Solution 3: Async warming (non-blocking startup)
asyncio.create_task(warmer.warm_cache_async(...))
```

---

## Performance Impact

### Expected Improvements
| Metric | Before | After (Semantic Cache) | Improvement |
|--------|--------|------------------------|-------------|
| Cache hit rate | ~30% | ~70% | +133% |
| Cached response | 5-10s | 3-5s | -40% |
| First query | 55s | 45s | -18% |

### Cache Hit Breakdown
```python
stats = semantic_cache.stats()
print(f"Total hits: {stats['hits']}")
print(f"  - Exact: {stats['exact_hits']}")
print(f"  - Semantic: {stats['semantic_hits']}")
print(f"Semantic hit rate: {stats['semantic_hit_rate']:.2%}")
```

---

## Integration Example

**Full setup in `app/main.py`:**
```python
from app.semantic_cache import SemanticQueryCache
from app.cache_warming import CacheWarmer

# Initialize semantic cache
semantic_cache = SemanticQueryCache(
    similarity_threshold=0.95,
    max_size=1000,
    ttl=300.0,
)

@app.on_event("startup")
async def startup_warm_cache():
    """Warm cache on startup."""
    warmer = CacheWarmer(
        analytics_log_dir=engine.persist_root + "/exp_logs",
        max_queries=50,
    )
    
    # Non-blocking background warming
    import asyncio
    asyncio.create_task(
        warmer.warm_cache_async(
            cache=semantic_cache,
            embedder=engine.ollama.embed,
            embeddings_only=True,
        )
    )

@app.post("/api/query")
def api_query(req: QueryRequest):
    # Try semantic cache
    cached = semantic_cache.get(
        req.query,
        embedder=engine.ollama.embed,
        return_metadata=True,
    )
    
    if cached is not None:
        result, meta = cached
        result["cache_hit"] = True
        result["cache_type"] = meta["cache_type"]
        return result
    
    # Execute query
    result = engine.query(...)
    
    # Cache result
    semantic_cache.set(
        req.query,
        result,
        embedder=engine.ollama.embed,
    )
    
    return result
```

---

**Created:** 2025-10-03  
**Last Updated:** 2025-10-03  
**Version:** 1.0
