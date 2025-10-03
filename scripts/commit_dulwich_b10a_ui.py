import sys

from dulwich import porcelain

msg_lines = [
    "feat(analytics): add dashboard UI (panel + refresh) + e2e",
    "",
    "ui: add Analytics panel with stats and top lists; refresh button",
    "tests: add tests/e2e/analytics_ui.spec.js",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B10a UI using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
