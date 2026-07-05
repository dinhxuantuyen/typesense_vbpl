# Kế hoạch: Đóng gói Docker all-in-one + MCP server tra cứu pháp luật

> Master plan cho Phase 2 (sản phẩm hóa). Chi tiết từng task sẽ có PTYC riêng trước khi code.

## 1. Mục tiêu
Giao một **Docker image all-in-one** chứa sẵn **dữ liệu thật đã index**, phục vụ tra cứu điều
luật qua **MCP server (HTTP/SSE)** để tích hợp vào hệ thống AI Agent của khách hàng. `docker run`
là chạy được, Agent kết nối MCP qua URL.

## 2. Quyết định kiến trúc đã chốt
| Hạng mục | Lựa chọn |
|---|---|
| Đóng gói | 1 image duy nhất (Typesense + index baked + MCP), entrypoint đa tiến trình |
| MCP transport | HTTP/SSE (streamable HTTP), remote |
| Quy mô | 100k–1M điều → **giảm chiều Matryoshka** (mặc định 1024d) để tiết kiệm RAM/dung lượng |
| Giao diện | Chỉ MCP (không REST) |
| Embedding | Qwen3-Embedding-4B (đổi 8B qua config khi proxy healthy); truncate MRL 2560→1024 |
| Rerank | Qwen3-Reranker-4B trong search path (bật/tắt qua config) |

## 3. Kiến trúc hệ thống
```
                 BUILD TIME (offline, 1 lần)                 RUN TIME (trong container)
  data thật JSON ─► ingest+embed (proxy) ─► Typesense ─► snapshot /data ─┐
                                                                          │ COPY vào image
  ┌───────────────────────── Docker image all-in-one ────────────────────▼─────────┐
  │  entrypoint: (1) typesense-server --data-dir /data  (index đã có sẵn)           │
  │              (2) đợi /health OK                                                  │
  │              (3) MCP server (HTTP/SSE)  ──tools──► search_legal / get_article    │
  │                        │ embed câu hỏi + rerank ─► proxy Qwen3 (runtime, env)    │
  └────────────────────────┼────────────────────────────────────────────────────────┘
                           ▲ MCP HTTP/SSE (cổng vd 8000)
                  Hệ thống AI Agent của bạn
```
- **Build time**: nhúng toàn bộ dữ liệu (embed 1 lần) → snapshot data dir Typesense → bake vào image.
- **Run time**: chỉ embed *câu hỏi* + rerank (gọi proxy) → cần proxy URL/key qua biến môi trường lúc `docker run` (KHÔNG bake secret).

## 4. Đóng gói all-in-one (multi-stage Dockerfile)
- **Stage builder**: base có Typesense binary + Python; chạy `ingest` nạp dữ liệu thật (embed qua proxy), tạo `/data` (rocksdb). Hỗ trợ **resumable** (checkpoint vector đã embed) vì 100k–1M điều tốn nhiều lần gọi proxy.
- **Stage final**: `FROM` base gọn (debian-slim) + copy `typesense-server` + copy `/data` đã build + copy `legal_search` + MCP server + Python runtime tối thiểu.
- **Entrypoint**: script bash (hoặc `tini` + supervisor nhẹ) → chạy typesense nền, chờ health, chạy MCP; trap SIGTERM để tắt sạch cả 2 tiến trình.
- **HEALTHCHECK**: kiểm tra cả Typesense `/health` lẫn cổng MCP.

## 5. Pipeline build index (mở rộng TASK-002)
- **Tách embedding khỏi build image**: chạy `embed_offline` sinh file vector (jsonl/npy) có **checkpoint** (bỏ qua chunk đã embed) → chịu được gián đoạn, chạy lại không mất công.
- **Giảm chiều Matryoshka**: truncate vector 2560→`EMBED_DIM` (mặc định 1024) + re-normalize. Kiểm chứng chất lượng 1024 vs 2560 bằng eval trước khi chốt.
- **Import vào Typesense** từ vector đã tính (không gọi proxy) → tạo snapshot `/data`.
- **Kiểm soát rate-limit/lỗi proxy**: batch + concurrency giới hạn + retry/backoff; log số thành công/lỗi.

## 6. MCP server (HTTP/SSE)
- Dùng **MCP Python SDK (FastMCP)**, transport streamable-HTTP.
- **Tools**:
  - `search_legal_articles(query, top_k=5, document_type?, effective_only=true)` → list {citation, article_heading, document_code, document_type, validity_status, snippet, source_url, score}. Luôn kèm **trích dẫn + source_url**.
  - `get_legal_article(chunk_id | citation)` → toàn văn Điều + metadata + văn bản liên quan.
  - (tùy chọn) `collection_stats()` → số điều, loại VB, tình trạng hiệu lực.
