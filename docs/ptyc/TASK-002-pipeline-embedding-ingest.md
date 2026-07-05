# PTYC — TASK-002: Pipeline embedding + ingest JSON điều luật

## Mục tiêu
Nạp dữ liệu văn bản pháp luật (JSON đã parse theo Điều) vào Typesense, mỗi Điều/Khoản là một
document có: text để keyword search + vector 2560 chiều để semantic search.

## Phạm vi
- Trong phạm vi: định nghĩa schema collection; script embedding client gọi proxy; script ingest đọc JSON → embed → upsert vào Typesense theo batch.
- Ngoài phạm vi: parse PDF/Word (dữ liệu đã được parse sẵn); tối ưu re-ranking nâng cao.

## Định dạng JSON đầu vào (đề xuất — người dùng cung cấp/điều chỉnh)
Mỗi phần tử là một **Điều** (hoặc một mảng các Điều). Trường tối thiểu:
```json
{
  "doc_id": "100/2019/ND-CP",
  "doc_title": "Nghị định 100/2019/NĐ-CP về xử phạt vi phạm hành chính lĩnh vực giao thông",
  "doc_type": "Nghị định",
  "issued_date": "2019-12-30",
  "effective_date": "2020-01-01",
  "status": "Còn hiệu lực",
  "chapter": "Chương II",
  "article_no": "6",
  "article_title": "Xử phạt người điều khiển xe mô tô, xe gắn máy...",
  "article_text": "Toàn văn nội dung Điều 6, bao gồm các khoản, điểm...",
  "clauses": [
    { "clause_no": "1", "clause_text": "Phạt tiền từ 100.000 đồng đến 200.000 đồng..." }
  ]
}
```
> Nếu JSON thực tế của bạn khác cấu trúc, script ingest sẽ có lớp **mapping cấu hình được**
> để ánh xạ tên trường thực tế → tên trường chuẩn ở trên (không phải sửa code lõi).

## Yêu cầu chức năng
1. Tạo collection Typesense với schema: các field metadata (facet/filter) + `article_text`/`clause_text` (index keyword) + `embedding` (`float[]`, `num_dim` = giá trị trong `.env`).
2. Client embedding: hàm `embed(texts: list) -> list[vector]` gọi proxy `Qwen3-Embedding-4B`, có retry + batch + xử lý lỗi proxy.
3. Chọn đơn vị index: mặc định index theo **Điều** (`article_text`); nếu Điều quá dài (> ngưỡng cấu hình) thì fallback tách theo **Khoản**.
4. Ingest theo batch (kích thước cấu hình), in tiến độ, chịu lỗi phần tử lẻ (skip + log).
5. Idempotent: chạy lại không tạo trùng (upsert theo `id` ổn định = `doc_id:article_no[:clause_no]`).

## Yêu cầu phi chức năng
- Retry/backoff khi proxy lỗi (đã quan sát proxy chập chờn).
- Số chiều vector đọc từ `.env` (`EMBED_DIM`, `EMBED_MODEL`) — đổi model chỉ sửa config.
- Ghi log số document thành công/thất bại.

## Tiêu chí chấp nhận (Acceptance Criteria)
- [ ] Tạo collection thành công với `num_dim` khớp model (2560).
- [ ] Chạy ingest trên file JSON mẫu → số document trong collection = số Điều/Khoản kỳ vọng.
- [ ] Mỗi document có vector đúng 2560 chiều (kiểm tra 1 document bất kỳ).
- [ ] Chạy ingest lần 2 không làm tăng số document (idempotent).
- [ ] Lỗi 1 phần tử không làm dừng toàn bộ tiến trình.

## Ghi chú kỹ thuật
- Ngôn ngữ: Python (dễ thao tác JSON + gọi HTTP), chạy trong WSL hoặc Windows đều được.
- Client Typesense: gọi REST trực tiếp hoặc `typesense` python client.
- Batch embedding để giảm số round-trip tới proxy; giới hạn kích thước input mỗi call.
- Chuẩn hóa text tiếng Việt tối thiểu (trim, gộp khoảng trắng) trước khi embed.
