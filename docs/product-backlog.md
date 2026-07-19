# Product Backlog — Tìm kiếm ngữ nghĩa văn bản pháp luật (Typesense)

> Mục tiêu tổng thể: Dựng hệ thống cho phép người dùng nhập **câu hỏi ngôn ngữ tự nhiên**
> và trả về các **Điều/Khoản** trong văn bản pháp luật liên quan nhất, dùng **Typesense**
> (hybrid search: keyword + vector) với embedding **Qwen3-Embedding-4B** (2560 chiều)
> qua proxy `https://proxy.cyberbot.vn/v1`.

## Ràng buộc & quyết định đã chốt
- Chạy Typesense bằng **Docker trong WSL2 Ubuntu-24.04** (Docker Windows chưa cài).
- Embedding tính **phía client** (script gọi proxy), đẩy `float[]` vào Typesense — không dùng auto-embedding của Typesense.
- Model embedding: `Qwen3-Embedding-4B` = **2560 chiều** (model 8B `Qwen/Qwen3-Embedding-8B` hiện lỗi phía proxy). Model + số chiều để **cấu hình được** trong `.env`.
- Dữ liệu đầu vào: **JSON đã parse chi tiết theo Điều** (người dùng cung cấp).

## Danh sách Task

| ID | Tên task | Mô tả | Trạng thái | Ngày tạo |
|----|----------|-------|-----------|----------|
| TASK-001 | Dựng Typesense server (WSL/Docker) + kiểm tra kết nối | Chạy Typesense (native binary do DNS docker lỗi IPv4), cấu hình API key, healthcheck, script start/stop/health | Done | 2026-07-04 |
| TASK-002 | Pipeline embedding + ingest JSON điều luật | Client embedding qua proxy (Qwen3-Embedding-4B, 2560d), tạo collection schema, nạp JSON điều luật (chunk theo Điều/Khoản) vào Typesense | Done | 2026-07-04 |
| TASK-003 | Tìm kiếm hybrid: câu hỏi → điều luật liên quan | Nhận câu hỏi tự nhiên, embed câu hỏi, hybrid search (keyword + vector), trả về Điều/Khoản kèm trích dẫn nguồn | Done | 2026-07-04 |
| TASK-004 | Tầng rerank (Qwen3-Reranker-4B) — Phase 2 | Hybrid lấy top-N thô → cross-encoder rerank → top-K tinh; giảm nhiễu keyword từ Điều boilerplate đồ sộ | Done | 2026-07-04 |
| TASK-005 | Chuẩn hóa keyword nâng cao + xử lý Điều boilerplate | Down-weight/loại các Điều "Điều khoản thi hành"/"Tổ chức thực hiện" đồ sộ khỏi nhánh keyword | Todo | 2026-07-04 |

## Epic 2 — Sản phẩm hóa: Docker all-in-one + MCP server

> Kế hoạch chi tiết: [docs/ptyc/ke-hoach-dong-goi-mcp.md](ptyc/ke-hoach-dong-goi-mcp.md).
> Chốt kiến trúc: 1 image all-in-one · MCP HTTP/SSE · 100k–1M điều (giảm chiều 1024d) · chỉ MCP.

