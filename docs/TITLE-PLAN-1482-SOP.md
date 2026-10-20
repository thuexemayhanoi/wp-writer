**CẬP NHẬT 20/10/2026 — ƯU TIÊN QUY ĐỊNH NÀY:** Chủ duyệt **SEO ≥76/100, Quality ≥76/100**, giữ đủ G1–G7. G3 chỉ kiểm nguồn URL HTTPS an toàn/nguồn chính thức khi nói luật; nội dung trích dẫn thay đổi hoặc link cũ/khó mở sẽ ghi **cảnh báo audit sau**, không tự giữ bài. Trạng thái `source_advisories` và `live_checked=false` phải trung thực; không bịa nguồn, luật, giá, trải nghiệm. Giữ Writer lease, chống trùng URL/intent, parent/child, canonical, ledger, công tắc Production và G7. Mọi chỗ còn nhắc 85 là hướng dẫn cũ đã thay bởi cấu hình hiện hành.

# AI SOP A–Z — 1.482 tiêu đề Excel, một đường viết → QA → WordPress

**Phiên bản:** 20/10/2026 · **Repo duy nhất:** `thuexemayhanoi/wp-writer` · **Website duy nhất:** https://thuexemaynguyentu.com

> **ĐỌC TRANG NÀY TRƯỚC** nếu người dùng nói “viết tiếp Excel”, “duyệt tiếp”, “tiếp tục 3 bài”, “QA rồi publish”. Đây là tài liệu điều phối duy nhất cho **kế hoạch 1.482 tiêu đề mới**; các hợp đồng kỹ thuật trong `docs/WRITER-RESEARCH-CONTRACT.md`, `docs/ARTICLE-CONTRACT.md`, `docs/SEO-QA-V2.md`, `docs/PIPELINE-V3.md` vẫn có hiệu lực. Nếu có khác biệt: không bỏ qua bất kỳ điều kiện QA/lease/ledger bảo vệ nào trong mã thực tế.

## 0. Học một lần, không đọc lại toàn repo

**Khi mở phiên mới:** đọc **chỉ bốn nguồn nhỏ**:
1. **Tài liệu này** (quy trình, trường dữ liệu, ngoại lệ).
2. `editorial/title-plan-1482/plan.json`: chỉ **1–3 dòng đang chọn**, không copy cả 1.482 dòng vào cuộc trò chuyện. Trên máy có Python: `python scripts/title_plan_next.py --limit 3`.
3. `data/taxonomy.json`: chỉ mục có `taxonomy_key` đã gán; WordPress Term ID đã có thật.
4. `data/business-facts.json` và topic đã được Topic Factory cấp, nếu bắt đầu viết.

**Chỉ khi có lỗi cụ thể:** đọc mục tương ứng trong `docs/ARTICLE-CONTRACT.md`, `docs/SEO-QA-V2.md`, `docs/WRITER-QUICKSTART.md` và file QA của **đúng Topic ID**. Không quét lại mọi tài liệu và mọi bài 518 trang ở mỗi lượt, nhưng **phải đối chiếu lại các bài gần trùng về intent trước khi nghiên cứu/đăng**.

**Chỉ dùng bản ghi thật trên GitHub; không suy đoán trạng thái của file hoặc WordPress khi mất mạng.** Các số 518/1.482 là snapshot và kế hoạch tại 20/10/2026; số bài hiện tại có thể thay đổi.

## 1. Vai trò của Excel, JSON và hàng đợi thật (rất dễ nhầm)

| Thành phần | Dùng để làm gì | Không được dùng làm gì |
|---|---|---|
| `editorial/title-plan-1482/seo-tieu-de-{01,02,03}-494.xlsx` | Ba bảng cho con người kiểm tra 494 tiêu đề/tệp, mục `Hướng dẫn` có A–Z | Không phải lệnh WordPress; không phải bằng chứng QA |
| Ba tệp `.csv` tương ứng | Đọc cùng dữ liệu nhanh, không cần thư viện Excel | Không dùng CSV để quyết định đã xuất bản |
| `editorial/title-plan-1482/plan.json` | Chứa `TP-0001…TP-1482`, tiêu đề ứng viên, intent, term ID cha/con, trạng thái bản kế hoạch | Không cấp tự động quyền viết hoặc xuất bản |
| `editorial/title-plan-1482/status.json` | Trạng thái dẫn xuất theo từng mã TP; cập nhật theo biên nhận thật | Không sửa tay để thành PASS |
| `data/topics.jsonl` | **Topic Registry chính thức:** `NT-XXXXXX`, slug/canonical/intent/taxonomy đã qua Research QA | Không tạo thêm topic trùng một TP |
| `data/state/writer-claims.json` | Quyền giữ topic theo W1–W9, phiên và SHA nộp | Không cướp hoặc tự viết lease |
| `data/state/publication-ledger.json` | Sổ Publisher, POST_INTENT, VERIFIED, G7 | Không tự thêm receipt hoặc G7 PASS |

**Quy tắc quan trọng:** Có một hàng `TP-*` chưa đồng nghĩa có một topic `NT-*` có thể claim. Phải nghiên cứu thật, qua Research QA/Topic Factory, tạo Topic Registry PLANNED **một lần** rồi mới giao Writer.

