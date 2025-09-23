from dulwich import porcelain
import sys

msg_lines = [
    "test: stabilize upload_ingest e2e (JS syntax, locator, wait /api/upload)",
    "",
    "- remove TS 'as any'",
    "- use array for setInputFiles; assert input files > 0",
    "- target #btn-upload to avoid strict-mode ambiguity",
    "- wait POST /api/upload and assert payload",
    "",
    "docs: update agent.md with B15 Upload & Ingest progress",
]
message = "\n".join(msg_lines).encode("utf-8")

repo_path = "."

author = b"User <user@example.com>"
committer = author

try:
    porcelain.add(repo_path)
    porcelain.commit(repo_path, message=message, author=author, committer=committer)
    print("Committed B15 (upload/ingest test + docs) using dulwich.")
except Exception as e:
    print("Commit failed:", e)
    sys.exit(1)