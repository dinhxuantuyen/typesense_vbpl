# PTYC — TASK-003: Tìm kiếm hybrid (câu hỏi → điều luật liên quan)

## Mục tiêu
Nhận câu hỏi ngôn ngữ tự nhiên của người dùng, trả về danh sách **Điều/Khoản** pháp luật liên
quan nhất, có trích dẫn nguồn (số hiệu VB, điều, khoản), kết hợp keyword + vector (hybrid).

## Phạm vi
- Trong phạm vi: hàm/CLI nhận câu hỏi → embed → hybrid search Typesense → trả top-K kèm citation; lọc theo metadata (loại VB, hiệu lực) tùy chọn.
- Ngoài phạm vi: sinh câu trả lời bằng LLM (RAG) — giai đoạn sau; UI web — giai đoạn sau.

## Yêu cầu chức năng
1. Nhận câu hỏi (CLI arg hoặc stdin).
2. Embed câu hỏi bằng cùng model `Qwen3-Embedding-4B` (đảm bảo cùng không gian vector với index).
3. Thực hiện **hybrid search** Typesense: `query_by=article_text,article_title` + `vector_query=embedding:([...], k)`.
4. Trả về top-K (cấu hình, mặc định 5) gồm: số hiệu VB, điều, khoản, tiêu đề, đoạn trích, điểm số (text match + vector distance).
5. Hỗ trợ filter tùy chọn: `doc_type`, `status` (chỉ VB còn hiệu lực), `issued_date` range.
6. So sánh nhanh 3 chế độ (keyword-only / vector-only / hybrid) để đánh giá — cờ dòng lệnh.

## Yêu cầu phi chức năng
- Thời gian phản hồi 1 truy vấn (không tính embed) < 200ms với kho PoC.
- Kết quả **luôn kèm trích dẫn** đủ để người dùng tra ngược văn bản gốc.
- Xử lý lỗi proxy khi embed câu hỏi (retry, thông báo rõ).

## Tiêu chí chấp nhận (Acceptance Criteria)
- [ ] Với bộ 15–30 câu hỏi thử, đo được **hit-rate top-5** (điều đúng nằm trong top-5) cho từng chế độ.
- [ ] Hybrid cho hit-rate ≥ max(keyword-only, vector-only) trên tập thử.
- [ ] Câu hỏi diễn đạt dân dã (không trùng từ khóa luật) vẫn tìm ra điều đúng nhờ nhánh vector.
- [ ] Mỗi kết quả in đủ: số hiệu VB + điều + (khoản) + đoạn trích.
- [ ] Filter `status = "Còn hiệu lực"` hoạt động đúng.

## Ghi chú kỹ thuật
- Dùng Typesense multi_search/hybrid: kết hợp `query_by` (keyword, rank_fusion) với `vector_query`.
- Có thể tinh chỉnh trọng số bằng `alpha` (rank fusion) nếu cần.
- Đánh giá: chuẩn bị file `eval_questions.json` gồm câu hỏi + điều kỳ vọng để tính hit-rate lặp lại được.
- Lưu ý: câu hỏi nên thêm tiền tố hướng dẫn nếu model embedding yêu cầu (một số model Qwen embedding dùng "query:"/"passage:" prompt) — kiểm chứng khi tích hợp.
