"""Danh gia hit-rate (Recall@k, MRR) cho tung che do search.

Nhan ca 2 dinh dang:
  - benchmark.jsonl: {"question","expected_chunk_id",...} (moi dong 1 json)
  - eval cu .json:  [{"q","expected"}, ...]

Usage (WSL):
  python3 -m legal_search.eval --questions data/benchmark/benchmark.jsonl --k 10 --workers 6
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from .config import Config
from .search import search
from .typesense_api import Typesense

# mode hien thi -> (search_mode, rerank_flag)
MODES = {
    "keyword": ("keyword", False),
    "vector": ("vector", False),
    "hybrid": ("hybrid", False),
    "rerank": ("hybrid", True),
}


def load_items(path):
    items = []
    if path.endswith(".jsonl"):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                items.append(json.loads(line))
    else:
        items = json.load(open(path, encoding="utf-8"))
    norm = []
    for it in items:
        q = it.get("question") or it.get("q")
        exp = it.get("expected_chunk_id") or it.get("expected")
        if q and exp:
            norm.append({"q": q, "expected": exp})
    return norm


def rank_of(results, expected):
    for i, h in enumerate(results, 1):
        if h["document"]["chunk_id"] == expected:
            return i
    return 0


def evaluate(cfg, ts, items, mode_name, k, alpha, workers):
    smode, rerank = MODES[mode_name]

    def one(it):
        try:
            res = search(cfg, ts, it["q"], mode=smode, k=k, alpha=alpha, rerank=rerank)
            return rank_of(res, it["expected"])
        except Exception:
            return 0

    with ThreadPoolExecutor(max_workers=workers) as ex:
        ranks = list(ex.map(one, items))

    n = len(ranks)
    return {
        "mode": mode_name,
        "R@1": sum(1 for r in ranks if r == 1) / n,
        "R@5": sum(1 for r in ranks if 1 <= r <= 5) / n,
        "R@10": sum(1 for r in ranks if 1 <= r <= 10) / n,
        "MRR": sum((1.0 / r) for r in ranks if r > 0) / n,
        "miss": sum(1 for r in ranks if r == 0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--alpha", type=float, default=0.7)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--modes", default="keyword,vector,hybrid,rerank")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = Config()
    ts = Typesense(cfg.ts_base, cfg.ts_api_key)
    items = load_items(args.questions)
    print(f"Benchmark: {len(items)} cau | k={args.k} | alpha={args.alpha} | workers={args.workers}\n")

    print(f"{'Mode':<10} {'R@1':>7} {'R@5':>7} {'R@10':>7} {'MRR':>7} {'miss':>6}")
    print("-" * 50)
    for mode in args.modes.split(","):
        mode = mode.strip()
        if mode not in MODES:
            continue
        r = evaluate(cfg, ts, items, mode, args.k, args.alpha, args.workers)
        print(f"{r['mode']:<10} {r['R@1']:>7.3f} {r['R@5']:>7.3f} {r['R@10']:>7.3f} {r['MRR']:>7.3f} {r['miss']:>6}")


if __name__ == "__main__":
    main()
