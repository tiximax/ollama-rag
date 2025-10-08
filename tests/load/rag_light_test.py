"""
🔥 RAG Light Load Test - Sprint 3 Day 2
========================================

Mục đích: Test RAG query performance với lightweight scenarios

Features:
- RAG query testing với repeated queries (cache test!)
- Health & cache stats monitoring
- Focus on infrastructure performance (circuit breaker, pool, cache)
- Tolerate Ollama degraded state

Vibe: Testing RAG performance như một chuyên gia! 🎯
"""

import random

from locust import HttpUser, between, task


class RagTestConfig:
    """Configuration for RAG load tests"""

    # Endpoints
    RAG_QUERY_ENDPOINT = "/api/query"
    HEALTH_ENDPOINT = "/health"
    CACHE_STATS_ENDPOINT = "/api/cache-stats"

    # Sample queries - Will be repeated to test semantic cache!
    SAMPLE_QUERIES = [
        "What is machine learning?",
        "Explain neural networks",
        "How does RAG work?",
        "What is deep learning?",
        "Explain vector databases",
    ]

    # Timeouts
    QUERY_TIMEOUT = 60  # Long timeout for Ollama (may be slow)
    CACHE_TIMEOUT = 5


class RagLightUser(HttpUser):
    """
    Lightweight RAG user for testing infrastructure.

    Focuses on repeated queries to trigger semantic cache!
    """

    wait_time = between(3, 7)  # Wait 3-7s between requests

    @task(5)
    def rag_query(self):
        """
        RAG query with repeated patterns to test cache.

        Weight=5 (highest priority)
        """
        query = random.choice(RagTestConfig.SAMPLE_QUERIES)

        payload = {"query": query, "n_results": 2, "rerank": False}

        with self.client.post(
            RagTestConfig.RAG_QUERY_ENDPOINT,
            json=payload,
            timeout=RagTestConfig.QUERY_TIMEOUT,
            catch_response=True,
            name="RAG Query",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "answer" in data:
                        response.success()
                        # Log if cache was hit (response should be faster!)
                        response_time = response.elapsed.total_seconds() * 1000
                        cache_indicator = (
                            "🚀 FAST (likely cache hit!)"
                            if response_time < 1000
                            else "🐢 SLOW (cache miss or Ollama)"
                        )
                        print(
                            f"✅ Query: '{query[:30]}...' - {response_time:.0f}ms {cache_indicator}"
                        )
                    else:
                        response.failure("Missing 'answer' field")
                except Exception as e:
                    response.failure(f"JSON parse error: {e}")
            elif response.status_code == 503:
                # Circuit breaker triggered!
                print(f"⚡ Circuit breaker OPEN for query: '{query[:30]}...'")
                response.success()  # Not a failure, expected behavior
            elif response.status_code == 500:
                # Server error (Ollama may be down)
                print(f"⚠️ Server error for query: '{query[:30]}...'")
                response.failure("Server error")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def cache_stats(self):
        """Check cache stats - monitoring cache hit rate"""
        with self.client.get(
            RagTestConfig.CACHE_STATS_ENDPOINT,
            timeout=RagTestConfig.CACHE_TIMEOUT,
            catch_response=True,
            name="Cache Stats",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "semantic_cache" in data and data["semantic_cache"]:
                        cache = data["semantic_cache"]
                        hit_rate = (
                            cache["cache_hits"] / cache["total_requests"] * 100
                            if cache["total_requests"] > 0
                            else 0
                        )
                        print(
                            f"📊 Cache: {cache['cache_hits']}/{cache['total_requests']} hits ({hit_rate:.1f}% hit rate)"
                        )
                    response.success()
                except Exception as e:
                    response.failure(f"Parse error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def health_check(self):
        """Health check endpoint"""
        with self.client.get(
            RagTestConfig.HEALTH_ENDPOINT,
            timeout=5,
            catch_response=True,
            name="Health Check",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
