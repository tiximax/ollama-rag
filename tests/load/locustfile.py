"""
🔥 Load Testing Master File - Sprint 3 Day 1
============================================

Mục đích: Stress-test hệ thống RAG với Ollama, validate metrics thực chiến!

Features:
- Realistic user behavior simulation (query, chat, RAG retrieval)
- Multiple load patterns (normal, spike, stress)
- Live Prometheus metrics integration
- Circuit breaker & connection pool validation

Vibe: Testing như một rockstar! 🎸
"""

import json
import random
import time

from locust import HttpUser, TaskSet, between, task

# ============================================================================
# 🎯 Configuration - Tùy chỉnh theo nhu cầu stress test
# ============================================================================


class LoadTestConfig:
    """Configuration ổn định cho load tests như kim cương! 💎"""

    # Endpoints to test
    OLLAMA_GENERATE_ENDPOINT = "/api/generate"
    OLLAMA_CHAT_ENDPOINT = "/api/chat"
    METRICS_ENDPOINT = "/metrics"
    HEALTH_ENDPOINT = "/health"

    # Test data - Realistic queries
    SAMPLE_QUERIES = [
        "What is machine learning?",
        "Explain neural networks",
        "How does RAG work?",
        "Tell me about transformers",
        "What is semantic search?",
        "Explain vector databases",
        "How to optimize LLM inference?",
        "What is prompt engineering?",
        "Describe attention mechanism",
        "What are embeddings?",
    ]

    # Chat conversation templates
    CHAT_TEMPLATES = [
        {"role": "user", "content": "Hello! Can you help me understand {topic}?"},
        {"role": "assistant", "content": "Of course! I'd be happy to explain {topic}."},
        {"role": "user", "content": "Can you give me an example?"},
    ]

    # Model to use for testing
    TEST_MODEL = "llama2"  # Thay đổi theo model bạn có

    # Request timeouts (seconds)
    GENERATE_TIMEOUT = 30
    CHAT_TIMEOUT = 30
    METRICS_TIMEOUT = 5


# ============================================================================
# 🎭 User Behaviors - Mô phỏng hành vi người dùng thực tế
# ============================================================================


class OllamaUserBehavior(TaskSet):
    """
    Hành vi user chuẩn chỉnh: query → check metrics → chat

    Mô phỏng workflow thực tế của user tương tác với RAG system!
    """

    def on_start(self):
        """
        Khởi tạo khi user bắt đầu session.
        Như lính canh, setup mọi thứ trước khi vào trận! 🚪
        """
        self.user_id = f"user_{random.randint(1000, 9999)}"
        self.session_start = time.time()
        print(f"🚀 User {self.user_id} started session")

    @task(5)
    def generate_query(self):
        """
        Task chính: Generate response từ query (weight=5)

        Đây là task phổ biến nhất, chiếm 50% traffic!
        """
        query = random.choice(LoadTestConfig.SAMPLE_QUERIES)

        payload = {
            "model": LoadTestConfig.TEST_MODEL,
            "prompt": query,
            "stream": False,  # Không stream để dễ đo latency
        }

        with self.client.post(
            LoadTestConfig.OLLAMA_GENERATE_ENDPOINT,
            json=payload,
            timeout=LoadTestConfig.GENERATE_TIMEOUT,
            catch_response=True,
            name="Ollama Generate",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Validate response có đúng format không
                    if "response" in data:
                        response.success()
                        print(f"✅ {self.user_id}: Query successful - {query[:30]}...")
                    else:
                        response.failure("Missing 'response' field in JSON")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 503:
                # Circuit breaker OPEN - Expected behavior!
                print(f"⚡ {self.user_id}: Circuit breaker triggered (503)")
                response.success()  # Không tính là lỗi, là feature!
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(3)
    def chat_conversation(self):
        """
        Task chat: Multi-turn conversation (weight=3)

        Mô phỏng cuộc trò chuyện nhiều lượt với context!
        """
        topic = random.choice(["AI", "ML", "NLP", "RAG", "LLMs"])

        # Build conversation from template
        messages = [
            {"role": msg["role"], "content": msg["content"].format(topic=topic)}
            for msg in LoadTestConfig.CHAT_TEMPLATES
        ]

        payload = {
            "model": LoadTestConfig.TEST_MODEL,
            "messages": messages,
            "stream": False,
        }

        with self.client.post(
            LoadTestConfig.OLLAMA_CHAT_ENDPOINT,
            json=payload,
            timeout=LoadTestConfig.CHAT_TIMEOUT,
            catch_response=True,
            name="Ollama Chat",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "message" in data:
                        response.success()
                        print(f"💬 {self.user_id}: Chat successful about {topic}")
                    else:
                        response.failure("Missing 'message' field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 503:
                print(f"⚡ {self.user_id}: Circuit breaker triggered in chat")
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def check_metrics(self):
        """
        Task metrics check (weight=2)

        User hoặc monitoring system check metrics định kỳ!
        """
        with self.client.get(
            LoadTestConfig.METRICS_ENDPOINT,
            timeout=LoadTestConfig.METRICS_TIMEOUT,
            catch_response=True,
            name="Metrics Check",
        ) as response:
            if response.status_code == 200:
                # Validate Prometheus format
                if "ollama_requests_total" in response.text:
                    response.success()
                    print(f"📊 {self.user_id}: Metrics checked")
                else:
                    response.failure("Invalid Prometheus metrics format")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def health_check(self):
        """
        Task health check (weight=1)

        Load balancer hoặc monitoring check health!
        """
        with self.client.get(
            LoadTestConfig.HEALTH_ENDPOINT, timeout=5, catch_response=True, name="Health Check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# 👤 User Classes - Các loại user với behavior khác nhau
# ============================================================================


class NormalUser(HttpUser):
    """
    User bình thường: Query ổn định, wait time hợp lý

    Đây là 80% traffic thực tế - user tương tác tự nhiên! 🎯
    """

    tasks = [OllamaUserBehavior]
    wait_time = between(2, 5)  # Wait 2-5s giữa các request (realistic!)
    weight = 8  # 80% users là normal


class PowerUser(HttpUser):
    """
    Power user: Query nhiều hơn, wait time ngắn hơn

    Developer hoặc heavy user - 15% traffic! 💪
    """

    tasks = [OllamaUserBehavior]
    wait_time = between(0.5, 2)  # Nhanh hơn gấp 2-3 lần
    weight = 2  # 15% users


class SpikeUser(HttpUser):
    """
    Spike user: Burst traffic đột ngột, no wait time

    Simulate traffic spike - 5% users nhưng tạo áp lực lớn! 🔥
    """

    tasks = [OllamaUserBehavior]
    wait_time = between(0, 0.5)  # Gần như không wait
    weight = 1  # 5% users


# ============================================================================
# 🎬 Main Entry Point
# ============================================================================

if __name__ == "__main__":
    """
    Chạy local test để verify trước khi stress test lớn!

    Usage:
        locust -f locustfile.py --host=http://localhost:8000
    """
    print(
        """
    🔥 Ollama Load Test Ready!

    Commands:
        # Web UI mode (recommended):
        locust -f locustfile.py --host=http://localhost:8000

        # Headless mode (CI/CD):
        locust -f locustfile.py --host=http://localhost:8000 \\
               --users 100 --spawn-rate 10 --run-time 5m --headless

        # Distributed mode (multiple workers):
        locust -f locustfile.py --master --host=http://localhost:8000
        locust -f locustfile.py --worker --master-host=localhost

    Vibe: Testing như rockstar! 🎸
    """
    )
