# PTYC — TASK-014: API CRUD cập nhật dữ liệu

## Mục tiêu
Cho phép cập nhật kho điều luật khi thông tin thay đổi (VB mới, sửa nội dung, sửa đổi/bãi bỏ)
mà không cần rebuild toàn bộ — qua module Python + CLI + REST admin API.

## Phạm vi
- CRUD ở cấp **Điều** (theo `chunk_id`) và cấp **Văn bản** (theo `law_id`).
- Ngoài phạm vi: UI (đã có Dashboard); crawl/diff nguồn dữ liệu.

## Yêu cầu chức năng
1. **Upsert (Create/Update)** một hoặc nhiều Điều từ JSON nguồn (đúng schema mẫu):
   - Chunk + enrichment + embed (proxy) + upsert theo `chunk_id`.
   - **Xử lý sub-chunk khi nội dung đổi**: xóa hết part cũ của `chunk_id` trước, rồi ghi part mới (tránh part mồ côi khi số part giảm).
2. **Patch hiệu lực (metadata-only, KHÔNG re-embed)**: đổi `validity_status`/`effective_date`/`expiration_date` → tự tính lại `is_effective_now`. Cập nhật theo `law_id` (tất cả điều của VB) hoặc `chunk_id`. Dùng update-by-query của Typesense.
3. **Delete**: theo `chunk_id` (1 điều, mọi part) hoặc `law_id` (cả VB). Dùng delete-by-query.
4. **Get**: 1 điều theo `chunk_id` (ghép part).
5. Giao diện: (a) hàm Python tái sử dụng, (b) CLI, (c) REST admin API (Starlette).

## Yêu cầu phi chức năng
- Idempotent; upsert an toàn khi chạy lại.
- REST admin **tách khỏi MCP tìm kiếm** (MCP cho Agent giữ read-only; CRUD là admin).
- Chịu lỗi proxy khi embed (retry — dùng lại `proxy.embed`).

## Tiêu chí chấp nhận
- [ ] Round-trip: upsert 1 điều test → get thấy đúng → patch hiệu lực đổi đúng `is_effective_now` → delete → get trả "không thấy".
- [ ] Upsert điều dài (sub-chunk) rồi upsert lại bản ngắn hơn → không còn part mồ côi.
- [ ] Patch theo `law_id` cập nhật đúng số điều (num_updated) mà không đổi vector.
- [ ] Delete theo `law_id` xóa đúng toàn bộ điều của VB.

## Ghi chú kỹ thuật
- Typesense: update-by-query `PATCH /collections/{c}/documents?filter_by=...`; delete-by-query `DELETE .../documents?filter_by=...`.
- Tái sử dụng `chunking.build_documents`, `proxy.embed`.
- REST: Starlette + uvicorn (đã có sẵn deps). Cổng cấu hình `ADMIN_PORT` (mặc định 8010).
