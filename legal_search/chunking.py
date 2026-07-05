"""Schema Typesense + bien doi chunk JSON -> document (enrichment, sub-chunk, co hieu luc)."""
import re
import unicodedata
from datetime import date, datetime


def fold_ascii(s: str | None) -> str:
    """Bo dau tieng Viet -> chu ASCII thuong (de keyword search bat bien voi dau)."""
    if not s:
        return ""
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", s).lower()


# ---------------- Schema ----------------
def build_schema(name: str, dim: int) -> dict:
    return {
        "name": name,
        "enable_nested_fields": False,
        "fields": [
            {"name": "chunk_id", "type": "string", "facet": True},      # id Dieu cha (rollup)
            {"name": "law_id", "type": "int64", "facet": True},
            {"name": "article_no", "type": "string", "optional": True},
            {"name": "article_heading", "type": "string", "optional": True},
            {"name": "citation", "type": "string", "optional": True},
            {"name": "citation_short", "type": "string", "optional": True},
            {"name": "content", "type": "string"},                       # text goc de hien thi
            {"name": "heading_ascii", "type": "string", "optional": True},  # keyword khong dau (heading+citation)
            {"name": "body_ascii", "type": "string"},                      # keyword khong dau (noi dung)
            {"name": "context_path", "type": "string", "optional": True, "facet": True},
            {"name": "document_title", "type": "string", "optional": True},
            {"name": "document_code", "type": "string", "optional": True, "facet": True},
            {"name": "document_type", "type": "string", "optional": True, "facet": True},
            {"name": "agency_issued", "type": "string", "optional": True, "facet": True},
            {"name": "fields", "type": "string[]", "optional": True, "facet": True},
            {"name": "validity_status", "type": "string", "optional": True, "facet": True},
            {"name": "date_issued", "type": "int64", "optional": True},
            {"name": "effective_date", "type": "int64", "optional": True},
            {"name": "expiration_date", "type": "int64", "optional": True},
            {"name": "is_effective_now", "type": "bool", "facet": True},
            {"name": "is_low_value", "type": "bool", "facet": True},
            {"name": "part_no", "type": "int32", "facet": True},         # 0 = ca Dieu; 1..n = subchunk
            {"name": "n_parts", "type": "int32"},
            {"name": "source_url", "type": "string", "optional": True, "index": False},
            {"name": "embedding", "type": "float[]", "num_dim": dim},
        ],
    }


# ---------------- Helpers ----------------
_WS = re.compile(r"[ \t]+")


def normalize_text(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(_WS.sub(" ", ln).strip() for ln in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def parse_date(s: str | None) -> int:
    if not s:
        return 0
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return int(datetime.strptime(s.strip(), fmt).timestamp())
        except (ValueError, AttributeError):
            continue
    return 0


REPEALED_RE = re.compile(r"\((?:\s*được\s+)?bãi\s*bỏ\s*\)", re.IGNORECASE)


def is_low_value(content: str, heading: str | None) -> bool:
    c = (content or "").strip()
    if len(c) < 40:
        return True
    if REPEALED_RE.search(c) and len(c) < 120:
        return True
    return False


def build_context_path(chunk: dict) -> str:
    ctx = chunk.get("context") or {}
    parts = [ctx.get(k) for k in ("phan", "chuong", "muc", "tieu_muc")]
    return " > ".join(p for p in parts if p)


def build_header(chunk: dict) -> str:
    """Header ngu canh gon dat truoc noi dung khi embed."""
    md = chunk.get("metadata") or {}
    dt = md.get("document_type") or ""
    code = md.get("document_code") or ""
    doc = (f"{dt} {code}").strip()
    ctx = build_context_path(chunk)
    heading = chunk.get("article_heading") or f"Điều {chunk.get('article_no','')}".strip()
    bits = [b for b in (doc, ctx, heading) if b]
    return " — ".join(bits)


# ---------------- Sub-chunk cho Dieu dai ----------------
_CLAUSE_RE = re.compile(r"^\s*(?:\d+\.|[a-zđ]\))", re.IGNORECASE)


def split_long_content(content: str, threshold: int) -> list[str]:
    """Tach noi dung dai thanh cac window <= ~threshold ky tu, uu tien ranh gioi Khoan/doan."""
    if len(content) <= threshold:
        return [content]
    # tach theo dong; gom cac dong thanh block bat dau bang moc Khoan
    lines = content.split("\n")
    blocks, cur = [], []
    for ln in lines:
        if _CLAUSE_RE.match(ln) and cur:
            blocks.append("\n".join(cur))
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        blocks.append("\n".join(cur))
    # greedy pack cac block vao window
    windows, buf = [], ""
    for b in blocks:
        if buf and len(buf) + len(b) + 1 > threshold:
            windows.append(buf)
            buf = b
        else:
            buf = (buf + "\n" + b) if buf else b
    if buf:
        windows.append(buf)
    # neu 1 block don le van qua dai -> cat cung theo ky tu
    final = []
    for w in windows:
        if len(w) <= threshold * 1.5:
            final.append(w)
        else:
            for i in range(0, len(w), threshold):
                final.append(w[i : i + threshold])
    return final


# ---------------- Bien doi 1 chunk -> list document ----------------
def build_documents(chunk: dict, threshold: int, now_ts: int | None = None) -> list[dict]:
    if now_ts is None:
        now_ts = int(datetime.combine(date.today(), datetime.min.time()).timestamp())
    md = chunk.get("metadata") or {}
    content = normalize_text(chunk.get("content"))
    heading = chunk.get("article_heading")
    header = build_header(chunk)
    low = is_low_value(content, heading)

    eff = parse_date(md.get("effective_date"))
    exp = parse_date(md.get("expiration_date"))
    effective_now = (eff == 0 or eff <= now_ts) and (exp == 0 or exp >= now_ts)

    base = {
        "chunk_id": str(chunk.get("chunk_id")),
        "law_id": int(chunk.get("law_id") or 0),
        "article_no": str(chunk.get("article_no") or ""),
        "article_heading": heading or "",
        "citation": chunk.get("citation") or "",
        "citation_short": chunk.get("citation_short") or "",
        "context_path": build_context_path(chunk),
        "document_title": md.get("title") or "",
        "document_code": md.get("document_code") or "",
        "document_type": md.get("document_type") or "",
        "agency_issued": md.get("agency_issued") or "",
        "fields": md.get("fields") or [],
        "validity_status": md.get("validity_status") or "",
        "is_effective_now": bool(effective_now),
        "is_low_value": bool(low),
        "source_url": md.get("source_url") or "",
    }
    for k, ts in (("date_issued", parse_date(md.get("date_issued"))),
                  ("effective_date", eff), ("expiration_date", exp)):
        if ts:
            base[k] = ts

    parts = split_long_content(content, threshold)
    docs = []
    n = len(parts)
    for idx, part in enumerate(parts):
        d = dict(base)
        if n == 1:
            d["id"] = base["chunk_id"]
            d["part_no"] = 0
        else:
            d["id"] = f"{base['chunk_id']}#p{idx+1}"
            d["part_no"] = idx + 1
        d["n_parts"] = n
        d["content"] = part                        # text goc de hien thi
        # Truong keyword khong dau (bat bien voi dau tieng Viet)
        d["heading_ascii"] = fold_ascii(f"{base['article_heading']} {base['citation']} {base['document_code']}")
        d["body_ascii"] = fold_ascii(part)
        # Enrichment: header ngu canh (lap lai o moi subchunk) + noi dung phan nay
        d["_embed_text"] = f"{header}\n{part}" if header else part
        docs.append(d)
    return docs
