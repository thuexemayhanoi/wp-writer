# SEO Autopilot Nguyễn Tú — 18/10/2026

Đây là báo cáo và điểm tiếp tục, không phải lô chủ đề để Writer xuất bản.

## Đã kiểm tra

- Đọc đầy đủ báo cáo OpenSEO 8b3d7af1-64b7-465b-8650-d1c4de15fa3d (24.906 byte HTML).
- GSC miễn phí: 18/09–15/10 và 21/08–17/09/2026, hai kỳ 28 ngày độc lập; kỳ 15/07–15/10 chỉ làm bối cảnh.
- Quét 389 URL HTML trong sitemap và nhóm ưu tiên: đích cuối đều 200. Kiểm tra thêm 19 đích canonical; 18 URL cũ 404, một URL trùng nhóm đã quét.
- Inventory trong repo có 323 mục, cập nhật 18/10/2026 14:54 UTC; topics.jsonl có 283 chủ đề. Đây là ảnh chụp, không phải số bài đang xuất bản hay tổng kho trực tiếp mới nhất.
- Không sửa registry, lease, ledger, taxonomy, cờ Production hoặc cơ chế QA.

## Thay đổi đã thực hiện trong WordPress

Đã sửa giờ 08:00–21:30 thành 09:00–21:00 trong nội dung trang chủ và 8 sản phẩm: Honda Vision (#412), Air Blade (#674), Honda Blade (#680), Mio Classico (#678), Honda Click (#676), bảng giá xe điện (#651), Honda Wave (#410), Yamaha Sirius (#659). Trang chủ còn được sửa nút đánh giá không có đích đến để dẫn tới hồ sơ Google Maps chính thức.

Các URL đã mở lại thành công: /, /san-pham/honda-vision/, /san-pham/honda-air-blade/, /san-pham/xe-so-honda-blade/, /san-pham/yamaha-mio-classico/, /san-pham/honda-click/, /san-pham/bang-gia-thue-xe-dien/, /san-pham/honda-wave/, /san-pham/yamaha-sirius/. Không đổi title, H1, slug hoặc canonical. Không viết thêm bài mới. Bản gốc/đoạn thay thế đã lưu trong gói bằng chứng của phiên Work.

## Mã theme

PR https://github.com/thuexemayhanoi/theme/pull/3:

- Mục lục bỏ qua heading trong comment, script, template và noscript; không sửa chữ hay cấp heading.
- Google Maps iframe thiếu title/loading được bổ sung tên mô tả và tải trễ, giữ URL/kích thước/thuộc tính cũ.
- Thêm điện thoại ngang 844×390 vào bộ kiểm thử; sửa một cảnh báo căn dấu bằng trong banner.
- Kiểm thử cục bộ: 83 unit tests, 1.815 assertions; 30 Node tests; PHP lint/PHPCS/JS/CSS/dung lượng/độ tương phản PASS.
- CI mới nhất khi ghi checkpoint: https://github.com/thuexemayhanoi/theme/actions/runs/39146136776, static PASS, sandbox đang chạy. Chưa xem trạng thái xanh là bằng chứng site đã deploy.

## Vấn đề phải duyệt hoặc có thao tác riêng

1. 18 URL cũ đang được khai báo canonical nhưng trả 404. Bảng URL cụ thể nằm trong data/research/seo-autopilot-review-2026-10-18.json. Cần khôi phục đúng nội dung/đường dẫn, kiểm tra staging; chưa tự đổi canonical hay redirect.
2. /danh-muc-san-pham/loai-xe/xe-dien/ và /shop/ có hai H1. Chưa đổi vì chủ bảo vệ H1.
3. WPCode option ihaf_insert_header tạo đồ thị WebSite/WebPage trùng với Yoast và vẫn ghi 08:00–21:30. WPVibe từ chối ghi thẳng vào bộ nhớ mã, yêu cầu luồng duyệt mã. Chưa sửa live. Có bản đề xuất chỉ sửa opens/closes, không tự thay graph.
4. Bài Ocean Park #880 có comment mở trước bảng giá xe điện cũ chưa đóng. Phần sau bị che; chưa khôi phục vì chứa giá/điều kiện thuê cũ cần rà soát và các nội dung pháp lý cần duyệt. Mục lục lỗi đã có bản sửa trong PR theme.
5. /llms.txt còn Hello world, cart/checkout và đường dẫn agent thiếu giao thức. Cần xác minh bên đang quản lý tệp gốc; không tự ghi đè bằng theme. Tệp này không bảo đảm khả năng được AI trích dẫn.
6. Mobile lab từ WPVibe: Performance 63, Accessibility 89, Best Practices 96, SEO 100; LCP 7,4 giây, CLS 0, TBT 30 ms. Không có dữ liệu CrUX; TBT không phải INP. Chưa chứng minh đạt Core Web Vitals thực tế. Không tắt plugin/jQuery khi chưa kiểm tra phụ thuộc.

## GSC trước tối ưu

| Phạm vi | 21/08–17/09 | 18/09–15/10 |
|---|---|---|
| Trang chủ: nhấp / hiển thị / vị trí | 106 / 2.468 / 9,4 | 103 / 2.199 / 10,3 |
| Truy vấn thuê xe máy Hà Nội: nhấp / hiển thị / vị trí | 25 / 453 / 14,8 | 15 / 232 / 19,3 |

Đây là dữ liệu trước các chỉnh sửa ngày 18/10, không thể dùng để kết luận hiệu quả sau chỉnh sửa. Số vị trí là trung bình GSC, không phải thứ hạng cố định hay Google Maps.

## Chọn URL chủ lực và nghiên cứu

- Trang chủ tiếp tục là URL ưu tiên cho thuê xe máy Hà Nội. Với thuê xe máy Long Biên, trang chủ đang có 92 hiển thị/vị trí 2,2; trang Long Biên chỉ có 2 hiển thị/vị trí 35,5 cho đúng truy vấn này. Không phá trang thắng để ép chuyển URL chủ lực.
- 50cc: /thue-xe-may-50cc-ha-noi/ phục vụ intent dịch vụ; trang xe ga 50cc phục vụ mẫu xe.
- Xe đạp điện: /san-pham/xe-dap-dien/ nhận cả truy vấn theo tháng (8 hiển thị, vị trí 6,5). Chưa tạo bài dịch vụ tháng trùng.
- Xe máy điện: danh mục xe điện nhận 87 hiển thị/vị trí 8,8 cho đúng truy vấn thuê xe máy điện Hà Nội. Không ép bài /cho-thue-xe-dien-ha-noi/ thay thế khi chưa có dữ liệu.
- Đã có /thue-xe-may-gan-ho-hoan-kiem/. Không tạo thêm URL dịch vụ Hoàn Kiếm.
- Vision có truy vấn TPHCM 66 hiển thị/vị trí 47 trong mẫu query-page. Tách nhu cầu ngoài thị trường, không thêm trang TPHCM.
- Ba ứng viên chỉ để nghiên cứu: thuê theo giờ (có tín hiệu GSC nhưng cần xác minh có dịch vụ); trả xe sớm (cần chính sách thực tế và nguồn); mất/quên chìa xe thuê (phải phân biệt với bài Smart Key hiện có). Chưa PLANNED, chưa được phép xuất bản.
- Gia hạn đã có NT-000002; không tạo trùng.

## Đo lại và tiếp tục

Mốc 14/28/90 ngày tính từ 18/10: 01/11/2026, 15/11/2026, 16/01/2027. Chỉ đọc kỳ hoàn chỉnh khi GSC đã đủ dữ liệu; so sánh các kỳ bằng độ dài, tách truy vấn–URL–thiết bị. Theo dõi nhấp và hiển thị của nhóm thương mại, CTR, vị trí, URL được Google chọn; nếu có dữ liệu đo cuộc gọi/Zalo thì xem thêm chuyển đổi. Không tự tạo lịch chạy nền hay gọi AI API.

Trước khi tiếp tục: đọc báo cáo này và JSON đi kèm, kiểm tra lại PR/CI và website. Không lặp chỉnh sửa giờ/nút đã xác minh, không mở lại ứng viên HOLD như chủ đề đã duyệt. Ngưỡng Writer SEO/Quality ≥85 và các hard gate không đổi.

## Hạn mức

OpenSEO bắt đầu 290 credit; mọi truy vấn GSC/đọc báo cáo đã dùng đều miễn credit. Ubersuggest chỉ kiểm tra hạn mức: 0/3 báo cáo sử dụng, không nghiên cứu tốn lượt. WPVibe dùng lượt gói Free trên kết nối đúng site; cần đọc lại usage khi tiếp tục. WP Agent không tạo bài mới; sửa bài không trừ hạn mức tạo bài. Không dùng nghiên cứu trả phí.
