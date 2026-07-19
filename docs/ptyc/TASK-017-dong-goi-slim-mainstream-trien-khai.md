# PTYC — TASK-017: Đóng gói image slim main-stream + triển khai + clear corpus cũ

## Mục tiêu
Đóng gói **image slim mới** (services-only, không kèm dữ liệu) mang code main-stream + MCP đã sửa,
kèm tài liệu triển khai chi tiết để **migrate từ bản production cũ** (`legal_articles`, 1024d)
sang corpus mới `legal_mainstream` (126.254 điều, 4096d, embed Qwen3-Embedding-8B), bao gồm
thao tác **xóa (clear) corpus cũ** để giải phóng RAM/disk.

## Phạm vi
- **Trong phạm vi:**
  - Sửa `legal_search/mcp_server.py` cho khớp schema `legal_mainstream` (dùng `id`/`parent_id`,
    bỏ `chunk_id` không tồn tại; trả `full_content`, quan hệ) + thêm tool `get_related_documents`.
  - Cập nhật `Dockerfile.slim` ENV mặc định: collection `legal_mainstream`, model 8B, dim 4096.
  - Cập nhật `docker-compose.deploy.yml` (tag image mới, mem_limit).
  - Viết lại `DEPLOY.md`: quy trình deploy + **migrate/clear corpus cũ** + import + snapshot + verify.
  - Build image slim mới, tag `ghcr.io/dinhxuantuyen/legal-mcp:mainstream`.
- **Ngoài phạm vi:** chạy re-embed lại (đã có `embedded_chunks.jsonl`); thay đổi thuật toán search;
  full corpus 106k VB.

## Yêu cầu chức năng
1. Image slim chạy được Typesense + MCP với collection `legal_mainstream` mà **không sửa env** thủ công.
2. MCP tool `search_legal_articles` trả đúng field điều (id=parent_id để get tiếp, citation, quan hệ, score).
3. MCP tool `get_legal_article(article_id)` ghép full điều theo `parent_id`.
4. MCP tool `get_related_documents(law_id, relation?)` trả các VB liên quan (hướng dẫn/được hướng dẫn/hợp nhất).
5. DEPLOY.md có bước clear collection cũ `legal_articles` (và/hoặc wipe volume) an toàn, có thể rollback.
6. Import `embedded_chunks.jsonl` KHÔNG cần gọi proxy embedding (vector đã có sẵn).

## Yêu cầu phi chức năng
- Image slim ≤ ~1GB (không bake 12GB dữ liệu).
- Import thuần localhost, không phụ thuộc proxy → không tốn tài nguyên proxy.
- RAM production ≥ 6GB (126k × 4096d float ≈ 2GB vector + nội dung + overhead).
- Không lộ secret trong image (EMBED_API_KEY truyền lúc run).

## Tiêu chí chấp nhận (Acceptance Criteria)
- [ ] `docker build -f Dockerfile.slim` thành công; `docker run` lên MCP, `collection_stats()` trả
      `collection=legal_mainstream, embed_dim=4096`.
- [ ] `search_legal_articles("Mức đóng thuế hộ kinh doanh năm 2026")` trả list điều có `id`
      (dạng `<law>-dieu-<n>`), `citation`, `related`, `score` — không có field None do sai tên.
- [ ] `get_legal_article("<parent_id>")` trả full điều nhiều part ghép đúng thứ tự.
- [ ] `get_related_documents(<law_id>)` trả đúng quan hệ từ `related_json`.
- [ ] DEPLOY.md mô tả rõ: deploy image mới → **drop `legal_articles`** (hoặc wipe volume) → chuyển
      `embedded_chunks.jsonl.gz` → import_mainstream `--recreate` → snapshot → verify → xóa file import.
- [ ] Có phương án rollback (giữ volume/collection cũ tới khi verify xong).

## Ghi chú kỹ thuật
- Schema `legal_mainstream` (import_mainstream.py): `id` có `#pN` cho điều nhiều part; `parent_id` = id điều gốc;
  quan hệ ở `related_json` (string JSON) + `rel_guides_ids/rel_guided_by_ids/rel_consolidated_ids` (int64[]).
- `n_parts`/`content`/`source_url`... là store-only (index:false) → không filter được, chỉ trả về.
- `get_legal_article` filter theo `parent_id:=` (đúng cho cả điều 1 part vì parent_id==id-gốc).
- `get_related_documents`: gom `related_json` qua các chunk của `law_id`, dedup theo (relation, law_id).
- Migration: đổi tên collection + đổi dim ⇒ không chia sẻ config với bản cũ; clear = drop collection
  `legal_articles` hoặc `docker volume rm` (reset sạch). Import không cần proxy.
- Tag image: `ghcr.io/dinhxuantuyen/legal-mcp:mainstream` (giữ `:slim` cũ để rollback).
