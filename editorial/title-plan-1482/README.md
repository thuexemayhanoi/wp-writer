# Ba Excel — 1.482 tiêu đề SEO của Nguyễn Tú

> **AI đọc trước:** [Quy trình A–Z gọn, đầy đủ](../../docs/TITLE-PLAN-1482-SOP.md) · [AGENTS chỉ cho thư mục Excel](AGENTS.md). Nếu chạy ChatGPT/Claude trên iPhone, chỉ cần mở SOP và lấy **1–3 hàng** trong `plan.json`, không tải cả 1.482 hàng vào ngữ cảnh.

## Tệp phải đọc theo thứ tự

| Tệp | Dùng để làm gì |
|---|---|
| `plan.json` | Danh sách gốc 1.482 đề tài `TP-0001…TP-1482`; Term ID, intent, trạng thái |
| `seo-tieu-de-01-494.xlsx` | Tập 1: TP-0001 → TP-0494 |
| `seo-tieu-de-02-494.xlsx` | Tập 2: TP-0495 → TP-0988 |
| `seo-tieu-de-03-494.xlsx` | Tập 3: TP-0989 → TP-1482 |
| `seo-tieu-de-*-494.csv` | Bản nhẹ cho AI đọc không cần mở Excel |
| `status.json` | Tình trạng từ biên nhận xác minh Publisher G7 |
| `baseline-518.json` | Snapshot **518 bài `publish` tại 20/10/2026** để so trùng ý định/slug; phải đối chiếu WordPress mới nhất |

**Không nhập Excel ngoài dự án:** Bảng Excel Nguyễn Hà của `wp-aiwriter` dành cho website khác. Ở đây là Excel Nguyễn Tú `wp-writer` mới. Excel là **lịch đề tài**, không phải Topic Registry đã QA.

## Một dòng Excel được dùng như thế nào?

1. Đọc 1–3 TP-ID qua `python scripts/title_plan_next.py --limit 3`, hoặc mở `plan.json` lấy đúng hàng còn PLANNED; không đọc lại toàn bảng.
2. Trước khi viết phải kiểm trùng với WordPress hiện tại, toàn bộ Topic Registry, những bài đang được claim. Nếu đã phục vụ cùng intent → HOLD và báo lý do.
3. Nghiên cứu **1–4 nguồn** công khai thật; sao lưu URL, thời điểm, excerpt và hash thật. Luật/GPLX phải có cơ quan chính thức. Không chép bài khác.
4. Đưa `TP-ID` vào metadata `title_plan_id` của **Topic Registry mới** qua Research QA → Trusted Intake; chỉ topic đã PLANNED mới được nhận W1–W9.
5. Writer phải có lease, viết **1.600–5.000 từ**, SEO & Quality ≥85, G1–G6 PASS; Publisher đăng đúng Term ID. Chỉ G7 VERIFIED + receipt PASS mới **đánh dấu vào Excel**.
6. Khi mất mạng/quota, lưu `TP-ID/NT-ID/session/lease/branch/commit/step` rồi tiếp tục đúng phiên; không ghi trạng thái giả.

### URL và SEO

- Slug bài mới **theo tiêu đề**, không có `excel`, `csv`, `xlsx`, tên file `seo-tieu-de-...xlsx` hoặc mã TP.
- Không sản xuất loạt title nhắm chính xác từ khóa “thuê xe máy Hà Nội”; 51 phường thuộc campaign khác (Term ID 182), không lặp lại.
- Phân phối 1.482 TP đều trong **18 danh mục đã có**, 82–83 mỗi danh mục. `data/taxonomy.json` quyết định term ID cha/con, không tự tạo category.
- Các title là **đề xuất ban đầu 60–80 ký tự**, AI vẫn phải đánh giá tính tự nhiên, intent, nguy cơ cannibalization và nguồn nghiên cứu trước khi cấp NT. Nếu tiêu đề không phù hợp, sửa kế hoạch qua coordinator, giữ TP-ID, không tự đăng bài mỏng.

### Trạng thái

`PLANNED` (Excel) ≠ `PLANNED` (NT Topic Registry). Excel chỉ chuyển `PUBLISHED_G7_PASS` **khi** Publisher có G7 receipt xác minh bài WordPress công khai đúng ID, URL, category và Yoast meta; GitHub Actions PASS chưa đủ.

## Lệnh 1 câu copy cho AI trên điện thoại

> Đọc `AGENTS.md` và `docs/TITLE-PLAN-1482-SOP.md` trong `thuexemayhanoi/wp-writer`. Chọn 3 TP-ID chưa xử lý, kiểm trùng URL/intent với WordPress, tìm 1–4 nguồn thật, vào Topic Factory/Research QA, claim NT-ID hợp lệ, viết đủ QA ≥85, Publisher tự đăng và G7 mới đánh dấu Excel. Không tên Excel trong slug, không cướp lease, mất quota thì lưu checkpoint, báo URL thật. Không hỏi duyệt từng bài.

**Giới hạn kỹ thuật:** GitHub tự kiểm dữ liệu, QA, lưu progress và Publisher; tự nó **không sinh 1.482 bài bằng mô hình AI**. Người dùng vẫn cần một phiên AI nghiên cứu/viết hoặc Writer đã kết nối; không dùng API key mới, không hạ chuẩn QA.
