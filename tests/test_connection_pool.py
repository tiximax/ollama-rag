"""
Unit tests for HTTP Connection Pooling in OllamaClient.

Tests verify connection pooling configuration, metrics tracking,
and proper connection reuse.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from requests.adapters import HTTPAdapter

from app.ollama_client import OllamaClient


class TestConnectionPool(unittest.TestCase):
    """Test HTTP connection pooling functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Save original env vars
        self.original_env = {
            "OLLAMA_POOL_CONNECTIONS": os.environ.get("OLLAMA_POOL_CONNECTIONS"),
            "OLLAMA_POOL_MAXSIZE": os.environ.get("OLLAMA_POOL_MAXSIZE"),
            "OLLAMA_POOL_BLOCK": os.environ.get("OLLAMA_POOL_BLOCK"),
        }

    def tearDown(self):
        """Clean up after tests."""
        # Restore original env vars
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Reload module to pick up restored env vars
        from importlib import reload

        import app.ollama_client

        reload(app.ollama_client)

    def test_connection_pool_initialized(self):
        """Test that connection pool is properly initialized."""
        client = OllamaClient(enable_circuit_breaker=False)

        # Verify session exists
        self.assertIsNotNone(client.session)

        # Verify HTTP adapter is mounted
        http_adapter = client.session.get_adapter("http://")
        self.assertIsInstance(http_adapter, HTTPAdapter)

        # Verify HTTPS adapter is mounted
        https_adapter = client.session.get_adapter("https://")
        self.assertIsInstance(https_adapter, HTTPAdapter)

    def test_connection_pool_default_config(self):
        """Test default connection pool configuration."""
        client = OllamaClient(enable_circuit_breaker=False)

        # Get metrics to check config
        metrics = client.get_connection_pool_metrics()

        self.assertIn("pool_config", metrics)
        config = metrics["pool_config"]

        # Check default values
        self.assertEqual(config["pool_connections"], 10)
        self.assertEqual(config["pool_maxsize"], 20)
        self.assertEqual(config["pool_block"], False)

    def test_connection_pool_custom_config(self):
        """Test custom connection pool configuration via environment."""
        os.environ["OLLAMA_POOL_CONNECTIONS"] = "5"
        os.environ["OLLAMA_POOL_MAXSIZE"] = "15"
        os.environ["OLLAMA_POOL_BLOCK"] = "true"

        # Need to reimport to pick up new env vars
        from importlib import reload

        import app.ollama_client

        reload(app.ollama_client)

        client = app.ollama_client.OllamaClient(enable_circuit_breaker=False)

        metrics = client.get_connection_pool_metrics()
        config = metrics["pool_config"]

        # Check custom values
        self.assertEqual(config["pool_connections"], 5)
        self.assertEqual(config["pool_maxsize"], 15)
        self.assertEqual(config["pool_block"], True)

    def test_connection_stats_tracking(self):
        """Test that connection statistics are tracked."""
        client = OllamaClient(enable_circuit_breaker=False)

        # Initial stats should be zero
        metrics = client.get_connection_pool_metrics()
        self.assertEqual(metrics["total_requests"], 0)

        # Mock a request to increment counter
        with patch.object(client.session, 'request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"embedding": [0.1, 0.2]}
            mock_request.return_value = mock_response

            try:
                client._request("POST", "/api/embeddings", json_body={"prompt": "test"})
            except Exception:
                pass  # Don't care about response validation

            # Stats should increment
            metrics_after = client.get_connection_pool_metrics()
            self.assertGreater(metrics_after["total_requests"], 0)

    def test_connection_reuse_no_close_header(self):
        """Test that 'Connection: close' header is NOT sent."""
        client = OllamaClient(enable_circuit_breaker=False)

        with patch.object(client.session, 'request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"tags": []}
            mock_request.return_value = mock_response

            try:
                client._request("POST", "/api/tags", json_body={})
            except Exception:
                pass

            # Verify request was made without Connection: close header
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args.kwargs

            # Headers should NOT contain "Connection: close"
            headers = call_kwargs.get("headers", {})
            self.assertNotIn("Connection", headers)

    def test_metrics_structure(self):
        """Test that connection pool metrics have correct structure."""
        client = OllamaClient(enable_circuit_breaker=False)

        metrics = client.get_connection_pool_metrics()

        # Verify required fields
        self.assertIn("total_requests", metrics)
        self.assertIn("pool_config", metrics)
        self.assertIn("adapter_info", metrics)

        # Verify pool_config structure
        config = metrics["pool_config"]
        self.assertIn("pool_connections", config)
        self.assertIn("pool_maxsize", config)
        self.assertIn("pool_block", config)

        # Verify adapter_info structure
        adapter_info = metrics["adapter_info"]
        self.assertIn("http_adapter", adapter_info)
        self.assertIn("https_adapter", adapter_info)

    def test_adapter_configuration(self):
        """Test that HTTPAdapter is configured with correct parameters."""
        client = OllamaClient(enable_circuit_breaker=False)

        http_adapter = client.session.get_adapter("http://")

        # Verify adapter configuration
        # Note: HTTPAdapter stores these in poolmanager.connection_pool_kw
        self.assertIsInstance(http_adapter, HTTPAdapter)

        # Verify max_retries is 0 (we handle retries manually)
        # max_retries is a Retry object, check its total attribute
        self.assertEqual(http_adapter.max_retries.total, 0)

    def test_concurrent_requests_tracking(self):
        """Test that multiple concurrent requests are tracked correctly."""
        client = OllamaClient(enable_circuit_breaker=False)

        initial_count = client.get_connection_pool_metrics()["total_requests"]

        with patch.object(client.session, 'request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"embedding": [0.1]}
            mock_request.return_value = mock_response

            # Simulate multiple requests
            num_requests = 5
            for _ in range(num_requests):
                try:
                    client._request("POST", "/api/embeddings", json_body={"prompt": "test"})
                except Exception:
                    pass

            # Verify counter incremented by number of requests
            final_metrics = client.get_connection_pool_metrics()
            expected_count = initial_count + num_requests
            self.assertEqual(final_metrics["total_requests"], expected_count)

    def test_pool_with_circuit_breaker(self):
        """Test that connection pool works with circuit breaker enabled."""
        client = OllamaClient(enable_circuit_breaker=True)

        # Verify both systems are initialized
        self.assertIsNotNone(client._circuit_breaker)
        self.assertIsNotNone(client.session)

        # Verify metrics are available for both
        cb_metrics = client.get_circuit_metrics()
        pool_metrics = client.get_connection_pool_metrics()

        self.assertIn("state", cb_metrics)
        self.assertIn("total_requests", pool_metrics)


if __name__ == "__main__":
    unittest.main()
