# PTYC — TASK-012: Tạo bộ benchmark 1000 mẫu

## Mục tiêu
Có bộ benchmark 1000 mẫu `(câu hỏi tự nhiên → chunk_id kỳ vọng)` từ dữ liệu thật, để đo
Recall@k/MRR khách quan cho hệ tìm kiếm (TASK-011).

## Phạm vi
- Lấy mẫu 1000 Điều đại diện; sinh câu hỏi bằng LLM qua proxy; lưu benchmark.jsonl.
- Ngoài phạm vi: chạy đo benchmark (thuộc TASK-011, sau khi index full sẵn sàng).

## Yêu cầu chức năng
1. **Lấy mẫu stratified** 1000 Điều từ 253.862:
   - Loại bỏ Điều low-value/boilerplate (heading kiểu "Điều khoản thi hành", "Hiệu lực thi hành", "Tổ chức thực hiện"; content < 200 ký tự; "(được bãi bỏ)").
   - Đa dạng theo `document_type` (Luật, Nghị định, Thông tư, Quyết định, VBHN...).
   - Ưu tiên content thực chất (200–4000 ký tự) để câu hỏi có căn cứ rõ.
2. **Sinh câu hỏi** bằng LLM (proxy chat): mỗi Điều → 1 câu hỏi tiếng Việt tự nhiên như người dân/luật sư hỏi, mà Điều đó trả lời được. Đa dạng văn phong; một phần không dấu.
3. **Lưu** `data/benchmark/benchmark.jsonl`: `{question, expected_chunk_id, citation, document_type, article_heading}`.
4. **Resumable** + concurrency **thấp** (2–4) để không nghẽn job embed đang chạy; retry/backoff.

## Yêu cầu phi chức năng
- Không làm hỏng job embed (ưu tiên embed). Nếu gây lỗi proxy → giảm concurrency.
- Câu hỏi chất lượng: tự nhiên, cụ thể đủ để phân biệt, không lộ nguyên văn heading.

## Tiêu chí chấp nhận
- [ ] Sinh đủ 1000 mẫu hợp lệ (question không rỗng, chunk_id tồn tại trong dữ liệu).
- [ ] Phân bố document_type đa dạng (không dồn 1 loại).
- [ ] Không có Điều boilerplate/low-value trong bộ mẫu.
- [ ] Kiểm tra thủ công ~10 mẫu: câu hỏi hợp lý, đúng Điều.

## Ghi chú kỹ thuật
- Model sinh: chọn 1 model chat mạnh tiếng Việt trên proxy (vd Qwen3-32B/235B).
- Prompt: cho heading + trích content (giới hạn ~1500 ký tự) → yêu cầu 1 câu hỏi, chỉ trả câu hỏi.
- Sinh 1 phần câu hỏi **không dấu** để test khả năng chịu thiếu dấu.
