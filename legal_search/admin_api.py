"""TASK-014: REST admin API cho CRUD dieu luat (Starlette).

Tach RIENG khoi MCP tim kiem (MCP cho Agent = read-only). API nay danh cho admin cap nhat du lieu.
Ngoai ra co endpoint tim kiem hybrid (POST /v1/search) — REST gateway tuong duong MCP search_legal_articles.

Chay (WSL):
  ~/legal-venv/bin/python -m legal_search.admin_api
Endpoints:
  GET    /health
  POST   /v1/search           body: {query, top_k?, document_type?, effective_only?, use_rerank?} -> hybrid search
  POST   /articles            body: record hoac list record -> upsert (re-embed)
  PATCH  /articles/status      body: {law_id|chunk_id, validity_status?, effective_date?, expiration_date?}
  GET    /articles/{chunk_id}
  DELETE /articles/{chunk_id}
  DELETE /laws/{law_id}
"""
import json
import os

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.routing import Route

from .config import Config
from .crud import LegalCRUD
from .search import search
from .typesense_api import Typesense

cfg = Config()
crud = LegalCRUD(cfg)
ts = Typesense(cfg.ts_base, cfg.ts_api_key)
ADMIN_TOKEN = cfg.env.get("ADMIN_TOKEN", "")  # neu dat -> bat buoc header Authorization: Bearer <token>


def _authorized(request):
    if not ADMIN_TOKEN:
        return True
    auth = request.headers.get("authorization", "")
    return auth == f"Bearer {ADMIN_TOKEN}"


def _guard(request):
    if not _authorized(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return None


async def health(request):
    return JSONResponse({"ok": True})


def _parse_related(d):
    """Doc quan he tu related_json (string) -> list gon."""
    try:
        rel = json.loads(d.get("related_json") or "[]")
    except (ValueError, TypeError):
        return []
    return [{
        "relation": r.get("relation"),
        "law_id": r.get("law_id"),
        "document_code": r.get("document_code"),
        "document_type": r.get("document_type"),
        "name": r.get("name"),
        "validity_status": r.get("validity_status"),
        "url": r.get("url"),
    } for r in rel]


def _to_result(hit):
    """Chuyen 1 hit Typesense -> ArticleResult (khop openapi SearchResponse)."""
    d = hit["document"]
    out = {
        "rerank_score": hit.get("rerank_score"),
        "text_match": hit.get("text_match"),
        "vector_distance": hit.get("vector_distance"),
        "id": d.get("id"),
        "parent_id": d.get("parent_id") or d.get("id"),
        "part_no": d.get("part_no"),
        "n_parts": d.get("n_parts", 1),
        "law_id": d.get("law_id"),
        "citation": d.get("citation"),
        "article_no": d.get("article_no"),
        "article_heading": d.get("article_heading"),
        "document_code": d.get("document_code"),
        "document_type": d.get("document_type"),
        "document_title": d.get("document_title"),
        "validity_status": d.get("validity_status"),
        "is_effective_now": d.get("is_effective_now"),
        "context_path": d.get("context_path"),
        "source_url": d.get("source_url"),
        "full_content": d.get("full_content") or d.get("content"),
        "related": _parse_related(d),
    }
    return out


async def search_articles(request):
    """POST /v1/search — tim dieu luat lien quan (hybrid + rollup + rerank). Read-only, khong can token."""
    try:
        b = await request.json()
    except (ValueError, json.JSONDecodeError):
        return JSONResponse({"error": "body phai la JSON hop le"}, status_code=400)
    query = (b.get("query") or "").strip()
    if not query:
        return JSONResponse({"error": "thieu truong 'query'"}, status_code=400)

    top_k = max(1, min(int(b.get("top_k", 10)), 100))
    document_type = (b.get("document_type") or "").strip()
    effective_only = bool(b.get("effective_only", True))
    use_rerank = bool(b.get("use_rerank", True))

    def _run():
        return search(
            cfg, ts, query, mode="hybrid", k=top_k,
            alpha=cfg.search_alpha, effective_only=effective_only,
            candidates=min(250, max(100, top_k * 3)),
            rerank=cfg.rerank_enable and use_rerank, rerank_pool=max(30, top_k),
        )

    try:
        results = await run_in_threadpool(_run)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": f"Loi tim kiem: {e}"}, status_code=502)

    if document_type:
        dt = document_type.lower()
        results = [h for h in results if (h["document"].get("document_type") or "").lower() == dt]

    hits = [_to_result(h) for h in results]
    return JSONResponse({
        "query": query,
        "collection": cfg.collection,
        "model": cfg.embed_model,
        "dim": cfg.embed_dim,
        "count": len(hits),
        "results": hits,
    })


async def upsert(request):
    if (r := _guard(request)):
        return r
    body = await request.json()
    return JSONResponse(await run_in_threadpool(crud.upsert, body))


async def patch_status(request):
    if (r := _guard(request)):
        return r
    b = await request.json()
    res = await run_in_threadpool(
        lambda: crud.patch_status(law_id=b.get("law_id"), chunk_id=b.get("chunk_id"),
                                  validity_status=b.get("validity_status"),
                                  effective_date=b.get("effective_date"),
                                  expiration_date=b.get("expiration_date")))
    return JSONResponse(res)


async def get_article(request):
    r = await run_in_threadpool(crud.get, request.path_params["chunk_id"])
    return JSONResponse(r, status_code=200) if r else JSONResponse({"error": "not found"}, status_code=404)


async def delete_article(request):
    if (r := _guard(request)):
        return r
    return JSONResponse(await run_in_threadpool(lambda: crud.delete(chunk_id=request.path_params["chunk_id"])))


async def delete_law(request):
    if (r := _guard(request)):
        return r
    return JSONResponse(await run_in_threadpool(lambda: crud.delete(law_id=request.path_params["law_id"])))


app = Starlette(routes=[
    Route("/health", health),
    Route("/v1/search", search_articles, methods=["POST"]),
    Route("/search", search_articles, methods=["POST"]),  # alias
    Route("/articles", upsert, methods=["POST"]),
    Route("/articles/status", patch_status, methods=["PATCH"]),
    Route("/articles/{chunk_id}", get_article, methods=["GET"]),
    Route("/articles/{chunk_id}", delete_article, methods=["DELETE"]),
    Route("/laws/{law_id}", delete_law, methods=["DELETE"]),
])


def main():
    import uvicorn
    uvicorn.run(app, host=cfg.env.get("ADMIN_HOST", "0.0.0.0"), port=int(cfg.env.get("ADMIN_PORT", "8010")))


if __name__ == "__main__":
    main()
