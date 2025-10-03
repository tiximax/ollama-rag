import sys

from dulwich import porcelain

msg_lines = [
    "feat(analytics): add DB/chat analytics endpoints + e2e",
    "",
    "api: /api/analytics/db and /api/analytics/chat/{chat_id}",
    "logic: aggregate qa_pairs, answered, with_contexts, answer length stats, top sources/versions/languages",
    "tests: add tests/e2e/analytics.spec.js",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B10a using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
