#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for RagEngine list_sources() and delete_sources() using a fake in-memory
collection to avoid touching real Chroma/Ollama.
"""

import unittest
from app.rag_engine import RagEngine


class FakeCollection:
    def __init__(self, metadatas=None, ids_map=None, fail_where_sources=None):
        # metadatas: list of dicts with key 'source'
        self.metas = list(metadatas or [])
        # ids_map: source -> list of ids (strings)
        self.ids_map = dict(ids_map or {})
        # which sources should fail on delete(where={"source": ...}) to trigger fallback
        self.fail_where = set(fail_where_sources or [])

    def get(self, include=None, where=None):
        include = include or []
        where = where or {}
        # If asked for ids by where filter
        if where and "source" in where:
            src = where.get("source")
            if "ids" in include:
                return {"ids": self.ids_map.get(src, [])}
            # Default return for safety
            return {"metadatas": [m for m in self.metas if (m or {}).get("source") == src]}
        # Non-filtered get
        out = {}
        if not include or "metadatas" in include:
            out["metadatas"] = list(self.metas)
        if "ids" in include:
            # Flatten ids (not really used in list_sources path)
            all_ids = []
            for v in self.ids_map.values():
                all_ids.extend(v)
            out["ids"] = all_ids
        return out

    def delete(self, where=None, ids=None):
        if where:
            src = (where or {}).get("source")
            if src in self.fail_where:
                raise Exception("delete by where not supported for this source")
            # emulate removal by source
            self.metas = [m for m in self.metas if (m or {}).get("source") != src]
            self.ids_map[src] = []
            return
        if ids:
            # emulate removal by ids
            # (we won't map ids back to metas precisely in this fake)
            return


class RagEngineSourcesTests(unittest.TestCase):
    def setUp(self):
        # Create engine but replace its collection with our fake
        self.engine = RagEngine(persist_dir="data/chroma_test_unit")

    def test_list_sources_empty(self):
        self.engine.collection = FakeCollection(metadatas=[], ids_map={})
        items = self.engine.list_sources()
        self.assertEqual(items, [])

    def test_list_sources_counts_sorted(self):
        metas = [
            {"source": "b.txt"},
            {"source": "a.txt"},
            {"source": "a.txt"},
            {"source": "c.txt"},
            {"source": "b.txt"},
        ]
        self.engine.collection = FakeCollection(metadatas=metas, ids_map={})
        items = self.engine.list_sources()
        # Expect alphabetical order by source with counts
        self.assertEqual(items, [
            {"source": "a.txt", "chunks": 2},
            {"source": "b.txt", "chunks": 2},
            {"source": "c.txt", "chunks": 1},
        ])

    def test_delete_sources_with_where_and_fallback(self):
        # Prepare metas and ids mapping per source
        metas = [
            {"source": "s1.txt"},
            {"source": "s1.txt"},
            {"source": "s2.txt"},
        ]
        ids_map = {
            "s1.txt": ["id1", "id2"],
            "s2.txt": ["id3"],
        }
        # s1 fails delete(where=...), triggers fallback; s2 succeeds delete(where=...)
        fake = FakeCollection(metadatas=metas, ids_map=ids_map, fail_where_sources={"s1.txt"})
        self.engine.collection = fake
        # Put something into caches to verify they get cleared
        self.engine._bm25 = object()
        self.engine._filters_cache["languages"] = ["vi"]

        deleted_count = self.engine.delete_sources(["s1.txt", "s2.txt"])
        self.assertEqual(deleted_count, 2)
        # caches cleared
        self.assertIsNone(self.engine._bm25)
        self.assertEqual(self.engine._filters_cache, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
