"""
🎯 Advanced Load Test Scenarios - Sprint 3 Day 1
================================================

Các pattern stress test khác nhau để validate hệ thống!

Scenarios:
1. Normal Load: Traffic ổn định (baseline)
2. Spike Test: Traffic tăng đột ngột (black friday!)
3. Stress Test: Tăng dần đến breaking point
4. Soak Test: Chạy lâu dài để detect memory leaks
5. Circuit Breaker Test: Trigger và validate failover

Vibe: Kiểm tra ổn định như siêu anh hùng! 🦸‍♂️
"""

import time
from dataclasses import dataclass

from locust import HttpUser, TaskSet, between, task

# ============================================================================
# 📊 Scenario Configurations
# ============================================================================


@dataclass
class ScenarioConfig:
    """Configuration cho mỗi scenario - ổn định như kim cương! 💎"""

    name: str
    description: str
    users: int
    spawn_rate: int  # users/second
    duration_minutes: int
    wait_min: float
    wait_max: float


# Định nghĩa các scenarios
SCENARIOS = {
    "normal": ScenarioConfig(
        name="Normal Load",
        description="Baseline traffic - 50 users tương tác tự nhiên",
        users=50,
        spawn_rate=5,
        duration_minutes=5,
        wait_min=2.0,
        wait_max=5.0,
    ),
    "spike": ScenarioConfig(
        name="Spike Test",
        description="Traffic spike - Từ 10 lên 200 users trong 30s!",
        users=200,
        spawn_rate=50,  # Tăng nhanh như rocket! 🚀
        duration_minutes=3,
        wait_min=0.5,
        wait_max=2.0,
    ),
    "stress": ScenarioConfig(
        name="Stress Test",
        description="Tăng dần đến breaking point - 500+ users",
        users=500,
        spawn_rate=10,  # Tăng từ từ để quan sát
        duration_minutes=10,
        wait_min=0.1,
        wait_max=1.0,
    ),
    "soak": ScenarioConfig(
        name="Soak Test",
        description="Chạy lâu dài - 100 users trong 30 phút",
        users=100,
        spawn_rate=5,
        duration_minutes=30,
        wait_min=2.0,
        wait_max=5.0,
    ),
    "circuit_breaker": ScenarioConfig(
        name="Circuit Breaker Validation",
        description="Force trigger circuit breaker - 300 users burst",
        users=300,
        spawn_rate=100,  # Burst cực nhanh!
        duration_minutes=2,
        wait_min=0.0,
        wait_max=0.5,
    ),
}


# ============================================================================
# 🎭 Specialized User Behaviors for Scenarios
# ============================================================================


