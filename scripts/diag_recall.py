"""Chan doan: 13% miss top-100 do dau? (bo loc / khong ton tai / that su hang thap)"""
import json, sys
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding="utf-8")

from legal_search.config import Config
from legal_search.typesense_api import Typesense
from legal_search.proxy import embed
from legal_search.search import _vector_query, rollup
from legal_search.chunking import fold_ascii

cfg = Config(); ts = Typesense(cfg.ts_base, cfg.ts_api_key)
items = [json.loads(l) for l in open("data/benchmark/benchmark_100.jsonl", encoding="utf-8") if l.strip()]


def rank_in(question, expected, filter_by):
    qvec = embed(cfg, [question], is_query=True)[0]
    s = {"collection": cfg.collection, "q": "*", "query_by": "body_ascii",
         "vector_query": _vector_query(qvec, 250, 0.7), "per_page": 250,
         "exclude_fields": "embedding"}
    if filter_by:
        s["filter_by"] = filter_by
    hits = ts.multi_search([s])["results"][0].get("hits", [])
    pool = rollup(hits, 250)
    for i, h in enumerate(pool[:100], 1):
        if h["document"]["chunk_id"] == expected:
            return i
    return 0


def doc_flags(chunk_id):
    r = ts.search(cfg.collection, {"q": "*", "query_by": "body_ascii",
                 "filter_by": f"chunk_id:=`{chunk_id}`", "per_page": 1, "exclude_fields": "embedding"})
    h = r.get("hits", [])
    if not h:
        return None
    d = h[0]["document"]
    return {"exists": True, "is_effective_now": d.get("is_effective_now"),
            "is_low_value": d.get("is_low_value"), "validity": d.get("validity_status")}


def analyze(it):
    q, exp = it["question"], it["expected_chunk_id"]
    r_filt = rank_in(q, exp, "is_low_value:false && is_effective_now:true")
    if r_filt:
        return ("hit", None)
    # miss voi filter -> thu KHONG filter
    r_nofilt = rank_in(q, exp, None)
    fl = doc_flags(exp)
    if fl is None:
        return ("khong_ton_tai", exp)          # chunk_id khong co trong collection
    if r_nofilt and (not fl["is_effective_now"] or fl["is_low_value"]):
        return ("bi_loc", (exp, fl))            # co the tim thay nhung bi filter loai
    if r_nofilt:
        return ("hit_neu_bo_filter", (exp, r_nofilt, fl))
    return ("that_su_miss", (exp, fl))          # embedding that su khong dua len top-100


with ThreadPoolExecutor(max_workers=6) as ex:
    res = list(ex.map(analyze, items))

from collections import Counter
cat = Counter(r[0] for r in res)
print("=== PHAN LOAI 100 CAU ===")
for k, v in cat.most_common():
    print(f"  {k}: {v}")
print()
print("R@100 (co filter)      =", cat["hit"] / len(items))
recoverable = cat["hit"] + cat["bi_loc"] + cat["hit_neu_bo_filter"] + cat["khong_ton_tai"]
print("R@100 (bo filter)      =", (cat["hit"] + cat["bi_loc"] + cat["hit_neu_bo_filter"]) / len(items))
print()
print("=== CHI TIET MISS ===")
for tag, info in res:
    if tag in ("bi_loc", "that_su_miss", "khong_ton_tai", "hit_neu_bo_filter"):
        print(f"  [{tag}] {info}")
