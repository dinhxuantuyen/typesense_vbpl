"""TASK-016: Import embedded_chunks.jsonl (main-stream, 4096d) vao Typesense collection moi.

Usage (WSL):
  python3 -m legal_search.import_mainstream --input data/mainstream/embed/embedded_chunks.jsonl \
      --collection legal_mainstream --recreate --batch 1000
"""
import argparse
import json
import sys
import time

from .config import Config
from .typesense_api import Typesense


def build_schema(name, dim):
    idx = lambda **k: k
    return {
        "name": name,
        "fields": [
            # --- indexed / filter / facet ---
            {"name": "law_id", "type": "int64", "facet": True},
            {"name": "parent_id", "type": "string", "facet": True},
            {"name": "part_no", "type": "int32"},
            {"name": "document_code", "type": "string"},
            {"name": "document_type", "type": "string", "facet": True},
            {"name": "document_title", "type": "string"},
            {"name": "validity_status", "type": "string", "facet": True, "optional": True},
            {"name": "is_effective_now", "type": "bool", "facet": True},
            {"name": "is_mainstream", "type": "bool", "facet": True},
            {"name": "effective_ts", "type": "int64", "optional": True},
            {"name": "expiration_ts", "type": "int64", "optional": True},
            {"name": "fields", "type": "string[]", "facet": True, "optional": True},
            {"name": "chapter", "type": "string", "facet": True, "optional": True},
            {"name": "article_num", "type": "int32", "optional": True},
            {"name": "article_heading", "type": "string"},
            {"name": "citation", "type": "string", "optional": True},
            {"name": "heading_ascii", "type": "string"},
            {"name": "body_ascii", "type": "string"},
            {"name": "rel_guided_by_ids", "type": "int64[]", "facet": True, "optional": True},
            {"name": "rel_guides_ids", "type": "int64[]", "facet": True, "optional": True},
            {"name": "rel_consolidated_ids", "type": "int64[]", "facet": True, "optional": True},
            {"name": "is_low_value", "type": "bool", "facet": True},
            {"name": "is_repealed", "type": "bool", "facet": True},
            {"name": "embedding", "type": "float[]", "num_dim": dim},
            # --- store-only (returned, khong index) ---
            {"name": "n_parts", "type": "int32", "index": False, "optional": True},
            {"name": "article_no", "type": "string", "index": False, "optional": True},
            {"name": "context_path", "type": "string", "index": False, "optional": True},
            {"name": "section", "type": "string", "index": False, "optional": True},
            {"name": "content", "type": "string", "index": False, "optional": True},
            {"name": "source_url", "type": "string", "index": False, "optional": True},
            {"name": "related_json", "type": "string", "index": False, "optional": True},
            {"name": "agency_issued", "type": "string", "index": False, "optional": True},
            {"name": "signer", "type": "string", "index": False, "optional": True},
            {"name": "issued_agencies", "type": "string[]", "index": False, "optional": True},
            {"name": "date_issued", "type": "string", "index": False, "optional": True},
            {"name": "effective_date", "type": "string", "index": False, "optional": True},
            {"name": "expiration_date", "type": "string", "index": False, "optional": True},
        ],
    }


def _to_str(v):
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return v


def transform(rec):
    rec["related_json"] = json.dumps(rec.pop("related", []), ensure_ascii=False)
    # coerce cac field khai bao string nhung du lieu co the la list
    for k in ("signer", "agency_issued"):
        if k in rec:
            rec[k] = _to_str(rec[k])
    # Typesense khong nhan null cho field co kieu -> bo cac key None
    return {k: v for k, v in rec.items() if v is not None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/mainstream/embed/embedded_chunks.jsonl")
    ap.add_argument("--collection", default="legal_mainstream")
    ap.add_argument("--batch", type=int, default=1000)
    ap.add_argument("--recreate", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = Config()
    ts = Typesense(cfg.ts_base, cfg.ts_api_key)
    name = args.collection

    if args.recreate and ts.collection_exists(name):
        ts.drop_collection(name)
        print(f"Da xoa collection cu '{name}'")
    if not ts.collection_exists(name):
        ts.create_collection(build_schema(name, cfg.embed_dim))
        print(f"Tao collection '{name}' (num_dim={cfg.embed_dim})")

    t0 = time.time()
    ok = fail = bad = 0
    buf = []

    def flush():
        nonlocal ok, fail
        if not buf:
            return
        res = ts.import_documents(name, buf, action="upsert")
        for r in res:
            if r.get("success"):
                ok += 1
            else:
                fail += 1
                if fail <= 5:
                    print("  loi:", str(r)[:200], file=sys.stderr)

    for line in open(args.input, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            buf.append(transform(json.loads(line)))
        except Exception:
            bad += 1
            continue
        if len(buf) >= args.batch:
            flush()
            buf = []
            print(f"  ok={ok} fail={fail} ({ok/max(1e-6,time.time()-t0):.0f}/s)", flush=True)
    flush()

    info = ts.get_json(f"/collections/{name}")
    print(f"\nDONE: ok={ok} fail={fail} bad_lines={bad} trong {time.time()-t0:.0f}s")
    print(f"Collection '{name}' num_documents={info['num_documents']}")


if __name__ == "__main__":
    main()
