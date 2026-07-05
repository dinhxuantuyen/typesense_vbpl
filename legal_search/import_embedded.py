"""Phase B: Nap file embedded.jsonl (da co embedding) vao Typesense — KHONG goi proxy.

Usage (WSL):
  python3 -m legal_search.import_embedded --input data/build/embedded.jsonl --recreate --batch 2000
"""
import argparse
import json
import sys
import time

from .config import Config
from .chunking import build_schema
from .typesense_api import Typesense


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/build/embedded.jsonl")
    ap.add_argument("--batch", type=int, default=2000)
    ap.add_argument("--recreate", action="store_true")
    args = ap.parse_args()

    cfg = Config()
    ts = Typesense(cfg.ts_base, cfg.ts_api_key)

    if args.recreate and ts.collection_exists(cfg.collection):
        ts.drop_collection(cfg.collection)
        print(f"Da xoa collection cu '{cfg.collection}'")
    if not ts.collection_exists(cfg.collection):
        ts.create_collection(build_schema(cfg.collection, cfg.embed_dim))
        print(f"Tao collection '{cfg.collection}' (num_dim={cfg.embed_dim})")

    t0 = time.time()
    total_ok = total_fail = 0
    buf = []

    def flush(buf):
        nonlocal total_ok, total_fail
        if not buf:
            return
        results = ts.import_documents(cfg.collection, buf, action="upsert")
        ok = sum(1 for r in results if r.get("success"))
        total_ok += ok
        total_fail += len(results) - ok
        for r in results:
            if not r.get("success"):
                print("  loi:", str(r)[:160], file=sys.stderr)

    bad = 0
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                buf.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
                continue
            if len(buf) >= args.batch:
                flush(buf)
                buf = []
                print(f"  imported ok={total_ok} fail={total_fail} "
                      f"({total_ok/max(1e-6,time.time()-t0):.0f}/s)", flush=True)
        flush(buf)

    info = ts.get_json(f"/collections/{cfg.collection}")
    print(f"\nDONE: ok={total_ok} fail={total_fail} bad_lines={bad} trong {time.time()-t0:.0f}s")
    print(f"Collection '{cfg.collection}' num_documents={info['num_documents']}")


if __name__ == "__main__":
    main()
