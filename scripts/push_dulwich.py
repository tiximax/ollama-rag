import os, sys
from dulwich import porcelain
import configparser
from urllib.parse import urlparse, urlunparse, quote

REPO = "."


def current_branch(repo_root: str = ".") -> str:
    head_path = os.path.join(repo_root, ".git", "HEAD")
    try:
        with open(head_path, "r", encoding="utf-8") as f:
            head = f.read().strip()
        if head.startswith("ref: "):
            ref = head.split(" ", 1)[1].strip()
            if ref.startswith("refs/heads/"):
                return ref.split("/")[-1]
    except Exception:
        pass
    return "master"


def origin_url(repo_root: str = ".") -> str | None:
    cfg_path = os.path.join(repo_root, ".git", "config")
    cp = configparser.ConfigParser()
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cp.read_file(f)
        return cp.get('remote "origin"', 'url', fallback=None)
    except Exception:
        return None


def with_credentials(url: str) -> str:
    # Lấy user/token từ ENV (không in ra, không log)
    user = os.environ.get("GIT_USER") or os.environ.get("GITHUB_USER") or os.environ.get("GH_USER")
    token = os.environ.get("GIT_PAT") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not url or not url.startswith("http"):
        return url
    p = urlparse(url)
    # Chuẩn hóa path có .git để hợp thức cho git smart HTTP
    path = p.path or ""
    if not path.endswith(".git"):
        path = path + ".git"
    # Nếu có token mà thiếu user → dùng user mặc định 'x-access-token' (GitHub)
    if (token and not user):
        user = "x-access-token"
    if user or token:
        ue = quote(user or "", safe="")
        te = quote(token or "", safe="")
        auth = ue if not te else f"{ue}:{te}"
        netloc = f"{auth}@{p.netloc}"
    else:
        netloc = p.netloc
    return urlunparse((p.scheme, netloc, path, p.params, p.query, p.fragment))


def main():
    br = current_branch(REPO)
    url = origin_url(REPO)
    if not url:
        print("No remote 'origin' configured. Please set a remote before pushing.")
        sys.exit(2)
    url_cred = with_credentials(url)
    refspec = f"refs/heads/{br}:refs/heads/{br}".encode("utf-8")
    try:
        # Nếu có user/token → push tới URL có credential; nếu không → dùng alias 'origin'
        remote_loc = url_cred if ("@" in url_cred.split("//",1)[-1]) else "origin"
        print(f"Pushing branch '{br}' to origin ({'with-credentials' if remote_loc!= 'origin' else 'no-credentials'})...")
        porcelain.push(REPO, remote_location=remote_loc, refspecs=[refspec])
        print("Push completed.")
    except Exception as e:
        print("Push failed:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()