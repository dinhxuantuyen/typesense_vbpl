# PTYC — TASK-016 (phần chunking): Tách Điều từ main-stream + dựng bản ghi

## Mục tiêu
Từ `mainstream_docs.jsonl` (4.371 VB nguyên văn) → tách thành **bản ghi cấp Điều** theo thiết
kế đã chốt (Cách 1 rollup, parent_id, content thô, embed_text tên-điều-trước, quan hệ từ edges),
xuất `chunks.jsonl` sẵn sàng embed (Phase 2 bước sau).

## Phạm vi
- Trong: tách Điều/Chương/Mục từ `content` thô; sub-chunk Điều dài; gắn metadata + hiệu lực + quan hệ; xuất chunks.jsonl.
- Ngoài: embed, index Typesense, MCP (bước sau).

## Quy tắc tách
- Marker Điều: dòng bắt đầu `Điều <số>[chữ]. ...` (vd "Điều 26a."). Số có thể kèm hậu tố chữ.
- Marker Chương/Mục: dòng `Chương ...` / `Mục ...` → cập nhật context cho các Điều sau.
- Phần trước "Điều 1" = preamble (Căn cứ, tiêu đề) → bỏ khỏi chunk (đã có metadata riêng).
- Điều dài > `SUBCHUNK_CHAR_THRESHOLD` (4000) → sub-chunk theo Khoản; **content = phần thô của part** (không header) để **gộp lại = Điều đầy đủ** (Cách 1).

## Bản ghi (đã chốt)
id/parent_id/part_no/n_parts · law_id · document_code/type/title/agency/fields · date/effective/expiration (+ts) ·
validity_status/is_effective_now/is_mainstream · chapter/section/context_path · article_no/num/heading/citation/source_url ·
content(thô) · heading_ascii/body_ascii · embed_text(tên điều trước) · rel_guided_by_ids/rel_guides_ids/rel_consolidated_ids · related[] · is_low_value/is_repealed.

## Ánh xạ quan hệ (từ edges.jsonl, anchor trên NĐ)
- edge `huong_dan` (VB hướng dẫn NĐ) → `rel_guided_by_ids`
- edge `duoc_huong_dan` (VB NĐ hướng dẫn) → `rel_guides_ids`
- edge `hop_nhat` (VBHN) → `rel_consolidated_ids`
- (Neighbor không phải backbone → quan hệ rỗng ở v1.)

## Tiêu chí chấp nhận
- [ ] Tách đúng số Điều (đối chiếu vài VB bằng tay).
- [ ] content các part gộp lại = nội dung Điều gốc (Cách 1).
- [ ] embed_text bắt đầu bằng tên điều; content không chứa header.
- [ ] NĐ backbone có quan hệ đúng; is_effective_now đúng.
- [ ] Báo cáo: #VB, #điều, #chunk (sau sub-chunk), phân bố độ dài.
