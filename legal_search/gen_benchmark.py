"""TASK-012 (buoc 2): Sinh cau hoi tu seed.jsonl bang LLM (chay SAU khi embed xong, proxy ranh).

Usage (WSL):
  python3 -m legal_search.gen_benchmark --seed data/benchmark/seed.jsonl \
      --out data/benchmark/benchmark.jsonl --model DeepSeek-V4-Flash --workers 4
"""
import argparse
import json
import os
import random
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .chunking import fold_ascii
from .config import Config

_cfg = Config()
CHAT_URL = f"{_cfg.embed_base_url}/chat/completions"
API_KEY = _cfg.embed_api_key  # doc tu .env / bien moi truong, khong hard-code secret

PROMPT_TMPL = (
    "Dưới đây là nội dung một điều luật Việt Nam. Hãy đóng vai người dân/doanh nghiệp "
    "đang cần tra cứu, và đặt MỘT câu hỏi tự nhiên bằng tiếng Việt mà điều luật này trả lời được.\n"
    "Yêu cầu:\n"
    "- Dùng lời lẽ đời thường, KHÁC văn phong hành chính và KHÁC nguyên văn tiêu đề.\n"
    "- KHÔNG nhắc số hiệu/tên văn bản, KHÔNG nói 'theo điều luật'.\n"
    "- Câu hỏi phải cụ thể, gắn với nội dung để tránh mơ hồ.\n"
    "- Chỉ trả về đúng MỘT câu hỏi, không giải thích.\n\n"
    "Tiêu đề (chỉ để tham khảo ngữ cảnh): {heading}\n"
    "Nội dung điều luật:\n{content}"
)


def gen_question(model, heading, content, max_retries=5):
    prompt = PROMPT_TMPL.format(heading=heading, content=content[:1800])
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 120, "temperature": 0.8}).encode()
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(CHAT_URL, data=body, headers={
                "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=120))
            msg = r["choices"][0]["message"]
            q = (msg.get("content") or "").strip()
            q = q.strip().strip('"').strip()
            q = re.sub(r"^(Câu hỏi|Question)\s*[:：]\s*", "", q, flags=re.I).strip()
            q = q.split("\n")[0].strip()  # lay dong dau neu model tra nhieu dong
            if q and len(q) > 8:
                return q
        except Exception:
            if attempt == max_retries:
                return None
            time.sleep(min(2 ** attempt, 10))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="data/benchmark/seed.jsonl")
    ap.add_argument("--out", default="data/benchmark/benchmark.jsonl")
    ap.add_argument("--model", default="DeepSeek-V4-Flash")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-accent-ratio", type=float, default=0.3)
    ap.add_argument("--rng-seed", type=int, default=7)
    args = ap.parse_args()
    rng = random.Random(args.rng_seed)

    seeds = [json.loads(l) for l in open(args.seed, encoding="utf-8") if l.strip()]
    done = set()
    if os.path.exists(args.out):
        for l in open(args.out, encoding="utf-8"):
            try:
                done.add(json.loads(l)["expected_chunk_id"])
            except Exception:
                pass
    todo = [s for s in seeds if s["chunk_id"] not in done]
    print(f"Seed={len(seeds)} | da co={len(done)} | can sinh={len(todo)} | model={args.model} workers={args.workers}", flush=True)

    fout = open(args.out, "a", encoding="utf-8")
    t0 = time.time()
    cnt = {"ok": 0, "fail": 0}

    def work(s):
        q = gen_question(args.model, s.get("article_heading") or "", s.get("content") or "")
        if not q:
            cnt["fail"] += 1
            return
        if rng.random() < args.no_accent_ratio:
            q = fold_ascii(q)
        row = {
            "question": q,
            "expected_chunk_id": s["chunk_id"],
            "citation": s.get("citation"),
            "document_type": s.get("document_type"),
            "article_heading": s.get("article_heading"),
        }
        fout.write(json.dumps(row, ensure_ascii=False) + "\n")
        fout.flush()
        cnt["ok"] += 1
        if cnt["ok"] % 25 == 0:
            print(f"   {cnt['ok']}/{len(todo)} ({cnt['ok']/max(1e-6,time.time()-t0):.1f}/s) fail={cnt['fail']}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, todo))
    fout.close()

    n = sum(1 for _ in open(args.out, encoding="utf-8"))
    print(f"\nDONE: ok={cnt['ok']} fail={cnt['fail']} | tong benchmark={n} dong -> {args.out}")


if __name__ == "__main__":
    main()