## 2. Sáu bước cho một tiêu đề (lặp 1–3 bài/lượt)

1. **Chọn** 1–3 mã TP có `status=PLANNED` và chưa gắn `title_plan_id` vào topic khác. Trên GitHub có thể đọc đúng dòng trong `plan.json`; trên máy tính: `python scripts/title_plan_next.py --limit 3`. Trường `suggested_slug` chỉ là gợi ý, phải duyệt chống trùng URL.
2. **Lọc trùng:** tìm exact slug, tên và *search intent* trên bài WordPress hiện tại, `baseline-518.json`, `data/topics.jsonl` và các topic đang có người claim. Nếu ý định tìm kiếm đã được bài cũ phục vụ tốt, **HOLD** mã TP và ghi lý do; không tạo bài mới chỉ vì đổi cách đặt tiêu đề. Không sinh thêm cụm chính xác “thuê xe máy Hà Nội” hàng loạt. Chiến dịch **51 phường** riêng ở Term **182**, không lấy lại ba bài Bồ Đề/Cửa Nam/Hoàn Kiếm.
3. **Research:** đọc **1–4 trang HTTPS phù hợp** (không mặc định đủ một nguồn cho mọi chủ đề). Mỗi nguồn ghi `url`, `checked_at`, `supports`, đoạn `evidence_text` **đọc thật**, `source_sha256` tính từ văn bản đã tải. Chính sách/luật/GPLX/độ tuổi cần kiểm tra văn bản chính thức còn hiệu lực. Thông số theo hãng và đúng mẫu/đời xe; giá, cọc, địa chỉ theo `data/business-facts.json`. **Không bịa hash, nguồn, số liệu, trải nghiệm.**
4. **Topic Factory / Research QA:** chuẩn bị ứng viên với `title_plan_id: TP-XXXX` và toàn bộ metadata research hợp lệ, `taxonomy_key` đúng danh mục, `word_target_min=1600`, `word_target_max=5000`; dùng `research/<session>`, `data/candidates/<session>-0001.jsonl`, checkpoint/QA/trusted intake theo `docs/RESEARCH-V2-GLOBAL-ADAPTATION.md`. **Chỉ khi topic `NT-XXXXXX` thành PLANNED** mới claim W1–W9. Nếu chỉ có điện thoại/GitHub API, vẫn phải theo request/candidate hợp lệ; không sửa trực tiếp registry để lách intake.
5. **Writer:** ưu tiên REPAIR của chính session trước; sau đó `python scripts/writer-session.py begin --slot auto --count 1 --session s-<stable-session>` hoặc request JSON ở `docs/WRITER-QUICKSTART.md`. Chỉ viết đúng Topic ID được cấp. Lưu `posts/drafts/NT-XXXXXX.md` với frontmatter theo `docs/ARTICLE-CONTRACT.md`, **1.600–5.000 từ hữu ích**, intent riêng, 4+ H2, trả lời trực tiếp, internal link thật. Kiểm QA G1–G6, **SEO ≥76 và Quality ≥76**, sửa lỗi REPAIR rồi push đúng session. Không tự cấp W1 và không ghi đè Writer khác.
6. **Publisher & đánh dấu:** Publisher trên `main` tự nhận **bài đã QA PASS và có writer receipt hợp lệ**, đăng vào **duy nhất category đúng Term ID**, ghi POST_INTENT **trước** POST, đọc lại **G7**. Chỉ khi `phase=VERIFIED`, `g7.status=PASS` và đủ check có thật → `title-plan-1482-sync.yml` đồng bộ `PUBLISHED_G7_PASS`, WordPress ID và URL trong plan/CSV/XLSX. **Workflow SUCCESS không thay cho WordPress/G7.** Nếu G7 hoặc WordPress lỗi: HOLD/NEEDS_RECONCILE, không POST lại mù; nguồn tham khảo đổi hoặc không mở được chỉ ghi cảnh báo audit.

## 3. Quy tắc URL đẹp — tên Excel tuyệt đối không lọt vào permalink

- Slug mới lấy **ý nghĩa của tiêu đề được duyệt**, viết chữ thường không dấu, nối bằng `-`, đủ ngắn và độc nhất. Ví dụ `doi-mau-xe-khi-nhan-cac-tinh-huong-thuong-gap`.
- `TP-0001`, `excel`, `xlsx`, `csv`, `seo-tieu-de-01-494`, `tu-file-excel` chỉ là metadata, **không bao giờ là slug** của bài thuộc kế hoạch này.
- `canonical_target = https://thuexemaynguyentu.com/<proposed_slug>/`; không tự thêm đường dẫn `/excel/`, `/blog/excel/` hoặc đường dẫn phân loại. Chỉ dùng slug đã thông qua chính sách `scripts/slug_policy.py`.
- **Không sửa slug/canonical, redirect hàng loạt hoặc xóa URL đã xuất bản.** Nếu phát hiện bài cũ từng bị dính `excel`, lập danh sách và xác minh SEO trước khi đề xuất 301 từng bài; không tự sửa vì có thể ảnh hưởng index.

