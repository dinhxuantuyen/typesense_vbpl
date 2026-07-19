import json, sys
sys.stdout.reconfigure(encoding="utf-8")
F = "data/mainstream/chunks.jsonl"

rec_rel = None      # 1 chunk co quan he
rec_multi = None    # 1 chunk part >1
by_parent = {}
for line in open(F, encoding="utf-8"):
    r = json.loads(line)
    if rec_rel is None and r.get("related"):
        rec_rel = r
    if rec_multi is None and r.get("n_parts", 1) > 1:
        rec_multi = r
    if rec_rel and rec_multi:
        break

print("=== 1) CHUNK CÓ QUAN HỆ (backbone NĐ) ===")
r = rec_rel
for k in ["id", "parent_id", "part_no", "n_parts", "law_id", "document_code", "document_type",
          "is_effective_now", "is_mainstream", "chapter", "context_path", "article_no",
          "article_heading", "citation", "source_url", "rel_guided_by_ids", "rel_guides_ids",
          "rel_consolidated_ids", "is_low_value"]:
    print(f"  {k}: {json.dumps(r.get(k), ensure_ascii=False)[:120]}")
print("  related[0]:", json.dumps((r.get("related") or [{}])[0], ensure_ascii=False)[:200])
print("  embed_text[:180]:", repr(r["embed_text"][:180]))
print("  content[:120] (THÔ, ko header):", repr(r["content"][:120]))

print("\n=== 2) ĐIỀU DÀI (kiểm tra gộp part = đầy đủ) ===")
pid = rec_multi["parent_id"]
parts = []
for line in open(F, encoding="utf-8"):
    r = json.loads(line)
    if r.get("parent_id") == pid:
        parts.append(r)
parts.sort(key=lambda x: x["part_no"])
print(f"  parent_id={pid} | n_parts={parts[0]['n_parts']} | article={parts[0]['citation']}")
merged = "\n".join(p["content"] for p in parts)
print(f"  Tổng độ dài gộp lại: {len(merged)} ký tự (từ {len(parts)} part)")
print(f"  Đầu điều gộp: {merged[:100]!r}")
print(f"  Header CÓ lọt vào content không? (mong đợi KHÔNG):",
      "[" in parts[0]['content'][:60] or "—" in parts[0]['content'][:60])
