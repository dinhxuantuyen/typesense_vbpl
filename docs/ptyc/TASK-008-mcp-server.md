# PTYC — TASK-008: MCP server HTTP/SSE

## Mục tiêu
Expose khả năng tra cứu điều luật qua **MCP server (streamable HTTP)** để AI Agent gọi tool,
mỗi kết quả kèm **trích dẫn + source_url** (chống trả lời không nguồn).

## Phạm vi
- MCP server bằng FastMCP, transport streamable-http, bind 0.0.0.0:`MCP_PORT`.
- Tools: `search_legal_articles`, `get_legal_article`, `collection_stats`.
- Ngoài phạm vi: REST API, auth nâng cao (bàn sau).

## Yêu cầu chức năng
1. `search_legal_articles(query, top_k=5, document_type?, effective_only=true)`:
   - hybrid (α=0.7) + rerank (nếu `RERANK_ENABLE`) → top_k Điều.
   - Trả list {citation, article_heading, document_code, document_type, validity_status, snippet, source_url, score}.
2. `get_legal_article(chunk_id)`:
   - Ghép toàn văn Điều từ các part (nếu bị sub-chunk), trả metadata + văn bản liên quan nếu có.
3. `collection_stats()`: số document, tên collection, số chiều.
4. Mô tả tool rõ ràng (docstring) để Agent gọi đúng; input validate qua type hints.

## Yêu cầu phi chức năng
- Không crash khi proxy lỗi: bắt lỗi, trả thông báo rõ trong kết quả tool.
- Cấu hình qua ENV (dùng chung `.env`): `MCP_PORT`, `RERANK_ENABLE`, embedding/proxy.
- Stateless; nhiều request song song được.

## Tiêu chí chấp nhận
- [ ] Server chạy, healthcheck cổng MCP OK.
- [ ] `search_legal_articles` trả kết quả đúng định dạng, có citation + source_url.
- [ ] `get_legal_article` ghép đúng Điều bị sub-chunk.
- [ ] Kết nối được bằng 1 MCP client thử nghiệm (list tools + call).

## Ghi chú kỹ thuật
- FastMCP `mcp.run(transport="streamable-http")`; endpoint mặc định `/mcp`.
- Tái sử dụng `legal_search.search` (đã có hybrid + rerank).
- `get_legal_article`: filter_by `chunk_id:=<id>` → gom part theo `part_no`.
