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
from app.main import app, chat_store


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

    def test_citations_chat_with_real_reference_and_filters(self):
        dbname, chat_id = self._create_db_and_chat(prefix="cit_real")
        try:
            user_q = "What is it?"
            ans = "Here's the info [1]. Duplicate [1] to test dedup."
            metas = [{
                "source": "docs/a.txt",
                "version": "v1",
                "language": "vi",
                "chunk": 5,
            }]
            ctxs = ["Excerpt A"]
            # Append a real QA pair with meta citations
            chat_store.append_pair(dbname, chat_id, user_q, ans, {"metas": metas, "contexts": ctxs})

            # JSON should contain exactly one deduplicated citation
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json")
            self.assertEqual(r.status_code, 200, r.text)
            data = r.json()
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            c = data[0]
            self.assertEqual(c.get("n"), 1)
            self.assertEqual(c.get("source"), "docs/a.txt")
            self.assertEqual(c.get("version"), "v1")
            self.assertEqual(c.get("language"), "vi")
            self.assertEqual(c.get("chunk"), 5)
            self.assertEqual(c.get("question"), user_q)
            self.assertEqual(c.get("excerpt"), "Excerpt A")
            self.assertTrue("ts" in c)

            # CSV: header + exactly one data row
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=csv")
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn("text/csv", r.headers.get("content-type", ""))
            reader = csv.DictReader(io.StringIO(r.text))
            self.assertEqual(reader.fieldnames, ['n','source','version','language','chunk','question','excerpt','ts'])
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['n'], '1')
            self.assertEqual(row['source'], 'docs/a.txt')
            self.assertEqual(row['version'], 'v1')
            self.assertEqual(row['language'], 'vi')
            self.assertEqual(row['chunk'], '5')
            self.assertEqual(row['question'], user_q)
            self.assertEqual(row['excerpt'], 'Excerpt A')
            self.assertTrue(row['ts'])

            # MD: contains one bullet line for [1]
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=md")
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn("text/markdown", r.headers.get("content-type", ""))
            md = r.text
            self.assertIn("# Citations", md)
            self.assertIn("- [1] docs/a.txt v=v1 lang=vi chunk=5", md)

            # Filters (sources substring)
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json&sources=a.txt")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.json()), 1)
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json&sources=other.txt")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.json()), 0)

            # Filters (versions exact)
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json&versions=v1")
            self.assertEqual(len(r.json()), 1)
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json&versions=v2")
            self.assertEqual(len(r.json()), 0)

            # Filters (languages exact)
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json&languages=vi")
            self.assertEqual(len(r.json()), 1)
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json&languages=en")
            self.assertEqual(len(r.json()), 0)
        finally:
            self.client.delete(f"/api/dbs/{dbname}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
