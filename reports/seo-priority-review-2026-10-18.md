# SEO priority triage — Nguyễn Tú (18/10/2026)

**Repo:** thuexemayhanoi/wp-writer · **Website:** https://thuexemaynguyentu.com

## Quy tắc triển khai

- **Bài mới:** chỉ đưa vào Writer W1–W9 khi Research QA đã cho chủ đề trạng thái PLANNED; bài qua SEO/Quality ≥85 và tất cả gate mới được Publisher xuất bản theo pipeline hiện có. Nếu Writer chưa có chỗ hoặc READY=0 thì không chiếm lease, không đăng ngoài workflow.
- **URL/bài hiện có:** chỉ báo cáo thứ hạng, lỗi, nội dung đề xuất; **chờ chủ website duyệt từng mục** rồi mới sửa; không tự sửa tiêu đề SEO đang bảo vệ, H1 trang chủ, slug, canonical, noindex, menu hoặc bài cũ.
- **Không tự tạo trang có intent giống trang chủ “Thuê xe máy Hà Nội”, trang khu vực, trang sản phẩm hay landing page đã có.**
- Không đổi Production, Publisher, QA, khóa, category, URL hoặc WordPress trong đợt kiểm tra này.

## Số lượng đã đối chiếu

- Kho topic: 283 dòng = 210 PLANNED, 72 RESEARCH, 1 REJECTED tại thời điểm kiểm tra (PLANNED không đồng nghĩa còn claimable; có thể đã nhận/đăng).
- Hàng đợi **claimable READY = 0** từ `reports/refill-request.json`, cả W1–W9 có lease.
- 25 gợi ý SEO được rà qua tiêu đề 323 mục WordPress và 283 topic; **8 gợi ý HOLD do trùng/tiệm cận intent**; 17 gợi ý chỉ **AWAITING_EXTERNAL_RESEARCH**, chưa phải bài đủ điều kiện viết.
- Đã xác minh 151 bài xuất bản công khai trong publication ledger (thêm một draft acceptance); trạng thái có thể đổi khi Writer khác đang chạy.

## Nhiệm vụ tối ưu URL cũ — chỉ làm sau khi chủ duyệt từng hạng mục

### P0 · Trang chủ — ĐỀ XUẤT DUYỆT ĐẦU TIÊN

- URL: https://thuexemaynguyentu.com/
- SiteGuru/GSC 16/09–15/10/2026: `thuê xe máy ở hà nội` vị trí trung bình 15,3 / 412 impressions; `thuê xe máy hà nội` vị trí trung bình 19,0 / 242 impressions. Cả hai giảm thứ hạng so với kỳ trước.
- Ubersuggest (Vietnam/vi) ghi nhóm `thuê xe máy hà nội` volume 8.100/tháng ở hai endpoint liên quan, nhưng SD biến động theo endpoint; dùng số liệu như tín hiệu, không bảo đảm vị trí/trafic.
- Audit SiteGuru: HTTP 200, indexable, Google canonical đúng `/`, 0 warning/suggestion trong 16 checks, speed score 90. **Không phải lỗi kỹ thuật cấp bách.**
- Nội dung WordPress #562 vẫn chứa shortcode Flatsome cũ trong raw page content; cần xem theme mới render thế nào trước bất cứ chỉnh sửa nào.
- **Đề xuất sau khi duyệt:** đối chiếu nội dung hiển thị thực tế; cải thiện diễn giải giá, điều kiện thuê, khu vực giao nhận và mục câu hỏi thường gặp nếu thiếu; rà internal links tới dịch vụ theo tháng, 50cc, xe điện, bảng giá, liên hệ; chỉ chỉnh đúng đoạn cần thiết, thử mobile/desktop, kiểm tra không mất shortcode/URL. Tuyệt đối **không đổi SEO title, H1 chính, meta/canonical, slug** khi chưa được duyệt riêng.

### P1 · Danh mục xe máy điện — ĐỀ XUẤT DUYỆT THỨ HAI

- URL: https://thuexemaynguyentu.com/danh-muc-san-pham/loai-xe/xe-dien/
- GSC 30 ngày: `thuê xe máy điện hà nội` vị trí trung bình 9,3 / 113 impressions.
- SiteGuru: HTTP 200, indexed, canonical đúng, **2 H1** (chỉ nên có một H1 rõ ràng). Cần xác định H1 trùng do template hay nội dung danh mục.
- Sau khi duyệt: sửa đúng thành phần tạo H1 thứ hai, kiểm thử frontend; giữ nguyên tên sản phẩm, category URL, title SEO và danh mục, không thay bằng bài blog.

### P1 · Trang 50cc — ĐỀ XUẤT DUYỆT SAU

- URL: https://thuexemaynguyentu.com/thue-xe-may-50cc-ha-noi/
- GSC 30 ngày: `thuê xe máy 50cc hà nội` vị trí 4,0 / 139 impressions.
- SiteGuru: HTTP 200, indexed, canonical đúng, 0 warning/suggestion. Giữ trang này làm đích; củng cố link nội bộ tự nhiên và rà độ rõ ràng của giá/đặt cọc, không tạo trang mới trùng intent.

### P2 · Khác

- `thuê xe máy phố cổ hà nội`: vị trí 14,9 / 30 impressions — ưu tiên kiểm tra URL hiện có và khu vực phục vụ thực tế trước khi tạo nội dung.
- `thuê xe máy theo tháng hà nội`: vị trí 8,4 / 8 impressions — mẫu nhỏ, củng cố landing page hiện có thay vì tạo bài bán hàng thứ hai.
- `thuê xe máy long biên`: vị trí 2,4 / 104 impressions — bảo vệ thứ hạng; không tạo doorway pages.
- SiteGuru site-wide còn ghi nhận 16 orphan pages và 78 pages có nội dung tương tự; đây là tín hiệu cần kiểm tra từng URL, không có nghĩa cần xóa/gộp hay chuyển noindex hàng loạt.

## Các gợi ý đang HOLD (không cho Writer nhặt)

- SEO-20261018-01 gần WordPress #2596.
- SEO-20261018-02 gần NT-000001/NT-000009.
- SEO-20261018-04 gần NT-000004.
- SEO-20261018-14 gần WordPress #2374.
- SEO-20261018-20 gần landing page Nội Bài WordPress #1061.
- SEO-20261018-22 gần NT-000008.
- SEO-20261018-23 gần WordPress #4051.
- SEO-20261018-24 gần WordPress #3948.

**Chú ý:** sàng lọc dựa trên tiêu đề/search intent sơ bộ; chỉ sau khi đọc toàn văn và xác minh nguồn mới kết luận trùng thật hoặc có thể mở góc nội dung mới. Đừng xóa các chủ đề cũ.

## Số liệu và dấu vết

- GSC SiteGuru qua connector: 16/09/2026 → 15/10/2026; báo cáo 30 ngày đã cache.
- GSC SMEPost: 13/10/2026 → 15/10/2026 (gói Free chỉ xem ba ngày).
- Ubersuggest: `domain_keywords`, `match_keywords` cho thị trường Vietnam/vi.
- SiteGuru `get_page_report` cho trang chủ, danh mục xe điện và 50cc.
- Dữ liệu gợi ý: `data/research/seo-opportunities-2026-10-18.json`.
