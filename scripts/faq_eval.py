import json, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from concurrent.futures import ThreadPoolExecutor
from legal_search.config import Config
from legal_search.typesense_api import Typesense
from legal_search.search import search

cfg = Config(); ts = Typesense(cfg.ts_base, cfg.ts_api_key)
bench = json.load(open("benchmark/benchmark_faq2_200.json", encoding="utf-8"))["data"]

CODE_RE = re.compile(r"\d+[a-zA-Z]?/\d{4}/[A-Za-zĐ][A-Za-zĐ0-9-]*|\d+/VBHN-[A-Za-zĐ]+|\d+[-/][A-ZĐ]{2,}(?:-[A-ZĐ]+)?")
DIEU_RE = re.compile(r"Điều\s+(\d+)")
K = 20

def codes_of(it):
    out = []
    for s in (it.get("can_cu_van_ban") or []):
        m = CODE_RE.findall(s)
        out.extend(m if m else [])
    return out

def dieu_of(it):
    nums = set()
    for s in (it.get("can_cu_dieu_khoan") or []):
        for m in DIEU_RE.findall(s):
            nums.add(int(m))
    return nums

# --- present set (ma VB co trong corpus) ---
uniq = set(c for it in bench for c in codes_of(it))
present = {}
for c in uniq:
    r = ts.search(cfg.collection, {"q": "*", "query_by": "document_code",
        "filter_by": f"document_code:=`{c}`", "per_page": 0})
    present[c] = r.get("found", 0) > 0

# --- subset 71 cau: co it nhat 1 can cu VB trong corpus ---
covered = []
for it in bench:
    cc = [c for c in codes_of(it) if present.get(c)]
    if cc:
        it = dict(it); it["_cc_codes"] = cc; it["_dieu"] = dieu_of(it)
        covered.append(it)
# luu subset
with open("benchmark/benchmark_faq2_covered.jsonl", "w", encoding="utf-8") as f:
    for it in covered:
        f.write(json.dumps({"id": it["id"], "cau_hoi": it["cau_hoi"],
            "can_cu_van_ban": it["can_cu_van_ban"], "can_cu_dieu_khoan": it["can_cu_dieu_khoan"],
            "_cc_codes": it["_cc_codes"], "_dieu": sorted(it["_dieu"])}, ensure_ascii=False) + "\n")
print(f"Subset đo được: {len(covered)} câu -> benchmark/benchmark_faq2_covered.jsonl\n")

# --- eval ---
def one(it):
    try:
        res = search(cfg, ts, it["cau_hoi"], mode="hybrid", k=K, rerank=True, rerank_pool=max(30, K))
    except Exception as e:
        return {"id": it["id"], "err": str(e)[:80]}
    retr = [(h["document"].get("document_code"), h["document"].get("article_num")) for h in res]
    cc = set(it["_cc_codes"])
    # doc-level: rank cua can cu dau tien
    doc_rank = 0
    for i, (rc, _) in enumerate(retr, 1):
        if rc in cc:
            doc_rank = i; break
    # article-level
    dieu = it["_dieu"]
    art_hit = bool(dieu) and any((rc in cc and ra in dieu) for rc, ra in retr)
    return {"id": it["id"], "doc_rank": doc_rank, "doc_hit": doc_rank > 0,
            "has_dieu": bool(dieu), "art_hit": art_hit,
            "top_codes": [rc for rc, _ in retr[:5]], "cc": list(cc)}

t0 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    rows = list(ex.map(one, covered))

n = len(rows)
doc_hit = sum(1 for r in rows if r.get("doc_hit"))
doc_mrr = sum((1.0 / r["doc_rank"]) for r in rows if r.get("doc_rank")) / n
with_dieu = [r for r in rows if r.get("has_dieu")]
art_hit = sum(1 for r in with_dieu if r.get("art_hit"))

print(f"=== KẾT QUẢ (top_k={K}, hybrid+rerank, {n} câu) — {time.time()-t0:.0f}s ===")
print(f"① VĂN BẢN  — Recall@20 = {doc_hit}/{n} = {doc_hit/n:.3f} | MRR = {doc_mrr:.3f}")
print(f"② ĐIỀU     — Recall@20 = {art_hit}/{len(with_dieu)} = {art_hit/max(1,len(with_dieu)):.3f}  ({len(with_dieu)} câu có tham chiếu Điều)")
print(f"\n=== MISS văn bản (không thấy căn cứ trong top-20) ===")
for r in rows:
    if not r.get("doc_hit") and not r.get("err"):
        print(f"  {r['id']} | cần {r['cc']} | top5 ra {r['top_codes']}")
