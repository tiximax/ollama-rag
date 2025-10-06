"""
Circuit Breaker Pattern Implementation
=======================================
Circuit Breaker siêu thông minh như siêu anh hùng bảo vệ hệ thống! 🦸‍♂️

Prevents cascade failures bằng cách:
1. Tracking failures và tự động mở circuit khi quá ngưỡng
2. Timeout để circuit tự động thử lại (half-open state)
3. Graceful degradation thay vì crash toàn hệ thống

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit tripped, requests fail fast
- HALF_OPEN: Testing if service recovered

Ổn định như kim cương! 💎
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

# Import metrics helpers - monitoring như siêu anh hùng! 🦸‍♂️
try:
    from app import metrics

    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit Breaker states - rõ ràng như ban ngày! ☀️"""

    CLOSED = "closed"  # Normal: requests pass through
    OPEN = "open"  # Circuit tripped: fail fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """
    Circuit Breaker configuration - cấu hình như công thức vàng! 📊

    Attributes:
        failure_threshold: Số lỗi liên tiếp trước khi mở circuit
        timeout: Thời gian (seconds) giữ circuit OPEN trước khi thử HALF_OPEN
        success_threshold: Số success cần trong HALF_OPEN để đóng circuit
        window_size: Kích thước window tracking failures (sliding window)
        half_open_max_calls: Số calls tối đa cho phép trong HALF_OPEN state
    """

    failure_threshold: int = 5
    timeout: float = 60.0  # seconds
    success_threshold: int = 2
    window_size: int = 10
    half_open_max_calls: int = 3  # Allow multiple test calls in HALF_OPEN


@dataclass
class CircuitBreakerStats:
    """Statistics tracking - metrics như rockstar! 🎸"""

    total_calls: int = 0
    success_calls: int = 0
    failure_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    state_transitions: int = 0


class CircuitBreakerError(Exception):
    """Exception khi circuit OPEN - thông báo rõ ràng! 🚨"""

    def __init__(self, message: str, stats: CircuitBreakerStats | None = None):
        super().__init__(message)
        self.stats = stats


class CircuitBreaker:
    """
    Circuit Breaker implementation - bảo vệ như siêu anh hùng! 🦸‍♂️

    Sử dụng sliding window để track failures và tự động mở/đóng circuit
    dựa trên thresholds. Thread-safe cho concurrent requests!

    Example:
        >>> breaker = CircuitBreaker(name="ollama", failure_threshold=5)
        >>> @breaker.protect
        ... def call_api():
        ...     return requests.get("http://api.example.com")
        >>> result = call_api()  # Protected by circuit breaker!
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        on_state_change: Callable[[CircuitState, CircuitState], None] | None = None,
    ):
        """
        Khởi tạo Circuit Breaker - ổn định như kim cương! 💎

        Args:
            name: Tên circuit breaker (for logging/metrics)
            config: Configuration object (sử dụng defaults nếu None)
            on_state_change: Optional callback khi state thay đổi
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change

        # State management - thread-safe với lock! 🔒
        self._state = CircuitState.CLOSED
        self._lock = threading.RLock()  # Reentrant lock cho nested calls

        # Failure tracking với sliding window
        self._failure_window: deque[float] = deque(maxlen=self.config.window_size)

        # Statistics tracking
        self._stats = CircuitBreakerStats()

        # State transition tracking
        self._opened_at: float | None = None
        self._half_open_calls: int = 0

        logger.info(
            f"🔌 Circuit Breaker '{name}' initialized: "
            f"failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current state - thread-safe! 🔒"""
        with self._lock:
            return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get current statistics - snapshot như ảnh! 📸"""
        with self._lock:
            return CircuitBreakerStats(
                total_calls=self._stats.total_calls,
                success_calls=self._stats.success_calls,
                failure_calls=self._stats.failure_calls,
                consecutive_failures=self._stats.consecutive_failures,
                consecutive_successes=self._stats.consecutive_successes,
                last_failure_time=self._stats.last_failure_time,
                last_success_time=self._stats.last_success_time,
                state_transitions=self._stats.state_transitions,
            )

    def _transition_to(self, new_state: CircuitState):
        """
        Chuyển state - tracking như pro! 🎯

        Thread-safe state transition với logging và callback.
        """
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        self._stats.state_transitions += 1

        # Update Prometheus metrics - real-time monitoring! 📊
        if METRICS_ENABLED:
            try:
                metrics.record_circuit_breaker_transition(
                    breaker_name=self.name, from_state=old_state.value, to_state=new_state.value
                )
                metrics.update_circuit_breaker_state(breaker_name=self.name, state=new_state.value)
            except Exception as e:
                logger.debug(f"Metrics update failed (non-critical): {e}")

        # Update state-specific tracking
        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self._half_open_calls = 0
            logger.warning(
                f"🔴 Circuit '{self.name}' OPENED after "
                f"{self._stats.consecutive_failures} consecutive failures"
            )
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            logger.info(f"🟡 Circuit '{self.name}' entering HALF_OPEN (testing recovery)")
        elif new_state == CircuitState.CLOSED:
            self._opened_at = None
            self._failure_window.clear()
            logger.info(f"🟢 Circuit '{self.name}' CLOSED (recovered)")

        # Callback notification
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    def _check_and_update_state(self):
        """
        Kiểm tra và update state dựa trên conditions - logic như vàng! 🏆

        Called before mỗi request để xác định xem circuit có mở/đóng không.
        """
        current_time = time.time()

        if self._state == CircuitState.OPEN:
            # Check if timeout expired → transition to HALF_OPEN
            if (
                self._opened_at is not None
                and current_time - self._opened_at >= self.config.timeout
            ):
                self._transition_to(CircuitState.HALF_OPEN)

    def _record_success(self):
        """
        Ghi nhận success - tracking như siêu sao! ⭐

        Updates stats và state transitions dựa trên consecutive successes.
        """
        with self._lock:
            self._stats.total_calls += 1
            self._stats.success_calls += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()

            # Update Prometheus metrics - success tracking! ✅
            if METRICS_ENABLED:
                try:
                    metrics.record_circuit_breaker_call(breaker_name=self.name, status='success')
                    metrics.update_circuit_breaker_failures(
                        breaker_name=self.name, consecutive_failures=0
                    )
                except Exception as e:
                    logger.debug(f"Metrics update failed (non-critical): {e}")

            if self._state == CircuitState.HALF_OPEN:
                # Success in HALF_OPEN → check if can close
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _record_failure(self):
        """
        Ghi nhận failure - tracking chính xác! 🎯

        Updates failure window và checks nếu cần open circuit.
        """
        with self._lock:
            current_time = time.time()
            self._stats.total_calls += 1
            self._stats.failure_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = current_time

            # Update Prometheus metrics - failure tracking! ❌
            if METRICS_ENABLED:
                try:
                    metrics.record_circuit_breaker_call(breaker_name=self.name, status='failure')
                    metrics.update_circuit_breaker_failures(
                        breaker_name=self.name,
                        consecutive_failures=self._stats.consecutive_failures,
                    )
                except Exception as e:
                    logger.debug(f"Metrics update failed (non-critical): {e}")

            # Add to sliding window
            self._failure_window.append(current_time)

            if self._state == CircuitState.HALF_OPEN:
                # Failure in HALF_OPEN → reopen circuit immediately
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                # Check if should open based on consecutive failures
                if self._stats.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function với circuit breaker protection - an toàn tuyệt đối! 🛡️

        Args:
            func: Function to execute
            *args: Positional arguments cho func
            **kwargs: Keyword arguments cho func

        Returns:
            Result từ func nếu success

        Raises:
            CircuitBreakerError: Nếu circuit OPEN
            Exception: Original exception từ func nếu call fails
        """
        with self._lock:
            self._check_and_update_state()

            # Check if circuit is open
            if self._state == CircuitState.OPEN:
                # Record rejected call in metrics 🚫
                if METRICS_ENABLED:
                    try:
                        metrics.record_circuit_breaker_call(
                            breaker_name=self.name, status='rejected'
                        )
                    except Exception:
                        pass
                raise CircuitBreakerError(
                    f"Circuit '{self.name}' is OPEN (will retry after timeout)",
                    stats=self.stats,
                )

            # Check half-open call limit
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    # Record rejected call in metrics 🚫
                    if METRICS_ENABLED:
                        try:
                            metrics.record_circuit_breaker_call(
                                breaker_name=self.name, status='rejected'
                            )
                        except Exception:
                            pass
                    raise CircuitBreakerError(
                        f"Circuit '{self.name}' is HALF_OPEN and max calls reached",
                        stats=self.stats,
                    )
                self._half_open_calls += 1

        # Execute function (outside lock để tránh block other threads!)
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            logger.error(f"❌ Circuit '{self.name}' call failed: {type(e).__name__}: {e}")
            raise

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator để wrap function với circuit breaker - dễ dàng như ăn kẹo! 🍬

        Example:
            >>> breaker = CircuitBreaker(name="api")
            >>> @breaker.protect
            ... def call_api():
            ...     return requests.get("http://api.example.com")
        """

        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    def reset(self):
        """
        Reset circuit breaker về initial state - fresh start! 🔄

        Useful for testing hoặc manual recovery.
        """
        with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._opened_at = None
            self._failure_window.clear()
            self._half_open_calls = 0
            self._stats = CircuitBreakerStats()
            logger.info(f"🔄 Circuit '{self.name}' reset (was {old_state.value})")

    def get_metrics(self) -> dict[str, Any]:
        """
        Get metrics dictionary - perfect cho monitoring! 📊

        Returns:
            Dict với all metrics và state info
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "total_calls": self._stats.total_calls,
                "success_calls": self._stats.success_calls,
                "failure_calls": self._stats.failure_calls,
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "error_rate_percent": (
                    (self._stats.failure_calls / self._stats.total_calls * 100)
                    if self._stats.total_calls > 0
                    else 0.0
                ),
                "success_rate_percent": (
                    (self._stats.success_calls / self._stats.total_calls * 100)
                    if self._stats.total_calls > 0
                    else 0.0
                ),
                "state_transitions": self._stats.state_transitions,
                "last_failure_time": (
                    datetime.fromtimestamp(self._stats.last_failure_time).isoformat()
                    if self._stats.last_failure_time
                    else None
                ),
                "last_success_time": (
                    datetime.fromtimestamp(self._stats.last_success_time).isoformat()
                    if self._stats.last_success_time
                    else None
                ),
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "timeout": self.config.timeout,
                    "success_threshold": self.config.success_threshold,
                    "window_size": self.config.window_size,
                },
            }

    def __repr__(self) -> str:
        """String representation - debug như pro! 🔍"""
        return (
            f"CircuitBreaker(name='{self.name}', state={self._state.value}, "
            f"failures={self._stats.consecutive_failures})"
        )