class NormalLoadBehavior(TaskSet):
    """
    Behavior cho normal load: Balanced queries

    Mô phỏng user bình thường, không áp lực! 😌
    """

    @task(5)
    def generate_query(self):
        """Query generation - task chính"""
        payload = {
            "model": "llama2",
            "prompt": "What is machine learning?",
            "stream": False,
        }

        with self.client.post(
            "/api/generate", json=payload, timeout=30, catch_response=True, name="Generate [Normal]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                # Circuit breaker - expected
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def check_metrics(self):
        """Metrics check"""
        with self.client.get(
            "/metrics", timeout=5, catch_response=True, name="Metrics [Normal]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class SpikeTestBehavior(TaskSet):
    """
    Behavior cho spike test: Aggressive queries

    Burst traffic như Black Friday! 🔥
    """

    @task(10)  # Weight cao hơn!
    def burst_generate(self):
        """Rapid-fire queries"""
        payload = {
            "model": "llama2",
            "prompt": "Quick question!",
            "stream": False,
        }

        with self.client.post(
            "/api/generate", json=payload, timeout=30, catch_response=True, name="Generate [Spike]"
        ) as response:
            # Accept cả 200 và 503 (circuit breaker)
            if response.status_code in [200, 503]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(3)
    def rapid_health_check(self):
        """Health checks dồn dập"""
        with self.client.get(
            "/health", timeout=5, catch_response=True, name="Health [Spike]"
        ) as response:
            if response.status_code == 200:
                response.success()


class StressTestBehavior(TaskSet):
    """
    Behavior cho stress test: Push to limits

    Đẩy hệ thống đến giới hạn! 💪
    """

    @task(8)
    def heavy_query(self):
        """Heavy computation queries"""
        payload = {
            "model": "llama2",
            "prompt": "Explain quantum computing in detail with examples",
            "stream": False,
        }

        with self.client.post(
            "/api/generate",
            json=payload,
            timeout=60,  # Longer timeout cho heavy query
            catch_response=True,
            name="Generate [Stress]",
        ) as response:
            if response.status_code in [200, 503]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(5)
    def concurrent_metrics(self):
        """Concurrent metrics checks"""
        with self.client.get(
            "/metrics", timeout=10, catch_response=True, name="Metrics [Stress]"
        ) as response:
            if response.status_code == 200:
                response.success()


class CircuitBreakerTestBehavior(TaskSet):
    """
    Behavior specific để trigger circuit breaker

    Force failover để validate protective mechanisms! ⚡
    """

    @task(10)
    def force_failure(self):
        """Queries designed to trigger failures"""
        payload = {
            "model": "llama2",
            "prompt": "Test circuit breaker trigger",
            "stream": False,
        }

        start_time = time.time()

        with self.client.post(
            "/api/generate",
            json=payload,
            timeout=5,  # Short timeout để nhanh trigger
            catch_response=True,
            name="Generate [CB Test]",
        ) as response:
            latency = (time.time() - start_time) * 1000

            if response.status_code == 503:
                # Circuit breaker OPEN - Mục tiêu đạt được! ✅
                print(f"✅ Circuit breaker triggered! Latency: {latency:.2f}ms")
                response.success()
            elif response.status_code == 200:
                # Normal response - OK
                response.success()
            else:
                response.failure(f"Unexpected: HTTP {response.status_code}")

    @task(5)
    def verify_metrics(self):
        """Verify circuit breaker metrics"""
        with self.client.get(
            "/metrics", timeout=5, catch_response=True, name="CB Metrics Verify"
        ) as response:
            if response.status_code == 200:
                # Check for circuit breaker metrics
                if "circuit_breaker_state" in response.text:
                    response.success()
                    print("📊 Circuit breaker metrics found!")
                else:
                    response.failure("Missing CB metrics")


# ============================================================================
# 👥 User Classes for Each Scenario
# ============================================================================


class NormalLoadUser(HttpUser):
    """User cho normal load scenario"""

    tasks = [NormalLoadBehavior]
    wait_time = between(2, 5)


class SpikeTestUser(HttpUser):
    """User cho spike test scenario"""

    tasks = [SpikeTestBehavior]
    wait_time = between(0.5, 2)


class StressTestUser(HttpUser):
    """User cho stress test scenario"""

    tasks = [StressTestBehavior]
    wait_time = between(0.1, 1)


class CircuitBreakerTestUser(HttpUser):
    """User cho circuit breaker validation"""

    tasks = [CircuitBreakerTestBehavior]
    wait_time = between(0, 0.5)


# ============================================================================
# 🎬 Scenario Runner Helper
# ============================================================================


class ScenarioRunner:
    """
    Helper class để chạy các scenarios một cách có tổ chức!

    Quản lý workflow như một conductor! 🎼
    """

    @staticmethod
    def print_scenario_info(scenario_name: str):
        """In thông tin scenario trước khi chạy"""
        if scenario_name not in SCENARIOS:
            print(f"❌ Unknown scenario: {scenario_name}")
            return

        config = SCENARIOS[scenario_name]
        print(
            f"""
╔═══════════════════════════════════════════════════════════════╗
║  🎯 {config.name.upper()}
╚═══════════════════════════════════════════════════════════════╝

Description: {config.description}

Configuration:
  - Users: {config.users}
  - Spawn Rate: {config.spawn_rate} users/second
  - Duration: {config.duration_minutes} minutes
  - Wait Time: {config.wait_min}s - {config.wait_max}s

Command to run:
  locust -f scenarios.py \\
         --host=http://localhost:8000 \\
         --users {config.users} \\
         --spawn-rate {config.spawn_rate} \\
         --run-time {config.duration_minutes}m \\
         --headless \\
         --html reports/{scenario_name}_report.html

Or Web UI:
  locust -f scenarios.py --host=http://localhost:8000

Press Ctrl+C to stop!
╔═══════════════════════════════════════════════════════════════╗
        """
        )

    @staticmethod
    def get_scenario_command(scenario_name: str) -> str:
        """Generate command cho scenario"""
        if scenario_name not in SCENARIOS:
            return "# Invalid scenario"

        config = SCENARIOS[scenario_name]
        return f"""locust -f scenarios.py \\
       --host=http://localhost:8000 \\
       --users {config.users} \\
       --spawn-rate {config.spawn_rate} \\
       --run-time {config.duration_minutes}m \\
       --headless \\
       --html reports/{scenario_name}_report.html"""


# ============================================================================
# 🎬 Main Entry Point
# ============================================================================

if __name__ == "__main__":
    """
    Entry point với hướng dẫn sử dụng!
    """
    print(
        """
╔═══════════════════════════════════════════════════════════════╗
║  🔥 Advanced Load Test Scenarios - Sprint 3
╚═══════════════════════════════════════════════════════════════╝

Available Scenarios:
  1. normal          - Baseline traffic (50 users, 5 min)
  2. spike           - Traffic spike (200 users, 3 min)
  3. stress          - Stress test (500 users, 10 min)
  4. soak            - Long run test (100 users, 30 min)
  5. circuit_breaker - CB validation (300 users, 2 min)

Usage:
  # Show scenario info:
  python scenarios.py <scenario_name>

  # Run scenario (Web UI):
  locust -f scenarios.py --host=http://localhost:8000

  # Run scenario (Headless):
  locust -f scenarios.py --host=http://localhost:8000 \\
         --users <N> --spawn-rate <R> --run-time <T>m --headless

Examples:
  # Normal load test with Web UI:
  locust -f scenarios.py --host=http://localhost:8000

  # Spike test headless:
  locust -f scenarios.py --host=http://localhost:8000 \\
         --users 200 --spawn-rate 50 --run-time 3m --headless

Vibe: Test scenarios như pro! 🎸
╔═══════════════════════════════════════════════════════════════╗
    """
    )

    # If argument provided, show scenario info
    import sys

    if len(sys.argv) > 1:
        scenario_name = sys.argv[1]
        ScenarioRunner.print_scenario_info(scenario_name)
