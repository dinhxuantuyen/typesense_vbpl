import json, sys
sys.stdout.reconfigure(encoding="utf-8")
from legal_search.config import Config
from legal_search.typesense_api import Typesense
from legal_search.search import search

cfg = Config()
ts = Typesense(cfg.ts_base, cfg.ts_api_key)
q = "Mức đóng thuế hộ kinh doanh năm 2026"
res = search(cfg, ts, q, mode="hybrid", k=10, rerank=True)

out = {"query": q, "collection": cfg.collection, "model": cfg.embed_model,
       "dim": cfg.embed_dim, "count": len(res), "results": []}
for h in res:
    d = h["document"]
    out["results"].append({
        "rerank_score": round(h.get("rerank_score"), 4) if h.get("rerank_score") is not None else None,
        "text_match": h.get("text_match"),
        "vector_distance": h.get("vector_distance"),
        "id": d.get("id"), "parent_id": d.get("parent_id"),
        "part_no": d.get("part_no"), "n_parts": d.get("n_parts"),
        "law_id": d.get("law_id"),
        "citation": d.get("citation"),
        "article_heading": d.get("article_heading"),
        "document_code": d.get("document_code"), "document_type": d.get("document_type"),
        "validity_status": d.get("validity_status"), "is_effective_now": d.get("is_effective_now"),
        "chapter": d.get("chapter"), "context_path": d.get("context_path"),
        "fields": d.get("fields"), "source_url": d.get("source_url"),
        "rel_guided_by_ids": d.get("rel_guided_by_ids"),
        "rel_guides_ids": d.get("rel_guides_ids"),
        "rel_consolidated_ids": d.get("rel_consolidated_ids"),
        "related": json.loads(d.get("related_json") or "[]"),
        "full_content": d.get("full_content"),
    })
print(json.dumps(out, ensure_ascii=False, indent=2))
