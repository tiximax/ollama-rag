#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests cho /api/citations/chat với các định dạng CSV/MD và negative case 404.
Các tests này KHÔNG cần sinh câu trả lời từ LLM; dùng chat rỗng để kiểm tra định dạng output hợp lệ.
"""

import io
import csv
import uuid
import unittest
from fastapi.testclient import TestClient
from app.main import app


class ApiCitationsChatFormatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _create_db_and_chat(self, prefix: str = "cit_fmt"):
        dbname = f"{prefix}_{uuid.uuid4().hex[:8]}"
        r = self.client.post("/api/dbs/create", json={"name": dbname})
        self.assertIn(r.status_code, (200, 409), r.text)
        r = self.client.post("/api/chats", json={"db": dbname, "name": "UT Chat FMT"})
        self.assertEqual(r.status_code, 200, r.text)
        chat_id = r.json().get("chat", {}).get("id")
        self.assertTrue(chat_id)
        return dbname, chat_id

    def test_citations_chat_csv_header_only_for_empty_chat(self):
        dbname, chat_id = self._create_db_and_chat(prefix="cit_csv")
        try:
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=csv")
            self.assertEqual(r.status_code, 200, r.text)
            ctype = r.headers.get("content-type", "")
            self.assertIn("text/csv", ctype)
            body = r.text
            # Parse bằng csv để đảm bảo hợp lệ
            reader = csv.DictReader(io.StringIO(body))
            # Kiểm tra header
            expected = ['n','source','version','language','chunk','question','excerpt','ts']
            self.assertEqual(reader.fieldnames, expected)
            # Chat rỗng => không có dòng dữ liệu
            rows = list(reader)
            self.assertEqual(rows, [])
        finally:
            self.client.delete(f"/api/dbs/{dbname}")

    def test_citations_chat_md_heading_only_for_empty_chat(self):
        dbname, chat_id = self._create_db_and_chat(prefix="cit_md")
        try:
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=md")
            self.assertEqual(r.status_code, 200, r.text)
            ctype = r.headers.get("content-type", "")
            self.assertIn("text/markdown", ctype)
            text = r.text
            # Phải có heading
            self.assertIn("# Citations", text)
            # Chat rỗng => không có mục bullet "- ["
            self.assertNotIn("- [", text)
        finally:
            self.client.delete(f"/api/dbs/{dbname}")

    def test_citations_chat_not_found_404(self):
        # Tạo DB nhưng dùng chat_id không tồn tại
        dbname = f"cit_nf_{uuid.uuid4().hex[:8]}"
        try:
            r = self.client.post("/api/dbs/create", json={"name": dbname})
            self.assertIn(r.status_code, (200, 409), r.text)
            missing_chat = uuid.uuid4().hex
            r = self.client.get(f"/api/citations/chat/{missing_chat}?db={dbname}&format=json")
            self.assertEqual(r.status_code, 404)
            data = r.json()
            self.assertEqual(data.get("detail"), "Chat not found")
        finally:
            self.client.delete(f"/api/dbs/{dbname}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
