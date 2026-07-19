"""Soi 12 ca miss: cau hoi la gi, dieu ky vong la gi, va he thong tra ve gi o top-3."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
from legal_search.config import Config
from legal_search.typesense_api import Typesense
from legal_search.proxy import embed
from legal_search.search import _vector_query, rollup

cfg = Config(); ts = Typesense(cfg.ts_base, cfg.ts_api_key)
MISS = ["15872-dieu-27","593571-dieu-71","660567-dieu-17","706373-dieu-16","593313-dieu-1",
        "39426-dieu-1","696357-dieu-270","18322-dieu-1","696081-dieu-20","52920-dieu-28",
        "699551-dieu-21","362598-dieu-2"]
items = {json.loads(l)["expected_chunk_id"]: json.loads(l)
         for l in open("data/benchmark/benchmark_100.jsonl", encoding="utf-8") if l.strip()}

def head(cid):
    r = ts.search(cfg.collection, {"q":"*","query_by":"body_ascii","filter_by":f"chunk_id:=`{cid}`",
                  "per_page":1,"exclude_fields":"embedding"})
    h=r.get("hits",[]); return h[0]["document"].get("article_heading") if h else "(?)"

for cid in MISS[:6]:
    it = items[cid]
    q = it["question"]
    qvec = embed(cfg,[q],is_query=True)[0]
    s={"collection":cfg.collection,"q":"*","query_by":"body_ascii",
       "vector_query":_vector_query(qvec,100,0.7),"per_page":100,"exclude_fields":"embedding"}
    pool = rollup(ts.multi_search([s])["results"][0].get("hits",[]),3)
    print("Q:", q[:90])
    print("  KY VONG:", cid, "|", (head(cid) or "")[:70])
    for i,h in enumerate(pool,1):
        d=h["document"]
        print(f"  TOP{i}: {d['citation']} | {(d.get('article_heading') or '')[:60]}")
    print()
