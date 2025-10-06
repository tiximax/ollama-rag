"""
Unit Tests for Circuit Breaker
===============================
Comprehensive test suite để đảm bảo Circuit Breaker hoạt động như kim cương! 💎

Test coverage:
- State transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure threshold triggering
- Timeout and recovery
- Thread safety
- Metrics tracking
"""

import threading
import time

import pytest

from app.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
)


class TestCircuitBreakerBasics:
    """Basic functionality tests - foundation như nền móng! 🏗️"""

    def test_initial_state_is_closed(self):
        """Circuit breaker bắt đầu với state CLOSED ✅"""
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED

    def test_successful_call_passes_through(self):
        """Successful calls pass through khi circuit CLOSED 🟢"""
        breaker = CircuitBreaker(name="test")

        def success_func():
            return "success"

        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.stats.success_calls == 1
        assert breaker.stats.failure_calls == 0

    def test_failed_call_records_failure(self):
        """Failed calls được track chính xác 📊"""
        breaker = CircuitBreaker(name="test")

        def fail_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            breaker.call(fail_func)

        assert breaker.stats.failure_calls == 1
        assert breaker.stats.consecutive_failures == 1

    def test_decorator_works(self):
        """@breaker.protect decorator hoạt động ổn định 🎯"""
        breaker = CircuitBreaker(name="test")

        @breaker.protect
        def decorated_func(x):
            return x * 2

        result = decorated_func(5)
        assert result == 10
        assert breaker.stats.success_calls == 1


class TestStateTransitions:
    """State transition tests - logic như vàng! 🏆"""

    def test_circuit_opens_after_threshold(self):
        """Circuit opens sau khi đạt failure threshold 🔴"""
        config = CircuitBreakerConfig(failure_threshold=3, timeout=1.0)
        breaker = CircuitBreaker(name="test", config=config)

        def fail_func():
            raise RuntimeError("fail")

        # Trigger failures
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        # Circuit should be OPEN now
        assert breaker.state == CircuitState.OPEN
        assert breaker.stats.consecutive_failures == 3

    def test_circuit_open_fails_fast(self):
        """Circuit OPEN fails fast without calling function 🚨"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=1.0)
        breaker = CircuitBreaker(name="test", config=config)

        call_count = 0

        def fail_func():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

        # Now calls should fail fast without executing function
        with pytest.raises(CircuitBreakerError) as exc_info:
            breaker.call(fail_func)

        assert "is OPEN" in str(exc_info.value)
        assert call_count == 2  # Function not called again

    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Circuit chuyển sang HALF_OPEN sau timeout 🟡"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.5)
        breaker = CircuitBreaker(name="test", config=config)

        def fail_func():
            raise RuntimeError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.6)

        # Next call should transition to HALF_OPEN
        def success_func():
            return "ok"

        # This call will check state and transition to HALF_OPEN
        result = breaker.call(success_func)
        assert result == "ok"

    def test_half_open_closes_on_success(self):
        """HALF_OPEN closes sau enough successes 🟢"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.5, success_threshold=2)
        breaker = CircuitBreaker(name="test", config=config)

        def fail_func():
            raise RuntimeError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.6)

        def success_func():
            return "ok"

        # First success - should stay HALF_OPEN
        breaker.call(success_func)

        # Second success - should close
        breaker.call(success_func)

        assert breaker.state == CircuitState.CLOSED

    def test_half_open_reopens_on_failure(self):
        """HALF_OPEN reopens immediately on failure 🔴"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.5)
        breaker = CircuitBreaker(name="test", config=config)

        def fail_func():
            raise RuntimeError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        # Wait for timeout
        time.sleep(0.6)

        # Try to call - will fail and reopen
        with pytest.raises(RuntimeError):
            breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN


class TestMetricsAndStats:
    """Metrics tracking tests - data như vàng! 📊"""

    def test_stats_tracking(self):
        """Stats được track chính xác 📈"""
        breaker = CircuitBreaker(name="test")

        def success_func():
            return "ok"

        def fail_func():
            raise RuntimeError("fail")

        # Mix of success and failures
        breaker.call(success_func)
        breaker.call(success_func)
        with pytest.raises(RuntimeError):
            breaker.call(fail_func)

        stats = breaker.stats
        assert stats.total_calls == 3
        assert stats.success_calls == 2
        assert stats.failure_calls == 1
        assert stats.consecutive_failures == 1
        assert stats.consecutive_successes == 0  # Reset by failure

    def test_get_metrics(self):
        """get_metrics returns complete metrics dict 📊"""
        config = CircuitBreakerConfig(failure_threshold=5, timeout=60.0)
        breaker = CircuitBreaker(name="test_metrics", config=config)

        metrics = breaker.get_metrics()

        assert metrics["name"] == "test_metrics"
        assert metrics["state"] == "closed"
        assert metrics["total_calls"] == 0
        assert metrics["config"]["failure_threshold"] == 5
        assert metrics["config"]["timeout"] == 60.0

    def test_error_rate_calculation(self):
        """Error rate được tính đúng % 🎯"""
        breaker = CircuitBreaker(name="test")

        def success_func():
            return "ok"

        def fail_func():
            raise RuntimeError("fail")

        # 3 success, 1 failure = 25% error rate
        breaker.call(success_func)
        breaker.call(success_func)
        breaker.call(success_func)
        with pytest.raises(RuntimeError):
            breaker.call(fail_func)

        metrics = breaker.get_metrics()
        assert metrics["error_rate_percent"] == 25.0
        assert metrics["success_rate_percent"] == 75.0


class TestConfiguration:
    """Configuration tests - settings như công thức! ⚙️"""

    def test_custom_config(self):
        """Custom configuration được apply đúng ✅"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            timeout=120.0,
            success_threshold=3,
            window_size=20,
        )
        breaker = CircuitBreaker(name="test", config=config)

        assert breaker.config.failure_threshold == 10
        assert breaker.config.timeout == 120.0
        assert breaker.config.success_threshold == 3
        assert breaker.config.window_size == 20

    def test_default_config(self):
        """Default config có giá trị hợp lý 📋"""
        breaker = CircuitBreaker(name="test")
        config = breaker.config

        assert config.failure_threshold == 5
        assert config.timeout == 60.0
        assert config.success_threshold == 2
        assert config.window_size == 10