- Mô tả tool viết kỹ (để Agent gọi đúng); output JSON có cấu trúc; chống trả lời không nguồn.
- Search path nội bộ = hybrid (α=0.7) → rerank Qwen3-Reranker-4B → top-k.

## 7. Cấu hình runtime & bảo mật
- Secret (proxy key) truyền lúc `docker run -e EMBED_API_KEY=...` — không bake.
- Biến chính: `EMBED_BASE_URL/API_KEY/MODEL/DIM`, `RERANK_MODEL`, `MCP_PORT`, `TYPESENSE_API_KEY` (nội bộ), `RERANK_ENABLE`.
- Dữ liệu index (không nhạy cảm) bake trong image; nếu dữ liệu nhạy cảm → cân nhắc mã hóa/volume (bàn thêm).

## 8. Xử lý quy mô 100k–1M
| Chiều | KB/vector | ~1.3M vector | Ghi chú |
|---|---|---|---|
| 2560 | 10.2 | ~13 GB RAM | Chất lượng gốc, image rất nặng |
| **1024** | 4.1 | **~5.3 GB** | Mặc định đề xuất, cân bằng |
| 768 | 3.1 | ~4 GB | Nhẹ nhất, kiểm chứng chất lượng |
- Image baked /data cho ~1M @1024d ước ~8–12GB → nặng nhưng chấp nhận được. Nếu >~500k và cần image nhẹ, cân nhắc phương án **volume** (đánh đổi "1 image").
- Bắt buộc **đo lại eval** sau khi giảm chiều để đảm bảo Recall không tụt đáng kể.

## 9. Rerank (chất lượng)
- Tích hợp `Qwen/Qwen3-Reranker-4B` (đã có trên proxy) vào search path; xác minh định dạng API `/rerank` của proxy; có cờ tắt để đo A/B.

## 10. Danh sách task & thứ tự (milestones)
| ID | Task | Phụ thuộc |
|----|------|-----------|
| TASK-004 | Tích hợp rerank vào search path + đo A/B | (đã có PoC) |
| TASK-006 | Nhận & validate dữ liệu thật (khớp schema mẫu, thống kê quy mô) | data khách |
| TASK-007 | Pipeline embed offline resumable + giảm chiều MRL + import + snapshot | 004,006 |
| TASK-008 | MCP server HTTP/SSE (FastMCP) + tools + trích dẫn | 004 |
| TASK-009 | Dockerfile multi-stage all-in-one + entrypoint + healthcheck | 007,008 |
| TASK-010 | Đóng gói phân phối (docker save, tài liệu tích hợp Agent, ENV) | 009 |
| TASK-011 | Kiểm thử tích hợp E2E + eval trên dữ liệu thật + tối ưu α/chiều | 009 |
| TASK-005 | Down-weight Điều boilerplate khỏi keyword (tối ưu) | tùy chọn |

**Trình tự đề xuất**: 004 → 006 → (008 song song) 007 → 009 → 010 → 011. TASK-005 xen khi tối ưu.

## 11. Rủi ro & giảm thiểu
| Rủi ro | Giảm thiểu |
|---|---|
| Embed 100k–1M điều tốn thời gian/chi phí, proxy chập chờn | Pipeline **resumable + checkpoint**, batch, retry/backoff; chạy offline 1 lần |
| Model 8B lỗi phía proxy | Mặc định 4B; config đổi 8B khi healthy; dim cấu hình được |
| Giảm chiều làm tụt chất lượng | Eval A/B 2560 vs 1024 vs 768 trước khi chốt |
| Image quá nặng khi ~1M | Giảm chiều; nếu cần, phương án volume |
| Runtime phụ thuộc proxy (embed query/rerank) | Retry; cờ tắt rerank; tài liệu hóa yêu cầu mạng |
| Multi-process trong 1 container (anti-pattern) | Entrypoint có supervisor + trap tín hiệu + healthcheck 2 lớp |

## 12. Điều kiện cần từ bạn
1. **Dữ liệu thật** (JSON, cùng schema mẫu 100 chunk; nếu khác → cung cấp mẫu để map).
2. **Quy mô chính xác** (số điều) để chốt chiều vector & chiến lược bake/volume.
3. **Proxy** dùng khi chạy thật (URL/key) — xác nhận 8B có sửa được không.
4. **Cổng MCP** mong muốn + cách Agent của bạn nạp remote MCP (để viết tài liệu tích hợp).
