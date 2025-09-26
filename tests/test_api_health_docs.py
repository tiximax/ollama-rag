#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API tests for /api/health and /api/docs (list/delete) using FastAPI TestClient.
Uses a lightweight FakeCollection to avoid touching real Chroma state.
"""

import unittest
from typing import List, Dict, Any

from fastapi.testclient import TestClient
from app.main import app, engine


class FakeCollection:
    def __init__(self, metadatas: List[Dict[str, Any]] = None):
        self.metas = list(metadatas or [])
        # build ids map by source
        self.ids_by_source = {}
        for i, m in enumerate(self.metas):
            src = str((m or {}).get("source") or "")
            if not src:
                continue
            self.ids_by_source.setdefault(src, []).append(f"id{i}")

    def get(self, include=None, where=None):
        include = include or []
        where = where or {}
        if where and "source" in where:
            src = where.get("source")
            if "ids" in include:
                return {"ids": self.ids_by_source.get(src, [])}
            return {"metadatas": [m for m in self.metas if (m or {}).get("source") == src]}
        out = {}
        if not include or "metadatas" in include:
            out["metadatas"] = list(self.metas)
        if "ids" in include:
            ids = []
            for v in self.ids_by_source.values():
                ids.extend(v)
            out["ids"] = ids
        return out

    def delete(self, where=None, ids=None):
        if where and "source" in (where or {}):
            src = where.get("source")
            self.metas = [m for m in self.metas if (m or {}).get("source") != src]
            self.ids_by_source[src] = []
        elif ids:
            # not required for these tests
            pass


class ApiHealthDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint_returns_keys(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("provider", data)
        self.assertIn("overall_status", data)

    def test_docs_list_empty_with_fake_collection(self):
        orig = engine.collection
        try:
            engine.collection = FakeCollection(metadatas=[])
            r = self.client.get("/api/docs")
            self.assertEqual(r.status_code, 200, r.text)
            data = r.json()
            self.assertIn("docs", data)
            self.assertEqual(data.get("docs"), [])
        finally:
            engine.collection = orig

    def test_docs_delete_single_source(self):
        orig = engine.collection
        try:
            # Prepare two sources, delete one
            engine.collection = FakeCollection(metadatas=[{"source": "a.txt"}, {"source": "a.txt"}, {"source": "b.txt"}])
            r = self.client.request("DELETE", "/api/docs", json={"sources": ["a.txt"]})
            self.assertEqual(r.status_code, 200, r.text)
            data = r.json()
            self.assertEqual(data.get("deleted_sources"), 1)
            # Verify listing now only shows b.txt
            r2 = self.client.get("/api/docs")
            self.assertEqual(r2.status_code, 200)
            docs = r2.json().get("docs") or []
            self.assertEqual(docs, [{"source": "b.txt", "chunks": 1}])
        finally:
            engine.collection = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
