from dulwich import porcelain
import sys

msg_lines = [
    "feat(citations): export citations per chat/DB (JSON/CSV/MD) + UI + e2e",
    "",
    "api: add /api/citations/chat/{chat_id} and /api/citations/db",
    "engine: save contexts in chat meta for stable excerpts",
    "ui: add Export Citations (Chat/DB) buttons",
    "tests: add tests/e2e/citations_export.spec.js",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B10b using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
