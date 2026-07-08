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


def evaluate(cfg, ts, items, mode_name, k, alpha, workers, candidates, levels):
    smode, rerank = MODES[mode_name]

    def one(it):
        try:
            res = search(cfg, ts, it["q"], mode=smode, k=k, alpha=alpha,
                         candidates=candidates, rerank=rerank, rerank_pool=k)
            return rank_of(res, it["expected"])
        except Exception:
            return 0

    with ThreadPoolExecutor(max_workers=workers) as ex:
        ranks = list(ex.map(one, items))

    n = len(ranks)
    row = {"mode": mode_name}
    for L in levels:
        row[f"R@{L}"] = sum(1 for r in ranks if 1 <= r <= L) / n
    row["MRR"] = sum((1.0 / r) for r in ranks if r > 0) / n
    row["miss"] = sum(1 for r in ranks if r == 0)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--alpha", type=float, default=0.7)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--candidates", type=int, default=0, help="0=auto (max(100, k*3))")
    ap.add_argument("--modes", default="keyword,vector,hybrid,rerank")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = Config()
    ts = Typesense(cfg.ts_base, cfg.ts_api_key)
    items = load_items(args.questions)
    candidates = args.candidates or min(250, max(100, args.k * 3))  # Typesense per_page toi da 250
    levels = sorted({1, 5, 10, args.k})
    print(f"Benchmark: {len(items)} cau | k={args.k} | candidates={candidates} | alpha={args.alpha} | workers={args.workers}\n", flush=True)

    hdr = f"{'Mode':<10}" + "".join(f"{'R@'+str(L):>8}" for L in levels) + f"{'MRR':>8}{'miss':>6}"
    print(hdr); print("-" * len(hdr), flush=True)
    for mode in args.modes.split(","):
        mode = mode.strip()
        if mode not in MODES:
            continue
        r = evaluate(cfg, ts, items, mode, args.k, args.alpha, args.workers, candidates, levels)
        line = f"{r['mode']:<10}" + "".join(f"{r['R@'+str(L)]:>8.3f}" for L in levels)
        line += f"{r['MRR']:>8.3f}{r['miss']:>6}"
        print(line, flush=True)


if __name__ == "__main__":
    main()
