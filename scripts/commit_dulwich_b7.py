from dulwich import porcelain
import sys

msg_lines = [
    "feat(eval): offline evaluation endpoint + UI + e2e test",
    "",
    "api: add /api/eval/offline supporting expected_sources/expected_substrings; recall@k",
    "ui: add Offline Evaluation panel (textarea + Run Eval); show Recall@k (hits/N)",
    "tests: add tests/e2e/eval_offline.spec.js using BM25 and versions filters",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B7 using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
