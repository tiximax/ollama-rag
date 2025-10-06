"""
Integration Tests for OllamaClient with Circuit Breaker
========================================================
Test Circuit Breaker integration với Ollama client - real-world scenarios! 🌍
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from app.circuit_breaker import CircuitState
from app.ollama_client import OllamaClient


class TestOllamaClientCircuitBreaker:
    """Test Circuit Breaker integration với OllamaClient 🛡️"""

    def test_client_initializes_with_circuit_breaker_by_default(self):
        """Client khởi tạo với Circuit Breaker enabled by default ✅"""
        client = OllamaClient()
        assert client._circuit_breaker is not None
        assert client._circuit_breaker.state == CircuitState.CLOSED

    def test_client_can_disable_circuit_breaker(self):
        """Client có thể tắt Circuit Breaker nếu cần 🔌"""
        client = OllamaClient(enable_circuit_breaker=False)
        assert client._circuit_breaker is None

    def test_get_circuit_metrics_when_enabled(self):
        """get_circuit_metrics returns metrics khi enabled 📊"""
        client = OllamaClient()
        metrics = client.get_circuit_metrics()

        assert "name" in metrics
        assert metrics["name"] == "ollama_client"
        assert "state" in metrics
        assert metrics["state"] == "closed"

    def test_get_circuit_metrics_when_disabled(self):
        """get_circuit_metrics returns disabled status khi tắt 🚫"""
        client = OllamaClient(enable_circuit_breaker=False)
        metrics = client.get_circuit_metrics()

        assert metrics == {"circuit_breaker": "disabled"}

    @patch("app.ollama_client.requests.Session")
    def test_embed_with_circuit_breaker_on_success(self, mock_session_class):
        """embed() passes through khi circuit CLOSED và call success 🟢"""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_session.request.return_value = mock_response

        client = OllamaClient()
        result = client.embed(["test text"])

        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
        assert client._circuit_breaker.state == CircuitState.CLOSED

    @patch("app.ollama_client.requests.Session")
    def test_embed_opens_circuit_after_failures(self, mock_session_class):
        """Circuit opens sau consecutive failures 🔴"""
        # Setup mock to always fail
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.ConnectionError("Connection failed")

        client = OllamaClient()

        # Trigger failures to open circuit
        for _ in range(5):  # failure_threshold = 5
            result = client.embed(["test"])
            # Should return fallback empty embeddings
            assert len(result) == 1
            assert len(result[0]) == 768  # Default dimension

        # Circuit should be OPEN now
        assert client._circuit_breaker.state == CircuitState.OPEN

    @patch("app.ollama_client.requests.Session")
    def test_embed_returns_fallback_when_circuit_open(self, mock_session_class):
        """embed() returns fallback khi circuit OPEN 🚨"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.ConnectionError("Connection failed")

        client = OllamaClient()

        # Open the circuit
        for _ in range(5):
            client.embed(["test"])

        assert client._circuit_breaker.state == CircuitState.OPEN

        # Call should return fallback without hitting Ollama
        result = client.embed(["test text"])
        assert len(result) == 1
        assert len(result[0]) == 768
        assert all(x == 0.0 for x in result[0])  # Empty embedding

    @patch("app.ollama_client.requests.Session")
    def test_generate_with_circuit_breaker_on_success(self, mock_session_class):
        """generate() works với circuit breaker 🟢"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Generated text"}
        mock_session.request.return_value = mock_response

        client = OllamaClient()
        result = client.generate("test prompt")

        assert result == "Generated text"
        assert client._circuit_breaker.state == CircuitState.CLOSED

    @patch("app.ollama_client.requests.Session")
    def test_generate_returns_fallback_when_circuit_open(self, mock_session_class):
        """generate() returns error message khi circuit OPEN 🚨"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.ConnectionError("Connection failed")

        client = OllamaClient()

        # Open the circuit
        for _ in range(5):
            client.generate("test")

        assert client._circuit_breaker.state == CircuitState.OPEN

        # Should return fallback message
        result = client.generate("test prompt")
        assert "Service temporarily unavailable" in result
        assert "try again" in result.lower()

    @patch("app.ollama_client.requests.Session")
    def test_circuit_breaker_tracks_metrics(self, mock_session_class):
        """Circuit breaker tracks metrics correctly 📈"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Setup successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1, 0.2]}
        mock_session.request.return_value = mock_response

        client = OllamaClient()

        # Make some successful calls
        client.embed(["text1"])
        client.embed(["text2"])

        metrics = client.get_circuit_metrics()
        assert metrics["total_calls"] == 2
        assert metrics["success_calls"] == 2
        assert metrics["failure_calls"] == 0
        assert metrics["error_rate_percent"] == 0.0

    def test_state_change_callback_is_called(self):
        """State change callback được gọi khi circuit state changes 🔔"""
        callback_calls = []

        def mock_callback(old_state, new_state):
            callback_calls.append((old_state.value, new_state.value))

        with patch("app.ollama_client.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            mock_session.request.side_effect = requests.ConnectionError("Fail")

            client = OllamaClient()
            # Override callback để test
            client._circuit_breaker.on_state_change = mock_callback

            # Trigger failures
            for _ in range(5):
                client.embed(["test"])

            # Should have callback for CLOSED → OPEN
            assert ("closed", "open") in callback_calls


class TestOllamaClientWithoutCircuitBreaker:
    """Test OllamaClient behavior khi Circuit Breaker disabled 🚫"""

    @patch("app.ollama_client.requests.Session")
    def test_embed_without_circuit_breaker_raises_on_failure(self, mock_session_class):
        """embed() raises exception khi Circuit Breaker disabled và có lỗi ❌"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.ConnectionError("Connection failed")

        client = OllamaClient(enable_circuit_breaker=False)

        with pytest.raises(requests.ConnectionError):
            client.embed(["test"])

    @patch("app.ollama_client.requests.Session")
    def test_generate_without_circuit_breaker_raises_on_failure(self, mock_session_class):
        """generate() raises exception khi Circuit Breaker disabled ❌"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.ConnectionError("Connection failed")

        client = OllamaClient(enable_circuit_breaker=False)

        with pytest.raises(requests.ConnectionError):
            client.generate("test")
