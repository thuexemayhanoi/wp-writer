# Cụm SEO 51 phường Hà Nội — lô 01/17

**Tình trạng:** Ba **bản biên tập** đã viết, **chưa phải bản thảo Topic Factory**, chưa gán ID/lease, chưa kiểm tra đủ Research QA và chưa đăng WordPress. Chỉ là kho bản gốc chuẩn bị nghiên cứu–tiếp nhận. Đây không phải bằng chứng G1–G7 PASS.

## Ba bài biên tập

| Phường mới | Tiêu đề H1 | File | Đếm từ sơ bộ theo quy tắc tách âm tiết của `scripts/qa.py` |
| --- | --- | --- | ---: |
| Bồ Đề | Thuê xe máy phường Bồ Đề: chọn Honda Vision hay Wave, nhận xe ở đâu? | [01-bo-de.md](batch-01/01-bo-de.md) | 4.564 |
| Cửa Nam | Thuê xe máy phường Cửa Nam: chọn Air Blade, tính gói ngày hay tuần? | [02-cua-nam.md](batch-01/02-cua-nam.md) | 4.726 |
| Hoàn Kiếm | Thuê xe máy phường Hoàn Kiếm: đi phố cổ chọn xe ga, xe số hay 50cc? | [03-hoan-kiem.md](batch-01/03-hoan-kiem.md) | 4.484 |

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

**Tiến độ biên tập:** 3/51, còn 48 bản thảo trong 16 lượt duyệt tiếp. Theo kế hoạch chủ website duyệt mỗi lượt 3 bài.
