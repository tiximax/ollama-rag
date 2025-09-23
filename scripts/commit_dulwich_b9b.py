from dulwich import porcelain
import sys

msg_lines = [
    "feat(rerank): add advanced params (provider/max_k/batch_size/num_threads) + UI + e2e",
    "",
    "engine: limit rerank candidates; batch scoring for BGE; ORT threads via rr_num_threads",
    "api: extend /api/query and streaming to accept rr_* params",
    "ui: add Reranker Advanced panel (provider/max_k/batch/threads)",
    "tests: add tests/e2e/rerank_opt.spec.js",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B9b using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
