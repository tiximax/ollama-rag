#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extra API tests:
- /api/analytics/chat/{id}: create a chat then fetch analytics
- /api/logs/export with since/until: ensure 200 OK
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app


class ApiExtraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_analytics_chat_empty_chat(self):
        # Create DB and chat
        name = "test_analytics_db"
        r = self.client.post("/api/dbs/create", json={"name": name})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.client.post("/api/chats", json={"db": name, "name": "Analytics Chat"})
        self.assertEqual(r.status_code, 200, r.text)
        cid = r.json().get("chat", {}).get("id")
        self.assertTrue(cid)
        # Fetch analytics for chat
        r = self.client.get(f"/api/analytics/chat/{cid}?db={name}")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        for k in ("db", "chat_id", "qa_pairs", "answered", "with_contexts"):
            self.assertIn(k, data)
        # Cleanup DB
        self.client.delete(f"/api/dbs/{name}")

    def test_logs_export_since_until(self):
        # Enable logs (no guarantee there are logs, but endpoint must respond 200)
        r = self.client.post("/api/logs/enable", json={"enabled": True})
        self.assertEqual(r.status_code, 200, r.text)
        # Export with since/until today pattern
        r = self.client.get("/api/logs/export?since=19700101&until=29991231")
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
