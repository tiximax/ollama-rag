import sys

from dulwich import porcelain

msg_lines = [
    "feat(logs): experiment JSONL logging + export + UI + e2e",
    "",
    "api: add /api/logs/info, /api/logs/enable, /api/logs/export, DELETE /api/logs",
    "engine: log /api/query, /api/stream_query (early+final), multihop routes",
    "ui: add Log experiments toggle + Export Logs button",
    "tests: add tests/e2e/logs.spec.js (parse JSONL and assert)",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B9a using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
