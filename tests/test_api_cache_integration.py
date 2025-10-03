from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.semantic_cache import SemanticQueryCache


class FakeOllama:
    def __init__(self, mapping: dict[str, np.ndarray]):
        self.mapping = mapping

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            v = self.mapping.get(t)
            if v is None:
                v = np.array([0.0, 1.0])
            out.append(v.tolist())
        return out


class FakeEngine:
    def __init__(self, mapping: dict[str, np.ndarray]):
        self.db_name = "testdb"
        self.persist_root = "data"
        self.default_provider = "ollama"
        self._dbs = [self.db_name]
        self.ollama = FakeOllama(mapping)

    @property
    def persist_dir(self) -> str:
        return "data/testdb"

    def list_dbs(self) -> list[str]:
        return list(self._dbs)

    def use_db(self, name: str) -> None:  # no-op for tests
        self.db_name = name

    def answer(self, query: str, **kwargs: Any) -> dict[str, Any]:
        # minimal result shape required by routes
        return {
            "answer": f"A:{query}",
            "metadatas": [],
            "contexts": [],
        }


@pytest.fixture()
def client(monkeypatch):
    # deterministic vectors for base/similar
    base = np.array([1.0, 0.0])
    similar = np.array([0.92, 0.392])  # ~cos>=0.92
    mapping = {
        "What is ML?": base,
        "Explain ML": similar,
    }

    # replace heavy engine with fake
    fake = FakeEngine(mapping)
    monkeypatch.setattr(main, "engine", fake)
    # reset semantic cache for app
    main.app.state.semantic_cache = SemanticQueryCache(
        similarity_threshold=0.90, max_size=100, ttl=3600
    )
    return TestClient(main.app)


def test_cache_config_get(client):
    r = client.get("/api/cache/config")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    assert "similarity_threshold" in data
    assert "stats" in data


def test_cache_config_post_update(client):
    r = client.post(
        "/api/cache/config", json={"similarity_threshold": 0.85, "ttl": 120, "max_size": 10}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    cur = data["current"]
    assert cur["similarity_threshold"] == 0.85
    assert cur["ttl"] == 120
    assert cur["max_size"] == 10


def test_query_exact_hit_flow(client):
    q = {"query": "What is ML?", "k": 3}

    r1 = client.post("/api/query", json=q)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["cache_hit"] is False

    r2 = client.post("/api/query", json=q)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["cache_hit"] is True


def test_query_semantic_hit_flow(client):
    q1 = {"query": "What is ML?", "k": 3}
    q2 = {"query": "Explain ML", "k": 3}

    _ = client.post("/api/query", json=q1)
    r2 = client.post("/api/query", json=q2)
    assert r2.status_code == 200
    d2 = r2.json()
    # with threshold=0.90 and our vectors, expect semantic HIT
    assert d2["cache_hit"] is True


def test_cache_stats_endpoint(client):
    r = client.get("/api/cache-stats")
    assert r.status_code == 200
    data = r.json()
    # semantic_cache should not be null with our state
    assert data.get("semantic_cache") is not None


def test_cache_clear_by_db(client):
    # Seed an exact entry
    q = {"query": "What is ML?", "k": 3}
    r1 = client.post("/api/query", json=q)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["cache_hit"] is False

    # Clear by DB prefix (testdb)
    rc = client.post("/api/cache/clear", json={"db": "testdb"})
    assert rc.status_code == 200
    info = rc.json()
    assert "size" in info

    # Query again should be MISS (recache)
    r2 = client.post("/api/query", json=q)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["cache_hit"] is False
