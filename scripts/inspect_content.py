import json, sys
sys.stdout.reconfigure(encoding="utf-8")
F = "data/mainstream/mainstream_docs.jsonl"
target = None
for line in open(F, encoding="utf-8"):
    d = json.loads(line)
    if d.get("documentType") == "Nghị định" and 3000 < len(d.get("content") or "") < 12000:
        target = d
        break
c = target.get("content") or ""
print("VB:", target.get("documentCode"), "| type:", target.get("documentType"), "| len:", len(c))
print("=== TOP KEYS ===")
print([k for k in target.keys()])
print("=== 2500 ky tu dau content THO ===")
print(c[:2500])
print("=== cac dong bat dau bang 'Điều'/'Chương'/'Mục' (20 dong) ===")
import re
n = 0
for ln in c.split("\n"):
    if re.match(r"^\s*(Điều|Chương|Mục|CHƯƠNG|MỤC|PHẦN)\b", ln):
        print(repr(ln[:80]))
        n += 1
        if n >= 20:
            break
