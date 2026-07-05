"""Tim kiem dieu luat lien quan tu cau hoi ngon ngu tu nhien (hybrid keyword + vector).

Usage (WSL):
  python3 -m legal_search.search "Xe may vuot den do bi phat bao nhieu?"
  python3 -m legal_search.search "..." --mode keyword|vector|hybrid --k 5 --alpha 0.5
  python3 -m legal_search.search "..." --all-status   # bo qua loc hieu luc
"""
import argparse
import sys

from .config import Config
from .proxy import embed, rerank as proxy_rerank
from .typesense_api import Typesense
from .chunking import fold_ascii

import re

QUERY_BY = "citation,heading_ascii,body_ascii"  # citation de khop truy van theo so hieu VB (vd "141/2026/ND-CP")
QUERY_BY_WEIGHTS = "5,3,1"
RERANK_INPUT_CHARS = 1500

# Truy van dang tra cuu so hieu VB (vd "141/2026/ND-CP", "Nghi dinh 68/2026") -> keyword-first,
# vi vector kem voi ma so, va rank-fusion RRF se dim hit keyword xuong duoi pool rerank.
DOC_CODE_RE = re.compile(r"\d{1,4}\s*/\s*\d{4}\s*/\s*[A-Za-z]", re.I)


def is_doc_code_query(question):
    return bool(DOC_CODE_RE.search(fold_ascii(question)))


def _vector_query(vec, k, alpha):
    body = ",".join(f"{x:.6f}" for x in vec)
    return f"embedding:([{body}], k:{k}, alpha:{alpha})"


def _rerank_text(doc):
    return f"{doc.get('article_heading','')}\n{(doc.get('content') or '')[:RERANK_INPUT_CHARS]}"


def search(cfg, ts, question, mode="hybrid", k=5, alpha=0.7, candidates=100,
           effective_only=True, exclude_low_value=True, rerank=False, rerank_pool=30):
    # Truy van theo so hieu VB -> keyword-first (chinh xac hon vector cho ma so).
    # Tat luon rerank: cross-encoder khong hieu "day chinh la VB duoc hoi",
    # trong khi text_match tren citation da la thu hang dung.
    if mode == "hybrid" and is_doc_code_query(question):
        mode = "keyword"
        rerank = False
    filters = []
    if exclude_low_value:
        filters.append("is_low_value:false")
    if effective_only:
        filters.append("is_effective_now:true")
    filter_by = " && ".join(filters)

    s = {
        "collection": cfg.collection,
        "query_by": QUERY_BY,
        "query_by_weights": QUERY_BY_WEIGHTS,
        "per_page": candidates,
        "exclude_fields": "embedding",     # khong tra vector ve cho nhe
    }
    if filter_by:
        s["filter_by"] = filter_by

    q_ascii = fold_ascii(question)     # keyword khong dau
    if mode == "keyword":
        s["q"] = q_ascii
    else:
        qvec = embed(cfg, [question], is_query=True)[0]
        if mode == "vector":
            s["q"] = "*"
            s["vector_query"] = _vector_query(qvec, candidates, alpha)
        else:  # hybrid
            s["q"] = q_ascii
            s["vector_query"] = _vector_query(qvec, candidates, alpha)

    res = ts.multi_search([s])
    hits = res["results"][0].get("hits", [])

    if rerank:
        pool = rollup(hits, rerank_pool)     # gom ve Dieu cha, lay pool rong hon
        if pool:
            texts = [_rerank_text(h["document"]) for h in pool]
            pairs = proxy_rerank(cfg, question, texts, top_n=k)
            if pairs:                        # pairs = [(index, score)] giam dan
                ranked = []
                for idx, sc in pairs[:k]:
                    h = pool[idx]
                    h["rerank_score"] = sc
                    ranked.append(h)
                return ranked
        return pool[:k]                      # fallback neu rerank loi
    return rollup(hits, k)


def rollup(hits, k):
    """Gom subchunk ve Dieu cha (theo chunk_id), giu hit diem cao nhat, tra top-k Dieu."""
    seen = {}
    order = []
    for h in hits:
        doc = h["document"]
        cid = doc["chunk_id"]
        if cid not in seen:
            seen[cid] = h
            order.append(cid)
        if len(order) >= k:
            break
    return [seen[c] for c in order[:k]]


def snippet(doc, width=220):
    c = (doc.get("content") or "").replace("\n", " ").strip()
    return c[:width] + ("..." if len(c) > width else "")


def format_results(results):
    lines = []
    for i, h in enumerate(results, 1):
        d = h["document"]
        tm = h.get("text_match", 0)
        vd = h.get("vector_distance")
        part = f" [subchunk {d['part_no']}/{d['n_parts']}]" if d.get("part_no") else ""
        rs = h.get("rerank_score")
        score = f"text_match={tm}" + (f" | vec_dist={vd:.4f}" if vd is not None else "")
        if rs is not None:
            score = f"rerank={rs:.4f} | " + score
        lines.append(f"#{i}  {d.get('citation') or d.get('chunk_id')}{part}")
        lines.append(f"    {d.get('article_heading','')}")
        lines.append(f"    VB: {d.get('document_type','')} {d.get('document_code','')} | {d.get('validity_status','')}")
        lines.append(f"    {snippet(d)}")
        lines.append(f"    ({score}) {d.get('source_url','')}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", choices=["hybrid", "keyword", "vector"], default="hybrid")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--alpha", type=float, default=0.7, help="Trong so vector trong rank fusion (0..1)")
    ap.add_argument("--all-status", action="store_true", help="Khong loc hieu luc")
    ap.add_argument("--with-repealed", action="store_true", help="Gom ca Dieu bi bai bo/low-value")
    ap.add_argument("--rerank", action="store_true", help="Bat tang rerank Qwen3-Reranker-4B")
    args = ap.parse_args()

    cfg = Config()
    ts = Typesense(cfg.ts_base, cfg.ts_api_key)
    results = search(
        cfg, ts, args.question, mode=args.mode, k=args.k, alpha=args.alpha,
        effective_only=not args.all_status, exclude_low_value=not args.with_repealed,
        rerank=args.rerank,
    )
    print(f"\n=== [{args.mode}] {args.question} ===\n")
    if not results:
        print("(khong co ket qua)")
    else:
        print(format_results(results))


if __name__ == "__main__":
    main()
