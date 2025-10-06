"""
Pytest configuration and fixtures for Sprint 1 tests.

This file provides auto-mocking for Ollama service in CI environments
to allow tests to run without requiring actual Ollama installation.
"""

import os
from unittest.mock import patch

import numpy as np
import pytest

# Determine if we're in CI
IS_CI = os.getenv("CI", "false").lower() == "true"
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"


@pytest.fixture(autouse=True)
def mock_ollama_in_ci(monkeypatch):
    """
    Automatically mock Ollama client methods in CI environment.

    This fixture runs for ALL tests automatically (autouse=True)
    and mocks Ollama connections only when running in CI.

    Local tests will still use real Ollama connection.
    """
    if not (IS_CI or IS_GITHUB_ACTIONS):
        # Skip mocking in local environment
        yield
        return

    # We're in CI - apply mocks
    print("🤖 CI detected - Mocking Ollama service")

    # Mock embed method
    def mock_embed(self, text: str, model: str = None) -> list:
        """Mock embedding generation with deterministic results"""
        # Use hash of text as seed for reproducible embeddings
        np.random.seed(hash(text) % (2**32))
        embedding = np.random.rand(768).tolist()
        return embedding

    # Mock generate method
    def mock_generate(self, prompt: str, model: str = None, **kwargs) -> str:
        """Mock text generation"""
        return f"Generated response for prompt: {prompt[:50]}..."

    # Mock health check
    def mock_is_healthy(self) -> bool:
        """Mock health check - always healthy in CI"""
        return True

    # Apply mocks to OllamaClient
    try:
        from app.ollama_client import OllamaClient

        monkeypatch.setattr(OllamaClient, "embed", mock_embed)
        monkeypatch.setattr(OllamaClient, "generate", mock_generate)
        monkeypatch.setattr(OllamaClient, "is_healthy", mock_is_healthy)
        print("✅ OllamaClient mocked successfully")
    except ImportError as e:
        print(f"⚠️ Could not mock OllamaClient: {e}")

    yield

    print("🧹 Cleaning up Ollama mocks")


@pytest.fixture
def mock_ollama_failure():
    """
    Fixture to simulate Ollama failures for Circuit Breaker tests.

    Usage:
        def test_circuit_breaker(mock_ollama_failure):
            # Ollama will fail in this test
            ...
    """
    with patch('app.ollama_client.OllamaClient.embed') as mock_embed:
        mock_embed.side_effect = ConnectionError("Connection refused")
        yield mock_embed


@pytest.fixture
def sample_embedding():
    """Provide a sample embedding vector for testing"""
    np.random.seed(42)
    return np.random.rand(768).tolist()


@pytest.fixture
def sample_documents():
    """Provide sample documents for testing"""
    return [
        {"id": "1", "content": "Sample document 1", "source": "test"},
        {"id": "2", "content": "Sample document 2", "source": "test"},
        {"id": "3", "content": "Sample document 3", "source": "test"},
    ]
