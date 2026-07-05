# Tìm kiếm ngữ nghĩa văn bản pháp luật với Typesense

PoC: người dùng nhập câu hỏi ngôn ngữ tự nhiên → trả về các **Điều/Khoản** pháp luật liên quan
(hybrid search: keyword + vector), embedding **Qwen3-Embedding-4B** (2560d) qua proxy.

Tài liệu: xem [docs/product-backlog.md](docs/product-backlog.md), [docs/ptyc/](docs/ptyc/).

## Yêu cầu môi trường
- WSL2 Ubuntu (đã có), truy cập internet.
- `.env` (copy từ `.env.example`, điền key). **Không commit `.env`.**

## Chạy Typesense (native binary trong WSL)

> Vì DNS của WSL hiện lỗi bản ghi IPv4 cho Docker Hub (không `docker pull` được) và sudo cần
> mật khẩu, PoC dùng **native binary** thay cho Docker. Khi DNS docker được sửa có thể dùng
> `docker-compose.yml` (đã kèm sẵn) thay thế.

Lần đầu — tải binary (đã thực hiện, nằm ở `bin/typesense-server`):
```bash
mkdir -p bin
curl -sL https://dl.typesense.org/releases/29.0/typesense-server-29.0-linux-amd64.tar.gz -o /tmp/ts29.tar.gz
tar -xzf /tmp/ts29.tar.gz -C bin
chmod +x bin/typesense-server
```

Quản lý server (chạy trong WSL):
```bash
bash scripts/typesense.sh start     # khoi dong
bash scripts/typesense.sh health    # {"ok":true}
bash scripts/typesense.sh status
bash scripts/typesense.sh logs
bash scripts/typesense.sh stop
```
- Data dir: `~/.typesense-legal/data` (FS native của WSL — tránh lỗi khóa RocksDB trên `/mnt`).
- Server: `http://localhost:8108` (truy cập được từ cả WSL và Windows nhờ WSL2 localhost forwarding).

## Kiểm tra nhanh
```bash
curl http://localhost:8108/health
curl http://localhost:8108/collections -H "X-TYPESENSE-API-KEY: <TYPESENSE_API_KEY>"
```

## Nạp dữ liệu (ingest) — TASK-002
```bash
# JSON dieu luat (list cac Dieu). Vi du bo mau 100 chunk:
python3 -m legal_search.ingest --input data/thuvienphapluat-chunks-sample-100.json --recreate
```
- Tự động: enrichment (header ngữ cảnh), sub-chunk Điều dài (> `SUBCHUNK_CHAR_THRESHOLD`),
  cờ `is_effective_now`/`is_low_value`, trường không dấu cho keyword, embed qua proxy, upsert.

## Tìm kiếm — TASK-003
```bash
python3 -m legal_search.search "toi muon xin tro lai quoc tich Viet Nam"      # hybrid (mac dinh)
python3 -m legal_search.search "..." --mode vector --k 5                       # vector-only
python3 -m legal_search.search "..." --mode keyword                           # keyword-only
python3 -m legal_search.search "..." --alpha 0.7 --all-status                  # chinh trong so / bo loc hieu luc
```

## Đánh giá (eval)
```bash
python3 -m legal_search.eval --questions data/eval_questions.json --alpha 0.7
```
Kết quả trên bộ mẫu: **hybrid α=0.7 đạt Recall@1 = 1.00, MRR = 1.0**. Xem
[docs/ptyc/chien-luoc-embedding-search.md](docs/ptyc/chien-luoc-embedding-search.md) mục "Kết quả eval".

---

# Sản phẩm hóa: Docker all-in-one + MCP server

Kế hoạch: [docs/ptyc/ke-hoach-dong-goi-mcp.md](docs/ptyc/ke-hoach-dong-goi-mcp.md).

## Quy trình build image (3 bước)

### B1. Embed offline toàn bộ dữ liệu (resumable, ~nhiều giờ)
```bash
python3 -m legal_search.embed_offline \
  --input data/thuvienphapluat-chunks-v260626.jsonl \
  --outdir data/build --workers 24 --window 2000
# Ngat giua chung roi chay lai cung lenh -> tu dong resume (bo qua id da xong).
```
Kết quả: `data/build/embedded.jsonl` (documents kèm vector 1024d).

### B2. Build index Typesense (Phase B, không gọi proxy)
```bash
bash scripts/build_index.sh data/build/embedded.jsonl
# -> data/build/ts-data  (rocksdb data dir, se duoc bake vao image)
```

### B3. Build & chạy Docker image
```bash
docker build -t legal-mcp:latest .
docker run -d --name legal-mcp -p 8000:8000 \
  -e EMBED_API_KEY=sk-xxxx \        # SECRET: bat buoc truyen luc chay, KHONG bake
  legal-mcp:latest
# MCP endpoint: http://<host>:8000/mcp   (streamable HTTP)
```

> ⚠️ **DNS docker**: máy dev hiện lỗi phân giải IPv4 tới Docker Hub nên `docker build`
> (pull base image) sẽ thất bại. Khắc phục một lần trong WSL:
> ```bash
> sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
> ```
> Sau đó `docker build` chạy bình thường (pip/apt trong build đã đi qua DNS 8.8.8.8 của daemon).

## Tích hợp vào AI Agent (MCP client)
- Transport: **streamable HTTP**, URL: `http://<host>:8000/mcp`.
- Tools: `search_legal_articles`, `get_legal_article`, `collection_stats`.
- Ví dụ khai báo remote MCP server (dạng config phổ biến):
```json
{ "mcpServers": { "legal-search": { "url": "http://<host>:8000/mcp" } } }
```
- Test nhanh: `~/legal-venv/bin/python scripts/mcp_client_test.py http://localhost:8000/mcp`

## Biến môi trường runtime (docker run -e ...)
| Biến | Mặc định (baked) | Ghi chú |
|---|---|---|
| `EMBED_API_KEY` | *(trống)* | **SECRET — bắt buộc truyền lúc chạy** |
| `EMBED_BASE_URL` | https://proxy.cyberbot.vn/v1 | endpoint proxy |
| `EMBED_MODEL` / `EMBED_DIM` | Qwen3-Embedding-4B / 1024 | đổi 8B khi proxy healthy (phải re-embed) |
| `RERANK_ENABLE` | true | bật/tắt tầng rerank |
| `SEARCH_ALPHA` | 0.7 | trọng số vector trong hybrid |
| `MCP_PORT` | 8000 | cổng MCP |

## Phương án docker-compose (khi DNS docker OK)
```bash
docker-compose up -d   # chi chay Typesense; MCP chay rieng
```
