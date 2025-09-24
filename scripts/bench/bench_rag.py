# Simple benchmark runner for Ollama RAG App
# - Measures client-side latency for /api/query across a dataset
# - Optionally enables server logs and fetches /api/logs/summary at the end
# - Writes CSV results to bench-results/bench-<timestamp>.csv

import argparse
import csv
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import requests


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 300) -> Dict[str, Any]:
    resp = requests.post(url, json=payload, timeout=timeout)
    try:
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}: {resp.text[:300]}") from e
    try:
        return resp.json()
    except Exception:
        return {}


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Accept either { queries: [...] } or a raw list
    if isinstance(data, dict) and isinstance(data.get("queries"), list):
        return data["queries"]
    if isinstance(data, list):
        return data
    raise ValueError("Dataset must be a list or an object with 'queries' list")


def ensure_logs(base_url: str, db: str, enabled: bool) -> None:
    try:
        _post_json(f"{base_url}/api/logs/enable", {"db": db, "enabled": bool(enabled)})
    except Exception:
        pass


def logs_summary(base_url: str, db: str) -> Dict[str, Any]:
    try:
        resp = requests.get(f"{base_url}/api/logs/summary", params={"db": db}, timeout=60)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return {}


def bench(args: argparse.Namespace) -> None:
    base = args.url.rstrip("/")
    db = args.db
    method = args.method
    k = args.k
    rerank_enable = args.rerank
    rerank_top_n = args.rerank_top_n
    bm25_weight = args.bm25_weight
    rounds = args.rounds

    # Load dataset
    items = load_dataset(args.dataset)
    if not items:
        raise SystemExit("Empty dataset")

    # Prepare output dir
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_csv = os.path.join(out_dir, f"bench-{ts}.csv")

    # Enable logs (optional)
    if args.enable_logs:
        ensure_logs(base, db, True)

    rows: List[List[Any]] = []
    header = [
        "round",
        "query",
        "status",
        "latency_ms_client",
        "contexts_count",
        "answer_len",
        "method",
        "k",
        "bm25_weight",
        "rerank_enable",
        "rerank_top_n",
    ]

    print(f"Running benchmark: {len(items)} queries x {rounds} rounds → {len(items)*rounds} requests")

    for r in range(1, rounds + 1):
        for it in items:
            q = str(it.get("query") or it.get("q") or "").strip()
            if not q:
                continue
            body = {
                "query": q,
                "method": method,
                "k": k,
                "bm25_weight": bm25_weight,
                "rerank_enable": rerank_enable,
                "rerank_top_n": rerank_top_n,
                "db": db,
                # Keep defaults low-cost by not enabling rewrite/multihop here
            }
            t0 = time.time()
            status = "ok"
            answer_len = 0
            ctx_count = 0
            try:
                data = _post_json(f"{base}/api/query", body, timeout=args.timeout)
                ans = str(data.get("answer") or "")
                metas = data.get("metadatas") or []
                answer_len = len(ans)
                ctx_count = len(metas)
            except Exception as e:
                status = f"err:{e.__class__.__name__}"
            t1 = time.time()
            rows.append([
                r,
                q,
                status,
                int((t1 - t0) * 1000),
                ctx_count,
                answer_len,
                method,
                k,
                bm25_weight,
                rerank_enable,
                rerank_top_n,
            ])

    # Write CSV
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    # Simple client-side summary
    latencies = [r[3] for r in rows if isinstance(r[3], int)]
    ok_rows = [r for r in rows if r[2] == "ok"]
    median = None
    if latencies:
        latencies_sorted = sorted(latencies)
        mid = len(latencies_sorted) // 2
        median = latencies_sorted[mid] if len(latencies_sorted) % 2 == 1 else int(
            (latencies_sorted[mid - 1] + latencies_sorted[mid]) / 2
        )

    print("\n=== Client-side summary ===")
    print(f"Requests: {len(rows)}, OK: {len(ok_rows)}")
    if latencies:
        print(f"Latency (ms): min={min(latencies)}, p50={median}, max={max(latencies)}")
    print(f"CSV written: {out_csv}")

    # Server-side logs summary (if enabled)
    if args.enable_logs:
        summ = logs_summary(base, db)
        if summ:
            print("\n=== Server logs summary ===")
            print(json.dumps(summ, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Benchmark /api/query latency & contexts")
    p.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of server")
    p.add_argument("--db", default="default", help="DB name")
    p.add_argument("--dataset", default="data/bench/queries.json", help="Dataset JSON path")
    p.add_argument("--method", default="hybrid", choices=["vector", "bm25", "hybrid"], help="Retrieval method")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--bm25-weight", type=float, default=0.5)
    p.add_argument("--rerank", action="store_true", help="Enable reranker")
    p.add_argument("--rerank-top-n", type=int, default=10)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--timeout", type=int, default=300, help="HTTP timeout seconds")
    p.add_argument("--enable-logs", action="store_true", help="Enable server logs and print logs summary")
    p.add_argument("--out-dir", default="bench-results", help="Output directory for CSV")
    args = p.parse_args()
    bench(args)