| ID | Tên task | Mô tả | Trạng thái | Ngày tạo |
|----|----------|-------|-----------|----------|
| TASK-006 | Nhận & validate dữ liệu thật | 253.862 điều (JSONL 2.9GB), schema khớp mẫu, ~365k document sau sub-chunk. Đã thống kê xong. | Done | 2026-07-04 |
| TASK-007 | Pipeline embed offline resumable + giảm chiều + snapshot | Embed toàn bộ có checkpoint, truncate MRL 2560→1024 + normalize, import vào Typesense, tạo snapshot /data | In Progress | 2026-07-04 |
| TASK-008 | MCP server HTTP/SSE (FastMCP) | Tools search_legal_articles / get_legal_article / collection_stats, output có trích dẫn + source_url | Done | 2026-07-04 |
| TASK-009 | Đóng gói Docker | **CHỐT: chuyển sang mô hình slim image + import** (bake 16GB vào image gặp chuỗi sự cố: WSL crash I/O, GHCR layer 10GB, braft snapshot, segfault khi nhận HTTP lúc load, ulimit nofile — tất cả đã chẩn đoán & fix trong entrypoint/scripts). Image `legal-mcp:slim` (1GB) build + test OK. | Done | 2026-07-04 |
| TASK-010 | Đóng gói phân phối | **XONG**: push `ghcr.io/dinhxuantuyen/legal-mcp:slim`; nén `data/embedded.jsonl.gz` (2.9GB) để chuyển server; DEPLOY.md 4 bước (deploy → chuyển data → import → snapshot) — cả 4 bước đã test end-to-end local. | Done | 2026-07-04 |
| TASK-012 | Tạo bộ benchmark 1000 mẫu | Hoàn tất: 1000/1000 câu hỏi (DeepSeek-V4-Flash, 0 lỗi, 30% không dấu) → data/benchmark/benchmark.jsonl. Câu hỏi đời thường, không lặp tiêu đề. | Done | 2026-07-04 |
| TASK-011 | Kiểm thử E2E + eval dữ liệu thật | Đo Recall/MRR trên dữ liệu thật (dùng benchmark TASK-012), A/B chiều vector & α, tối ưu | Todo | 2026-07-04 |
| TASK-013 | Dựng Typesense Dashboard (GUI quản trị) | Container `bfritscher/typesense-dashboard` chạy port 8888 (HTTP 200), kết nối server 8108. Xem/sửa/xóa document, chạy search. Sẽ đóng gói vào image sau. | Done | 2026-07-05 |
| TASK-014 | API CRUD cập nhật dữ liệu | Module + CLI + REST admin (Starlette): upsert (re-embed, xử lý sub-chunk), patch hiệu lực (không re-embed), delete theo chunk_id/law_id, get. Đã test round-trip CLI + HTTP OK. | Done | 2026-07-05 |

## Epic 3 — Main-stream Nghị định + đồ thị quan hệ (dữ liệu vbpl v260710, 105.975 VB)

> Nguồn: `E:\vbpl\thuvienphapluat-v260710.jsonl` (cấp Văn bản, quan hệ trong `documentDiagrams`).
> Quy tắc chốt: NĐ còn hiệu lực tính đến 19/7/2026 + tương lai · quan hệ hướng dẫn / được hướng dẫn / hợp nhất (2 chiều, dedup VBHN mới hơn) · mục tiêu cả đồ thị + search (embed ở phase sau).

| ID | Tên task | Mô tả | Trạng thái | Ngày tạo |
|----|----------|-------|-----------|----------|
| TASK-015 | Trích main-stream NĐ + đồ thị quan hệ (Phase 1) | XONG: 2.067 NĐ backbone + 4.094 edges (hướng dẫn/được hướng dẫn/hợp nhất, dedup 267 VBHN) + 4.371 văn bản main-stream (full nội dung). data/mainstream/. | Done | 2026-07-19 |
| TASK-016 | Chunk + embed main-stream + search quan hệ (Phase 2) | Tách chunk (126.254 điều), embed 8B/4096d, index `legal_mainstream`, search API (rollup parent_id, gộp full điều, doc-code routing). MCP: sửa field cho collection mới + thêm tool `get_related_documents`. OpenAPI spec. | In Progress | 2026-07-19 |

## Epic 4 — Đóng gói & triển khai main-stream lên production

> Bản cũ (`legal_articles`, 1024d) đang chạy production. Cần image slim mới (code main-stream + MCP đã sửa),
> quy trình deploy chi tiết, và thao tác **clear corpus cũ** để chuyển sang `legal_mainstream` (4096d).

| ID | Tên task | Mô tả | Trạng thái | Ngày tạo |
|----|----------|-------|-----------|----------|
| TASK-017 | Đóng gói image slim main-stream + triển khai + clear corpus cũ | Build image slim mới (default `legal_mainstream`/8B/4096, MCP đã sửa), viết DEPLOY.md quy trình migrate từ bản production cũ (drop collection `legal_articles`), import `embedded_chunks.jsonl` (126k điều, 4096d), snapshot. | Analyzing | 2026-07-19 |
