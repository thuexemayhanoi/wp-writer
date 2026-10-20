# Kế hoạch 1.482 tiêu đề SEO mới cho Nguyễn Tú

Dữ liệu gốc: 518 bài WordPress đã xuất bản (REST, 20/10/2026). Mục tiêu kế hoạch là 2.000 bài, do đó còn 1.482 dòng, chia làm ba file Excel 494 dòng; phân bổ 18 danh mục con hoặc danh mục lá đã tồn tại.

## Hàng đợi và ba bảng Excel

- seo-tieu-de-01-494.xlsx: TP-0001 đến TP-0494.
- seo-tieu-de-02-494.xlsx: TP-0495 đến TP-0988.
- seo-tieu-de-03-494.xlsx: TP-0989 đến TP-1482.

Có ba CSV máy đọc, plan.json là danh sách nền và status.json là nhật ký trạng thái. Excel là bản trình bày; không được dùng trạng thái ở Excel để bỏ qua cổng QA.

## Dữ liệu đối chiếu và phân loại

baseline-518.json lưu ID, title, slug, category và URL của 518 bài publish. Trình tạo tiêu đề còn đọc data/topics.jsonl để chống trùng tên/góc khai thác với topic trong pipeline khi lập kế hoạch. Lúc thực sự viết phải làm lại chống trùng intent và URL vì website có thể đã thay đổi.

Chỉ dùng 18 WordPress Term ID có thật: 163, 164, 165, 166, 167, 168, 160, 169, 170, 161, 171, 172, 173, 174, 175, 176, 177, 156. Không tự tạo danh mục, không fallback vào Blog hoặc Uncategorized.

SEO 51 phường (Term ID 182) thuộc chiến dịch độc lập editorial/seo-51-phuong và có 3 bài đầu Bồ Đề, Cửa Nam, Hoàn Kiếm. Không nhân bản chiến dịch này trong danh sách 1.482. Không tạo thêm hàng loạt title chứa đúng cụm “thuê xe máy Hà Nội”.

## Quy trình sử dụng với ChatGPT thường và GitHub

1. Lấy 1–3 dòng PLANNED tiếp theo trong plan.json hoặc chạy: python scripts/title_plan_next.py --limit 3.
2. Mỗi tiêu đề tìm 1–4 nguồn thật phù hợp chủ đề; kiểm tra source URL, trích dẫn và trang chính thức cho các khẳng định luật/giấy phép. Nếu tiêu đề không phù hợp nguồn hoặc trùng intent, sửa đề cương tiêu đề trước khi viết, giữ nguyên mã TP để theo dõi.
3. Gửi Topic Factory + Research QA bằng trường title_plan_id=TP-XXXX, taxonomy_key và wordpress_category_id của dòng tương ứng. Dữ liệu nghiên cứu phải tuân thủ docs/ARTICLE-CONTRACT.md và chống trùng bài/URL mới nhất.
4. Writer W1–W9 lấy lease riêng hợp lệ, viết 1.600–5.000 từ, QA SEO và chất lượng đều từ 85 trở lên, G1–G6 PASS, không còn REVIEW hoặc FAIL.
5. Publisher duy nhất xuất bản public vào đúng category. Không tạo WordPress draft nếu QA không đạt. Khi POST không rõ kết quả thì HOLD và đối soát, không POST trùng.
6. Chỉ khi ledger có phase VERIFIED và receipt G7 PASS đủ 10 checks, workflow title-plan-1482-sync.yml cập nhật status trong plan.json, CSV, XLSX thành PUBLISHED_G7_PASS cùng WP ID/URL.

Đây là danh sách ứng viên tiêu đề chứ không phải các bài đã qua Research QA. Chỉ có GitHub không thể tự viết bài bằng AI nếu không có phiên ChatGPT/Claude hoặc hệ thống Writer đang chạy. Không cấp thêm API keys hay nới hàng rào QA. Không sửa production-policy.json, qa.py, publisher.py, leases W1–W9, URL/canonical của bài cũ hoặc sổ Publisher.

Nếu title đã có Topic ID, sửa và tiếp tục trên Topic ID đó, không đăng bản sao.
