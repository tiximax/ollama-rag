import sys

from dulwich import porcelain

msg_lines = [
    "feat(feedback): API + UI + e2e test",
    "",
    "api: add /api/feedback (POST/GET/DELETE) per-DB JSONL storage",
    "ui: add feedback bar (👍/👎, comment, send) with query/answer/context capture",
    "tests: add tests/e2e/feedback.spec.js",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B8 using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
