import argparse
import csv
import os
import time
from datetime import datetime
from typing import List, Dict, Any

from bench_rag import load_dataset, _post_json  # reuse helper from bench_rag.py


def run_case(base: str, db: str, qlist: List[Dict[str, Any]], method: str, k: int, rerank: bool, rounds: int) -> Dict[str, Any]:
    latencies: List[int] = []
    ok = 0
    total = 0
    for _ in range(rounds):
        for it in qlist:
            q = str(it.get("query") or it.get("q") or "").strip()
            if not q:
                continue
            body = {
                "query": q,
                "method": method,
                "k": k,
                "rerank_enable": rerank,
                "db": db,
            }
            t0 = time.time()
            try:
                data = _post_json(f"{base}/api/query", body, timeout=300)
                ok += 1
            except Exception:
                pass
            t1 = time.time()
            latencies.append(int((t1 - t0) * 1000))
            total += 1
    latencies.sort()
    p50 = latencies[len(latencies)//2] if latencies else None
    return {
        "method": method,
        "k": k,
        "rerank": rerank,
        "total": total,
        "ok": ok,
        "p50_ms": p50,
        "min_ms": min(latencies) if latencies else None,
        "max_ms": max(latencies) if latencies else None,
    }


def main():
    p = argparse.ArgumentParser(description="Benchmark matrix for RAG")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--db", default="chroma")
    p.add_argument("--dataset", default="data/bench/queries.json")
    p.add_argument("--rounds", type=int, default=1)
    args = p.parse_args()

    qs = load_dataset(args.dataset)
    grid = [
        ("vector", 3, False),
        ("bm25", 3, False),
        ("hybrid", 3, False),
        ("hybrid", 5, False),
        ("hybrid", 3, True),
    ]
    rows: List[Dict[str, Any]] = []
    for method, k, rerank in grid:
        rows.append(run_case(args.url, args.db, qs, method, k, rerank, args.rounds))

    # Write summary CSV
    os.makedirs("bench-results", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_csv = os.path.join("bench-results", f"bench-matrix-{ts}.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("Matrix CSV:", out_csv)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
