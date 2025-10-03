#!/usr/bin/env python3
"""
Tests cho /api/citations/chat với các định dạng CSV/MD và negative case 404.
Các tests này KHÔNG cần sinh câu trả lời từ LLM; dùng chat rỗng để kiểm tra định dạng output hợp lệ.
"""

import csv
import io
import unittest
import uuid

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
            expected = ['n', 'source', 'version', 'language', 'chunk', 'question', 'excerpt', 'ts']
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

    def test_citations_chat_multiple_indices_dedup_and_invalid_ignored(self):
        dbname = f"cit_multi_{uuid.uuid4().hex[:8]}"
        try:
            # Create DB and chat with a fixed name for predictable zip entries later if reused
            r = self.client.post("/api/dbs/create", json={"name": dbname})
            self.assertIn(r.status_code, (200, 409), r.text)
            r = self.client.post("/api/chats", json={"db": dbname, "name": "MULTI"})
            self.assertEqual(r.status_code, 200, r.text)
            chat_id = r.json().get("chat", {}).get("id")
            self.assertTrue(chat_id)

            # Prepare metas/contexts for 3 citations
            metas = [
                {"source": "docs/a.txt", "version": "v1", "language": "vi", "chunk": 1},
                {"source": "docs/b.txt", "version": "v2", "language": "en", "chunk": 2},
                {"source": "docs/c.txt", "version": "v3", "language": "vi", "chunk": 3},
            ]
            ctxs = ["Ex A", "Ex B", "Ex C"]
            user_q = "Q?"
            # Answer with duplicates and invalid indices [0], [99]
            ans = "Part [1] next [2] dup[2] invalid[0] out[99] and finally [3]."
            chat_store.append_pair(dbname, chat_id, user_q, ans, {"metas": metas, "contexts": ctxs})

            # JSON: should dedup to [1],[2],[3] only in order of first occurrence
            r = self.client.get(f"/api/citations/chat/{chat_id}?db={dbname}&format=json")
            self.assertEqual(r.status_code, 200, r.text)
            data = r.json()
            self.assertEqual(len(data), 3, data)
            self.assertEqual([c.get("n") for c in data], [1, 2, 3])
            # Validate mapping
            self.assertEqual(data[0]["source"], "docs/a.txt")
            self.assertEqual(data[0]["excerpt"], "Ex A")
            self.assertEqual(data[1]["source"], "docs/b.txt")
            self.assertEqual(data[1]["excerpt"], "Ex B")
            self.assertEqual(data[2]["source"], "docs/c.txt")
            self.assertEqual(data[2]["excerpt"], "Ex C")
            # Filters: sources multi substring
            r = self.client.get(
                f"/api/citations/chat/{chat_id}?db={dbname}&format=json&sources=a.txt,b.txt"
            )
            self.assertEqual(len(r.json()), 2)
            # Filters: versions exact multi
            r = self.client.get(
                f"/api/citations/chat/{chat_id}?db={dbname}&format=json&versions=v2,v3"
            )
            self.assertEqual(len(r.json()), 2)
            # Filters: languages exact multi
            r = self.client.get(
                f"/api/citations/chat/{chat_id}?db={dbname}&format=json&languages=vi,en"
            )
            self.assertEqual(len(r.json()), 3)
        finally:
            self.client.delete(f"/api/dbs/{dbname}")

    def test_citations_db_csv_and_md_multiple_chats(self):
        dbname = f"citdbmulti_{uuid.uuid4().hex[:8]}"
        try:
            r = self.client.post("/api/dbs/create", json={"name": dbname})
            self.assertIn(r.status_code, (200, 409), r.text)
            # Chat 1
            r1 = self.client.post("/api/chats", json={"db": dbname, "name": "X1"})
            self.assertEqual(r1.status_code, 200, r1.text)
            c1 = r1.json().get("chat", {}).get("id")
            # Chat 2
            r2 = self.client.post("/api/chats", json={"db": dbname, "name": "X2"})
            self.assertEqual(r2.status_code, 200, r2.text)
            c2 = r2.json().get("chat", {}).get("id")

            # Append a single citation to each
            chat_store.append_pair(
                dbname,
                c1,
                "Q1",
                "Ans [1]",
                {
                    "metas": [
                        {"source": "docs/x1.txt", "version": "v1", "language": "vi", "chunk": 1}
                    ],
                    "contexts": ["CX1"],
                },
            )
            chat_store.append_pair(
                dbname,
                c2,
                "Q2",
                "Ans [1]",
                {
                    "metas": [
                        {"source": "docs/x2.txt", "version": "v2", "language": "en", "chunk": 2}
                    ],
                    "contexts": ["CX2"],
                },
            )

            # CSV zip
            r = self.client.get(f"/api/citations/db?db={dbname}&format=csv")
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn("application/zip", r.headers.get("content-type", ""))
            z = io.BytesIO(r.content)
            from zipfile import ZipFile

            with ZipFile(z, 'r') as zf:
                names = zf.namelist()
                self.assertTrue(any(n.endswith("X1-citations.csv") for n in names), names)
                self.assertTrue(any(n.endswith("X2-citations.csv") for n in names), names)
                # Inspect: ensure each CSV has exactly one row with expected source
                expected_hdr = [
                    'n',
                    'source',
                    'version',
                    'language',
                    'chunk',
                    'question',
                    'excerpt',
                    'ts',
                ]
                for nm in [n for n in names if n.endswith("-citations.csv")]:
                    with zf.open(nm) as f:
                        content = f.read().decode('utf-8')
                        rdr = csv.DictReader(io.StringIO(content))
                        self.assertEqual(rdr.fieldnames, expected_hdr)
                        rows = list(rdr)
                        self.assertEqual(len(rows), 1)
                with zf.open([n for n in names if n.endswith("X1-citations.csv")][0]) as f:
                    r1 = list(csv.DictReader(io.StringIO(f.read().decode('utf-8'))))
                    self.assertEqual(r1[0]['source'], 'docs/x1.txt')
                with zf.open([n for n in names if n.endswith("X2-citations.csv")][0]) as f:
                    r2 = list(csv.DictReader(io.StringIO(f.read().decode('utf-8'))))
                    self.assertEqual(r2[0]['source'], 'docs/x2.txt')

            # MD zip
            r = self.client.get(f"/api/citations/db?db={dbname}&format=md")
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn("application/zip", r.headers.get("content-type", ""))
            z = io.BytesIO(r.content)
            from zipfile import ZipFile

            with ZipFile(z, 'r') as zf:
                names = zf.namelist()
                self.assertTrue(any(n.endswith("X1-citations.md") for n in names), names)
                self.assertTrue(any(n.endswith("X2-citations.md") for n in names), names)
                # Inspect content: expect bullet lines exist for each chat
                with zf.open([n for n in names if n.endswith("X1-citations.md")][0]) as f:
                    md1 = f.read().decode('utf-8')
                    self.assertIn("# Citations", md1)
                    self.assertIn("- [1] docs/x1.txt v=v1 lang=vi chunk=1", md1)
                with zf.open([n for n in names if n.endswith("X2-citations.md")][0]) as f:
                    md2 = f.read().decode('utf-8')
                    self.assertIn("# Citations", md2)
                    self.assertIn("- [1] docs/x2.txt v=v2 lang=en chunk=2", md2)
        finally:
            self.client.delete(f"/api/dbs/{dbname}")


if __name__ == "__main__":
    unittest.main(verbosity=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
