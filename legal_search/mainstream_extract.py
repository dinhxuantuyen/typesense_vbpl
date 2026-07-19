"""TASK-015: Trich main-stream Nghi dinh hieu luc + do thi quan he (Phase 1).

Pass 1: backbone (NĐ hieu luc) + edges (huong dan/duoc huong dan/hop nhat 2 chieu, dedup VBHN moi hon)
        + tap lawId hang xom. Xuat nodes_backbone.jsonl, edges.jsonl, neighbor_ids.txt, stats.
Pass 2: trich full record cho lawId thuoc main-stream -> mainstream_docs.jsonl.

Usage (WSL):
  python3 -m legal_search.mainstream_extract pass1 --input /mnt/e/vbpl/thuvienphapluat-v260710.jsonl --outdir data/mainstream
  python3 -m legal_search.mainstream_extract pass2 --input /mnt/e/vbpl/thuvienphapluat-v260710.jsonl --outdir data/mainstream
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

REF_DATE = date(2026, 7, 19)   # "hom nay" theo yeu cau nghiep vu

EXCLUDE_STATUS = ("Hết hiệu lực", "Không còn phù hợp", "Không xác định",
                  "Chưa xác định", "Ngưng hiệu lực")

RELATION_MAP = {
    "Văn bản hướng dẫn": "huong_dan",
    "Văn bản được hướng dẫn": "duoc_huong_dan",
    "Văn bản hợp nhất": "hop_nhat",
    "Văn bản được hợp nhất": "duoc_hop_nhat",
}
CONSOLIDATE_REL = {"hop_nhat", "duoc_hop_nhat"}


def parse_date(s):
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)          # ISO
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)          # dd/mm/yyyy
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def is_effective(rec, ref=REF_DATE):
    vs = rec.get("validityStatus") or ""
    if any(kw in vs for kw in EXCLUDE_STATUS):
        return False
    exp = parse_date(rec.get("expirationDate"))
    if exp and exp < ref:
        return False
    return True


def node_of(rec):
    return {
        "law_id": rec.get("lawId"),
        "document_code": rec.get("documentCode"),
        "title": rec.get("title"),
        "document_type": rec.get("documentType"),
        "validity_status": rec.get("validityStatus"),
        "date_issued": rec.get("dateIssued"),
        "effective_date": rec.get("effectiveDate"),
        "expiration_date": rec.get("expirationDate"),
        "url": rec.get("url"),
    }


def pass1(args):
    os.makedirs(args.outdir, exist_ok=True)
    backbone = {}              # law_id -> node
    edges = []                 # list dict
    neighbor_ids = set()
    stats = Counter()
    rel_count = Counter()
    neighbor_types = Counter()
    n = 0
    for line in open(args.input, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            rec = json.loads(line)
        except Exception:
            stats["parse_error"] += 1
            continue
        if rec.get("documentType") != "Nghị định":
            continue
        stats["nghi_dinh_total"] += 1
        if not is_effective(rec):
            stats["nghi_dinh_loai_het_hieu_luc"] += 1
            continue
        stats["backbone"] += 1
        lid = rec.get("lawId")
        backbone[lid] = node_of(rec)

        # gom quan he theo relation, dedup VBHN moi hon cho quan he hop nhat
        for grp in (rec.get("documentDiagrams") or []):
            rel = RELATION_MAP.get(grp.get("relatedDocumentType"))
            if not rel:
                continue
            targets = grp.get("documents") or []
            if rel in CONSOLIDATE_REL and len(targets) > 1:
                # giu VBHN moi hon (dateIssued lon nhat)
                targets = [max(targets, key=lambda t: (parse_date(t.get("dateIssued")) or date.min))]
                stats["vbhn_deduped_groups"] += 1
            for t in targets:
                tid = t.get("id") or t.get("_id")
                if tid is None:
                    continue
                neighbor_ids.add(tid)
                neighbor_types[t.get("documentType")] += 1
                rel_count[rel] += 1
                edges.append({
                    "source_law_id": lid,
                    "source_code": rec.get("documentCode"),
                    "relation": rel,
                    "target_law_id": tid,
                    "target_code": t.get("documentCode"),
                    "target_type": t.get("documentType"),
                    "target_validity": t.get("validityStatus"),
                    "target_date": t.get("dateIssued"),
                    "target_name": t.get("documentName"),
                    "target_url": t.get("url"),
                })
        if n % 20000 == 0:
            print(f"  ...{n} record, backbone={stats['backbone']}", flush=True)

    # ghi output
    with open(os.path.join(args.outdir, "nodes_backbone.jsonl"), "w", encoding="utf-8") as f:
        for nd in backbone.values():
            f.write(json.dumps(nd, ensure_ascii=False) + "\n")
    with open(os.path.join(args.outdir, "edges.jsonl"), "w", encoding="utf-8") as f:
        for e in edges:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    only_neighbor = neighbor_ids - set(backbone.keys())
    with open(os.path.join(args.outdir, "neighbor_ids.txt"), "w", encoding="utf-8") as f:
        for i in sorted(only_neighbor, key=str):
            f.write(f"{i}\n")

    print(f"\n=== PASS 1 XONG ({n} record) ===")
    print("Backbone (NĐ hiệu lực):", stats["backbone"], "/", stats["nghi_dinh_total"], "NĐ")
    print("  loại (hết hiệu lực/không phù hợp...):", stats["nghi_dinh_loai_het_hieu_luc"])
    print("Edges:", len(edges), "| theo loại:", dict(rel_count))
    print("VBHN groups đã dedup:", stats["vbhn_deduped_groups"])
    print("Hàng xóm (distinct lawId):", len(neighbor_ids), "| chỉ-hàng-xóm (không phải backbone):", len(only_neighbor))
    print("Hàng xóm theo documentType:", dict(neighbor_types.most_common(10)))
    print(f"Output -> {args.outdir}/ (nodes_backbone.jsonl, edges.jsonl, neighbor_ids.txt)")


def pass2(args):
    ids = set()
    for fn in ("nodes_backbone.jsonl",):
        for line in open(os.path.join(args.outdir, fn), encoding="utf-8"):
            if line.strip():
                ids.add(json.loads(line)["law_id"])
    nb = os.path.join(args.outdir, "neighbor_ids.txt")
    if os.path.exists(nb):
        for line in open(nb, encoding="utf-8"):
            line = line.strip()
            if line:
                ids.add(int(line) if line.isdigit() else line)
    print(f"[pass2] main-stream cần trích: {len(ids)} lawId")

    out = os.path.join(args.outdir, "mainstream_docs.jsonl")
    found = 0
    with open(out, "w", encoding="utf-8") as fo:
        for line in open(args.input, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("lawId") in ids:
                fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
                found += 1
    print(f"[pass2] Đã trích {found}/{len(ids)} văn bản -> {out}")
    print(f"[pass2] Thiếu (hàng xóm không có trong corpus): {len(ids) - found}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("pass1", "pass2"):
        p = sub.add_parser(c)
        p.add_argument("--input", required=True)
        p.add_argument("--outdir", default="data/mainstream")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    (pass1 if args.cmd == "pass1" else pass2)(args)


if __name__ == "__main__":
    main()
