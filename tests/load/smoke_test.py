"""
🔥 Smoke Test Load File - Sprint 3 Day 1
========================================

Mục đích: Verify basic endpoints hoạt động trước khi full load test!

Features:
- Test health endpoint
- Test cache stats endpoint
- Test metrics endpoint
- Lightweight, không cần database hoặc Ollama

Vibe: Testing cơ bản trước khi lên sàn đấu lớn! 🎯
"""

from locust import HttpUser, between, task


class SmokeTestUser(HttpUser):
    """
    Simple user chỉ test các endpoint cơ bản.

    Để verify server sẵn sàng cho load test lớn hơn!
    """

    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        """Health check endpoint - Task chính"""
        with self.client.get("/health", catch_response=True, name="Health Check") as response:
            if response.status_code == 200:
                response.success()
                print("✅ Health check OK")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def cache_stats(self):
        """Cache stats endpoint"""
        with self.client.get(
            "/api/cache-stats", catch_response=True, name="Cache Stats"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "database" in data:
                        response.success()
                        print("📊 Cache stats OK")
                    else:
                        response.failure("Missing database field")
                except Exception as e:
                    response.failure(f"JSON parse error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def metrics(self):
        """Prometheus metrics endpoint"""
        with self.client.get("/metrics", catch_response=True, name="Metrics") as response:
            if response.status_code == 200:
                # Just check it returns something
                if len(response.text) > 0:
                    response.success()
                    print("📈 Metrics OK")
                else:
                    response.failure("Empty metrics response")
            else:
                response.failure(f"HTTP {response.status_code}")
