# Chiến lược Embedding & Search — Tìm kiếm văn bản pháp luật

> Phân tích dựa trên dữ liệu thật: `thuvienphapluat-chunks-sample-100.json` (100 Điều).
> Phục vụ TASK-002 (ingest/embedding) và TASK-003 (search).

## 1. Đặc điểm dữ liệu thật (số liệu đo được)

| Chỉ số | Giá trị | Hệ quả |
|---|---|---|
| Số chunk | 100 (mỗi chunk = 1 Điều) | Đơn vị index tự nhiên = **Điều** |
| Độ dài `content` (ký tự) | p50=698 · p90=3.559 · p95=5.007 · **max=147.159** | Đa số ngắn (~200 token); **đuôi dài cực lớn** |
| Ước lượng token (chars/3.5) | p90≈1.017 · **max≈42.045** | 1 Điều vượt cả context 32k của Qwen3 → phải **sub-chunk** |
| Chunk > 8.000 ký tự | 4 | Đều là "Điều khoản thi hành"/"Tổ chức thực hiện" (phụ lục dài) |
| Chunk > 4.000 ký tự | 8 | Ngưỡng sub-chunk hợp lý ~4.000–6.000 ký tự |
| `context` (chương/mục) có dữ liệu | 68/100 | Dùng làm ngữ cảnh embedding khi có |
| `article_heading` null | 1 | Cần xử lý null |
| `validity_status` | 96 "Còn hiệu lực" + 4 có mốc ngày | Lọc hiệu lực dùng `effective_date`/`expiration_date`, KHÔNG parse chuỗi hiển thị |
| Chunk rác | có (vd `"Điều 29 [43] (được bãi bỏ)"` = 26 ký tự) | Cần cờ `is_repealed`/low-value |
| `document_type` | Luật, Nghị định, Thông tư, Quyết định, VB hợp nhất, Nghị quyết, Lệnh | Facet lọc theo thứ bậc VB |
| `citation` | luôn có | Dùng làm nhãn trích dẫn trả về |

**Nhận định cốt lõi:** dữ liệu **lệch nặng** — 90% Điều gọn (1 vector là đủ), nhưng một số ít Điều dài tới 42k token sẽ phá vỡ chất lượng nếu nhồi vào 1 vector. Chiến lược phải xử lý riêng đuôi dài.

## 2. Chiến lược EMBEDDING

### 2.1. Đơn vị embedding: parent–child theo ngưỡng
- **Điều ngắn/vừa (≤ ~4.000 ký tự, ~90%)**: embed nguyên Điều → **1 vector/Điều**.
- **Điều dài (> ngưỡng)**: tách **child sub-chunk** theo Khoản (`1.`, `2.`, `a)`, `b)`) hoặc theo đoạn, mỗi child ~512–1.024 token, overlap nhỏ. Mỗi child có vector riêng, **chung metadata + citation** với Điều cha.
- Khi search: truy hồi ở mức child → **rollup về Điều cha** (lấy điểm cao nhất) để trả kết quả là "Điều" + đánh dấu khoản khớp.

### 2.2. Văn bản đưa vào embedding (enrichment) — QUAN TRỌNG
Không embed `content` trần. Nhiều Điều bị "mồ côi ngữ cảnh" (vô số "Điều 2. ...có hiệu lực thi hành" gần trùng nhau giữa các VB). Ghép **header ngữ cảnh gọn** trước nội dung:

```
<document_title ngắn> — <chương/mục nếu có> — <article_heading>
<content>
```
Với child sub-chunk: **lặp lại header** ở đầu mỗi child để vector không mất định danh.

### 2.3. Bất đối xứng query/document (đặc thù Qwen3-Embedding)
Qwen3-Embedding là instruction-tuned, khuyến nghị **thêm instruction ở phía QUERY**, document để trần:
- **Document (Điều)**: embed enriched text như trên, không instruction.
- **Query (câu hỏi)**: bọc instruction, ví dụ:
  `Instruct: Cho câu hỏi pháp lý tiếng Việt, tìm các điều luật liên quan nhất.\nQuery: <câu hỏi>`
- → Cần **kiểm chứng thực nghiệm** (bật/tắt instruction) trong bước eval; nhưng đây là mặc định khuyến nghị.

### 2.4. Chuẩn hóa & khoảng cách
- L2-normalize vector; Typesense vector field dùng **cosine**.
- `Qwen3-Embedding-4B` = **2560 chiều** (đọc từ `.env`, đổi model chỉ sửa config).

### 2.5. Chunk rác / bãi bỏ
- Điều "(được bãi bỏ)"/nội dung < ~40 ký tự: gắn cờ `is_repealed=true` hoặc `low_value=true`; vẫn index nhưng **loại khỏi search mặc định** (có thể bật lại qua filter).

## 3. Chiến lược SEARCH

