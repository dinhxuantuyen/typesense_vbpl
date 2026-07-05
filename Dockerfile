# All-in-one image: Typesense (index baked) + MCP server tra cuu phap luat.
# LUU Y: build can DNS docker hoat dong (pull base + apt + pip). Xem README muc "DNS".
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Lib runtime toi thieu: curl (healthcheck/entrypoint), ca-certificates (HTTPS goi proxy)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (MCP SDK, uvicorn)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Typesense binary
COPY bin/typesense-server /usr/local/bin/typesense-server
RUN chmod +x /usr/local/bin/typesense-server

# Ma nguon + entrypoint
COPY legal_search/ /app/legal_search/
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Index da build san (rocksdb data dir) — bake vao image
COPY data/build/ts-data/ /data/

# Cau hinh mac dinh (KHONG chua secret). EMBED_API_KEY phai truyen luc `docker run -e ...`.
ENV TYPESENSE_HOST=localhost \
    TYPESENSE_PORT=8108 \
    TYPESENSE_COLLECTION=legal_articles \
    TYPESENSE_API_KEY=poc_legal_search_2026 \
    EMBED_BASE_URL=https://proxy.cyberbot.vn/v1 \
    EMBED_MODEL=Qwen3-Embedding-4B \
    EMBED_DIM=1024 \
    EMBED_BATCH_SIZE=16 \
    RERANK_MODEL=Qwen/Qwen3-Reranker-4B \
    RERANK_ENABLE=true \
    SEARCH_ALPHA=0.7 \
    SUBCHUNK_CHAR_THRESHOLD=4000 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD curl -sf http://localhost:8108/health >/dev/null && curl -s http://localhost:8000/mcp >/dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
