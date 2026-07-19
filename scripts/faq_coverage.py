import json, re, sys
sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter
from legal_search.config import Config
from legal_search.typesense_api import Typesense

cfg = Config(); ts = Typesense(cfg.ts_base, cfg.ts_api_key)
bench = json.load(open("benchmark/benchmark_faq2_200.json", encoding="utf-8"))["data"]

# trich ma so VB tu chuoi can_cu (vd "Thông tư 90/2026/TT-BTC" -> "90/2026/TT-BTC")
CODE_RE = re.compile(r"\d+[a-zA-Z]?/\d{4}/[A-Za-zĐ][A-Za-zĐ0-9-]*|\d+/VBHN-[A-Za-zĐ]+|\d+[-/][A-ZĐ]{2,}(?:-[A-ZĐ]+)?")

def codes_of(item):
    out = []
    for s in (item.get("can_cu_van_ban") or []):
        m = CODE_RE.findall(s)
        out.extend(m if m else [s.strip()])   # neu khong match -> giu nguyen (ten VB)
    return out

# tap ma so trong benchmark
all_codes = Counter()
for it in bench:
    for c in codes_of(it):
        all_codes[c] += 1
uniq = list(all_codes)
print(f"Benchmark: {len(bench)} câu | {len(uniq)} mã VB căn cứ distinct")

# kiem tra tung ma co trong collection khong
present = {}
for c in uniq:
    r = ts.search(cfg.collection, {"q": "*", "query_by": "document_code",
        "filter_by": f"document_code:=`{c}`", "per_page": 0})
    present[c] = r.get("found", 0) > 0

n_present = sum(present.values())
print(f"Mã VB CÓ trong corpus: {n_present}/{len(uniq)}")

# do phu theo CAU HOI
full = partial = none = 0
for it in bench:
    cs = codes_of(it)
    if not cs:
        continue
    have = [c for c in cs if present.get(c)]
    if len(have) == len(cs): full += 1
    elif have: partial += 1
    else: none += 1
print(f"\n=== ĐỘ PHỦ THEO CÂU HỎI ===")
print(f"  Đủ căn cứ trong corpus:     {full}")
print(f"  Thiếu 1 phần:               {partial}")
print(f"  KHÔNG có căn cứ nào:        {none}")
print(f"  -> Tối đa có thể đo được:   {full+partial}/{len(bench)}")

print("\n=== 15 mã VB căn cứ THIẾU (nhiều câu nhất) ===")
missing = Counter({c: all_codes[c] for c in uniq if not present[c]})
for c, n in missing.most_common(15):
    print(f"  {n} câu | {c}")
