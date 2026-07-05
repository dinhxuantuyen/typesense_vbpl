# PTYC — TASK-013: Dựng Typesense Dashboard (GUI quản trị)

## Mục tiêu
Có giao diện web trực quan để quản trị dữ liệu Typesense (xem/sửa/xóa document, chạy search,
xem collection/alias/API key) phục vụ vận hành & cập nhật về sau.

## Phạm vi
- Chạy container `bfritscher/typesense-dashboard` kết nối tới server Typesense đang chạy (8108).
- Ngoài phạm vi (giai đoạn sau): đóng gói dashboard vào image all-in-one; pipeline cập nhật.

## Yêu cầu chức năng
1. Dashboard chạy trên 1 cổng host (không đụng 8000/8107/8108/8109/8110), vd 8888.
2. Kết nối được tới Typesense (đã bật `--enable-cors`) bằng API key.
3. Duyệt được collection `legal_articles` (124k+ điều), xem document, chạy search thử.

## Yêu cầu phi chức năng
- Không ảnh hưởng job embed đang chạy (dashboard chỉ là web tĩnh + gọi Typesense, không gọi proxy).
- Kết nối cấu hình được (host/port/api-key) khi mở trên trình duyệt Windows.

## Tiêu chí chấp nhận
- [ ] `http://localhost:8888` mở được UI dashboard.
- [ ] Nhập host=localhost, port=8108, protocol=http, api-key → kết nối thành công.
- [ ] Thấy collection `legal_articles` với đúng số document; chạy được 1 truy vấn search.

## Ghi chú kỹ thuật
- Dashboard là app client-side chạy trong trình duyệt → gọi Typesense trực tiếp từ browser
  (cần CORS bật, đã có). Từ browser Windows, `localhost:8108` map tới Typesense trong WSL (forwarding).
- Đóng gói sau: có thể thêm dashboard như service thứ 2 (compose) hoặc build tĩnh vào image.
