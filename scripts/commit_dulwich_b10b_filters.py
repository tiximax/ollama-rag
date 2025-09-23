from dulwich import porcelain
import sys

msg_lines = [
    "feat(citations): add filters (sources/versions/languages) to export + UI + e2e",
    "",
    "api: filter citations by CSV params (sources substring, versions, languages)",
    "ui: add filter inputs next to Export Citations buttons",
    "tests: add tests/e2e/citations_export_filter.spec.js",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed citations filters using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)
