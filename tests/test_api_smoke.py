#!/usr/bin/env python3
"""
API smoke tests using FastAPI TestClient and unittest.
Các bài test chỉ dùng các API an toàn, không gọi đến embeddings/LLM.
"""

import unittest
import uuid

try:
    from fastapi.testclient import TestClient  # requires httpx
except Exception:
    TestClient = None  # type: ignore
from app.main import app


@unittest.skipIf(
    TestClient is None, "httpx (and fastapi TestClient) chưa được cài — bỏ qua smoke tests"
)
class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_serves_index(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        # nội dung HTML
        self.assertIn("<!doctype html>".lower(), r.text.lower())

    def test_provider_endpoint(self):
        r = self.client.get("/api/provider")
        self.assertEqual(r.status_code, 200)
        self.assertIn("provider", r.json())

    def test_health_endpoint_exists(self):
        r = self.client.get("/api/health")
        # Dù backend có thể lỗi, endpoint vẫn phải trả JSON 200
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("provider", data)
        self.assertIn("overall_status", data)

    def test_dbs_crud(self):
        # Tạo DB
        name = f"test_{uuid.uuid4().hex[:8]}"
        r = self.client.post("/api/dbs/create", json={"name": name})
        self.assertEqual(r.status_code, 200, r.text)
        # List DBs
        r = self.client.get("/api/dbs")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn(name, data.get("dbs", []))
        # Use DB
        r = self.client.post("/api/dbs/use", json={"name": name})
        self.assertEqual(r.status_code, 200)
        # Delete DB
        r = self.client.delete(f"/api/dbs/{name}")
        self.assertEqual(r.status_code, 200)

    def test_chats_crud(self):
        # Tạo DB riêng để cô lập
        name = f"test_{uuid.uuid4().hex[:8]}"
        r = self.client.post("/api/dbs/create", json={"name": name})
        self.assertEqual(r.status_code, 200, r.text)
        # Use DB
        r = self.client.post("/api/dbs/use", json={"name": name})
        self.assertEqual(r.status_code, 200)
        # Create chat
        r = self.client.post("/api/chats", json={"db": name, "name": "UT Chat"})
        self.assertEqual(r.status_code, 200, r.text)
        cid = r.json().get("chat", {}).get("id")
        self.assertTrue(cid)
        # List chats
        r = self.client.get(f"/api/chats?db={name}")
        self.assertEqual(r.status_code, 200)
        # Rename chat
        r = self.client.patch(f"/api/chats/{cid}?db={name}", json={"name": "Renamed"})
        self.assertEqual(r.status_code, 200)
        # Get chat
        r = self.client.get(f"/api/chats/{cid}?db={name}")
        self.assertEqual(r.status_code, 200)
        # Delete chat
        r = self.client.delete(f"/api/chats/{cid}?db={name}")
        self.assertEqual(r.status_code, 200)
        # Cleanup DB
        self.client.delete(f"/api/dbs/{name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
