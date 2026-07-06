"""Client goi proxy embedding/rerank (OpenAI-compatible) — thuan stdlib, co retry/batch."""
import json
import math
import time
import urllib.request
import urllib.error


class ProxyError(RuntimeError):
    pass


def _post(url: str, api_key: str, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


# Instruction cho phia QUERY (bat doi xung — document embed KHONG co instruction,
# nen doi instruction nay khong can re-embed du lieu).
QUERY_INSTRUCTION = (
    "Intruction: Hãy truy xuất điều luật trả lời cho câu hỏi hoặc mệnh đề sau: \n Query: "
)


def _wrap_query(texts, is_query):
    if not is_query:
        return texts
    return [QUERY_INSTRUCTION + t for t in texts]


def _postprocess(vec, target_dim):
    """Cat chieu Matryoshka (2560 -> target_dim) + L2-normalize (khuyen nghi khi truncate MRL)."""
    if target_dim and len(vec) > target_dim:
        vec = vec[:target_dim]
    n = math.sqrt(sum(x * x for x in vec))
    if n > 0:
        vec = [x / n for x in vec]
    return vec


def embed(cfg, texts, is_query=False, max_retries=4):
    """Embed danh sach text -> list vector (da cat chieu ve cfg.embed_dim + normalize).

    Batch theo cfg.embed_batch, retry co backoff. Neu ca batch loi -> chia nho ve tung item.
    """
    url = f"{cfg.embed_base_url}/embeddings"
    out = []
    batch = cfg.embed_batch
    i = 0
    while i < len(texts):
        chunk = texts[i : i + batch]
        vecs = _embed_batch(url, cfg.embed_api_key, cfg.embed_model, _wrap_query(chunk, is_query), max_retries)
        if vecs is None:
            for t in chunk:  # fallback tung item de co lap loi
                v = _embed_batch(url, cfg.embed_api_key, cfg.embed_model, _wrap_query([t], is_query), max_retries)
                if v is None:
                    raise ProxyError(f"Embed that bai sau {max_retries} lan cho 1 item: {t[:80]!r}")
                out.extend(v)
        else:
            out.extend(vecs)
        i += batch
    return [_postprocess(v, cfg.embed_dim) for v in out]


def embed_batch_pp(cfg, texts, is_query=False, max_retries=4):
    """Embed 1 batch -> list vector da cat chieu + normalize. Tra None neu that bai (de caller fallback)."""
    url = f"{cfg.embed_base_url}/embeddings"
    vecs = _embed_batch(url, cfg.embed_api_key, cfg.embed_model, _wrap_query(texts, is_query), max_retries)
    if vecs is None:
        return None
    return [_postprocess(v, cfg.embed_dim) for v in vecs]


def _embed_batch(url, api_key, model, inputs, max_retries):
    for attempt in range(1, max_retries + 1):
        try:
            resp = _post(url, api_key, {"model": model, "input": inputs})
            if "data" not in resp:
                raise ProxyError(str(resp)[:200])
            # sap xep theo index de dam bao dung thu tu
            items = sorted(resp["data"], key=lambda d: d.get("index", 0))
            return [it["embedding"] for it in items]
        except Exception as e:  # noqa: BLE001
            if attempt == max_retries:
                return None
            time.sleep(min(2 ** attempt, 8))
    return None


def rerank(cfg, query, documents, top_n=None, max_retries=3):
    """Goi reranker (Phase 2). Tra list (index, score) giam dan.
    Ho tro 2 dang API: /rerank chuan, hoac fallback None neu proxy khong ho tro."""
    url = f"{cfg.embed_base_url}/rerank"
    payload = {"model": cfg.rerank_model, "query": query, "documents": documents}
    if top_n:
        payload["top_n"] = top_n
    for attempt in range(1, max_retries + 1):
        try:
            resp = _post(url, cfg.embed_api_key, payload)
            results = resp.get("results") or resp.get("data")
            if not results:
                return None
            pairs = [(r["index"], r.get("relevance_score", r.get("score", 0.0))) for r in results]
            pairs.sort(key=lambda x: -x[1])
            return pairs
        except Exception:  # noqa: BLE001
            if attempt == max_retries:
                return None
            time.sleep(1)
    return None
