"""TASK-014: CRUD cap nhat du lieu dieu luat (module + CLI).

- upsert: them/sua Dieu (re-embed, xu ly sub-chunk, thay the part cu).
- patch_status: doi hieu luc, KHONG re-embed (nhanh).
- delete: theo chunk_id (1 Dieu) hoac law_id (ca VB).
- get: lay 1 Dieu (ghep part).

CLI (WSL):
  python3 -m legal_search.crud upsert --file dieu_moi.json
  python3 -m legal_search.crud patch-status --law-id 12076 --status "Het hieu luc" --expiration 2026-01-01
  python3 -m legal_search.crud delete --chunk-id 12076-dieu-25
  python3 -m legal_search.crud get --chunk-id 12076-dieu-25
"""
import argparse
import json
import sys
from datetime import date, datetime

from .config import Config
from .chunking import build_documents, parse_date
from .proxy import embed
from .typesense_api import Typesense


def _now_ts():
    return int(datetime.combine(date.today(), datetime.min.time()).timestamp())


class LegalCRUD:
    def __init__(self, cfg=None, ts=None):
        self.cfg = cfg or Config()
        self.ts = ts or Typesense(self.cfg.ts_base, self.cfg.ts_api_key)

    # ---- Create / Update ----
    def upsert(self, records):
        """Them/sua Dieu tu record schema nguon. Re-embed + thay the toan bo part cua chunk_id."""
        if isinstance(records, dict):
            records = [records]
        total_docs = 0
        for rec in records:
            docs = build_documents(rec, self.cfg.subchunk_threshold)
            cid = str(rec.get("chunk_id"))
            # xoa part cu (tranh part mo coi khi so part giam so voi ban truoc)
            self.ts.delete_by_filter(self.cfg.collection, f"chunk_id:=`{cid}`")
            texts = [d.pop("_embed_text") for d in docs]
            vecs = embed(self.cfg, texts, is_query=False)
            for d, v in zip(docs, vecs):
                d["embedding"] = v
            self.ts.import_documents(self.cfg.collection, docs, action="upsert")
            total_docs += len(docs)
        return {"upserted_articles": len(records), "documents": total_docs}

    # ---- Patch hieu luc (khong re-embed) ----
    def patch_status(self, *, law_id=None, chunk_id=None, validity_status=None,
                     effective_date=None, expiration_date=None):
        fields = {}
        if validity_status is not None:
            fields["validity_status"] = validity_status
        eff = parse_date(effective_date) if effective_date else None
        exp = parse_date(expiration_date) if expiration_date else None
        if eff:
            fields["effective_date"] = eff
        if exp:
            fields["expiration_date"] = exp
        if eff or exp:
            now = _now_ts()
            e, x = eff or 0, exp or 0
            fields["is_effective_now"] = (e == 0 or e <= now) and (x == 0 or x >= now)
        if not fields:
            return {"error": "khong co field nao de patch"}
        return self.ts.update_by_filter(self.cfg.collection, self._filter(law_id, chunk_id), fields)

    # ---- Delete ----
    def delete(self, *, law_id=None, chunk_id=None):
        return self.ts.delete_by_filter(self.cfg.collection, self._filter(law_id, chunk_id))

    # ---- Read ----
    def get(self, chunk_id):
        res = self.ts.search(self.cfg.collection, {
            "q": "*", "query_by": "body_ascii",
            "filter_by": f"chunk_id:=`{chunk_id}`", "per_page": 250, "exclude_fields": "embedding"})
        hits = res.get("hits", [])
        if not hits:
            return None
        docs = sorted((h["document"] for h in hits), key=lambda d: d.get("part_no", 0))
        m = docs[0]
        out = {k: m.get(k) for k in ("chunk_id", "citation", "article_heading", "document_code",
                                     "document_type", "validity_status", "is_effective_now",
                                     "source_url", "n_parts")}
        out["content"] = "\n".join(d.get("content", "") for d in docs)
        return out

    @staticmethod
    def _filter(law_id, chunk_id):
        if chunk_id:
            return f"chunk_id:=`{chunk_id}`"
        if law_id is not None:
            return f"law_id:={int(law_id)}"
        raise ValueError("Can cung cap law_id hoac chunk_id")


def _load_records(path):
    if path.endswith(".jsonl"):
        return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    data = json.load(open(path, encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def main():
    ap = argparse.ArgumentParser(description="CRUD dieu luat")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("upsert"); p.add_argument("--file", required=True)
    p = sub.add_parser("patch-status")
    p.add_argument("--law-id"); p.add_argument("--chunk-id")
    p.add_argument("--status"); p.add_argument("--effective"); p.add_argument("--expiration")
    p = sub.add_parser("delete"); p.add_argument("--law-id"); p.add_argument("--chunk-id")
    p = sub.add_parser("get"); p.add_argument("--chunk-id", required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    crud = LegalCRUD()
    if args.cmd == "upsert":
        print(crud.upsert(_load_records(args.file)))
    elif args.cmd == "patch-status":
        print(crud.patch_status(law_id=args.law_id, chunk_id=args.chunk_id,
                                validity_status=args.status,
                                effective_date=args.effective, expiration_date=args.expiration))
    elif args.cmd == "delete":
        print(crud.delete(law_id=args.law_id, chunk_id=args.chunk_id))
    elif args.cmd == "get":
        print(json.dumps(crud.get(args.chunk_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
