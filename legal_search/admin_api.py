"""TASK-014: REST admin API cho CRUD dieu luat (Starlette).

Tach RIENG khoi MCP tim kiem (MCP cho Agent = read-only). API nay danh cho admin cap nhat du lieu.

Chay (WSL):
  ~/legal-venv/bin/python -m legal_search.admin_api
Endpoints:
  GET    /health
  POST   /articles            body: record hoac list record -> upsert (re-embed)
  PATCH  /articles/status      body: {law_id|chunk_id, validity_status?, effective_date?, expiration_date?}
  GET    /articles/{chunk_id}
  DELETE /articles/{chunk_id}
  DELETE /laws/{law_id}
"""
import os

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.routing import Route

from .config import Config
from .crud import LegalCRUD

cfg = Config()
crud = LegalCRUD(cfg)
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
