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
| TASK-009 | Dockerfile all-in-one + Phase B import | DNS đã fix; image build OK, container healthy, 3 MCP tool chạy trong container (5k doc). Chỉ chờ embed full để build image thật. | Done | 2026-07-04 |
| TASK-010 | Đóng gói phân phối | Scripts finalize_image.sh + save_image.sh + tài liệu tích hợp (README) + danh mục ENV/secret. Chờ image build. | In Progress | 2026-07-04 |
| TASK-012 | Tạo bộ benchmark 1000 mẫu | B1 chọn mẫu 1000 (offline) → seed.jsonl: XONG. B2 sinh câu hỏi bằng LLM **DeepSeek-V4-Flash** (gen_benchmark.py) chờ chạy sau khi embed xong (proxy rảnh). | In Progress | 2026-07-04 |
| TASK-011 | Kiểm thử E2E + eval dữ liệu thật | Đo Recall/MRR trên dữ liệu thật (dùng benchmark TASK-012), A/B chiều vector & α, tối ưu | Todo | 2026-07-04 |
| TASK-013 | Dựng Typesense Dashboard (GUI quản trị) | Container `bfritscher/typesense-dashboard` chạy port 8888 (HTTP 200), kết nối server 8108. Xem/sửa/xóa document, chạy search. Sẽ đóng gói vào image sau. | Done | 2026-07-05 |
| TASK-014 | API CRUD cập nhật dữ liệu | Module + CLI + REST admin (Starlette): upsert (re-embed, xử lý sub-chunk), patch hiệu lực (không re-embed), delete theo chunk_id/law_id, get. Đã test round-trip CLI + HTTP OK. | Done | 2026-07-05 |
