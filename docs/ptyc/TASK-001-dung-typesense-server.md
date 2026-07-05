# PTYC — TASK-001: Dựng Typesense server (WSL/Docker) + kiểm tra kết nối

## Mục tiêu
Có một Typesense server chạy ổn định trên máy dev (qua Docker trong WSL2), truy cập được từ cả
WSL lẫn Windows, sẵn sàng để tạo collection và index dữ liệu ở TASK-002.

## Phạm vi
- Trong phạm vi: chạy Typesense bằng `docker`/`docker compose` trong WSL2, cấu hình data dir bền vững, API key, healthcheck, script start/stop/logs.
- Ngoài phạm vi: cluster nhiều node, TLS/HTTPS, backup tự động (để giai đoạn sau).

## Yêu cầu chức năng
1. Chạy Typesense server phiên bản ổn định (>= 29.0) bằng container.
2. Dữ liệu index lưu ở volume bền vững (`./typesense-data`), không mất khi restart container.
3. API key admin cấu hình qua biến môi trường (`.env`), không hard-code.
4. Server nghe cổng `8108`, truy cập được qua `http://localhost:8108`.
5. Có script tiện ích: khởi động, dừng, xem log, kiểm tra sức khỏe (`/health`).

## Yêu cầu phi chức năng
- Cấu hình tách biệt (`.env`) — không commit secret.
- Chạy được với ~14GB RAM sẵn có; giới hạn RAM container hợp lý.
- Tài liệu README ngắn để chạy lại từ đầu.

## Tiêu chí chấp nhận (Acceptance Criteria)
- [ ] `docker compose up -d` (trong WSL) khởi động Typesense không lỗi.
- [ ] `curl http://localhost:8108/health` trả `{"ok":true}` từ cả WSL và Windows.
- [ ] `curl` với header `X-TYPESENSE-API-KEY` liệt kê được collections (rỗng ban đầu).
- [ ] Restart container → dữ liệu (nếu có) vẫn còn.

## Ghi chú kỹ thuật
- Image: `typesense/typesense:29.0`.
- Cổng 8108; API key đọc từ `.env` (`TYPESENSE_API_KEY`).
- Data dir map `/data` → `./typesense-data` (nằm trong `/mnt/d/...` hoặc trong FS của WSL để nhanh hơn).
- Lưu ý hiệu năng: đặt data dir trong FS Linux của WSL (`~/...`) nhanh hơn nhiều so với `/mnt/d`; nhưng để tiện quản lý cùng repo, cân nhắc `/mnt/d` cho PoC.
