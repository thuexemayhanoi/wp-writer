# Cụm SEO 51 phường Hà Nội — lô 04/17 đã biên tập

**Tình trạng:** Ba **bản biên tập** đã viết, **chưa phải bản thảo Topic Factory**, chưa gán ID/lease, chưa kiểm tra đủ Research QA và chưa đăng WordPress. Chỉ là kho bản gốc chuẩn bị nghiên cứu–tiếp nhận. Đây không phải bằng chứng G1–G7 PASS.

## Ba bài biên tập

| Phường mới | Tiêu đề H1 | File | Đếm từ sơ bộ theo quy tắc tách âm tiết của `scripts/qa.py` |
| --- | --- | --- | ---: |
| Bồ Đề | Thuê xe máy phường Bồ Đề: chọn Honda Vision hay Wave, nhận xe ở đâu? | [01-bo-de.md](batch-01/01-bo-de.md) | 4.564 |
| Cửa Nam | Thuê xe máy phường Cửa Nam: chọn Air Blade, tính gói ngày hay tuần? | [02-cua-nam.md](batch-01/02-cua-nam.md) | 4.726 |
| Hoàn Kiếm | Thuê xe máy phường Hoàn Kiếm: đi phố cổ chọn xe ga, xe số hay 50cc? | [03-hoan-kiem.md](batch-01/03-hoan-kiem.md) | 4.484 |

## Quy tắc bắt buộc khi đưa bài lên WordPress (20/10/2026)

