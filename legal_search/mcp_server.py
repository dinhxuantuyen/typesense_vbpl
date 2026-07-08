"""MCP server (streamable HTTP) tra cuu van ban phap luat cho AI Agent.

Tools:
  - search_legal_articles: tim cac Dieu luat lien quan tu cau hoi (hybrid + rerank), co trich dan.
  - get_legal_article: lay toan van 1 Dieu theo chunk_id (ghep cac part neu bi sub-chunk).
  - collection_stats: thong tin collection.

Chay (WSL):
  ~/legal-venv/bin/python -m legal_search.mcp_server
"""
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .config import Config
from .search import search
from .typesense_api import Typesense

cfg = Config()
ts = Typesense(cfg.ts_base, cfg.ts_api_key)

mcp = FastMCP(
    "legal-search",
    host=cfg.mcp_host,          # mac dinh 0.0.0.0 (env MCP_HOST)
    port=cfg.mcp_port,
    # Cho phep Agent goi bang IP/domain (khong chi localhost) — tat DNS-rebinding check.
    # Chi expose port MCP trong mang tin cay/noi bo.
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


def _to_result(hit: dict) -> dict:
    d = hit["document"]
    return {
        "chunk_id": d.get("chunk_id"),
        "citation": d.get("citation"),
        "article_no": d.get("article_no"),
        "article_heading": d.get("article_heading"),
        "document_title": d.get("document_title"),
        "document_code": d.get("document_code"),
        "document_type": d.get("document_type"),
        "validity_status": d.get("validity_status"),
        "context_path": d.get("context_path"),
        "snippet": (d.get("content") or "").replace("\n", " ")[:400],
        "source_url": d.get("source_url"),
        "score": round(hit.get("rerank_score", 0.0), 4) if "rerank_score" in hit
                 else (round(1 - hit["vector_distance"], 4) if hit.get("vector_distance") is not None else None),
    }


@mcp.tool()
def search_legal_articles(
    query: str,
    top_k: int = 10,
    document_type: str = "",
    effective_only: bool = True,
    use_rerank: bool = True,
) -> list[dict]:
    """Tim cac Dieu luat lien quan nhat toi cau hoi ngon ngu tu nhien (tieng Viet).

    Dung cho: hoi dap phap luat, tra cuu quy dinh, tim can cu phap ly.
    - query: cau hoi hoac tu khoa (co dau hoac khong dau deu duoc).
    - top_k: so Dieu tra ve (mac dinh 10 — khuyen nghi giu 10 de dat recall tot nhat).
    - document_type: loc theo loai VB (vd 'Luat', 'Nghi dinh', 'Thong tu'); de trong = tat ca.
    - effective_only: chi tra Dieu thuoc VB con hieu luc (mac dinh True).
    - use_rerank: True (mac dinh) = chinh xac hon (+0.5-1s); False = nhanh hon, giam do chinh xac.
      (Chi co tac dung khi server bat RERANK_ENABLE.)

    Tra ve list Dieu, moi Dieu co: citation, article_heading, document_code/type,
    validity_status, snippet noi dung, source_url (de tra nguoc van ban goc), score.
    LUU Y: khi tra loi nguoi dung PHAI trich dan citation + source_url.
    """
    try:
        k = max(1, min(top_k, 100))
        results = search(
            cfg, ts, query, mode="hybrid", k=k,
            alpha=cfg.search_alpha, effective_only=effective_only,
            candidates=min(250, max(100, k * 3)),
            rerank=cfg.rerank_enable and use_rerank, rerank_pool=max(30, k),
        )
    except Exception as e:  # noqa: BLE001
        return [{"error": f"Loi tim kiem: {e}"}]

    hits = results
    if document_type:
        dt = document_type.strip().lower()
        hits = [h for h in hits if (h["document"].get("document_type") or "").lower() == dt]
    return [_to_result(h) for h in hits]


@mcp.tool()
def get_legal_article(chunk_id: str) -> dict:
    """Lay toan van 1 Dieu luat theo chunk_id (vd '12076-dieu-25').

    Neu Dieu bi tach nhieu part (Dieu dai), ham se ghep lai theo thu tu.
    Tra ve: toan van content + metadata (citation, VB, hieu luc, source_url).
    """
    try:
        res = ts.search(cfg.collection, {
            "q": "*", "query_by": "body_ascii",
            "filter_by": f"chunk_id:=`{chunk_id}`",
            "per_page": 250, "exclude_fields": "embedding",
        })
    except Exception as e:  # noqa: BLE001
        return {"error": f"Loi truy van: {e}"}

    hits = res.get("hits", [])
    if not hits:
        return {"error": f"Khong tim thay chunk_id={chunk_id}"}
    docs = sorted((h["document"] for h in hits), key=lambda d: d.get("part_no", 0))
    full = "\n".join(d.get("content", "") for d in docs)
    m = docs[0]
    return {
        "chunk_id": chunk_id,
        "citation": m.get("citation"),
        "article_heading": m.get("article_heading"),
        "document_title": m.get("document_title"),
        "document_code": m.get("document_code"),
        "document_type": m.get("document_type"),
        "validity_status": m.get("validity_status"),
        "context_path": m.get("context_path"),
        "content": full,
        "n_parts": m.get("n_parts", 1),
        "source_url": m.get("source_url"),
    }


@mcp.tool()
def collection_stats() -> dict:
    """Thong tin collection: so document, ten, so chieu vector, model embedding."""
    try:
        info = ts.get_json(f"/collections/{cfg.collection}")
        return {
            "collection": cfg.collection,
            "num_documents": info.get("num_documents"),
            "embed_model": cfg.embed_model,
            "embed_dim": cfg.embed_dim,
            "rerank_enabled": cfg.rerank_enable,
        }
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
