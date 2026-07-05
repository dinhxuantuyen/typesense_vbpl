# Hướng dẫn triển khai lên server

Mô hình: **image slim (services-only, ~1GB)** + **import dữ liệu đã embed** vào volume sau khi deploy.
Không nhồi dữ liệu vào image → push/pull nhanh, cập nhật dữ liệu không cần rebuild image.

```
┌────────────────────────── SERVER ──────────────────────────┐
│  container legal-mcp (ghcr.io/dinhxuantuyen/legal-mcp:slim) │
│    ├─ Typesense 29.0  (dữ liệu ở volume /data)              │
│    └─ MCP server HTTP/SSE  :8000/mcp  ← AI Agent kết nối    │
│         └─ embed câu hỏi + rerank → proxy (EMBED_API_KEY)   │
└─────────────────────────────────────────────────────────────┘
```

## Chuẩn bị
- Server có Docker, ≥ 8GB RAM (Typesense giữ index trong RAM), ≥ 40GB disk.
- File dữ liệu `embedded.jsonl.gz` (~3-4GB — 378k điều đã có sẵn vector 1024d,
  KHÔNG cần gọi proxy embedding khi import).
- Key proxy (`EMBED_API_KEY`) — chỉ dùng lúc chạy để embed **câu hỏi** + rerank.

## Bước 1 — Deploy services
```bash
docker pull ghcr.io/dinhxuantuyen/legal-mcp:slim

docker run -d --name legal-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  -v legal-data:/data \
  -v /opt/legal/import:/import \
  --ulimit nofile=65535:65535 \
  -e TYPESENSE_API_KEY='DOI_KEY_MANH_KHI_PRODUCTION' \
  -e EMBED_API_KEY='sk-xxxx' \
  ghcr.io/dinhxuantuyen/legal-mcp:slim

# Cho den khi log bao "MCP server" (voi /data trong thi chi ~10s):
docker logs -f legal-mcp
```

## Bước 2 — Chuyển dữ liệu lên server (1 lần)
```bash
# tu may local:
scp embedded.jsonl.gz user@server:/opt/legal/import/
# tren server:
gunzip /opt/legal/import/embedded.jsonl.gz     # -> /opt/legal/import/embedded.jsonl (~11GB)
```

## Bước 3 — Import vào Typesense (~30-45 phút, thuần localhost)
```bash
docker exec legal-mcp python -m legal_search.import_embedded \
  --input /import/embedded.jsonl --recreate --batch 2000

# Ket qua mong doi:  DONE: ok=378308 fail=0 ... num_documents=378206
```

## Bước 4 — Chốt snapshot (bắt buộc — để restart nhanh & an toàn)
```bash
docker exec legal-mcp bash -c \
  'curl -s -X POST "http://localhost:8108/operations/snapshot?snapshot_path=/data/backup" \
   -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"'
# -> {"success":true}
# Sau do co the xoa file import: rm /opt/legal/import/embedded.jsonl
```

## Kiểm tra
```bash
# So document:
docker exec legal-mcp bash -c \
  'curl -s http://localhost:8108/collections/legal_articles -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"' \
  | grep -o '"num_documents":[0-9]*'

# MCP tools (tu may khac):
# endpoint: http://<server>:8000/mcp  (streamable HTTP)
```

## Tích hợp AI Agent
```json
{ "mcpServers": { "legal-search": { "url": "http://<server>:8000/mcp" } } }
```
Tools: `search_legal_articles(query, top_k, document_type, effective_only)`,
`get_legal_article(chunk_id)`, `collection_stats()`.

## Cập nhật dữ liệu về sau (không đụng image)
```bash
# Them/sua dieu (tu dong re-embed qua proxy):
docker exec legal-mcp python -m legal_search.crud upsert --file /import/dieu_moi.json
# Doi hieu luc (KHONG re-embed):
docker exec legal-mcp python -m legal_search.crud patch-status --law-id 12076 --status "Het hieu luc" --expiration 2026-01-01
# Xoa:
docker exec legal-mcp python -m legal_search.crud delete --law-id 12076
```
Hoặc chạy REST admin API (cổng 8010, tách khỏi MCP): `docker exec -d legal-mcp python -m legal_search.admin_api`
(đặt `ADMIN_TOKEN` để bảo vệ; chỉ expose 8010 trong mạng nội bộ).

## Biến môi trường chính
| Biến | Mặc định | Ghi chú |
|---|---|---|
| `EMBED_API_KEY` | *(trống)* | **BẮT BUỘC** — key proxy, truyền lúc run |
| `TYPESENSE_API_KEY` | poc_legal_search_2026 | **NÊN ĐỔI** khi production |
| `EMBED_MODEL` / `EMBED_DIM` | Qwen3-Embedding-4B / 1024 | đổi model phải re-embed toàn bộ |
| `RERANK_ENABLE` | true | tắt nếu muốn giảm latency (~0.5s/truy vấn) |
| `SEARCH_ALPHA` | 0.7 | trọng số vector trong hybrid |
| `MCP_PORT` | 8000 | cổng MCP |

## Lưu ý vận hành
- **RAM**: 378k document @1024d ≈ 4-6GB khi load. Đặt limit container ≥ 8GB.
- **`--ulimit nofile=65535`**: bắt buộc — raft log nhiều file segment.
- **Load lại khi restart**: container restart sẽ load snapshot (vài phút với index lớn);
  healthcheck chỉ check MCP nên trạng thái `healthy` = sẵn sàng phục vụ.
- **Backup**: snapshot ngoài đã nằm ở `/data/backup` (bước 4); hoặc backup volume `legal-data`.
- **Benchmark/eval**: bộ 1000 câu hỏi ở `data/benchmark/benchmark.jsonl` — chạy
  `python -m legal_search.eval --questions data/benchmark/benchmark.jsonl` để đo Recall/MRR.
