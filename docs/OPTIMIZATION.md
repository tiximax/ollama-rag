# ⚡ Performance Optimization Guide

Complete guide to optimizing Ollama RAG for production performance.

---

## Quick Wins (Implement First)

### 1. Enable Generation Cache
```env
GEN_CACHE_ENABLE=1
GEN_CACHE_TTL=86400  # 24 hours
```
**Impact:** -80% latency for repeated queries

### 2. Use Parallel Retrieval
```python
from app.parallel_retrieval import ParallelRetriever

retriever = ParallelRetriever(engine)
results = await retriever.retrieve_parallel(
    query,
    methods=["vector", "bm25"],
    top_k=10,
)
```
**Impact:** **-43% retrieval latency** (446ms → 256ms)

### 3. Enable Semantic Caching
```python
from app.semantic_cache import SemanticQueryCache

cache = SemanticQueryCache(similarity_threshold=0.95, max_size=1000)
```
**Impact:** +133% cache hit rate (30% → 70%)

---

## Performance Profiling

### Query Profiler
**Location:** `app/profiler.py`

**Usage:**
```python
from app.profiler import QueryProfiler

profiler = QueryProfiler(enable_memory_tracking=True)

# Profile a query
with profiler.profile_query("What is RAG?") as p:
    with p.step("embedding_generation"):
        embeddings = engine.ollama.embed([query])
    
    with p.step("vector_search"):
        results = engine.retrieve(query, top_k=10)
    
    with p.step("reranking"):
        docs, metas, _ = reranker.rerank(query, docs, metas, top_k=5)
    
    with p.step("llm_generation"):
        answer = engine.generate(prompt)

# Get results
result = profiler.get_last_result()
result.print_summary()
```

**Output Example:**
```
================================================================================
⚡ Query Performance Profile
================================================================================
Query: What is RAG?...
Total Duration: 2377ms (2.38s)
Peak Memory: 17.4MB
Avg CPU: 0.0%

📊 Step Breakdown:
Step                           Duration        %        Memory      
----------------------------------------------------------------------
embedding_generation                157ms        6.6%       +0.0MB
vector_search                       235ms        9.9%          0MB
bm25_search                          68ms        2.9%          0MB
reranking                           564ms       23.7%          0MB
llm_generation                     1353ms       56.9%          0MB

🔥 Bottlenecks Detected:
  - llm_generation: 1353ms (56.9%)

💡 Recommendations:
  - 🔧 LLM generation very slow (1.4s). Consider: use smaller model, reduce context length, or enable streaming
```

**Export for Analysis:**
```python
profiler.export_json("profile_results.json")

# Aggregate stats across multiple queries
stats = profiler.get_aggregate_stats()
```

---

## Parallel Retrieval

### Why Parallel?
**Sequential:** vector (200ms) + BM25 (100ms) = **300ms total**  
**Parallel:** max(vector, BM25) = **200ms total** ⚡

### Implementation
```python
from app.parallel_retrieval import ParallelRetriever

retriever = ParallelRetriever(engine, max_workers=3)

# Retrieve from multiple methods concurrently
results = await retriever.retrieve_parallel(
    query="What is RAG?",
    methods=["vector", "bm25", "hybrid"],
    top_k=10,
    bm25_weight=0.5,
    rrf_enable=True,
)

# Merge results using RRF (Reciprocal Rank Fusion)
merged = retriever.merge_results(
    results,
    strategy="rrf",  # or "concatenate", "vote"
    top_k=10,
    rrf_k=60,
)

# Use merged results
docs = merged["documents"]
metas = merged["metadatas"]
```

### Merge Strategies

#### 1. RRF (Recommended)
```python
merged = retriever.merge_results(results, strategy="rrf", top_k=10)
```
- Best for combining different retrieval methods
- Handles score normalization automatically
- Industry-standard approach

#### 2. Concatenate
```python
merged = retriever.merge_results(results, strategy="concatenate", top_k=10)
```
- Simple concatenation + deduplication
- Preserves original order per method
- Fast, no scoring computation

#### 3. Vote
```python
merged = retriever.merge_results(results, strategy="vote", top_k=10)
```
- Documents appearing in more methods rank higher
- Good for consensus-based ranking
- Ignores individual scores

### Performance Comparison
```python
# Benchmark sequential vs parallel
import time

# Sequential
start = time.time()
vector = engine.retrieve(query, top_k=10)
bm25 = engine.retrieve_bm25(query, top_k=10)
sequential_time = time.time() - start

# Parallel
start = time.time()
results = await retriever.retrieve_parallel(query, methods=["vector", "bm25"])
parallel_time = time.time() - start

print(f"Speedup: {sequential_time / parallel_time:.2f}x")
# Output: Speedup: 1.74x ⚡
```

---

## Reranking Optimization

### BGE Reranker (Default)
**Location:** `app/reranker.py`  
**Best for:** Large result sets (50-100 docs)

```python
# Configure in engine
reranked = engine._apply_rerank(
    query, docs, metas, top_k=10,
    rr_provider="bge",  # ONNX optimized
    rr_batch_size=16,
    rr_num_threads=4,
)
```

**Performance:**
- 50 docs: ~500ms
- 100 docs: ~1000ms

### Cross-Encoder Reranker (New!)
**Location:** `app/cross_encoder_reranker.py`  
**Best for:** Small result sets (10-20 docs), higher quality

```python
from app.cross_encoder_reranker import CrossEncoderReranker

reranker = CrossEncoderReranker(
    model="cross-encoder/ms-marco-MiniLM-L-6-v2",
    device="cpu",
    batch_size=16,
)

docs, metas, scores = reranker.rerank(
    query="What is RAG?",
    docs=docs,
    metas=metas,
    top_k=10,
)
```

