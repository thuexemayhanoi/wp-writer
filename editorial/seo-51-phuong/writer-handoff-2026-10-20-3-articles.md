# SEO 51 phường — bàn giao 3 bài cũ cho Writer (20/10/2026)

**Nguồn sự thật:** `main` / `data/topics.jsonl`, `reports/topic-qa.json`, `editorial/seo-51-phuong/pipeline-queue.json`, WordPress REST site Nguyễn Tú.

**Trạng thái:** Research QA đã PASS cho đúng 3 Topic ID; **chưa có Writer lease/receipt cho 3 ID này; Writer QA chưa PASS; WordPress 0/3; G7 0/3.** Tài liệu này chỉ ghi nhận bước kiểm tra, tuyệt đối không phải chứng nhận Writer QA hay lệnh ép xuất bản.

## Bảng bàn giao

| Phường | Topic ID đã tồn tại (PLANNED) | File biên tập gốc | Số từ tách khoảng trắng (ước lượng, chưa là số đếm QA) | H2 | WordPress |
|---|---|---|---:|---:|---|
| Bồ Đề | `NT-001101` | `editorial/seo-51-phuong/batch-01/01-bo-de.md` | ~3.064 | 12 | Chưa tạo |
| Cửa Nam | `NT-001102` | `editorial/seo-51-phuong/batch-01/02-cua-nam.md` | ~3.123 | 12 | Chưa tạo |
| Hoàn Kiếm | `NT-001103` | `editorial/seo-51-phuong/batch-01/03-hoan-kiem.md` | ~2.999 | 11 | Chưa tạo |

**Danh mục duy nhất:** `hanoi-ward-rentals` → WordPress Term ID **182**, parent **162**, ancestor **69**. Không tạo thêm danh mục từng phường. Canonical và slug lấy chính xác từ ba Topic ID trên, không tự đặt lại.

## Nguồn địa giới đã đọc, 20/10/2026

- **Bồ Đề:** https://bode.hanoi.gov.vn/gioi-thieu-chung/gioi-thieu-phuong-bo-de-2831250626121314553.htm — mô tả Ngọc Lâm, Bồ Đề, Ngọc Thụy, Gia Thụy và phần phường lân cận.
- **Cửa Nam:** https://cuanam.hanoi.gov.vn/gioi-thieu/gioi-thieu-chung-ve-phuong-cua-nam-2801250629153745569.htm — phường mới vận hành từ 01/07/2025, khu ga Hà Nội, Trần Hưng Đạo, Lê Duẩn.
- **Hoàn Kiếm:** https://hoankiem.hanoi.gov.vn/chi-dao-cua-dia-phuong/dai-hoi-dai-bieu-dang-bo-phuong-hoan-kiem-lan-thu-i-nhiem-ky-2025-2030-2812250723162946227.htm — phường mới có Hàng Mã, Hàng Bồ, Hàng Đào, Hàng Bạc, Hàng Buồm, Hàng Gai, Lý Thái Tổ.
- Các nguồn đã được truy xuất bằng công cụ tìm/trích xuất trang trong lượt làm việc; Firecrawl riêng từng URL gặp lỗi proxy. Bản gốc Research QA có `external_sources` và `reviewed_content_hashes` theo topic registry. **Không tự chế hay thay thế source hash trong tài liệu này.**

## Giá/NAP đối chiếu repo

Nguồn: `data/business-facts.json` (owner verified 16/10/2026). Nguyễn Tú — **112 Nguyễn Văn Cừ, Bồ Đề, Hà Nội**, **0942 467 674**, **09:00–21:00**. Wave **150.000đ/ngày**, Vision và Air Blade **200.000đ/ngày**, xe tay ga 50cc **200.000đ/ngày**. Giá điện / phí giao nhận phải liên hệ, không tự bịa. Đặt cọc tùy mẫu. Cửa hàng **không được mô tả là có chi nhánh Cửa Nam/Hoàn Kiếm**.

## Đã kiểm tra WordPress REST

1. Danh mục `182` tồn tại, parent `162`, count = `0` tại thời điểm đọc.
2. Ba slug dự kiến của các topic `NT-001101`, `NT-001102`, `NT-001103`: `GET /wp/v2/posts?slug=...&context=edit` đều trả `[]`. Đây **chỉ là kiểm tra trùng slug chính xác**; kiểm tra trùng ngữ nghĩa vẫn thuộc QA.
3. 5 URL nội bộ ở các bài đã xác nhận thuộc **published posts**: bài chọn xe ga cho người mới `#2590`, hướng dẫn thuê xe máy du lịch `#2613`, hợp đồng thuê xe `#891`, thuê 50cc Hà Nội `#895`, lựa chọn xe số đi 1–3 tháng `#2588`. Những link khác vẫn cần QA đầy đủ.

## Việc Writer hợp lệ phải làm tiếp

1. **Không chiếm hoặc tự giải phóng W1–W9** đang có lease. Theo snapshot `data/state/writer-claims.json` được đọc lúc khoảng **13:40 ICT ngày 20/10**, 9/9 slot còn hợp đồng lease; hạn sớm nhất W8 **16:00:40 ICT**, muộn nhất khoảng **22:41:45 ICT**. Lease có thể được gia hạn bất kỳ lúc nào, phải đọc mới trước claim.
2. Khi **slot auto trống thật**, dùng đúng `scripts/writer-session.py begin` hoặc **request action `begin` có receipt xác thực**, không tự gán slot. Chỉ viết/submit ba Topic ID nêu trên, mỗi lượt tối đa 3; không chiếm ID của phiên khác.
3. Biến nội dung biên tập đã có thành article theo `docs/ARTICLE-CONTRACT.md`, đối chiếu field từng topic và lấy source từ topic registry (không sáng tác hash/review). Chạy QA đầy đủ **SEO ≥85, Quality ≥85, G1–G6 PASS**, repair thật nếu lỗi.
4. QA PASS → Publisher hiện hữu → WordPress **publish**, danh mục **182 duy nhất** → G7 xác minh **post_id, URL, published status, category, canonical, SEO**. Không tạo WordPress draft và không override policy của chiến dịch 2.000 chủ đề.
5. Chỉ sửa `progress.json` / `pipeline-queue.json` bằng số liệu đã xác thực sau mỗi bước, không tự nâng lên Writer QA PASS hay G7 PASS.

**Kết luận:** Tài liệu lưu bằng chứng có thể tái sử dụng, không phải bài đăng và không phải QA giả. Ưu tiên khép 3 bài này trước khi làm lô 04–06.
