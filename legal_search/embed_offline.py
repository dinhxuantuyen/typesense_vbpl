"""Phase A: Embed offline resumable + concurrent cho du lieu lon.

Stream JSONL -> build docs -> embed concurrent (truncate 1024d) -> ghi embedded.jsonl + checkpoint.
Chay lai duoc: bo qua id da co trong done.txt.

Usage (WSL):
  python3 -m legal_search.embed_offline --input data/thuvienphapluat-chunks-v260626.jsonl \
      --outdir data/build --workers 8 --window 2000
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from .config import Config
from .chunking import build_documents
from .proxy import embed_batch_pp


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    done.add(s)
    return done


def embed_worker(cfg, batch):
    """Embed 1 batch docs -> gan embedding. Fallback tung item neu batch loi. Tra list doc (bo item loi)."""
    texts = [d["_embed_text"] for d in batch]
    vecs = embed_batch_pp(cfg, texts, is_query=False)
    out = []
    if vecs is not None:
        for d, v in zip(batch, vecs):
            d["embedding"] = v
            out.append(d)
        return out, 0
    # fallback tung item
    fail = 0
    for d in batch:
        v = embed_batch_pp(cfg, [d["_embed_text"]], is_query=False)
        if v is None:
            fail += 1
            continue
        d["embedding"] = v[0]
        out.append(d)
    return out, fail


def process_window(cfg, docs, workers, fout, fdone):
    """Embed 1 cua so docs song song, ghi ket qua + checkpoint."""
    batch = cfg.embed_batch
    batches = [docs[i : i + batch] for i in range(0, len(docs), batch)]
    written = failed = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for result, fail in ex.map(lambda b: embed_worker(cfg, b), batches):
            failed += fail
            for d in result:
                d.pop("_embed_text", None)
                fout.write(json.dumps(d, ensure_ascii=False) + "\n")
                fdone.write(d["id"] + "\n")
                written += 1
    fout.flush()
    fdone.flush()
    return written, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", default="data/build")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--window", type=int, default=2000)
    ap.add_argument("--limit", type=int, default=0, help="Chi xu ly N record dau (0=tat ca)")
    args = ap.parse_args()

    cfg = Config()
    os.makedirs(args.outdir, exist_ok=True)
    embedded_path = os.path.join(args.outdir, "embedded.jsonl")
    done_path = os.path.join(args.outdir, "done.txt")

    done = load_done(done_path)
    print(f"[resume] da co {len(done)} document embedded truoc do", flush=True)

    t0 = time.time()
    total_written = total_failed = total_skipped = 0
    buffer = []
    n_rec = 0

    with open(embedded_path, "a", encoding="utf-8") as fout, open(done_path, "a", encoding="utf-8") as fdone:
        with open(args.input, encoding="utf-8") as fin:
            for line in fin:
                line = line.strip()
                if not line:
                    continue
                n_rec += 1
                if args.limit and n_rec > args.limit:
                    break
                try:
                    rec = json.loads(line)
                    new_docs = build_documents(rec, cfg.subchunk_threshold)
                except Exception as e:  # noqa: BLE001
                    print(f"  [skip rec] {e}", file=sys.stderr)
                    continue
                for d in new_docs:
                    if d["id"] in done:
                        total_skipped += 1
                        continue
                    buffer.append(d)
                if len(buffer) >= args.window:
                    w, f = process_window(cfg, buffer, args.workers, fout, fdone)
                    total_written += w
                    total_failed += f
                    for d in buffer:
                        done.add(d["id"])
                    buffer = []
                    rate = total_written / max(1e-6, time.time() - t0)
                    print(f"  rec={n_rec} written={total_written} failed={total_failed} "
                          f"skipped={total_skipped} rate={rate:.0f}/s", flush=True)
            if buffer:
                w, f = process_window(cfg, buffer, args.workers, fout, fdone)
                total_written += w
                total_failed += f

    dt = time.time() - t0
    print(f"\nDONE: written={total_written} failed={total_failed} skipped={total_skipped} "
          f"trong {dt:.0f}s ({total_written/max(1e-6,dt):.0f}/s)")
    print(f"Output: {embedded_path}")


if __name__ == "__main__":
    main()
