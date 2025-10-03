import sys

from dulwich import porcelain

msg_lines = [
    "feat(logs): add /api/logs/summary and dashboard UI + e2e",
    "",
    "api: /api/logs/summary computes total, median latency, contexts_rate, and top route/provider/method",
    "ui: add Logs Summary panel (since/until + refresh + lists)",
    "tests: add tests/e2e/logs_dashboard_ui.spec.js",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed logs dashboard using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
