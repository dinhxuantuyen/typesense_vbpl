"""Embed cac chunk da dung san (chunks.jsonl co truong embed_text) -> embedded_chunks.jsonl.

Resumable + concurrent. Dung cho main-stream (chunk da tach san, chi can embed).

Usage (WSL):
  python3 -m legal_search.embed_chunks --input data/mainstream/chunks.jsonl \
      --outdir data/mainstream/embed --workers 16
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from .config import Config
from .proxy import embed_batch_pp


def load_done(path):
    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            s = line.strip()
            if s:
                done.add(s)
    return done


def embed_worker(cfg, batch):
    texts = [r["embed_text"] for r in batch]
    vecs = embed_batch_pp(cfg, texts, is_query=False)
    out, fail = [], 0
    if vecs is not None:
        for r, v in zip(batch, vecs):
            r["embedding"] = v
            r.pop("embed_text", None)
            out.append(r)
        return out, 0
    for r in batch:      # fallback tung item
        v = embed_batch_pp(cfg, [r["embed_text"]], is_query=False)
        if v is None:
            fail += 1
            continue
        r["embedding"] = v[0]
        r.pop("embed_text", None)
        out.append(r)
    return out, fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/mainstream/chunks.jsonl")
    ap.add_argument("--outdir", default="data/mainstream/embed")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--window", type=int, default=1600)
    args = ap.parse_args()
    cfg = Config()
    os.makedirs(args.outdir, exist_ok=True)
    out_path = os.path.join(args.outdir, "embedded_chunks.jsonl")
    done_path = os.path.join(args.outdir, "done.txt")

    done = load_done(done_path)
    print(f"[resume] da co {len(done)} chunk embedded | model={cfg.embed_model} dim={cfg.embed_dim}", flush=True)

    t0 = time.time()
    tot_w = tot_f = tot_skip = 0
    buf = []
    with open(out_path, "a", encoding="utf-8") as fo, open(done_path, "a", encoding="utf-8") as fd:
        def flush():
            nonlocal tot_w, tot_f
            if not buf:
                return
            batch_sz = cfg.embed_batch
            batches = [buf[i:i + batch_sz] for i in range(0, len(buf), batch_sz)]
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                for res, f in ex.map(lambda b: embed_worker(cfg, b), batches):
                    tot_f += f
                    for r in res:
                        fo.write(json.dumps(r, ensure_ascii=False) + "\n")
                        fd.write(r["id"] + "\n")
                        tot_w += 1
            fo.flush()
            fd.flush()

        for line in open(args.input, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["id"] in done:
                tot_skip += 1
                continue
            buf.append(r)
            if len(buf) >= args.window:
                flush()
                for r in buf:
                    done.add(r["id"])
                buf = []
                rate = tot_w / max(1e-6, time.time() - t0)
                remain = "?"
                print(f"  written={tot_w} failed={tot_f} skip={tot_skip} rate={rate:.0f}/s", flush=True)
        flush()

    dt = time.time() - t0
    print(f"\nDONE: written={tot_w} failed={tot_f} skip={tot_skip} trong {dt:.0f}s ({tot_w/max(1e-6,dt):.0f}/s)")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
