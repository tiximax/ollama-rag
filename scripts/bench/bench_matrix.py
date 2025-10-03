import argparse
import csv
import os
import time
from datetime import datetime
from typing import Any

import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


def wait_server(timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(BASE + "/")
            if r.status_code in (200, 404):
                return True
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Server not ready on " + BASE)


def ensure_ingest(db=None):
    payload = {"paths": ["data/docs"]}
    if db:
        payload["db"] = db
    r = requests.post(BASE + "/api/ingest", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def bench_query(method: str, streaming: bool) -> dict[str, Any]:
    q = "Bitsness là gì?"
    body = {
        "query": q,
        "k": 3,
        "method": method,
        "bm25_weight": 0.5,
        "rerank_enable": False,
    }
    if streaming:
        t0 = time.time()
        r = requests.post(BASE + "/api/stream_query", json=body, stream=True, timeout=180)
        t_conn = time.time() - t0
        r.raise_for_status()
        # read until CTX header, then until end
        hdr_tag = "[[CTXJSON]]"
        ctx_seen = False
        t_hdr = None
        ans_len = 0
        for chunk in r.iter_content(chunk_size=None):
            if not chunk:
                continue
            ans_len += len(chunk)
            if (not ctx_seen) and (hdr_tag.encode() in chunk):
                ctx_seen = True
                t_hdr = time.time() - t0
        t_end = time.time() - t0
        return {
            "method": method,
            "mode": "stream",
            "t_connect": t_conn,
            "t_ctx": t_hdr or t_conn,
            "t_ans": t_end,
            "ans_bytes": ans_len,
        }
    else:
        t0 = time.time()
        r = requests.post(BASE + "/api/query", json=body, timeout=180)
        dt = time.time() - t0
        r.raise_for_status()
        data = r.json()
        return {
            "method": method,
            "mode": "nonstream",
            "latency": dt,
            "ans_len": len((data or {}).get("answer", "")),
        }


def run_matrix(rounds: int = 3):
    wait_server()
    ensure_ingest()
    items = []
    for method in ("bm25", "hybrid"):
        for streaming in (False, True):
            for _ in range(rounds):
                try:
                    row = bench_query(method, streaming)
                    row["ok"] = 1
                except Exception as e:
                    row = {
                        "method": method,
                        "mode": ("stream" if streaming else "nonstream"),
                        "ok": 0,
                        "error": str(e),
                    }
                items.append(row)
    return items


def save_csv(rows):
    os.makedirs("bench-results", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    path = os.path.join("bench-results", f"bench-matrix-{ts}.csv")
    if not rows:
        return None
    # union of keys
    keys = set()
    for r in rows:
        keys.update(r.keys())
    keys = list(sorted(keys))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    args = ap.parse_args()
    rows = run_matrix(rounds=args.rounds)
    out = save_csv(rows)
    if out:
        print(out)


if __name__ == "__main__":
    main()
