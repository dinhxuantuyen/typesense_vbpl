"""Ingest JSON dieu luat vao Typesense.

Usage (chay trong WSL):
  python3 -m legal_search.ingest --input /mnt/e/thuvienphapluat-chunks-sample-100.json --recreate
"""
import argparse
import json
import sys
import time

from .config import Config
from .chunking import build_schema, build_documents
from .proxy import embed
from .typesense_api import Typesense


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Duong dan file JSON (list cac Dieu)")
    ap.add_argument("--recreate", action="store_true", help="Xoa va tao lai collection")
    ap.add_argument("--limit", type=int, default=0, help="Chi ingest N chunk dau (0 = tat ca)")
    args = ap.parse_args()

    cfg = Config()
    ts = Typesense(cfg.ts_base, cfg.ts_api_key)

    # 1) Doc du lieu
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("chunks") or data.get("data") or [data]
    if args.limit:
        data = data[: args.limit]
    print(f"[1/5] Doc {len(data)} chunk tu {args.input}")

    # 2) Build documents (enrichment + sub-chunk)
    docs = []
    for ch in data:
        try:
            docs.extend(build_documents(ch, cfg.subchunk_threshold))
        except Exception as e:  # noqa: BLE001
            print(f"  [skip] chunk {ch.get('chunk_id')}: {e}", file=sys.stderr)
    n_parent = sum(1 for d in docs if d["part_no"] == 0)
    n_child = sum(1 for d in docs if d["part_no"] > 0)
    print(f"[2/5] Tao {len(docs)} document ({n_parent} Dieu nguyen + {n_child} subchunk cua Dieu dai)")

    # 3) Tao/tao lai collection
    schema = build_schema(cfg.collection, cfg.embed_dim)
    if args.recreate and ts.collection_exists(cfg.collection):
        ts.drop_collection(cfg.collection)
        print(f"[3/5] Da xoa collection cu '{cfg.collection}'")
    if not ts.collection_exists(cfg.collection):
        ts.create_collection(schema)
        print(f"[3/5] Tao collection '{cfg.collection}' (num_dim={cfg.embed_dim})")
    else:
        print(f"[3/5] Dung collection san co '{cfg.collection}'")

    # 4) Embed theo batch
    texts = [d.pop("_embed_text") for d in docs]
    print(f"[4/5] Embedding {len(texts)} text qua {cfg.embed_model} (batch={cfg.embed_batch})...")
    t0 = time.time()
    vecs = embed(cfg, texts, is_query=False)
    for d, v in zip(docs, vecs):
        d["embedding"] = v
    bad = [d["id"] for d, v in zip(docs, vecs) if len(v) != cfg.embed_dim]
    if bad:
        print(f"  [CANH BAO] {len(bad)} vector sai chieu: {bad[:3]}", file=sys.stderr)
    print(f"      xong trong {time.time()-t0:.1f}s")

    # 5) Upsert vao Typesense
    results = ts.import_documents(cfg.collection, docs, action="upsert")
    ok = sum(1 for r in results if r.get("success"))
    fail = [r for r in results if not r.get("success")]
    print(f"[5/5] Upsert: {ok} thanh cong, {len(fail)} loi")
    for r in fail[:5]:
        print("   loi:", str(r)[:200], file=sys.stderr)

    # Kiem tra
    info = ts.get_json(f"/collections/{cfg.collection}")
    print(f"\nCollection '{cfg.collection}' hien co {info['num_documents']} documents.")


if __name__ == "__main__":
    main()
