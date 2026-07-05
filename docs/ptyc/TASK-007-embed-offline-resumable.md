# PTYC — TASK-007: Pipeline embed offline resumable + giảm chiều + import + snapshot

## Mục tiêu
Embed ~365k document (từ 253.862 điều) một cách **chịu lỗi, resumable, có concurrency**, tạo file
import-ready, nạp vào Typesense, sẵn sàng snapshot để bake vào image.

## Phạm vi
- Phase A: `embed_offline` — stream JSONL → build docs → embed concurrent (truncate 1024d) → ghi `embedded.jsonl` + checkpoint.
- Phase B: `import_embedded` — nạp `embedded.jsonl` vào Typesense theo batch (không gọi proxy).
- Ngoài phạm vi: snapshot/dockerfile (TASK-009).

## Yêu cầu chức năng
1. Stream file 2.9GB (không load hết vào RAM); build docs theo window để giới hạn bộ nhớ.
2. Embed concurrent bằng ThreadPool (N workers cấu hình), batch theo `EMBED_BATCH_SIZE`.
3. **Resumable**: ghi `done.txt` (id đã xong) + append `embedded.jsonl`; chạy lại bỏ qua id đã embed.
4. Cắt chiều 2560→`EMBED_DIM` (1024) + normalize (đã có ở proxy).
5. Chịu lỗi proxy: retry/backoff; batch lỗi → fallback từng item; item lỗi vẫn ghi log, không dừng cả job.
6. Tiến độ: log số đã xong / tổng, tốc độ, ETA.
7. Phase B: tạo collection (num_dim=1024) + import upsert theo batch lớn (vd 2.000/lần), báo cáo ok/lỗi.

## Yêu cầu phi chức năng
- Bộ nhớ ổn định (window-based), không phình theo kích thước file.
- Ghi đĩa an toàn (flush + append) để mất điện/gián đoạn vẫn resume được.
- Idempotent ở cả 2 phase.

## Tiêu chí chấp nhận
- [ ] Chạy được trên toàn bộ 253.862 điều, sinh ~365k dòng `embedded.jsonl`.
- [ ] Ngắt giữa chừng rồi chạy lại → tiếp tục từ chỗ dừng, không embed lại phần đã xong.
- [ ] Import xong: `num_documents` trong Typesense ≈ số dòng embedded.
- [ ] Mỗi vector đúng 1024 chiều.

## Ghi chú kỹ thuật
- ThreadPool + urllib (blocking, nhả GIL khi I/O) → concurrency thật.
- Kích thước window ~2.000 docs; workers khởi đầu 8, đo throughput rồi tăng.
- `embedded.jsonl` chính là file import cho Typesense (không lặp công).