## 4. Danh mục: giữ nguyên 18 Term ID, không tạo thêm

Từ 1.482 dòng đề xuất, mỗi danh mục có **82–83 tiêu đề**, phân bổ như sau:

| Term ID | Taxonomy key | Nhóm |
|---|---|---|
| 163 | rental-procedures | Thủ tục và giao nhận |
| 164 | rental-costs | Chi phí thuê xe |
| 165 | rental-50cc | Sử dụng xe thuê 50cc |
| 166 | ebikes | Xe đạp điện |
| 167 | battery-charging | Pin và sạc |
| 168 | electric-tech | Công nghệ xe điện |
| 160 | electric-maintenance | Chăm sóc xe điện |
| 169 | electric-transition | Điện hóa và hạ tầng |
| 170 | engine-care | Chăm sóc xe máy |
| 161 | road-safety | An toàn khi di chuyển |
| 171 | driving-licence | Giấy phép và giấy tờ |
| 172 | hanoi-travel | Khám phá Hà Nội |
| 173 | vietnam-travel | Hành trình Việt Nam |
| 174 | food-culture | Ẩm thực và văn hóa |
| 175 | trip-planning | Lập kế hoạch chuyến đi |
| 176 | urban-mobility | Di chuyển đô thị |
| 177 | green-travel | Du lịch xanh |
| 156 | reviews | Đánh giá và so sánh xe |

Luôn xác minh `wordpress_term_id` + `wordpress_parent_id` trong `data/taxonomy.json` và WordPress REST trước khi đăng. Không gán Uncategorized, không tạo danh mục phường mới.

## 5. Nếu mất mạng/quota, trở lại trong 30 giây

Lưu checkpoint **thực tế đã ghi lên GitHub**, chỉ gồm: `TP-ID`, `NT-ID nếu có`, `session`, `slot`, `branch`, `file/commit SHA`, `giai đoạn hiện tại`, `lỗi gần nhất`, `bước kế tiếp`. Cụ thể:

- **Chưa có NT:** đọc lại đúng TP, Research checkpoint, xác minh không bị intake phiên khác nhận, tiếp tục nghiên cứu.
- **Đã có NT + đang WRITING/REPAIR:** đọc `data/state/writer-claims.json` và `docs/WRITER-AUTO-REPAIR.md`; khôi phục session/lease hợp lệ, không đổi session để vượt quota hoặc giành quyền.
- **QA PASS nhưng chưa đăng:** kiểm `data/qa/NT-*.json`, receipt và pipeline board; không trực tiếp POST WordPress để tiết kiệm thời gian.
- **Publisher timeout:** đối soát `publication-ledger.json`, WordPress ID/marker/slug trước; tuyệt đối không POST lại khi `POST_INTENT` chưa được phân giải.
- **Đã VERIFIED nhưng Excel chưa đổi:** đọc ledger và workflow sync; **không tự sửa bảng** thành PASS.

**Giữ nguyên mọi trạng thái chưa xác minh khi offline; chỉ báo những gì đã kiểm được.**

## 6. Lệnh ngắn để chủ dùng trên iPhone (dán vào ChatGPT/Claude)

> Mở `thuexemayhanoi/wp-writer`. Đọc `AGENTS.md` và `docs/TITLE-PLAN-1482-SOP.md` trước. Tiếp tục **3 mã TP PLANNED tiếp theo** trong `editorial/title-plan-1482/plan.json`; loại trùng với WordPress/Topic Registry, nghiên cứu 1–4 nguồn thật, đưa qua Research QA/Topic Factory, claim W1–W9 đúng lease, viết theo `ARTICLE-CONTRACT`. Bài đạt SEO ≥76, Quality ≥76, G1–G6 PASS và có receipt hợp lệ thì Publisher tự đăng WordPress; sau G7 PASS mới đánh dấu Excel. URL theo tiêu đề, không có chữ excel. Ưu tiên REPAIR đang sở hữu; hết quota giữ checkpoint và dừng, không giả QA hay ghi đè. **Làm trực tiếp nếu có kết nối, báo TP-ID/NT-ID/WordPress ID/URL thực tế; không hỏi duyệt từng bài.**

## 7. Trạng thái được phép và báo cáo gọn

`PLANNED` (chưa Research QA) → topic `RESEARCH` → topic `PLANNED` (Research PASS) → `WRITING` → `QA/REPAIR` → `READY` → `PUBLISHING` → `PUBLISHED_G7_PASS`.

Mã TP có thể vẫn `PLANNED` trong file xuất cho đến lúc ledger xác minh; tiến trình trung gian phải tra topic/claims/QA thật. Báo cáo mỗi lượt một dòng cho mỗi TP: `TP-ID | NT-ID | WordPress ID | category | QA | URL | lỗi/cần làm`. **Không nói “đã đăng” chỉ vì commit/CI xanh.**

**Lưu ý phạm vi:** Đây là *bộ tài liệu giúp AI nhanh hơn*, không tự cung cấp bộ não AI cho GitHub Actions, không thêm API/mật khẩu mới, không hạ cổng QA, không tự bật/tắt production.