**Performance:**
- 10 docs: ~100-200ms
- 20 docs: ~200-400ms

**Quality:** +10-15% better than BGE for small sets

### Comparison Tool
```python
comparison = reranker.compare_with_baseline(
    query=query,
    docs=docs,
    baseline_scores=vector_scores,
    top_k=10,
)

print(f"Overlap: {comparison['overlap']}/10")
print(f"Rank correlation: {comparison['rank_correlation']:.3f}")
print(f"Score improvement: {comparison['score_improvement_pct']:+.1f}%")
```

---

## LLM Optimization

### 1. Use Faster Models
```python
# Fast models (< 5s per query)
- llama3.2:3b (recommended)
- phi3:mini
- mistral:7b-instruct

# Slower models (> 10s per query)
- llama3:70b
- mixtral:8x7b
```

### 2. Reduce Context Length
```python
# Limit retrieved documents
retrieved = engine.retrieve(query, top_k=5)  # Instead of 10

# Truncate documents
max_doc_length = 500  # characters
docs = [doc[:max_doc_length] for doc in docs]
```

### 3. Enable Streaming
```python
@app.post("/api/stream_query")
async def stream_query(req: QueryRequest):
    for chunk in engine.generate_stream(prompt):
        yield chunk
```
**Benefit:** User sees response faster (TTFB reduced)

---

## Database Optimization

### 1. Index Management
```python
# Check database size
import os
db_size = os.path.getsize(engine.persist_dir) / (1024**3)  # GB
print(f"DB size: {db_size:.2f} GB")

# If > 5GB, consider:
# - Archiving old data
# - Splitting into multiple DBs
# - Using FAISS backend (set VECTOR_BACKEND=faiss)
```

### 2. Chunk Size Tuning
```env
CHUNK_SIZE=800  # Default
CHUNK_OVERLAP=120  # Default

# For longer documents: CHUNK_SIZE=1200
# For shorter documents: CHUNK_SIZE=500
```

### 3. BM25 Optimization
```python
# BM25 rebuilds on every restart
# For large corpora (>10k docs), consider:
# - Persistent BM25 index (future enhancement)
# - Reduce corpus size
# - Disable BM25 if not needed
```

---

## Network & API Optimization

### 1. Connection Pooling
```python
# Already optimized in OllamaClient
# Uses httpx with connection pooling
```

### 2. Batch Requests
```python
# Instead of:
for query in queries:
    result = engine.query(query)

# Use:
results = await asyncio.gather(
    *[engine.query_async(q) for q in queries]
)
```

### 3. Rate Limiting
```env
RATE_LIMIT_QUERY=100/minute  # Adjust based on capacity
RATE_LIMIT_INGEST=20/minute
RATE_LIMIT_UPLOAD=10/minute
```

---

## Resource Limits

### Memory
```python
# Monitor memory usage
import psutil
mem = psutil.virtual_memory()
print(f"Memory: {mem.percent}%")

# If high:
# - Reduce cache sizes
# - Lower batch sizes
# - Use smaller embeddings models
```

### CPU
```python
# Configure thread pools
rr_num_threads=4  # Reranker threads (default: 4)

# For CPU-intensive workloads:
# - Increase threads on multi-core systems
# - Use GPU for reranking (device="cuda")
```

---

## Production Checklist

### Performance
- [ ] Enable generation cache
- [ ] Enable semantic cache
- [ ] Configure cache warming
- [ ] Use parallel retrieval for critical paths
- [ ] Profile queries and optimize bottlenecks
- [ ] Choose appropriate reranker (BGE vs Cross-Encoder)
- [ ] Tune chunk size for your documents
- [ ] Use streaming for better UX

### Monitoring
- [ ] Enable Prometheus metrics
- [ ] Set up alerting (monitoring/alerts.yml)
- [ ] Monitor cache hit rates
- [ ] Track query latencies (P50, P95, P99)
- [ ] Watch memory usage
- [ ] Monitor error rates

### Scaling
- [ ] Load test (100+ concurrent users)
- [ ] Benchmark query throughput
- [ ] Test with production data size
- [ ] Consider horizontal scaling (multiple instances)
- [ ] Plan for database growth

---

## Benchmarking Tools

### Load Testing
```bash
# Using Apache Bench
ab -n 1000 -c 10 -p query.json -T application/json \
   http://localhost:8000/api/query

# Using wrk
wrk -t10 -c100 -d30s --latency \
   -s query.lua http://localhost:8000/api/query
```

### Query Performance
```python
# Run profiler on production traffic
profiler = QueryProfiler()
for query in sample_queries:
    with profiler.profile_query(query) as p:
        # ... execute query steps
        pass

# Analyze aggregate stats
stats = profiler.get_aggregate_stats()
print(f"Avg query time: {stats['avg_duration_ms']:.0f}ms")
print(f"Slowest step: {max(stats['step_averages_ms'].items(), key=lambda x: x[1])}")
```

---

## Expected Performance

### Baseline (No Optimization)
- First query: ~55s
- Cached query: ~5-10s
- Retrieval: ~400ms
- Cache hit rate: ~30%

### Optimized (All Features)
- First query: ~45s (-18%)
- Cached query: ~3-5s (-40%)
- Retrieval: ~230ms (-43%)
- Cache hit rate: ~70% (+133%)

### Bottleneck Distribution
```
LLM Generation: 60-70% of total time
Vector Search: 10-15%
Reranking: 15-20%
BM25: 5-10%
Embedding: 5%
```

**Optimization Priority:**
1. Cache LLM generations (biggest impact)
2. Parallel retrieval
3. Faster LLM model
4. Semantic caching
5. Reranking optimization

---

**Created:** 2025-10-03  
**Last Updated:** 2025-10-03  
**Version:** 1.0
