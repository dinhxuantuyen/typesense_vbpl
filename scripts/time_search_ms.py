import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from legal_search.config import Config
from legal_search.typesense_api import Typesense
from legal_search.proxy import embed, rerank as proxy_rerank
from legal_search.search import (QUERY_BY, QUERY_BY_WEIGHTS, _vector_query, _rerank_text,
                                 rollup, merge_full_article)
from legal_search.chunking import fold_ascii

cfg = Config()
ts = Typesense(cfg.ts_base, cfg.ts_api_key)
queries = [
    "Mức đóng thuế hộ kinh doanh năm 2026",
    "thủ tục đăng ký khai sinh cho trẻ",
    "điều kiện thành lập doanh nghiệp",
]
K, CAND, POOL, ALPHA = 10, 100, 30, 0.7

print(f"{'Query':<38}{'embed':>9}{'typesense':>11}{'rerank':>9}{'merge':>8}{'TỔNG':>9}")
print("-" * 84)
for q in queries:
    t = time.time(); qvec = embed(cfg, [q], is_query=True)[0]; t_emb = time.time() - t

    s = {"collection": cfg.collection, "query_by": QUERY_BY, "query_by_weights": QUERY_BY_WEIGHTS,
         "per_page": CAND, "exclude_fields": "embedding,body_ascii,heading_ascii,related_json",
         "filter_by": "is_low_value:false && is_effective_now:true",
         "q": fold_ascii(q), "vector_query": _vector_query(qvec, CAND, ALPHA)}
    t = time.time(); hits = ts.multi_search([s])["results"][0].get("hits", []); t_ts = time.time() - t

    pool = rollup(hits, POOL)
    texts = [_rerank_text(h["document"]) for h in pool]
    t = time.time(); pairs = proxy_rerank(cfg, q, texts, top_n=K); t_rr = time.time() - t
    results = [pool[i] for i, _ in (pairs or [])[:K]]

    t = time.time()
    for h in results:
        d = h["document"]
        if d.get("n_parts", 1) > 1:
            merge_full_article(ts, cfg.collection, d["parent_id"])
    t_mg = time.time() - t

    tot = t_emb + t_ts + t_rr + t_mg
    print(f"{q[:36]:<38}{t_emb:>8.2f}s{t_ts*1000:>9.0f}ms{t_rr:>8.2f}s{t_mg*1000:>6.0f}ms{tot:>8.2f}s")