**Đã tạo và đọc lại từ WordPress thật:**
- Blog `id=69, parent=0`
- Hướng dẫn thuê xe `id=162, parent=69`
- **Thuê xe máy theo phường Hà Nội `id=182, parent=162, slug=thue-xe-may-theo-phuong-ha-noi`** — [xem archive](https://thuexemaynguyentu.com/blog/huong-dan-thue-xe/thue-xe-may-theo-phuong-ha-noi/).
- Mã taxonomy chính thức trong `data/taxonomy.json`: **`hanoi-ward-rentals`**. Không tạo danh mục phường khác; không chọn `rental-guide` hoặc `blog` làm danh mục thay thế.

**Thứ tự vận hành cho 51 bài:** giữ bài Markdown gốc trong `editorial/seo-51-phuong/` → so intent/slug/canonical với các bài đã đăng + toàn bộ Topic Factory → Researcher lập nguồn thật, evidence_text và source_sha256 (không tự tạo từ việc nhìn link) → Topic Factory **PLANNED** có `campaign_id: HN-51-WARDS` và `taxonomy_key: hanoi-ward-rentals` → Writer hợp lệ giữ lease của Topic ID, chuyển nội dung đã kiểm chứng thành Markdown theo `docs/ARTICLE-CONTRACT.md` (bỏ H1 Markdown, để WordPress title sinh H1; metadata và body SHA thật) → QA G1–G6, SEO ≥85, Quality ≥85, category/URL chính xác → Publisher duy nhất đăng trạng thái **publish** vào **đúng term ID 182** → đọc lại G7, kiểm chứng permalink, canonical, Yoast SEO và duy nhất `categories=[182]` → cập nhật `progress.json` có Topic ID/WordPress ID/URL thật.

**Không WordPress draft, không giả QA PASS và không đăng nhầm:** nếu thiếu Research QA, writer lease, nguồn thật, sai taxonomy, trùng intent/slug, không thể đọc danh mục chính xác hoặc QA <85/REVIEW, **giữ tại GitHub để sửa**. Mã Publisher đã có chốt `HANOI_WARD_CATEGORY_HOLD` và `HANOI_WARD_PUBLIC_ONLY`; không tự tạo term mới và không fallback sang Blog/danh mục cha. Tài khoản WPVibe có thể hết quota, có thể dùng WP Agent để đọc lại WordPress.

**Ưu tiên xử lý:** 9 bản đầu (Bồ Đề, Cửa Nam, Hoàn Kiếm, Việt Hưng, Tây Hồ, Đống Đa, Ngọc Hà, Giảng Võ, Hai Bà Trưng), rồi ba bản lô 04 (Bạch Mai, Vĩnh Tuy, Cầu Giấy). Hiện 12/51 bài viết xong nhưng **0 bài thuộc chiến dịch đã được nhập Topic Factory hoặc đăng WordPress**. Việc WP REST xác nhận 9 slug chưa bị trùng chính xác **không** thay cho kiểm tra trùng search intent. Lịch mỗi giờ và lượt duyệt thủ công cùng đọc `progress.json` để tránh tranh chấp.

## Lô 02/17 — Việt Hưng, Tây Hồ, Đống Đa

| Phường mới | Tiêu đề H1 | File | Đếm từ sơ bộ theo quy tắc `scripts/qa.py` |
| --- | --- | --- | ---: |
| Việt Hưng | Thuê xe máy phường Việt Hưng: chọn Honda Wave hay Yamaha Sirius để đi làm theo tuần? | [04-viet-hung.md](batch-02/04-viet-hung.md) | ~4.495 |
| Tây Hồ | Thuê xe máy phường Tây Hồ: chọn Honda Vision hay xe điện cho hành trình quanh hồ? | [05-tay-ho.md](batch-02/05-tay-ho.md) | ~4.873 |
| Đống Đa | Thuê xe máy phường Đống Đa: sinh viên chọn Honda Wave, Cub 50 hay SYM 50cc? | [06-dong-da.md](batch-02/06-dong-da.md) | ~4.600 |

Nguồn hành chính từ cổng [Việt Hưng](https://viethung.hanoi.gov.vn/gioi-thieu-chung/gioi-thieu-chung-ve-phuong-viet-hung-2783250629163216816.htm), [Tây Hồ](https://tayho.hanoi.gov.vn/gioi-thieu-chung-65783/gioi-thieu-chung-phuong-tay-ho-2697250628103656273.htm), [Đống Đa](https://dongda.hanoi.gov.vn/gioi-thieu-chung-62989/gioi-thieu-chung-ve-phuong-dong-da-thanh-pho-ha-noi-2806250627173844843.htm), và [Luật Trật tự, an toàn giao thông đường bộ 2024](https://vbpl.vn/bonoivu/Pages/vbpq-print.aspx?ItemID=170620) cho điều kiện phương tiện. Giá/NAP từ `data/business-facts.json`.

**Lưu ý:** Yamaha Sirius, Cub 50, SYM 50cc chỉ là **mẫu để hỏi cửa hàng**; không suy đoán tình trạng tồn kho, giá từng mẫu, chi nhánh mới, hay cam kết giao miễn phí. Theo điều khoản website Nguyễn Tú, người thuê tối thiểu 18 tuổi, dù luật giao thông có quy định riêng cho người 16 tuổi lái loại xe gắn máy phù hợp; phải kiểm tra nguồn/điều khoản thật trước khi xuất bản.

## Lô 03/17 — Ngọc Hà, Giảng Võ, Hai Bà Trưng

| Phường mới | H1 | File | Đếm từ sơ bộ |
| --- | --- | --- | ---: |
| Ngọc Hà | Thuê xe máy phường Ngọc Hà: Honda Click hay Yamaha Mio, đi ba ngày thế nào? | [07-ngoc-ha.md](batch-03/07-ngoc-ha.md) | 4.459 |
| Giảng Võ | Thuê xe máy phường Giảng Võ: đi làm theo tháng chọn Honda Air Blade hay Wave? | [08-giang-vo.md](batch-03/08-giang-vo.md) | 4.763 |
| Hai Bà Trưng | Thuê xe máy phường Hai Bà Trưng: chọn Honda Vision hay Wave khi có nhiều điểm hẹn? | [09-hai-ba-trung.md](batch-03/09-hai-ba-trung.md) | 4.854 |

Tham khảo chính thức: [Ngọc Hà](https://ngocha.hanoi.gov.vn/gioi-thieu-chung/ngoc-ha-dong-chay-cua-van-hoa-ngan-nam-tiep-tuc-khoi-dong-phat-trien-trong-thoi-dai-moi-2802250628080417605.htm), [Giảng Võ](https://giangvo.hanoi.gov.vn/ban-do-dia-gioi-phuong/ban-do-dia-gioi-hanh-chinh-phuong-giang-vo-2808250701094557434.htm), [Hai Bà Trưng](https://haibatrung.hanoi.gov.vn/gioi-thieu/phuong-hai-ba-trung-dau-an-moi-trong-lo-trinh-phat-trien-thu-do-2814250625151256399.htm). Mức giá xe theo `data/business-facts.json`; các điều khoản phải đối chiếu lại lúc nhập Topic Factory.

**Góc tìm kiếm khác nhau:** Ngọc Hà cho thuê xe ga Click/Mio 3 ngày; Giảng Võ so gói tháng Air Blade/Wave cho người làm việc; Hai Bà Trưng chọn Vision/Wave cho nhiều điểm hẹn. Không xác nhận chi nhánh tại ba phường, không suy đoán miễn phí giao xe hoặc xe còn sẵn. Mỗi bài có đúng một H1, liên kết nguồn chính thức và tối thiểu 2 liên kết nội bộ.

## Lô 04/17 — Bạch Mai, Vĩnh Tuy, Cầu Giấy

| Phường mới | H1 | File | Đếm từ theo quy tắc QA gần đúng |
| --- | --- | --- | ---: |
| Bạch Mai | Thuê xe máy phường Bạch Mai: chọn Wave hay xe ga 50cc khi đi học, đi thực tập? | [10-bach-mai.md](batch-04/10-bach-mai.md) | ~4.033 |
| Vĩnh Tuy | Thuê xe máy phường Vĩnh Tuy: Honda Vision hay Air Blade cho lịch qua cầu, đi nhiều điểm? | [11-vinh-tuy.md](batch-04/11-vinh-tuy.md) | ~4.342 |
| Cầu Giấy | Thuê xe máy phường Cầu Giấy: Honda Vision hay Yamaha Janus cho người đi làm một tuần? | [12-cau-giay.md](batch-04/12-cau-giay.md) | ~4.791 |

Nguồn địa giới từ cổng chính quyền [Bạch Mai](https://bachmai.hanoi.gov.vn/dang-doan-the/dai-hoi-dai-bieu-dang-bo-phuong-bach-mai-lan-thu-nhatnhiem-ky-2025-2030-2821250729163538002.htm), [Vĩnh Tuy](https://vinhtuy.hanoi.gov.vn/gioi-thieu/y-nghia-ten-goi-phuong-vinh-tuy-moi-sau-01-7-2025-2823250629163913423.htm) và [Cầu Giấy](https://caugiay.hanoi.gov.vn/gioi-thieu-chung/gioi-thieu-chung-2805250626170626104.htm). NAP và giá tham khảo từ `data/business-facts.json`. Không khẳng định xe Janus, SYM hoặc Cub có sẵn, chi nhánh ở phường, giá xe điện/Janus, phí giao miễn phí hoặc hướng cầu luôn được phép đi. Bạch Mai nói đến quyết định Wave/50cc cho lịch thực tập; Vĩnh Tuy bàn chọn xe ga và giao thông qua sông; Cầu Giấy hướng đến làm việc theo tuần và đối chiếu Janus chưa có giá xác minh.

**Lưu ý kiểm tra:** WPVibe đã báo giới hạn lượt gọi; vì vậy kiểm tra đối chiếu WordPress trực tiếp với ba bài mới **chưa hoàn tất**, phải làm lại trước Research Intake/đăng. Đây vẫn là 3 bản biên tập, chưa có G1–G7 hoặc Topic ID, không sửa dữ liệu Production.

## Phạm vi và nguồn

- Sử dụng địa giới mới của phường [Bồ Đề](https://bode.hanoi.gov.vn/gioi-thieu-chung/gioi-thieu-phuong-bo-de-2831250626121314553.htm), [Cửa Nam](https://cuanam.hanoi.gov.vn/gioi-thieu/gioi-thieu-chung-ve-phuong-cua-nam-2801250629153745569.htm), [Hoàn Kiếm](https://hoankiem.hanoi.gov.vn/chi-dao-cua-dia-phuong/dai-hoi-dai-bieu-dang-bo-phuong-hoan-kiem-lan-thu-i-nhiem-ky-2025-2030-2812250723162946227.htm).
- Dữ kiện doanh nghiệp lấy từ [`data/business-facts.json`](../../data/business-facts.json) và [website Nguyễn Tú](https://thuexemaynguyentu.com/): 112 Nguyễn Văn Cừ, Bồ Đề; 0942 467 674; 09:00–21:00; Wave 150.000đ/ngày; Vision và Air Blade 200.000đ/ngày; xe tay ga 50cc 200.000đ/ngày. Giá theo gói, tiền cọc và phí giao nhận phải được xác minh theo thời điểm/đúng mẫu xe.
- Không giả rằng có chi nhánh tại Cửa Nam/Hoàn Kiếm; không khẳng định SYM/Cub/Vision/Air Blade luôn còn sẵn; không tự bịa phí giao, khuyến mại, trải nghiệm khách, luật.
- Mỗi bài có H1 riêng, từ khóa/phường đặt tự nhiên, có các liên kết nội bộ đã kiểm tra trạng thái `publish`. Hai bài khác góc tìm kiếm không phải hoán đổi tên phường.
- **Thông tin thời gian và bảng giá phải rà lại ngay trước khi đăng.** Hai nguồn nội bộ và nguồn chính quyền là tham chiếu biên tập, chưa phải `research.external_sources` với bằng chứng hash như yêu cầu của hệ thống.

## Điều kiện đưa vào pipeline

1. Đối chiếu bài/bản ghi WordPress hiện tại và danh sách topic trên `main` ngay trước lúc nhập. Không tạo 51 landing pages giống nhau, không sửa slug/canonical bài cũ.
2. Researcher tạo ba topic **riêng** hợp lệ bằng nhánh `research/<session>`, lưu snapshot nguồn, kiểm tra `intent-check`, `check`, push và chờ Research Intake trên `main` chấp nhận. **Không tự chèn vào `data/topics.jsonl`** hoặc chiếm Topic ID của phiên khác.
3. Writer có lease trống nhận đúng ba chủ đề, chuyển ba bản biên tập thành bài `posts/drafts/NT-XXXXXX.md` theo `docs/ARTICLE-CONTRACT.md`: metadata khớp manifest, mở đầu trùng `direct_answer`, nội dung bỏ H1 Markdown (WordPress tự tạo H1), hash, source evidence và receipt của session thật.
4. QA trên hệ thống phải xác nhận SEO ≥85, Quality ≥85, G1–G6; Publisher chỉ được chạy khi chính sách chủ website cho phép. `publisher_pilot.max_posts=3` đang sử dụng hết 3 lần trước; **không được tự nâng hoặc gỡ giới hạn**. Việc đăng mới đòi hỏi quyết định tách biệt của chủ website và xác minh G7.
5. Sau khi xuất bản thành công, cập nhật `progress.json` với Topic ID, WordPress ID, permalink và ngày xác minh; không đếm bản thảo thành bài đã đăng.

**Tiến độ biên tập:** **12/51**, còn **39 bài trong 13 lượt duyệt**. Đã biên tập lô 01–04; **0/12 bài biên tập được nhập Topic Factory hoặc đăng WordPress**. Không tự nới `publisher_pilot`. Lượt tự động mỗi giờ phải đọc `progress.json` để tránh trùng lượt thủ công.
