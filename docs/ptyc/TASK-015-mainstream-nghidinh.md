# PTYC — TASK-015: Trích main-stream Nghị định + đồ thị quan hệ (Phase 1)

## Mục tiêu
Từ 105.975 văn bản (E:\vbpl), trích **xương sống là Nghị định còn hiệu lực (gồm cả sẽ có hiệu
lực trong tương lai)** và **đồ thị quan hệ** quanh chúng (hướng dẫn / được hướng dẫn / hợp nhất),
xuất tập văn bản main-stream (giữ nội dung) làm đầu vào cho Phase 2 (chunk+embed).

## Phạm vi
- Trong: lọc backbone, trích quan hệ 3 loại, gom tập VB main-stream, xuất nodes/edges.
- Ngoài (Phase 2): chunk, embed, index Typesense, MCP tra quan hệ.

## Quy tắc nghiệp vụ (đã chốt)
1. **Backbone** = record có `documentType == "Nghị định"` AND **còn hiệu lực tại 19/7/2026 hoặc sẽ có hiệu lực tương lai**:
   - Loại nếu `validityStatus` chứa: "Hết hiệu lực", "Không còn phù hợp", "Không xác định", "Chưa xác định", "Ngưng hiệu lực".
   - Loại nếu `expirationDate` < 2026-07-19.
   - Giữ: "Còn hiệu lực", "Còn hiệu lực đến <ngày ≥ hôm nay>", "Có hiệu lực từ <tương lai>".
2. **Quan hệ** (từ `documentDiagrams[].relatedDocumentType`), chỉ giữ:
   - "Văn bản hướng dẫn" → `huong_dan`
   - "Văn bản được hướng dẫn" → `duoc_huong_dan`
   - "Văn bản hợp nhất" → `hop_nhat`
   - "Văn bản được hợp nhất" → `duoc_hop_nhat`
3. **Dedup hợp nhất**: nếu 1 NĐ có ≥2 VBHN (quan hệ hợp nhất) cùng nội dung → **giữ VBHN mới hơn** (theo `dateIssued`).
4. **Tập main-stream** = { backbone NĐ } ∪ { văn bản đích của các quan hệ trên, nếu có trong corpus }.

## Yêu cầu chức năng
- Stream 19GB (không load hết RAM). 2 pass:
  - Pass 1: xác định backbone + tập lawId hàng xóm + dựng edges (đã dedup VBHN).
  - Pass 2: trích **full record** cho lawId ∈ (backbone ∪ hàng xóm) → `mainstream_docs.jsonl` (giữ content cho Phase 2).
- Xuất:
  - `nodes_backbone.jsonl` (NĐ backbone: lawId, code, title, type, validity, dates, url).
  - `edges.jsonl` (`{source_law_id, source_code, relation, target_law_id, target_code, target_type, target_validity, target_date}`).
  - `mainstream_docs.jsonl` (full VB thuộc main-stream).
- Báo cáo thống kê: #NĐ backbone, #edges theo loại, #hàng xóm theo documentType, #VBHN bị dedup, #hàng xóm không có trong corpus.

## Yêu cầu phi chức năng
- Idempotent; chịu record lỗi (skip + log).
- Ngày tham chiếu cấu hình được (mặc định 2026-07-19).

## Tiêu chí chấp nhận
- [ ] `nodes_backbone.jsonl`: toàn NĐ, đều thỏa quy tắc hiệu lực (kiểm tra mẫu).
- [ ] `edges.jsonl`: chỉ 4 loại quan hệ trên; VBHN đã dedup theo mới hơn.
- [ ] `mainstream_docs.jsonl`: chứa backbone + hàng xóm có trong corpus, không trùng lawId.
- [ ] Báo cáo số liệu khớp (tổng edges, phân bố loại VB hàng xóm).

## Ghi chú kỹ thuật
- `effectiveDate`/`expirationDate` dạng ISO `YYYY-MM-DDT..` → parse phần ngày.
- `documents[]` trong diagram đã đủ metadata (id=lawId, documentCode, documentType, validityStatus, dateIssued, url) → dựng edge không cần tra ngược, nhưng full content lấy ở Pass 2.
