# SEO Nguyễn Tú — quyết định viết mới hay tối ưu URL cũ (18/10/2026)

Repo duy nhất: `thuexemayhanoi/wp-writer`. Website đích: `https://thuexemaynguyentu.com/`.

## Kết quả rà soát có thật

- Đã đối chiếu 25 đề xuất SEO với 283 dòng canonical Topic Registry và 323 mục inventory WordPress (bài, trang, sản phẩm), đồng thời đọc các đoạn liên quan ở bài WordPress.
- 12 ý tưởng có góc triển khai riêng *sơ bộ*; 7 ý tưởng cần so sánh sâu, 6 ý tưởng trùng nên không tạo bài mới. Đây là màn hình lọc ban đầu, **không phải Research QA PASS**.
- Bộ điều phối hiện chỉ cho **3 chủ đề** đi tới nghiên cứu trước (`decision=RESEARCH_FIRST` và `state=AWAITING_EXTERNAL_RESEARCH`): SEO-20261018-05, SEO-20261018-06, SEO-20261018-17. Các ý tưởng còn lại bị giữ để không lấn nội dung cũ.
- 9/9 Writer có phiên nhận Topic ID trong ledger ở thời điểm audit. Báo cáo refill ghi `ready_stock=0`. Tuyệt đối không tự nhận Topic ID, giành lease, viết `posts/drafts` không có topic PLANNED, hoặc vượt QA.
- Danh sách quyết định/cặp URL trùng ở [tệp nguồn](../data/research/seo-opportunities-2026-10-18.json). Lệnh `python scripts/research_v2.py hints --limit 10` ưu tiên các chủ đề có `RESEARCH_FIRST`; nghiên cứu thật, kiểm tra hash và Research QA rồi mới nhập PLANNED cho W1–W9.

## 3 chủ đề được nghiên cứu TRƯỚC

1. **SEO-20261018-05** — Trả xe thuê trễ: cần xác nhận những khoản phí và thủ tục nào? Khác bài tính kỳ thuê 2 ngày 1 đêm và chủ đề gia hạn, nhưng phải xác minh điều kiện trả muộn thực tế; tuyệt đối không tự đặt mức phí.
2. **SEO-20261018-06** — Chụp ảnh biên bản bàn giao xe máy: những góc nào cần lưu? Đối chiếu bài nhận xe tại homestay (WP #4046) và hợp đồng đặt cọc (WP #891); bài mới chỉ tập trung cách ghi hình đối chiếu lúc nhận/trả xe, không thay thế hướng dẫn thủ tục tổng hợp. Tham khảo nguyên tắc ghi nhận tình trạng và ảnh trước/sau từ hướng dẫn cơ quan bảo vệ người tiêu dùng: [GOV.UK](https://www.gov.uk/government/publications/renting-a-car-advice-for-consumers/hiring-a-car-what-to-watch-out-for), [ACCC Úc](https://www.accc.gov.au/consumers/specific-products-and-activities/car-hire). Đây là nguồn về **xe thuê nói chung/ô tô**, chỉ áp dụng nguyên tắc ghi nhận, không viện dẫn thành quy định pháp luật bắt buộc của Việt Nam.
3. **SEO-20261018-17** — Nhận xe thuê ở Long Biên để đi Phố Cổ: chuẩn bị tuyến đường và chỗ đỗ. Khác bài Phố Cổ tham quan đi bộ. Mọi quy định phố đi bộ, giờ cấm, điểm giữ xe phải kiểm chứng theo ngày xuất bản. Không tự bịa lộ trình/khoảng cách/giá gửi xe.

Không mục nào ở trên đã được viết đủ 1.600–5.000 từ, đạt SEO/Quality ≥85, nhập PLANNED hay xuất bản chỉ nhờ tệp này.

## 6 ý tưởng không tạo bài mới vì trùng ý định

- SEO-20261018-04: đã có NT-000004 về biên nhận đặt cọc.
- SEO-20261018-10: đã có NT-000017 về xe 50cc chạy phố đông.
- SEO-20261018-14: đã có bài xe máy điện đi mưa WP #2374.
- SEO-20261018-22: đã có NT-000008 về giấy tờ khách nước ngoài thuê xe.
- SEO-20261018-23: đã có bài thuê xe máy Hà Nội ngày mưa WP #4051.
- SEO-20261018-24: đã có bài mũ bảo hiểm đi kèm xe thuê WP #4057.

Không xóa bài/Topic ID cũ; chỉ không sản xuất thêm phiên bản trùng.

## URL nên tối ưu, CHỜ chủ duyệt từng mục

**Duyệt số 1 — Trang chủ** `https://thuexemaynguyentu.com/`: Search Console qua SiteGuru 16/09–15/10: “thuê xe máy Hà Nội” vị trí trung bình 19, 242 lần hiển thị; “thuê xe máy ở Hà Nội” vị trí 15,3, 412 hiển thị. Đề nghị audit bổ sung nội dung trả lời thuê ngày/tuần/tháng, bảng giá thực tế, khu vực giao xe được xác nhận, thủ tục/cọc và internal links về 50cc, xe điện, xe ga. **Không đổi title, meta, H1, URL hoặc canonical khi chưa duyệt riêng**. Đây là bổ sung nội dung và liên kết dựa trên dữ liệu thực tế, không làm landing page mới cạnh tranh homepage.

**Duyệt số 2 — Trang 50cc** `https://thuexemaynguyentu.com/thue-xe-may-50cc-ha-noi/`: thứ hạng TB 4, 139 impressions cùng kỳ. Đề nghị rà nội dung xe hiện có, điều kiện sử dụng, link sản phẩm 50cc, câu hỏi thủ tục theo dữ liệu thật; giữ nguyên thứ hạng/intent hiện tại, không tự tạo bài giá 50cc trùng.

**Duyệt số 3 — Danh mục xe điện** `https://thuexemaynguyentu.com/danh-muc-san-pham/loai-xe/xe-dien/`: vị trí TB 9,3; 113 impressions cùng kỳ. Đề nghị kiểm tra mô tả danh mục, mẫu xe đang có thật, liên kết hướng dẫn pin/quãng đường và điều kiện thuê; không tạo blog post cùng ý định thuê xe máy điện Hà Nội.

**Trạng thái tất cả mục tối ưu: AWAITING_OWNER_APPROVAL.** Không tự chỉnh sửa nội dung WordPress hoặc tiêu đề SEO.

## Quy tắc phân phối

Nguồn nghiên cứu → `research_v2.py hints` → nghiên cứu nguồn HTTPS trực tiếp, bằng chứng có hash thật, so toàn bài cũ, `intent-check` → checkpoint/QA → chỉ PASS mới vào PLANNED → Writer có lease hợp lệ → Quality/SEO ≥85 + G1–G6 PASS → Publisher xác minh WordPress.

Không có AI API nền trong GitHub Actions. Không đổi cổng QA, lịch xuất bản, URL/canonical/SEO hiện có hoặc hàng đợi Writer để thúc tiến độ.
