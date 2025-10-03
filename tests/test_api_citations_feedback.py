#!/usr/bin/env python3
"""
API tests for citations and feedback endpoints.
- /api/citations/chat/{chat_id}
- /api/citations/db
- /api/feedback (POST/GET/DELETE)

Các bài test này không yêu cầu LLM/embeddings, chỉ thao tác CRUD và export.
"""

import io
import unittest
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app


class ApiCitationsFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _create_db_and_chat(self, prefix: str = "test_cf"):
        import uuid

        dbname = f"{prefix}_{uuid.uuid4().hex[:8]}"
        # Create DB
        r = self.client.post("/api/dbs/create", json={"name": dbname})
        self.assertIn(r.status_code, (200, 409), r.text)
        # Create chat in that DB
        r = self.client.post("/api/chats", json={"db": dbname, "name": "UT Chat CF"})
        self.assertEqual(r.status_code, 200, r.text)
        chat_id = r.json().get("chat", {}).get("id")
        self.assertTrue(chat_id)
        return dbname, chat_id

    def test_citations_chat_empty_list(self):
        dbname, chat_id = self._create_db_and_chat(prefix="cit_chat")
        # No messages yet -> citations should be an empty list
        r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIsInstance(data, list)
        # Cleanup DB
        self.client.delete(f"/api/dbs/{dbname}")

    def test_citations_db_zip_contains_json(self):
        dbname, _ = self._create_db_and_chat(prefix="cit_db")
        r = self.client.get(f"/api/citations/db?db={dbname}&format=json")
        self.assertEqual(r.status_code, 200, r.text)
        ctype = r.headers.get("content-type", "")
        self.assertIn("application/zip", ctype)
        # Validate it is a valid zip and has at least one file
        buf = io.BytesIO(r.content)
        with ZipFile(buf, mode="r") as zf:
            namelist = zf.namelist()
            self.assertTrue(len(namelist) >= 1, f"Expected >=1 file in zip, got {namelist}")
            # Prefer JSON entries
            has_json = any(name.endswith("-citations.json") for name in namelist)
            self.assertTrue(has_json, f"Zip entries: {namelist}")
        # Cleanup DB
        self.client.delete(f"/api/dbs/{dbname}")

    def test_feedback_flow_add_list_clear(self):
        import uuid

        dbname = f"fb_{uuid.uuid4().hex[:8]}"
        # Create DB
        r = self.client.post("/api/dbs/create", json={"name": dbname})
        self.assertIn(r.status_code, (200, 409), r.text)
        # Ensure empty first
        self.client.delete(f"/api/feedback?db={dbname}")
        # Add feedback
        item = {
            "db": dbname,
            "score": 1,
            "query": "Hello?",
            "answer": "Hi!",
            "provider": "ollama",
            "method": "bm25",
            "k": 3,
            "languages": ["vi"],
            "versions": ["v1"],
            "sources": ["a.txt"],
        }
        r = self.client.post("/api/feedback", json=item)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json().get("status"), "ok")
        # List feedback
        r = self.client.get(f"/api/feedback?db={dbname}")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertEqual(data.get("db"), dbname)
        items = data.get("items") or []
        self.assertTrue(len(items) >= 1)
        # Clear feedback
        r = self.client.delete(f"/api/feedback?db={dbname}")
        self.assertEqual(r.status_code, 200, r.text)
        deleted = int(r.json().get("deleted") or 0)
        self.assertTrue(deleted >= 1)
        # Verify empty
        r = self.client.get(f"/api/feedback?db={dbname}")
        self.assertEqual(r.status_code, 200)
        items2 = r.json().get("items") or []
        self.assertEqual(items2, [])
        # Cleanup DB
        self.client.delete(f"/api/dbs/{dbname}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
