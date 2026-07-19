"""TASK-016 (chunking): Tach Dieu tu mainstream_docs.jsonl -> chunks.jsonl.

Tach content nguyen van ban thanh ban ghi cap Dieu (Cach 1: content tho de gop lai;
embed_text ten-dieu-truoc; quan he tu edges). Chua embed (buoc sau).

Usage (WSL):
  python3 -m legal_search.mainstream_chunk --docs data/mainstream/mainstream_docs.jsonl \
      --edges data/mainstream/edges.jsonl --out data/mainstream/chunks.jsonl
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict

from .chunking import fold_ascii, split_long_content
from .mainstream_extract import parse_date, is_effective, REF_DATE

ART_RE = re.compile(r"^Điều\s+(\d+[A-Za-zđĐ]?)\s*\.\s*(.*)$")
CHUONG_RE = re.compile(r"^(Chương|CHƯƠNG|Phần|PHẦN)\s+(.+)$")
MUC_RE = re.compile(r"^(Mục|MỤC)\s+(.+)$")
SUBCHUNK_TH = 4000
LOW_VALUE_HEADINGS = re.compile(
    r"(điều khoản thi hành|hiệu lực thi hành|tổ chức thực hiện|trách nhiệm thi hành)", re.I)


def to_ts(s):
    d = parse_date(s)
    return int(__import__("datetime").datetime(d.year, d.month, d.day).timestamp()) if d else 0


def split_articles(content):
    """Tra list dict {article_no, heading, chapter, section, body}."""
    lines = content.split("\n")
    chapter = section = None
    pending_chapter_title = False
    arts, cur = [], None
    for ln in lines:
        s = ln.strip()
        if not s:
            if cur:
                cur["lines"].append(ln)
            continue
        mc = CHUONG_RE.match(s)
        mm = MUC_RE.match(s)
        ma = ART_RE.match(s)
        if ma:
            if cur:
                arts.append(cur)
            cur = {"article_no": ma.group(1), "heading_rest": ma.group(2).strip(),
                   "chapter": chapter, "section": section, "lines": [ln]}
            pending_chapter_title = False
        elif mc:
            chapter = s
            section = None
            pending_chapter_title = True     # dong ke tiep co the la tieu de chuong
            cur = None if cur is None else cur  # chuong khong thuoc dieu
        elif mm:
            section = s
            pending_chapter_title = False
        elif pending_chapter_title and cur is None:
            # tieu de chuong nam o dong sau "Chương X"
            chapter = f"{chapter} — {s}" if chapter else s
            pending_chapter_title = False
        elif cur:
            cur["lines"].append(ln)
        # else: preamble truoc Dieu 1 -> bo
    if cur:
        arts.append(cur)
    return arts


def build_relmap(edges_path):
    """law_id -> {guided_by:set, guides:set, consolidated:set, related:[...]}"""
    rel = defaultdict(lambda: {"guided_by": set(), "guides": set(),
                               "consolidated": set(), "related": []})
    field = {"huong_dan": "guided_by", "duoc_huong_dan": "guides",
             "hop_nhat": "consolidated", "duoc_hop_nhat": "consolidated"}
    for line in open(edges_path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        src = e["source_law_id"]
        f = field.get(e["relation"])
        if not f:
            continue
        tid = e["target_law_id"]
        rel[src][f].add(tid)
        rel[src]["related"].append({
            "relation": e["relation"], "law_id": tid,
            "document_code": e.get("target_code"), "document_type": e.get("target_type"),
            "name": e.get("target_name"), "validity_status": e.get("target_validity"),
            "url": e.get("target_url"),
        })
    return rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="data/mainstream/mainstream_docs.jsonl")
    ap.add_argument("--edges", default="data/mainstream/edges.jsonl")
    ap.add_argument("--out", default="data/mainstream/chunks.jsonl")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    relmap = build_relmap(args.edges)
    backbone_ids = set(relmap.keys())
    st = Counter()
    lens = []
    fout = open(args.out, "w", encoding="utf-8")

    for line in open(args.docs, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        st["docs"] += 1
        lid = d.get("lawId")
        code = d.get("documentCode")
        title = d.get("title") or ""
        eff_now = is_effective(d)
        rel = relmap.get(lid, {})
        base_meta = {
            "law_id": lid, "document_code": code, "document_type": d.get("documentType"),
            "document_title": title, "agency_issued": d.get("agencyIssued"),
            "issued_agencies": d.get("issuedAgencies") or [], "signer": (d.get("signer") or ""),
            "fields": d.get("fields") or [],
            "date_issued": d.get("dateIssued"), "effective_date": d.get("effectiveDate"),
            "expiration_date": d.get("expirationDate"),
            "effective_ts": to_ts(d.get("effectiveDate")), "expiration_ts": to_ts(d.get("expirationDate")),
            "validity_status": d.get("validityStatus"), "is_effective_now": eff_now,
            "is_mainstream": lid in backbone_ids,
            "source_url": d.get("url"),
            "rel_guided_by_ids": sorted(rel.get("guided_by", [])),
            "rel_guides_ids": sorted(rel.get("guides", [])),
            "rel_consolidated_ids": sorted(rel.get("consolidated", [])),
            "related": rel.get("related", []),
        }

        arts = split_articles(d.get("content") or "")
        st["articles"] += len(arts)
        for a in arts:
            body = "\n".join(a["lines"]).strip()
            if not body:
                continue
            ano = a["article_no"]
            m = re.match(r"(\d+)", ano)
            anum = int(m.group(1)) if m else 0
            heading = (a["lines"][0].strip())[:200]
            chapter = a.get("chapter")
            ctx = " › ".join(x for x in [chapter, a.get("section")] if x)
            base_pid = f"{lid}-dieu-{ano}"
            citation = f"Điều {ano} {code}"
            low_value = bool(LOW_VALUE_HEADINGS.search(heading)) or len(body) < 40

            parts = split_long_content(body, SUBCHUNK_TH)
            npar = len(parts)
            for k, part in enumerate(parts):
                cid = base_pid if npar == 1 else f"{base_pid}#p{k+1}"
                header = f"{code} — {chapter}" if chapter else code
                embed_text = f"{heading}\n[{header}]\n{part}"
                rec = {
                    "id": cid, "parent_id": base_pid,
                    "part_no": k, "n_parts": npar,
                    **base_meta,
                    "chapter": chapter, "section": a.get("section"), "context_path": ctx,
                    "article_no": ano, "article_num": anum, "article_heading": heading,
                    "citation": citation,
                    "content": part,
                    "heading_ascii": fold_ascii(heading),
                    "body_ascii": fold_ascii(part),
                    "embed_text": embed_text,
                    "is_low_value": low_value, "is_repealed": "(được bãi bỏ)" in heading.lower(),
                }
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                st["chunks"] += 1
                lens.append(len(part))
        if st["docs"] % 500 == 0:
            print(f"  ...{st['docs']} VB, {st['chunks']} chunk", flush=True)

    fout.close()
    lens.sort()
    pct = lambda p: lens[min(len(lens) - 1, int(p / 100 * len(lens)))] if lens else 0
    print(f"\n=== CHUNKING XONG ===")
    print(f"Văn bản: {st['docs']} | Điều: {st['articles']} | Chunk (sau sub-chunk): {st['chunks']}")
    print(f"Độ dài chunk (ký tự): p50={pct(50)} p90={pct(90)} p95={pct(95)} max={lens[-1] if lens else 0}")
    print(f"Output -> {args.out}")


if __name__ == "__main__":
    main()
