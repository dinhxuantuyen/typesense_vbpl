"""TASK-012 (buoc 1, OFFLINE - khong dung proxy): chon mau stratified 1000 Dieu -> seed.jsonl

Usage (WSL):
  python3 -m legal_search.sample_benchmark --input ~/tvpl.jsonl --n 1000 --out data/benchmark/seed.jsonl
"""
import argparse
import json
import os
import random
import re
from collections import Counter

from .chunking import is_low_value

BOILERPLATE = re.compile(
    r"(điều khoản thi hành|hiệu lực thi hành|tổ chức thực hiện|trách nhiệm thi hành|"
    r"quy định chuyển tiếp|điều khoản chuyển tiếp|hiệu lực và trách nhiệm)", re.I)


def eligible(rec):
    """Dieu du dieu kien lam mau benchmark (co noi dung thuc chat, khong boilerplate)."""
    c = rec.get("content") or ""
    h = rec.get("article_heading") or ""
    if not h or is_low_value(c, h):
        return False
    if not (200 <= len(c) <= 4000):
        return False
    if BOILERPLATE.search(h):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.expanduser("~/tvpl.jsonl"))
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--out", default="data/benchmark/seed.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    rng = random.Random(args.seed)

    # Pass 1: thu thap eligible id theo loai VB
    print("[1/3] Quet eligible...", flush=True)
    by_type = {}
    total = 0
    for line in open(args.input, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        total += 1
        if eligible(rec):
            dt = (rec.get("metadata") or {}).get("document_type") or "?"
            by_type.setdefault(dt, []).append(rec["chunk_id"])
    n_elig = sum(len(v) for v in by_type.values())
    print(f"      {n_elig} eligible / {total} record; {len(by_type)} loai VB", flush=True)

    # Stratified: quota theo ti le loai VB
    selected = {}
    for dt, ids in by_type.items():
        quota = max(1, round(args.n * len(ids) / n_elig))
        for cid in rng.sample(ids, min(quota, len(ids))):
            selected[cid] = dt
    sel_ids = list(selected.keys())
    rng.shuffle(sel_ids)
    sel_ids = sel_ids[: args.n]
    selected = set(sel_ids)
    print(f"[2/3] Chon {len(selected)} mau. Nap noi dung (pass 2)...", flush=True)

    # Pass 2: nap noi dung
    rows = {}
    for line in open(args.input, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec["chunk_id"] in selected:
            md = rec.get("metadata") or {}
            rows[rec["chunk_id"]] = {
                "chunk_id": rec["chunk_id"],
                "citation": rec.get("citation"),
                "document_type": md.get("document_type"),
                "article_heading": rec.get("article_heading"),
                "content": (rec.get("content") or "")[:2500],
            }
            if len(rows) == len(selected):
                break

    with open(args.out, "w", encoding="utf-8") as f:
        for cid in sel_ids:
            if cid in rows:
                f.write(json.dumps(rows[cid], ensure_ascii=False) + "\n")

    dist = Counter(r["document_type"] for r in rows.values())
    print(f"[3/3] Da ghi {len(rows)} seed -> {args.out}")
    print("      Phan bo loai VB:", dict(dist.most_common()))


if __name__ == "__main__":
    main()
