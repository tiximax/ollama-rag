#!/usr/bin/env python3
"""
API tests for logs and analytics endpoints.
- Toggle logs enable/disable and fetch info/export/summary
- Analytics DB basic response
"""

import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiLogsAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_logs_toggle_and_info_export_summary(self):
        # Enable logs
        r = self.client.post("/api/logs/enable", json={"enabled": True, "db": None})
        self.assertEqual(r.status_code, 200, r.text)
        # Info
        r = self.client.get("/api/logs/info")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("enabled", data)
        # Export (may be empty)
        r = self.client.get("/api/logs/export")
        self.assertEqual(r.status_code, 200)
        # Summary
        r = self.client.get("/api/logs/summary")
        self.assertEqual(r.status_code, 200)
        self.assertIn("total", r.json())
        # Clear
        r = self.client.delete("/api/logs")
        self.assertEqual(r.status_code, 200)
        self.assertIn("deleted_files", r.json())

    def test_analytics_db_basic(self):
        r = self.client.get("/api/analytics/db")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for k in ("db", "chats", "qa_pairs", "answered", "with_contexts"):
            self.assertIn(k, data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