class TestThreadSafety:
    """Thread safety tests - concurrent như rockstar! 🎸"""

    def test_concurrent_calls(self):
        """Circuit breaker thread-safe cho concurrent calls 🔒"""
        breaker = CircuitBreaker(name="test")
        results = []
        lock = threading.Lock()

        def thread_func(i):
            def work():
                return i

            try:
                result = breaker.call(work)
                with lock:
                    results.append(("success", result))
            except Exception as e:
                with lock:
                    results.append(("error", str(e)))

        threads = [threading.Thread(target=thread_func, args=(i,)) for i in range(50)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All calls should succeed
        assert len(results) == 50
        successes = [r for r in results if r[0] == "success"]
        assert len(successes) == 50

        # Stats should be accurate
        assert breaker.stats.total_calls == 50
        assert breaker.stats.success_calls == 50

    def test_concurrent_failures(self):
        """Thread-safe failure tracking 🎯"""
        config = CircuitBreakerConfig(failure_threshold=10)
        breaker = CircuitBreaker(name="test", config=config)
        errors = []
        lock = threading.Lock()

        def thread_func():
            def fail_work():
                raise RuntimeError("fail")

            try:
                breaker.call(fail_work)
            except CircuitBreakerError:
                with lock:
                    errors.append("circuit_open")
            except RuntimeError:
                with lock:
                    errors.append("runtime_error")

        threads = [threading.Thread(target=thread_func) for _ in range(15)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Circuit should have opened during concurrent failures
        # Some calls will fail with RuntimeError, others with CircuitBreakerError
        assert breaker.state == CircuitState.OPEN
        assert "circuit_open" in errors  # At least some were blocked


class TestReset:
    """Reset functionality tests - fresh start! 🔄"""

    def test_reset_clears_state(self):
        """Reset clears all state và stats 🔄"""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(name="test", config=config)

        def fail_func():
            raise RuntimeError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.total_calls == 0
        assert breaker.stats.failure_calls == 0
        assert breaker.stats.consecutive_failures == 0


class TestCallbacks:
    """State change callback tests - notifications! 🔔"""

    def test_state_change_callback(self):
        """on_state_change callback được gọi đúng 📞"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.5)
        state_changes = []

        def on_change(old_state, new_state):
            state_changes.append((old_state.value, new_state.value))

        breaker = CircuitBreaker(name="test", config=config, on_state_change=on_change)

        def fail_func():
            raise RuntimeError("fail")

        # Trigger state change to OPEN
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        assert ("closed", "open") in state_changes


class TestEdgeCases:
    """Edge case tests - cover mọi tình huống! 🎭"""

    def test_half_open_max_calls_limit(self):
        """HALF_OPEN respects max calls limit 🚧"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.5, half_open_max_calls=1)
        breaker = CircuitBreaker(name="test", config=config)

        def fail_func():
            raise RuntimeError("fail")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(fail_func)

        # Wait for timeout
        time.sleep(0.6)

        # First call in HALF_OPEN should work
        def success_func():
            return "ok"

        breaker.call(success_func)

        # Second call should be blocked (max_calls=1)
        with pytest.raises(CircuitBreakerError) as exc_info:
            breaker.call(success_func)

        assert "max calls reached" in str(exc_info.value)

    def test_repr(self):
        """__repr__ provides useful debug info 🔍"""
        breaker = CircuitBreaker(name="test_repr")
        repr_str = repr(breaker)

        assert "test_repr" in repr_str
        assert "closed" in repr_str


# Integration test example
class TestIntegration:
    """Integration tests - real-world scenarios! 🌍"""

    def test_realistic_failure_recovery_scenario(self):
        """
        Realistic scenario:
        1. Service starts healthy
        2. Service degrades (failures)
        3. Circuit opens
        4. Service recovers
        5. Circuit closes
        """
        config = CircuitBreakerConfig(failure_threshold=3, timeout=0.5, success_threshold=2)
        breaker = CircuitBreaker(name="api", config=config)

        # Phase 1: Healthy service
        def healthy_call():
            return "ok"

        assert breaker.call(healthy_call) == "ok"
        assert breaker.state == CircuitState.CLOSED

        # Phase 2: Service degrades
        def failing_call():
            raise RuntimeError("service degraded")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_call)

        # Phase 3: Circuit opened
        assert breaker.state == CircuitState.OPEN
        with pytest.raises(CircuitBreakerError):
            breaker.call(healthy_call)  # Blocked even though would succeed

        # Phase 4: Wait for recovery window
        time.sleep(0.6)

        # Phase 5: Service recovered, circuit closes
        breaker.call(healthy_call)  # Transitions to HALF_OPEN
        breaker.call(healthy_call)  # Closes circuit

        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.success_calls == 3  # 1 initial + 2 in recovery
