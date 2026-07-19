# Hướng dẫn triển khai — corpus main-stream (`legal_mainstream`)

Mô hình: **image slim (services-only, ~1GB)** + **import dữ liệu đã embed** vào volume sau khi deploy.
Không nhồi dữ liệu vào image → push/pull nhanh, đổi dữ liệu không cần rebuild.

```
┌───────────────────────────── SERVER ─────────────────────────────┐
│  container legal-mcp (ghcr.io/dinhxuantuyen/legal-mcp:mainstream) │
│    ├─ Typesense 29.0   (collection legal_mainstream, ở /data)     │
│    └─ MCP server HTTP   :8000/mcp   ← AI Agent kết nối            │
│         └─ embed câu hỏi + rerank → proxy (EMBED_API_KEY)         │
└───────────────────────────────────────────────────────────────────┘
```

| Thông số | Giá trị |
|---|---|
| Collection | `legal_mainstream` |
| Số điều (document) | **126.254** |
| Vector | Qwen3-Embedding-8B — **4096 chiều** |
| Rerank | Qwen3-Reranker-4B (`/v1/rerank`) |
| File dữ liệu | `embedded_chunks.jsonl` (~12GB, gzip ~3–4GB) — **đã có sẵn vector, import KHÔNG gọi proxy** |
| Image | `ghcr.io/dinhxuantuyen/legal-mcp:mainstream` |

---

## Chuẩn bị
- Server có Docker, **≥ 8GB RAM** (126k × 4096d ≈ 2GB vector + nội dung/index → ~4–6GB khi load), ≥ 40GB disk.
- File `embedded_chunks.jsonl.gz` (nén từ `data/mainstream/embed/embedded_chunks.jsonl`).
- Key proxy (`EMBED_API_KEY`) — chỉ dùng lúc chạy để embed **câu hỏi** + rerank (import không cần).

Nén file trên máy local trước khi chuyển:
```bash
gzip -k -1 data/mainstream/embed/embedded_chunks.jsonl   # -> embedded_chunks.jsonl.gz (~3-4GB)
```

---

## KỊCH BẢN A — Migrate bản production đang chạy (thay corpus cũ `legal_articles` → `legal_mainstream`)

> Bản cũ đang chạy container `legal-mcp` image `:slim` (collection `legal_articles`, 1024d).
> Corpus mới đổi cả **tên collection** lẫn **số chiều** ⇒ không dùng chung config. Cần **clear corpus cũ**.
> Quy trình dưới đây **giữ volume cũ tới khi verify xong** (rollback được).

### A1. Kéo image mới, cập nhật compose
```bash
cd /opt/legal
docker pull ghcr.io/dinhxuantuyen/legal-mcp:mainstream
# sua image tag trong docker-compose.deploy.yml -> :mainstream  (hoac dung ban moi tu repo)
```

### A2. Thay container sang image mới (giữ nguyên volume dữ liệu cũ)
```bash
EMBED_API_KEY='sk-xxxx' TYPESENSE_API_KEY='KEY_MANH' \
  docker compose -f docker-compose.deploy.yml up -d
# Container mới load snapshot cũ (legal_articles) — cho tới khi log bao san sang:
docker logs -f legal-mcp        # cho toi dong "Typesense san sang" / "MCP server"
```

### A3. ✦ CLEAR CORPUS CŨ — xóa collection `legal_articles` (giải phóng RAM/disk)
```bash
docker exec legal-mcp bash -c \
  'curl -s -X DELETE "http://localhost:8108/collections/legal_articles" \
   -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"' | head -c 200; echo
# -> tra ve JSON mo ta collection vua xoa. RAM cua index cu duoc giai phong.

# (tuy chon) kiem tra chi con cac collection mong muon:
docker exec legal-mcp bash -c \
  'curl -s "http://localhost:8108/collections" -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"' \
  | grep -o '"name":"[^"]*"'
```
> **Reset sạch thay vì drop từng collection** (nếu muốn bỏ hẳn mọi dữ liệu + snapshot cũ):
> ```bash
> docker compose -f docker-compose.deploy.yml down
> docker volume ls | grep legal-data          # tim ten volume, vd legal_legal-data
> docker volume rm legal_legal-data            # XOA TAT CA du lieu cu (khong rollback duoc)
> EMBED_API_KEY=... TYPESENSE_API_KEY=... docker compose -f docker-compose.deploy.yml up -d
> ```

### A4. Chuyển + giải nén dữ liệu mới
```bash
# tu may local:
scp embedded_chunks.jsonl.gz user@server:/opt/legal/import/
# tren server:
gunzip /opt/legal/import/embedded_chunks.jsonl.gz    # -> /import/embedded_chunks.jsonl (~12GB)
```

### A5. Import vào Typesense (~15–30 phút, thuần localhost, KHÔNG gọi proxy)
```bash
docker exec legal-mcp python -m legal_search.import_mainstream \
  --input /import/embedded_chunks.jsonl \
  --collection legal_mainstream --recreate --batch 1000
# Ket qua mong doi:  DONE: ok=... fail=0 ...  Collection 'legal_mainstream' num_documents=126254
```
> `--recreate` tự drop + tạo lại `legal_mainstream` (an toàn nếu chạy lại). Trùng `id` (điều nhiều part)
> được gộp → `num_documents` (~126.254) có thể nhỏ hơn số dòng file.

