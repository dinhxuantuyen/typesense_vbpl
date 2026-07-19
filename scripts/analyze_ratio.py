import json, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
F = "data/mainstream/chunks.jsonl"

docs = defaultdict(set)      # type -> set(law_id)
arts = defaultdict(set)      # type -> set(parent_id)  (dieu)
chunks = defaultdict(int)    # type -> chunk count
art_per_doc = defaultdict(lambda: defaultdict(int))  # type -> law_id -> dieu count
seen_parent = set()

for line in open(F, encoding="utf-8"):
    r = json.loads(line)
    t = r.get("document_type") or "?"
    lid = r.get("law_id")
    pid = r.get("parent_id")
    docs[t].add(lid)
    chunks[t] += 1
    if pid not in seen_parent:
        seen_parent.add(pid)
        arts[t].add(pid)
        art_per_doc[t][lid] += 1

print(f"{'Loại VB':<22}{'#VB':>7}{'#Điều':>9}{'#Chunk':>9}{'Điều/VB':>9}{'Chunk/VB':>10}")
print("-" * 66)
tot_d = tot_a = tot_c = 0
rows = []
for t in docs:
    nd = len(docs[t]); na = len(arts[t]); nc = chunks[t]
    rows.append((na, t, nd, na, nc))
    tot_d += nd; tot_a += na; tot_c += nc
for na, t, nd, na2, nc in sorted(rows, reverse=True):
    print(f"{t:<22}{nd:>7}{na:>9}{nc:>9}{na/nd:>9.1f}{nc/nd:>10.1f}")
print("-" * 66)
print(f"{'TỔNG':<22}{tot_d:>7}{tot_a:>9}{tot_c:>9}{tot_a/tot_d:>9.1f}{tot_c/tot_d:>10.1f}")

# top 5 VB nhieu dieu nhat
print("\n=== 5 văn bản NHIỀU ĐIỀU nhất ===")
alld = []
for t in art_per_doc:
    for lid, c in art_per_doc[t].items():
        alld.append((c, t, lid))
for c, t, lid in sorted(alld, reverse=True)[:5]:
    print(f"  {c} điều | {t} | law_id={lid}")
