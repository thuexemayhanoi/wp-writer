# SEO Opportunity Triage — Nguyễn Tú (18/10/2026)

Site: https://thuexemaynguyentu.com/
Repo: thuexemayhanoi/wp-writer

## Snapshot: thực tế và hạn chế

- GSC qua SiteGuru 16/09–15/10: "thuê xe máy Hà Nội" vị trí TB 19, 242 impressions; "thuê xe máy ở Hà Nội" 15,3 và 412 impressions; "thuê xe máy 50cc Hà Nội" 4,0; "thuê xe máy điện Hà Nội" 9,3. Thứ hạng là trung bình, không phải dự đoán.
- Ubersuggest Vietnam báo volume "thuê xe máy Hà Nội" 8.100/tháng (domain_keywords), "cho thuê xe máy Hà Nội" 1.600/tháng, "thuê xe máy điện Hà Nội" 260/tháng, "thuê xe máy 50cc Hà Nội" 110/tháng. Số volume của Ubersuggest từng không đồng nhất giữa một số endpoint; không bảo đảm thứ hạng trong vài tháng.
- SiteGuru kỹ thuật: health 86; 15 URL báo không index được, 16 URL thiếu incoming internal links, 78 URL bị đánh dấu nội dung tương tự. Các nhóm này **cần soát chi tiết**, không được tự bật index hay gộp/xóa bài.
- WordPress page #562 là homepage (https://thuexemaynguyentu.com/), WP Agent đánh giá nội dung on-page 83/100 (Quality 88/100). Bộ chấm điểm đánh giá liên kết thân bài 0/10 dù source chứa các thẻ liên kết: đây có thể là giới hạn bộ phân tích, không kết luận site thiếu toàn bộ internal links.
- Homepage vẫn chứa nhiều shortcodes [ux_banner], [section], [ux_products], [ux_image] từ Flatsome; theme hiện tại đã đổi, cần kiểm tra render trước khi chỉnh giao diện; không sửa bằng cách xóa hàng loạt shortcode.
- Theo registry 283 topic: 210 PLANNED, 72 RESEARCH, 1 REJECTED. Có 9 lease Writer; chỉ 3 PLANNED chưa thấy trong lease, submissions hay publication ledger khi đối chiếu: NT-000111, NT-000113, NT-000285. **Báo cáo refill ready_stock=0** có thể dùng bộ lọc khác hoặc snapshot khác; không tự nhận lease chỉ dựa trên phép trừ này. 151 bài công khai VERIFIED trong publication ledger (còn một entry nháp thử nghiệm).

## Quyết định viết bài — CHỈ SAU RESEARCH QA

Gợi ý SEO từ data/research/seo-opportunities-2026-10-18.json đã sàng lọc; pipeline research_v2.py hints hiện lọc decision=RESEARCH_FIRST và state=AWAITING_EXTERNAL_RESEARCH.

| Thứ tự | ID | Tiêu đề nghiên cứu | Lý do có hướng riêng | Trạng thái |
|---|---|---|---|---|
| 1 | SEO-20261018-06 | Chụp ảnh biên bản bàn giao xe máy: những góc nào cần lưu? | Mục đích cụ thể: lưu bằng chứng nhận trả xe; cần soát bài #2596, #4046 | RESEARCH_FIRST, chưa PLANNED |
| 2 | SEO-20261018-05 | Trả xe thuê trễ: cần xác nhận những khoản phí và thủ tục nào? | Mục đích xử lý quá hạn và thỏa thuận, tách với bài tính giá một ngày | RESEARCH_FIRST, chưa PLANNED |
| 3 | SEO-20261018-17 | Nhận xe thuê ở Long Biên để đi Phố Cổ: chuẩn bị tuyến đường và chỗ đỗ | Hướng dẫn tuyến thực tế, tách với trang đặt xe thương mại; xác minh thông tin tuyến và chỗ đỗ | RESEARCH_FIRST, chưa PLANNED |

