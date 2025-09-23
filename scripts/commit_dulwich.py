from dulwich import porcelain
from dulwich.repo import Repo
import sys

msg_lines = [
    "feat(filters): add versioning + language filtering; API/UI integration; e2e tests",
    "",
    "ingest: detect language via langid; persist version (UI input or hash fallback)",
    "retrieval: apply languages[]/versions[] filters across vector/BM25/hybrid/rewrite/multihop",
    "api: extend query/stream/multihop bodies; add /api/filters",
    "ui: add ingest version/paths; language/version multi-select",
    "tests: add filters.spec; add data/docs/en_traffic_sample.txt",
    "docs: update agent.md; add langid to requirements.txt",
]
message = "\n".join(msg_lines).encode("utf-8")

author = b"User <user@example.com>"
committer = author

repo_path = "."

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