### 3.1. Hybrid = keyword (BM25) + vector — mặc định
- **Keyword** (`query_by`, ưu tiên: `article_heading` > `content` > `citation` > `document_title`): bắt thuật ngữ pháp lý chính xác, số hiệu VB ("100/2019/NĐ-CP"), số điều.
- **Vector**: bắt câu hỏi diễn đạt dân dã ↔ ngôn ngữ hành chính.
- Typesense **rank fusion**; tinh chỉnh `alpha` (trọng số vector/keyword). Câu hỏi dân dã → tăng trọng vector.

### 3.2. Lọc (filter) — bắt buộc cho pháp luật
- **Hiệu lực**: mặc định lọc Điều thuộc VB còn hiệu lực tại thời điểm hỏi (dùng `effective_date`/`expiration_date` đã chuẩn hóa; cờ `is_effective_now`).
- **Loại VB / lĩnh vực** (`document_type`, `fields`): facet thu hẹp.
- (Tùy chọn) ưu tiên thứ bậc: Luật > Nghị định > Thông tư khi trùng chủ đề.

### 3.3. Tầng RERANK (đề xuất — chất lượng cao)
Proxy có `Qwen/Qwen3-Reranker-4B`:
- Hybrid lấy **top-N thô** (vd N=50) → **cross-encoder rerank** → **top-K tinh** (vd K=5).
- Cross-encoder đọc đồng thời (câu hỏi, điều) nên chính xác hơn hẳn bi-encoder cho QA pháp luật.
- Triển khai ở **Phase 2** sau khi hybrid chạy; cần xác minh định dạng API rerank của proxy.

### 3.4. Rollup & trích dẫn
- Gom child theo Điều cha, lấy điểm cao nhất, trả về: **citation + số hiệu VB + điều + (khoản khớp) + đoạn trích + điểm số**.
- Luôn kèm `source_url` để tra ngược văn bản gốc.

### 3.5. Đánh giá (eval) — để chọn cấu hình bằng số liệu
- Bộ `eval_questions.json`: câu hỏi → `chunk_id` kỳ vọng.
- Đo **Recall@5, MRR** cho: keyword-only / vector-only / hybrid / hybrid+rerank, và bật/tắt query-instruction.
- Chọn cấu hình theo số đo, không theo cảm tính.

## 4. Lưu ý MỞ RỘNG QUY MÔ (khi lên toàn bộ thuvienphapluat)
- 2560 chiều × 4 byte = **~10KB/vector**. 1 triệu Điều (+sub-chunk) ⇒ **~15–20GB RAM chỉ riêng vector** (Typesense in-memory).
- Giải pháp: **cắt chiều Matryoshka (MRL)** của Qwen3 xuống 1024/768 (giảm ~60% RAM, mất chất lượng ít) hoặc sharding. PoC giữ 2560, ghi nhận cho giai đoạn scale.

## 4b. KẾT QUẢ EVAL THỰC TẾ (14 câu hỏi, 100 chunk mẫu)

Đo trên bộ `data/eval_questions.json` (gồm câu không dấu + diễn đạt dân dã):

| Mode | R@1 | R@3 | R@5 | MRR |
|---|---|---|---|---|
| keyword (không dấu) | 0.36 | 0.36 | 0.36 | 0.357 |
| **vector** | **1.00** | 1.00 | 1.00 | **1.000** |
| hybrid α=0.5 | 0.36 | 1.00 | 1.00 | 0.679 |
| **hybrid α=0.7** | **1.00** | **1.00** | **1.00** | **1.000** |

**Bài học rút ra (đã áp dụng vào code):**
1. **Dấu tiếng Việt phá keyword** → đã thêm trường không dấu `heading_ascii`/`body_ascii` + fold câu hỏi. Keyword giờ bất biến với dấu.
2. **Embedding Qwen3-4B rất mạnh** cho ngữ nghĩa pháp luật tiếng Việt (vector-only đã đạt 1.0 trên tập này).
3. **Fusion α=0.5 để keyword nhiễu kéo tụt R@1** → chọn **α=0.7 mặc định** (vector dẫn, keyword hỗ trợ). Hybrid phục hồi về 1.0.
4. **Điều boilerplate đồ sộ** ("Điều khoản thi hành"/"Tổ chức thực hiện", vd Điều 147k ký tự → 39 subchunk) là **nam châm hút nhiễu keyword** → TASK-005 (down-weight) + TASK-004 (rerank) sẽ xử lý triệt để.

> Lưu ý: tập 14 câu còn nhỏ; cần mở rộng bộ eval khi có dữ liệu thật đầy đủ để kết luận chắc hơn.

## 5. Mặc định đề xuất (để bắt đầu code)
| Hạng mục | Mặc định |
|---|---|
| Đơn vị index | Điều; sub-chunk khi > 4.000 ký tự |
| Embedding text | Enriched header + content |
| Query instruction | Bật (kiểm chứng bằng eval) |
| Model / dim | Qwen3-Embedding-4B / 2560 |
| Search | Hybrid (keyword+vector), lọc hiệu lực mặc định |
| Rerank | Phase 2 (Qwen3-Reranker-4B) |
| Trích dẫn | citation + source_url bắt buộc |