**Những chủ đề phải giữ lại, chưa tạo post mới:** mũ bảo hiểm nhận kèm xe (đã có WP #4057); thuê xe ngày mưa (WP #4051); thuê xe khu vực Nội Bài (WP #1061); so sánh xe số/xe ga (WP #2580); chi phí xe điện với xe xăng (WP #2370); giấy tờ khách nước ngoài (đã có NT-000008); biên nhận cọc (đã có NT-000004). Các ý tưởng còn lại trong file cơ hội SEO tiếp tục ở trạng thái REVIEW, không tự công bố.

## Danh sách sửa trang đang có — CHỜ CHỦ DUYỆT, một URL mỗi đợt

### Ưu tiên đầu tiên: Trang chủ WordPress page #562

URL: https://thuexemaynguyentu.com/
Truy vấn: "thuê xe máy Hà Nội", "thuê xe máy ở Hà Nội", "cho thuê xe máy Hà Nội".
Tình trạng GSC: vị trí TB khoảng 15–19 cho hai biến thể chính, tỷ lệ nhấp còn thấp.
Đề xuất chỉ khi chủ duyệt:
1. Kiểm tra theme mới render các shortcode Flatsome cũ như thế nào trên di động và máy tính; KHÔNG xóa shortcode trước khi có cách thay thế.
2. Rà thông tin NAP, giờ 09:00–21:00, chính sách giao xe có phí và giá/đặt cọc theo data/business-facts.json. Thay câu hứa không thể xác minh bằng diễn giải có điều kiện.
3. Kiểm tra đích và vị trí liên kết đến trang giá, thuê tháng, 50cc, danh mục xe điện, hướng dẫn giao xe, và FAQ. WP Agent báo 0/10 internal links trong thân bài, nhưng mã trang đã chứa liên kết; phải đối chiếu rendered HTML trước.
4. Giữ nguyên SEO title, title hiển thị, H1, slug, canonical, sitemap và URL trừ khi có duyệt riêng. Không tạo landing page mới cùng intent.

### Sau trang chủ, lần lượt đề xuất duyệt

1. https://thuexemaynguyentu.com/thue-xe-may-50cc-ha-noi/ — bảo vệ thứ hạng ~4.
2. https://thuexemaynguyentu.com/danh-muc-san-pham/loai-xe/xe-dien/ — thứ hạng ~9,3, nâng nội dung giao dịch và links đến xe điện.
3. https://thuexemaynguyentu.com/san-pham/xe-dap-dien — kiểm tra sản phẩm và nội dung CTR.
4. https://thuexemaynguyentu.com/san-pham/honda-vision — cải thiện mô tả mua/thuê chính xác.
5. https://thuexemaynguyentu.com/app-thue-xe-may-ha-noi — giữ đúng ý định app.
6. Nội dung Phố Cổ / thuê tháng / nhận giao xe dựa trên URL hiện có, tuyệt đối không tạo bản sao thương mại.

## Quy tắc pipeline

- 25 đề xuất SEO là **lead nghiên cứu**, KHÔNG phải Topic Registry PLANNED. AI Researcher đọc nguồn thật, so intent với WordPress và registry, rồi nộp research/*; Topic QA PASS mới được nhập.
- Writer W1–W9 chỉ viết topic đã được cấp qua lease hợp lệ; không chiếm lease, không tự gán Topic ID, không nhét markdown trực tiếp để lách gate.
- Giữ QA SEO & Content >=85, Production như cũ, Publisher 2 bài/batch. Không sửa WordPress hoặc trang cũ khi chủ chưa duyệt.
- Không coi số lượt tìm kiếm Ubersuggest hay vị trí TB là bảo đảm lên trang 1.

Report authored from connected GitHub topic registry/inventory, Search Console via SiteGuru and SMEPost, Ubersuggest, and read-only WP Agent analysis. Đây là báo cáo hỗ trợ quyết định, không phải một bài đã xuất bản.
