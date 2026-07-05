"""Do thoi gian tung phase cua 1 luot search."""
import sys, time
sys.stdout.reconfigure(encoding="utf-8")

from legal_search.config import Config
from legal_search.typesense_api import Typesense
from legal_search.proxy import embed, rerank as proxy_rerank
from legal_search.search import _vector_query, QUERY_BY, QUERY_BY_WEIGHTS, _rerank_text, rollup
from legal_search.chunking import fold_ascii

cfg = Config()
ts = Typesense(cfg.ts_base, cfg.ts_api_key)

queries = [
    "Mức thuế hộ kinh doanh năm 2026",
    "thủ tục đăng ký khai sinh cho trẻ",
    "điều kiện thành lập doanh nghiệp",
]

print(f"{'Query':<40} {'embed':>8} {'typesense':>10} {'rerank':>8} {'TONG':>8}")
print("-" * 78)
for q in queries:
    # 1) embed query
    t = time.time(); qvec = embed(cfg, [q], is_query=True)[0]; t_embed = time.time() - t
    # 2) typesense hybrid
    s = {"collection": cfg.collection, "query_by": QUERY_BY, "query_by_weights": QUERY_BY_WEIGHTS,
         "per_page": 100, "exclude_fields": "embedding",
         "filter_by": "is_low_value:false && is_effective_now:true",
         "q": fold_ascii(q), "vector_query": _vector_query(qvec, 100, 0.7)}
    t = time.time(); res = ts.multi_search([s]); t_ts = time.time() - t
    hits = res["results"][0].get("hits", [])
    pool = rollup(hits, 30)
    # 3) rerank
    texts = [_rerank_text(h["document"]) for h in pool]
    t = time.time(); proxy_rerank(cfg, q, texts, top_n=5); t_rr = time.time() - t
    total = t_embed + t_ts + t_rr
    print(f"{q[:38]:<40} {t_embed:>7.2f}s {t_ts*1000:>8.0f}ms {t_rr:>7.2f}s {total:>7.2f}s")