### A6. Chốt snapshot (bắt buộc — restart nhanh & an toàn)
```bash
docker exec legal-mcp bash -c \
  'curl -s -X POST "http://localhost:8108/operations/snapshot?snapshot_path=/data/backup" \
   -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"'
# -> {"success":true}
rm /opt/legal/import/embedded_chunks.jsonl        # don file import sau khi xong
```

### A7. Verify
```bash
# so document + tra cuu thu qua MCP-side search (dung ham search truc tiep):
docker exec legal-mcp python -m legal_search.search "Mức đóng thuế hộ kinh doanh năm 2026" --k 3 --rerank
# -> tra ve 3 Dieu, co citation + score cao.
```
> **Rollback**: nếu chạy theo cách drop collection (không wipe volume) và cần quay lại,
> chỉ cần import lại dữ liệu cũ; snapshot mới ở `/data/backup` đã là của corpus mới. Muốn an toàn tuyệt đối,
> backup volume `legal-data` trước khi A3.

---

## KỊCH BẢN B — Deploy mới hoàn toàn (server trắng)

**Cách khuyến nghị — docker compose (kèm Dashboard):**
```bash
mkdir -p /opt/legal/import && cd /opt/legal
# tai docker-compose.deploy.yml tu repo ve day, roi:
TYPESENSE_API_KEY='KEY_MANH' EMBED_API_KEY='sk-xxxx' \
  docker compose -f docker-compose.deploy.yml up -d
docker logs -f legal-mcp        # cho toi khi san sang
```
Sau đó làm **A4 → A5 → A6 → A7**.

**Chỉ services (docker run, không dashboard):**
```bash
docker pull ghcr.io/dinhxuantuyen/legal-mcp:mainstream
docker run -d --name legal-mcp --restart unless-stopped \
  -p 8000:8000 -p 8108:8108 \
  -v legal-data:/data -v /opt/legal/import:/import \
  --ulimit nofile=65535:65535 \
  -e TYPESENSE_API_KEY='KEY_MANH' -e EMBED_API_KEY='sk-xxxx' \
  ghcr.io/dinhxuantuyen/legal-mcp:mainstream
```
> Endpoint MCP: `http://<server>:8000/mcp`. Dashboard (compose): `http://<server>:8888`
> (Host=`<server>`, Port=8108, Protocol=http, API key = `TYPESENSE_API_KEY`).
> Cổng 8108 + 8888 **chỉ mở trong mạng nội bộ/VPN**, không public internet.

---

## Tích hợp AI Agent (MCP)
```json
{ "mcpServers": { "legal-search": { "url": "http://<server>:8000/mcp" } } }
```
Tools:
| Tool | Tham số | Trả về |
|---|---|---|
| `search_legal_articles` | `query, top_k(≤100), document_type, effective_only, use_rerank` | list Điều: `id` (dùng cho get), citation, article_heading, document_code/type, validity_status, snippet, source_url, **related** (quan hệ), score |
| `get_legal_article` | `article_id` (= `id` từ search, vd `713724-dieu-25`) | toàn văn Điều (ghép part) + metadata + related |
| `get_related_documents` | `law_id, relation?` (`huong_dan`/`duoc_huong_dan`/`hop_nhat`) | các VB liên quan (document_code, name, validity_status, url) |
| `collection_stats` | — | num_documents, embed_model, embed_dim, rerank_enabled |

> Đặc tả REST đầy đủ: [docs/openapi.yaml](docs/openapi.yaml).

---

## Cập nhật dữ liệu về sau (không đụng image)
```bash
# Doi hieu luc 1 VB (KHONG re-embed):
docker exec legal-mcp python -m legal_search.crud patch-status --law-id 12076 \
  --status "Het hieu luc" --expiration 2026-01-01
# Xoa 1 VB:
docker exec legal-mcp python -m legal_search.crud delete --law-id 12076
```
REST admin API (cổng 8010, tách khỏi MCP): `docker exec -d legal-mcp python -m legal_search.admin_api`
(đặt `ADMIN_TOKEN` để bảo vệ; chỉ expose 8010 trong mạng nội bộ).

---

## Biến môi trường chính
| Biến | Mặc định (image mới) | Ghi chú |
|---|---|---|
| `EMBED_API_KEY` | *(trống)* | **BẮT BUỘC** — key proxy, truyền lúc run |
| `TYPESENSE_API_KEY` | poc_legal_search_2026 | **NÊN ĐỔI** khi production |
| `TYPESENSE_COLLECTION` | legal_mainstream | tên collection |
| `EMBED_MODEL` / `EMBED_DIM` | Qwen/Qwen3-Embedding-8B / 4096 | đổi model/chiều phải re-embed toàn bộ |
| `RERANK_ENABLE` | true | tắt nếu muốn giảm latency (~0.5–0.8s/truy vấn) |
| `SEARCH_ALPHA` | 0.7 | trọng số vector trong hybrid |
| `MCP_PORT` | 8000 | cổng MCP |

## Lưu ý vận hành
- **RAM**: 126k document @4096d ≈ 4–6GB khi load. Đặt limit container ≥ 8GB (compose để `mem_limit: 10g`).
- **`--ulimit nofile=65535`**: bắt buộc — raft log nhiều file segment.
- **Restart**: container load snapshot `/data` (vài phút với index lớn); healthcheck chỉ check MCP nên
  trạng thái `healthy` = sẵn sàng phục vụ.
- **Backup**: snapshot ngoài ở `/data/backup` (bước A6); hoặc backup volume `legal-data`.
