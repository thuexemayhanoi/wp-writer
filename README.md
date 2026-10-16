# WP-WRITER — UNIVERSAL AI CONTENT FACTORY FOR WORDPRESS


> **SEO QA V2 / Website chính:** Bài mới chỉ đủ điều kiện WordPress **Published** khi **SEO ≥85/100**, Quality ≥75 và cả sáu cổng đều PASS. QA chấm title/meta, câu trả lời đầu bài, H2, linking, anchor, URL theo intent; SEO 84 → FAIL/REPAIR. Không bắt buộc ảnh/FAQ/CTA quảng cáo cho mọi bài. Xem [SEO QA V2](docs/SEO-QA-V2.md). **Production vẫn dry_run**, thay đổi ngưỡng không tự bật đăng bài.


**AI bên ngoài — một lệnh để bắt đầu:** [AI-START-HERE.md](docs/AI-START-HERE.md). Nhận tối đa 10 chủ đề, QA từng bài, tự nộp và nhận tiếp; không xin duyệt từng bài. Publisher đã kết nối sau QA nhưng **Production hiện OFF**; không tuyên bố đã đăng công khai khi không có ledger và URL verified.

> **QA → WordPress ngay, 2+2+2+2+2:** xem [Instant Publishing](docs/INSTANT-PUBLISHING.md). QA PASS trên main tự kích hoạt Publisher không cần cron; tối đa 5 batch × 2 bài, daily cap 10. **Unattended Production vẫn OFF** do bảo vệ code đặc quyền và E2E GitHub Publisher chưa nghiệm thu. Main đã có Ruleset, Yoast REST smoke PASS; hai bài public #3888 và #3890 là kiểm thử **thủ công bằng WPVibe**.

> **Topic Discovery V3:** [Autonomous research queue → external AI researcher → Topic QA → W1/W2/W3](docs/AUTONOMOUS-TOPIC-RESEARCH.md). Runs every 6h without AI API keys, gathering public RSS *leads* plus topical gaps, capped at 20 ideas/batch and 300 pending; discovery proposal capacity 10,000. **This is not an LLM doing autonomous factual research**: external AI researchers must independently verify and submit evidence before an idea becomes PLANNED. Canonical intake remains approved only to 1,000; WordPress Production remains OFF.

> **Factory Operations V2:** [Liveness + queue/refill + Writer request safety + post-publish SEO QA](docs/FACTORY-OPERATIONS-V2.md). Adapted from /blog and /global patterns for native WordPress. The new read-only checks never turn on staging or production and do not imply articles have been published.
## Workflow không Excel — Topic Registry + WordPress REST

Khác **wp-aiwriter** sử dụng Excel cố định (data/topics.json), **wp-writer** dùng **data/topics.jsonl** chứa topic ID/title/intent/canonical/taxonomy_key; **data/taxonomy.json** chứa toàn bộ danh mục cha/con. Không nhập Excel, không dừng tại ranh giới chuyên mục và không suy category từ tiêu đề bài.

**AI bên ngoài → W1/W2/W3 claim → posts/drafts/NT-XXXXXX.md → GitHub QA PASS → Publisher → WordPress REST.** Khi Production thực sự bật: khớp chính xác category leaf và toàn bộ parent ancestry mới public; thiếu/sai thì nháp; trùng slug/title/marker hoặc có trong ledger thì skip/đối soát, không tạo lại. Không cần chờ cron; cron :17/:47 là fallback.

**Production tự động hiện vẫn dry_run.** Hai bài mới #3888/#3890 được chủ duyệt đăng thủ công qua WPVibe và đang được đưa vào ledger để tránh đăng trùng. QA success không tự chứng minh WordPress đã đăng.

Đọc [đối chiếu phương pháp wp-aiwriter và wp-writer](docs/WORKFLOW-COMPARISON-WP-AIWRITER.md) và [điều kiện kích hoạt](docs/ACTIVATION.md).

## MASTER README / MASTER WORK SPECIFICATION — Nguyễn Tú

## Nâng cấp native auto-delivery (chuẩn bị bật)

Sau khi Writer push bài, hệ thống tự intake + QA và định tuyến bài đạt chuẩn sang WordPress:
- **Production được nghiệm thu:** category chính xác → xuất bản công khai; thiếu/sai category → WordPress nháp với lý do mapping và taxonomy đích trong ledger.
- **Staging được duyệt:** mọi bài đạt QA vào WordPress nháp, không public.
- **Production và staging đều chưa được phê duyệt đầy đủ:** dry-run, không gửi WordPress. Cần bảo vệ branch/secrets và nghiệm thu Yoast trước khi kích hoạt.
- Tạo tối đa 2 bài/lần chạy, giới hạn riêng bài mới public/nháp theo ngày. Không auto-update hoặc auto-promote draft đã có.
- Chỉ tham khảo hành vi của wp-aiwriter; code và Topic Factory của wp-writer hoàn toàn độc lập.

Quy trình và điều kiện: [WordPress Auto Delivery](docs/WORDPRESS-AUTO-DELIVERY.md).

## Trạng thái triển khai cập nhật 16/10/2026

Đặc tả MASTER phía dưới được giữ làm yêu cầu gốc. Những chỗ ghi “CHƯA” hoặc “ĐỀ XUẤT” là snapshot trước triển khai; trạng thái thực luôn lấy từ `reports/dashboard.json`, `reports/health.json` và ledger.

- Đã nhập đủ 9 sheet Excel, kiểm kê có xác thực: 135 bài, 10 trang, 13 sản phẩm; giữ 8 category cũ.
- Registry ban đầu có 8 category cũ + 19 category dự kiến; nay đã tạo 2 category con: Chăm sóc xe điện #160 (con #157), An toàn khi di chuyển #161 (con #159). Các category khác vẫn phải được đối chiếu qua WordPress REST.
- Registry ban đầu có 80 candidate/8 PLANNED; đây là snapshot trước các đợt tiếp theo. Không tính allocation là topic. Dùng reports/dashboard.json và data/topics.jsonl để xem số mới nhất.
- W1/W2/W3 provider-neutral, GitHub-only claim request, CAS leases, intake receipts, 6 gate QA, REPAIR, create-only publisher, idempotent remote ledger, reconcile, internal-link graph, dashboard và refill đã có code/test.
- Draft-only REST acceptance: WordPress #3870, Blog #69, chạy lại cùng ID; giữ nguyên #3861. **Đã đăng thủ công qua WPVibe 2 bài mới: NT-000037 → #3888; NT-000047 → #3890, đúng category, Yoast/canonical/index verified.** Chi tiết: reports/manual-wp-smoke-20261016.json.
- **Unattended Production OFF (dry_run).** Yoast title/meta đã REST-writeable qua credential GitHub smoke. Enforced protection của Publisher và E2E tự đăng bằng Github Publisher chưa được chứng minh.
- Quy định mới: **1.600–5.000 từ hữu ích/bài**. Writer đọc [Quickstart](docs/WRITER-QUICKSTART.md). Chủ đọc [Activation](docs/ACTIVATION.md). Số liệu mới nhất xem [dashboard](reports/latest.md).


> **Tình trạng tài liệu:** Bản yêu cầu sản phẩm + kiến trúc mục tiêu, cập nhật ngày 16/10/2026. Đây là **đặc tả để triển khai sau**, không phải tuyên bố rằng toàn bộ nhà máy đã hoạt động.
>
> **Yêu cầu của chủ website:** Khởi đầu chiến dịch **1.000 bài nội dung chất lượng**, kiến trúc mở rộng **tối đa 10.000 bài** nếu có đủ nhu cầu tìm kiếm và chủ đề độc lập. Claude, ChatGPT, Gemini, Mistral hoặc bất kỳ AI nào được chủ cấp quyền GitHub có thể làm **external writer**. AI viết nội dung; hệ thống GitHub Actions kiểm tra, quản lý và đăng WordPress **khi đủ điều kiện**, không buộc một AI cụ thể.
>
> **Nguyên tắc:** LÀM THẬT → TEST → QA → COMMIT → PUSH → VERIFY, triển khai theo những bước nhỏ có thể kiểm chứng; không chỉ tạo kế hoạch. **Không tự ý phát hành hàng loạt khi chưa kiểm thử hoặc chưa được chủ bật chế độ sản xuất.**

---

## 0. PHẠM VI, ĐÍCH ĐẾN VÀ ĐIỀU ĐÃ XÁC NHẬN

| Hạng mục | Giá trị |
|---|---|
| Repo duy nhất cho dự án này | https://github.com/thuexemayhanoi/wp-writer |
| Nhánh sản xuất | main |
| Website WordPress đích DUY NHẤT | https://thuexemaynguyentu.com/ |
| WordPress | WordPress + Flatsome Parent + Flatsome Child hiện có |
| Mục tiêu giai đoạn 1 | 1.000 bài hợp lệ (chỉ tiêu nội dung, không phải 1.000 URL spam) |
| Trần mở rộng | 10.000 bài hợp lệ (năng lực kiến trúc, KHÔNG đồng nghĩa đã có 10.000 chủ đề/bài) |
| Ngôn ngữ ưu tiên | Tiếng Việt (vi-VN); ngôn ngữ khác là dự án tách biệt nếu được duyệt |
| AI writer | Provider-neutral: Claude, ChatGPT, Gemini, Mistral, v.v. khi được cấp quyền repo |
| Bộ xuất bản | GitHub Actions + WordPress REST API chuẩn |
| Phạm vi | Bài viết mới; không thay thế hoặc tái tạo hàng loạt các trang đang SEO |
| Sự thật doanh nghiệp | Mục 2 của tài liệu này; một nguồn cấu hình chuẩn chung trong engine sau khi triển khai |

**Đã thực hiện và kiểm chứng tại thời điểm viết:**
- Repo đã có README, thư mục posts/, và workflow kiểm thử `.github/workflows/wp-connection-smoke.yml`.
- Chủ website đã tự tạo các GitHub Actions Secrets: `WP_URL`, `WP_USERNAME`, `WP_APPLICATION_PASSWORD`. **Không có giá trị secret trong Git.**
- GitHub Actions run #38886147525 đã **SUCCESS**: xác thực WordPress user ID 1, tạo nháp WordPress **ID 3861**, đọc lại xác nhận `status=draft`, chưa công khai bài kiểm thử. Xem https://github.com/thuexemayhanoi/wp-writer/actions/runs/38886147525.
- Bài nháp thử có tên `[KIỂM THỬ] Kết nối GitHub WP Writer`, slug `wp-writer-connection-test-20261016`. **Không tính vào chiến dịch 1.000 bài; không tự đăng, sửa hay xóa** bài nháp thử này.
- **CHƯA xây dựng** Topic Factory 1.000/10.000, hệ thống nhiều writer, publish gate, SEO audit, lịch sản xuất hay bảng điều khiển sản xuất. Không giả định các chức năng đó đã tồn tại.

**Các dự án KHÁC — tuyệt đối không trộn:**
- `thuexemayhanoi/wp-aiwriter` → dự án 500 bài SEO Nguyễn Hà, xuất bản tới `blog.rentbikehanoi.com`, có Excel/JSON riêng.
- `thuexemayhanoi/blog` → GitHub Pages Jekyll Content Factory/Blog riêng.
- `thuexemayhanoi/global` và các repo ngôn ngữ → hệ sinh thái riêng.
- **wp-writer KHÔNG nhập lại chủ đề Excel 500 bài; KHÔNG đồng bộ/xuất bản sang các website khác; KHÔNG coi bài đã đăng ở website khác là bài mới.** Có thể tham khảo thiết kế của hai repo trên, nhưng triển khai adapter WordPress riêng.

---

## 1. TẦM NHÌN SẢN PHẨM VÀ NGUYÊN TẮC VẬN HÀNH

1. **Một GitHub repository, nhiều AI bên ngoài, một publisher chuẩn:** writer chỉ viết/chỉnh draft thuộc quyền mình; GitHub Actions thực thi QA khách quan và gửi bài đạt chuẩn qua WordPress REST API.
2. **Bất kỳ AI có khả năng đọc/ghi repo** đều có thể bắt đầu bằng một tài liệu Quickstart, không phụ thuộc thương hiệu AI và không cần AI API key trong Actions. AI vẫn phải **chủ động chạy phiên viết**; GitHub Actions không thể tự sinh bài khi không có writer hoặc dịch vụ AI được cấu hình.
3. **Content Factory chia việc thật:** danh sách chủ đề có ID bất biến, topic cluster, primary keyword, search intent, parent/child category, độ ưu tiên, trạng thái. Một chủ đề có một chủ biên tại một thời điểm.
4. **Tự động xuất bản có kiểm soát:** khi writer push draft → CI kiểm tra → PASS → đưa vào hàng đợi → publisher đăng từng lô nhỏ, lưu trạng thái và xác minh. Chế độ xuất bản mặc định phải an toàn cho tới khi chủ website phê duyệt bật production.
5. **Chất lượng quan trọng hơn số lượng:** không kéo dài nội dung để đạt word count; không tạo các trang địa phương doorway; chủ đề yếu/trùng nhau phải được loại hoặc hợp nhất về một URL chủ lực sau khi được duyệt.
6. **Không đụng SEO đang hoạt động:** tuyệt đối không bulk sửa xóa bài cũ, URL, canonical, slug, H1, meta, menu, footer, theme, plugin, category cũ, sitemap hoặc noindex.
7. **Sửa một chỗ đồng bộ toàn hệ thống:** dữ liệu NAP, bảng giá, contact, policy, schema, QA rules, template, navigation và các component dùng chung trong cấu hình tập trung.
8. **Tối ưu Hostinger/WordPress:** tránh bắn hàng trăm request đồng thời, plugin nặng, cron liên tục hoặc query toàn site không phân trang. Làm lô nhỏ có rate limit/backoff.
9. **Không báo cáo thành công giả:** luôn phân biệt topic IDEA/PLANNED, draft authored, QA PASS, WP DRAFT, WP PUBLISHED, VERIFIED PUBLIC, INDEXED (nếu có dữ liệu Search Console). Không gọi "đã SEO/đã index" chỉ vì có bài WordPress.

### Mô hình tổng quát

```text
                         EXTERNAL AI WRITERS (no AI API inside Actions)
                Claude W1       ChatGPT W2       Gemini/Mistral W3
                      \              |              /
                       \--- GitHub Writer Queue ----/
                         lease per ID / CAS / heartbeat
                                       |
                              posts/drafts/<ID>.md
                                       |
                                   Commit/Push
                                       |
                         GitHub CI -> Quality Gate
                        /              |            \
                  FAIL/REPAIR      BLOCKED/REVIEW     PASS
                       |               |               |
                 back to owner    report + hold   READY QUEUE
                                                        |
                                             serialized Publisher
                                              (small safe batches)
                                                        |
                                   WordPress REST -> create draft/publish
                                                        |
                                    readback -> public URL -> checkpoint
                                                        |
                                         reports / next claimable topic
```

---

## 2. SINGLE SOURCE OF TRUTH — NGUYỄN TÚ BUSINESS FACTS

**GBP:** Thuê xe máy ở Hà Nội - Nguyễn Tú  
**Thương hiệu:** Cho Thuê Xe Máy Nguyễn Tú  
**Địa chỉ NAP:** 112 Nguyễn Văn Cừ, Bồ Đề, Long Biên, Hà Nội, Việt Nam  
**Điện thoại/Zalo:** 0942 467 674  
**Điện thoại quốc tế:** +84 942 467 674  
**Website chính (đích xuất bản):** https://thuexemaynguyentu.com/  
**Trang blog tham chiếu:** https://thuexemaynguyentu.com/blog/  
**Google Maps:** https://maps.google.com/maps?cid=7448790013669858019  
**Giờ niêm yết:** 09:00–21:00 tất cả các ngày  
**Ngành nghề:** Thuê xe số, xe tay ga, xe 50cc, xe máy điện và xe đạp điện tại Hà Nội.

### Bảng giá tham chiếu — VNĐ

| Dòng xe | Theo ngày | Theo tuần | Theo tháng | Đặt cọc |
|---|---:|---:|---:|---:|
| Honda Wave | 150.000đ | 700.000đ | 900.000–1.200.000đ | 2–3 triệu |
| Honda Vision | 200.000đ | 1.000.000đ | 1.800.000–2.000.000đ | 4–5 triệu |
| Honda Air Blade | 200.000đ | 1.000.000đ | 1.500.000đ | 3 triệu |
| Honda Click / Yamaha Mio | 150.000đ | 700.000đ | 900.000–1.200.000đ | 2 triệu |
| Xe tay ga 50cc | 200.000đ | Báo giá riêng | Báo giá riêng | 4 triệu |
| Xe máy điện / Xe đạp điện | Liên hệ | Liên hệ | Liên hệ | Xác nhận theo mẫu |

**Chính sách cọc:** thông thường 2–5 triệu đồng tùy loại xe. Một số phương án giấy tờ bảo đảm có thể trao đổi riêng theo điều kiện và thỏa thuận hợp pháp. **Không tự bịa phương án, miễn cọc hay điều kiện khác.**

### Ràng buộc dữ liệu kinh doanh

- Không tự bịa giá, khuyến mãi, phí giao/nhận, tiền phạt, số xe tồn kho, quy trình, thời gian phục vụ ngoài giờ, review, giải thưởng, số năm kinh nghiệm, cam kết bảo hành hoặc quyền sử dụng pháp lý.
- Không viết như thể đã trực tiếp thử xe/đi khảo sát thực địa khi không có bằng chứng.
- Phân biệt dịch vụ doanh nghiệp thực cung cấp với kiến thức chung về thị trường. Không tự nhận cho thuê một mẫu xe cụ thể ngoài thông tin được chủ xác nhận.
- Nếu không có mức giá chính xác: ghi "Liên hệ để xác nhận theo loại xe và thời điểm", không tự ước lượng.
- Khi triển khai, mã hóa thông tin chuẩn trong **một** `data/business-facts.json` + cấu hình có version/updated_at. Nội dung đã đăng không tự thay đổi chỉ vì cấu hình thay đổi: cần QA và cơ chế cập nhật có kiểm soát.
- Schema LocalBusiness/Organization chỉ thể hiện thực tế có thể kiểm chứng; không tự thêm rating/review/aggregateRating giả.

---

## 3. SEO SCOPE — TOPICAL AUTHORITY KHÔNG PHẢI 10.000 BÀI QUẢNG CÁO

### Nhóm từ khóa dịch vụ ưu tiên

- Thuê xe máy Hà Nội
- Thuê xe máy tháng
- Thuê xe máy gần đây
- Giá thuê xe máy
- Thuê xe máy 50cc
- Thuê xe máy Long Biên
- Thuê xe máy Hoàn Kiếm
- Thuê xe máy Tây Hồ
- Thuê xe máy Phố Cổ
- Thuê xe máy Ba Đình
- Thuê xe máy Honda Vision

**Một ý định tìm kiếm thương mại chỉ có một URL chủ lực phù hợp.** Những bài hướng dẫn liên quan phải dẫn link tự nhiên về pillar/commercial page; không tạo hàng loạt URL gần giống chỉ để lấp từ khóa, địa điểm hoặc biến thể chữ.

### Hệ chủ đề được phép nghiên cứu mở rộng

1. Cho thuê xe máy.
2. Giá thuê xe máy.
3. Thủ tục và kinh nghiệm thuê xe.
4. Các dòng xe máy, xe số và xe ga.
5. Xe máy 50cc.
6. Xe máy điện.
7. Xe đạp điện.
8. Cho thuê xe máy điện.
9. Cho thuê xe đạp điện.
10. Giá xe máy điện và xe đạp điện.
11. Công nghệ xe điện.
12. Pin và sạc xe điện.
13. Bảo dưỡng và sửa chữa xe điện.
14. So sánh xe điện và xe xăng.
15. Luật giao thông Việt Nam.
16. Giấy phép lái xe.
17. An toàn khi lái xe.
18. Bảo dưỡng và sửa chữa xe máy.
19. Phương tiện giao thông.
20. Giao thông đô thị.
21. Du lịch Hà Nội.
22. Du lịch Việt Nam.
23. Du lịch bằng xe máy.
24. Cung đường phượt.
25. Địa điểm tham quan.
26. Ẩm thực địa phương.
27. Văn hóa và đời sống Việt Nam.
28. Lịch trình và chi phí du lịch.
29. Kinh nghiệm du lịch tự túc.
30. Di chuyển dành cho người nước ngoài.
31. Giao thông công cộng.
32. Du lịch xanh và phương tiện bền vững.
33. Hạ tầng trạm sạc xe điện.
34. Xu hướng giao thông điện hóa.
35. Chính sách và quy định về xe điện.

**Tỷ trọng nội dung:** Topic Factory tự phân bổ theo nhu cầu thực tế và semantic relevance, không mặc định mọi bài đều quảng bá thuê xe; không biến tất cả chủ đề luật, du lịch, ẩm thực thành landing page bán hàng. Chủ đề quá xa năng lực/chủ đích website phải được gắn REVIEW hoặc loại bỏ.

### Mô hình kiến trúc website

```text
Homepage / Commercial pages hiện có (GIỮ)
  ├── About / Contact / FAQ / Privacy / Terms (GIỮ hoặc tối ưu riêng nếu duyệt)
  ├── Parent Hub / Pillar (trang/danh mục có giá trị)
  │     ├── Child Silo / Topic Cluster
  │     │     ├── Supporting article A
  │     │     ├── Supporting article B
  │     │     └── Supporting article C
  │     └── Cluster liên quan
  └── Commercial landing page phù hợp theo intent
```

**Mỗi URL:** một primary keyword / một search intent / một content role / một canonical; không cannibalization. Kiểm kê cấu trúc WordPress đã có TRƯỚC khi định tạo mới pillar, category hoặc page. Tuyệt đối không tự tạo trùng category, slug, trang chính, chức năng Flatsome hay bài đã có.

---

## 4. QUY TẮC BÀI VIẾT — SEO + AEO + GEO

### Độ sâu nội dung định hướng (không ép số từ khi không cần)

| Loại nội dung | Định hướng |
|---|---|
| Homepage / Hub / Pillar lớn | Thường 1.600–3.000 từ khi có đủ chất liệu |
| About | Khoảng 800–1.600 từ, chỉ dữ liệu thực |
| Danh mục cha/con | Duy nhất, giải quyết ý định tìm kiếm |
| Bài hỗ trợ chuyên sâu | Bắt buộc 1.600–5.000 từ hữu ích cho mọi supporting article mới |
| FAQ tổng | 15–20 câu hỏi thực tế, trả lời trực tiếp |
| Contact | Ngắn gọn, NAP chính xác |
| Privacy / Terms | Đầy đủ và phù hợp hoạt động thật, không ép từ |

Bài thực tế nên có: title rõ intent; mở đầu trả lời đúng nhu cầu; các H2/H3 có giá trị; thông tin có thể kiểm chứng; bước hành động/thí dụ hữu ích; câu trả lời ngắn trích dẫn được khi phù hợp; FAQ không trùng lặp máy móc; internal link ngữ cảnh; không keyword stuffing hay AI filler.

**AEO/GEO:** dùng entity rõ nghĩa, định nghĩa và câu trả lời trực tiếp, nguồn chính thống cho thông tin biến đổi theo thời gian, mô tả ngữ cảnh/đối tượng/giới hạn, schema JSON-LD phù hợp. Chọn Article, BreadcrumbList, Organization, WebSite, LocalBusiness theo loại trang và dữ liệu có thật. FAQPage chỉ khi phù hợp, không kỳ vọng rich results mặc định.

**Luật giao thông / GPLX / mức phạt / chính sách xe điện:** phải có nguồn chính thức và ngày kiểm tra, không bịa điều luật, không lấy bài cũ làm sự thật pháp lý cập nhật. Nếu nguồn không xác minh được: giữ REVIEW, không xuất bản như khẳng định chắc chắn.

---

## 5. TOPIC FACTORY — 1.000 BÀI ĐẦU, ĐƯỜNG MỞ 10.000

**Hai con số cần tách bạch:**
- `editorial_target_initial = 1000`: mục tiêu 1.000 bài hữu ích được xác minh, không cam kết tự động đủ 1.000 URL.
- `hard_capacity = 10000`: quy mô hệ thống quản lý được nếu đủ topic/QA/công suất; KHÔNG phải số bài đã viết.
- `materialized_topics`: số topic thật đã nghiên cứu, phân loại và qua Topic QA.
- `published_verified`: số bài WordPress tồn tại, trạng thái publish + kiểm chứng URL.
- `indexed`: chỉ khi dữ liệu từ nguồn kiểm chứng phù hợp; không suy từ sitemap.

### Một chủ đề chuẩn phải có

`topic_id`, `title`, `slug_proposal`, `primary_keyword`, `secondary_keywords`, `search_intent`, `content_role`, `parent_cluster`, `child_cluster`, `wordpress_category_path`, `priority`, `word_target_range`, `content_outline`, `internal_link_candidates`, `source_requirements`, `risk_flags`, `canonical_target`, `similarity_key`, `status`, `created_at`, `updated_at`, `origin`, `version`.

### Trạng thái đề xuất (state machine)

```text
IDEA -> RESEARCH -> TOPIC_QA -> PLANNED -> CLAIMED -> WRITING
          |             |           |        |
        REJECTED       REVIEW       BLOCKED  lease/heartbeat
                                                |
                                    DRAFT_READY -> CONTENT_QA
                                                |          |
                                             REPAIR      PASS
                                                \        /
                                                  READY
                                                    |
                                              PUBLISH_INTENT
                                                    |
                                           WP_DRAFT / WP_PUBLISH
                                                    |
                                               VERIFY_PENDING
                                                    |
                                           VERIFIED / NEEDS_RECONCILE
```

**Không thay đổi số đếm/checkpoint bằng tay**; các report phải sinh từ manifest + transaction ledger. Claim một ID có khóa đồng thời, không có hai writer cùng sửa. FAIL nội dung → REPAIR, không tự nhảy sang bài mới để che lỗi.

### Tự bổ sung chủ đề khi queue thấp

- Chỉ cân nhắc refill khi PLANNED claimable < ngưỡng cấu hình (đề xuất `min_ready_queue=100`, `refill_target=300`; xác thực theo tài nguyên thật trước).
- AI writer/coordinator chủ động nghiên cứu thêm candidate thật từ nhu cầu tìm kiếm, taxonomy/knowledge gap, đối chiếu với bài WordPress đang tồn tại và manifest.
- Topic Gate: unique ID, unique primary intent, kiểm tra slug/title/semantic near-duplicate, canonical target, website fit, legal risk, search usefulness, child cluster, có nguồn khả dụng.
- Refill phải phân biệt **đề xuất candidate** với **đã được đưa vào PLANNED**. Không tự hạ QA nếu hết hàng; ghi `NEEDS_TOPIC_EXPANSION`.
- Không dùng "chủ đề lấp chỗ" để đạt 1.000/10.000. Một bài hỗ trợ phải giải quyết vấn đề thực, không phải doorway page.
- Không cần dịch tự động 10.000 bài sang ngôn ngữ khác và không copy/syndicate nội dung từ các repo khác.

---

## 6. MULTI-WRITER PROVIDER-NEUTRAL — CLAUDE / CHATGPT / GEMINI / KHÁC

### Vai trò

- **W1/W2/W3:** ba slot writer độc lập trước mắt, có thể dùng bất kỳ AI nào được chủ cấp quyền GitHub. Tên AI không được hard-code vào publisher.
- **Coordinator/Topic Factory:** kiểm kê và đề xuất chủ đề; có thể là phiên AI bên ngoài, không buộc API trả phí.
- **Publisher:** DUY NHẤT một engine GitHub Actions được quyền gọi REST WordPress.
- **QA Lead:** cấu hình luật + kiểm thử; machine QA đánh giá điều kiện kỹ thuật, AI writer chịu trách nhiệm đánh giá sự thật và chất lượng thực.
- Mọi AI chỉ cần biết `AGENTS.md`, `docs/WRITER-QUICKSTART.md` và source manifest chuẩn, không cần mật khẩu WordPress.

### Quy tắc an toàn đa-writer

1. `writer-session begin --slot auto` claim tối đa 10 topic/slot (tham số tùy chỉnh), có `session_id` ổn định, lease TTL/heartbeat, owner cụ thể, commit CAS; mỗi writer chỉ giữ một slot.
2. Nếu slot của phiên khác còn hạn → không chiếm quyền; chọn slot khác hoặc chờ. Mất mạng/quota thì draft đã push vẫn thuộc queue; draft chưa push chỉ phục hồi khi cùng phiên hoặc lease hết hạn hợp lệ.
3. `writer-session check` chạy QA trước push; `push` chỉ đẩy đúng ID được sở hữu; `confirm` xem trạng thái PUBLISHED/REPAIR/PENDING; `release` nhả claim sau khi an toàn.
4. Không force push; fetch latest main, so sánh expected SHA / lock/transaction; bounded retry khi xung đột không đụng dữ liệu người khác.
5. Không có chuyện hai writer cùng xuất bản trực tiếp WordPress. Publisher có concurrency group + idempotency.
6. Writer không sửa protected: `.github/workflows/**`, `data/state/**`, `data/qa/**`, `config/**`, `data/business-facts.json` hay bài PUBLISHED, trừ thay đổi code được chủ duyệt.
7. Có thể bàn giao slot giữa ChatGPT/Claude bằng đúng session + checkpoint mà không xóa hoặc cướp lease còn hạn.
8. **AI hoạt động khi phiên đang chạy**; nếu đóng hết phiên AI và không có dịch vụ tạo nội dung đã được chủ cho phép, sẽ không có bài mới tự sinh. GitHub Actions vẫn có thể QA/xuất bản draft **đã push**.

### Không dùng AI API keys theo mặc định

- Không thêm OpenAI/Anthropic/Gemini API keys vào GitHub Secrets; không dùng mô hình AI mã nguồn mở hay endpoint bên ngoài làm writer tự động nếu chủ không yêu cầu.
- `WP_APPLICATION_PASSWORD` là credential WordPress **bắt buộc cho publisher**, không phải AI API key.
- Không cấp WordPress credentials cho các AI writer chỉ để họ viết nháp; xác thực thực hiện riêng trong job publisher.
- Nếu tương lai muốn AI chạy 24/7 không cần phiên chat, phải có nguồn compute/model thật, chi phí, quota, giám sát và sự cho phép riêng; không tuyên bố chế độ đó đang tồn tại.

---

## 7. CONTENT QA + SEO QA + PUBLISH GATE (BẮT BUỘC)

Kế thừa ý tưởng tốt từ `/blog` và `/wp-aiwriter`, nhưng **không sao chép mù mã publisher GitHub Pages sang WordPress**.

### Ba lớp QA

**A. Topic QA — trước khi viết**
- Intent duy nhất, không cannibalization với manifest và site WordPress hiện hữu.
- Đúng parent/child taxonomy, đề xuất anchor và pillar liên quan.
- Chủ đề đủ giá trị, phù hợp chuyên môn, có thể xác minh; không tạo doorway hay thin content.

**B. Content QA — trước READY**
- ID/title/category/keyword/intent khớp topic manifest; frontmatter chính xác.
- Không HTML/script nguy hiểm, placeholder, sao chép dài, câu lặp, heading rác, H1 trùng.
- Độ dài có giá trị theo intent; mặc định bài hỗ trợ 1.600–5.000 từ hữu ích theo yêu cầu chiến dịch 16/10/2026, không chỉ dựa word count.
- Title/meta/slug rõ nghĩa, không nhồi keyword; H2/H3 logic; câu trả lời rõ; accessibility và alt text khi có ảnh.
- Kiểm chứng business facts theo mục 2, facts ngày càng thay đổi, nguồn pháp lý có thẩm quyền, không bịa review/kinh nghiệm.
- Near-duplicate dựa trên text shingles + slug/title và đối chiếu search intent; không dựa duy nhất vào title.
- Outgoing link/anchor phù hợp, không trỏ draft/404; parent hub/sibling thương mại chỉ khi liên quan.
- Kiểm tra dự kiến schema JSON-LD và không tạo rich-result markup sai điều kiện.
- QA không thể bảo đảm 100% chất lượng Google, EEAT hay tính xác thực nội dung: AI cần thực sự đọc, kiểm chứng và sửa.

**C. Publish QA — trước và sau POST**
- WordPress xác thực, category full ancestry có đúng một leaf match.
- Trùng title/slug/canonical/matrix ID/marker với cả publish/draft/private → SKIP/REVIEW, không ghi đè.
- Không truy cập hay chỉnh sửa Trash; không tự xử lý post bị xóa nếu có nghi vấn.
- Trước POST ghi intent/checkpoint bền vững; POST timeout/không rõ trạng thái → NEVER blind retry, cần đối soát.
- Sau POST đọc WordPress authenticated REST, trạng thái category + permalink; với publish phải GET trang công khai để xác minh response và nội dung chính.
- Mỗi bài có receipt `topic_id, source_sha256, wp_id, status, URL, category_id, verified_at, git_commit, run_id`. Không lộ bí mật.

### Điểm QA nội bộ định hướng

- Quality Score **≥75/100** và SEO Score **≥70/100** nếu triển khai scorer có tiêu chí/bằng chứng rõ ràng.
- Gate riêng `business_fact=PASS`, `legal=PASS|NOT_REQUIRED`, `critical_failure=false`.
- `90+` chỉ ghi nhãn nội bộ EXCELLENT, **không** đồng nghĩa Google đánh giá tốt hoặc bài có khả năng lên top.
- Điểm tự động bằng pattern/proxy **không thay thế fact-check thực chất**; nếu không có bằng chứng phải REVIEW thay vì cộng điểm ảo.
- FAIL → có danh sách lỗi có thể hành động và REPAIR đúng ID, không giảm ngưỡng để tăng số lượng.

### QA modes

- **FAST:** per new batch; nội dung mới, metadata, business/legal, topic duplication, links, category, state.
- **DEEP:** sau khoảng 50 bài hoặc khi có thay đổi taxonomy/publisher; audit internal linking, cannibalization, categories, matrix drift, indexability, performance.
- **FULL:** trước mở rộng 1.000 / 2.000 / 5.000 / 10.000 và định kỳ; full test, sitemap, robots, taxonomy, URL collision, accessibility/CWV sampling, hồi quy workflow, kiểm website thực.
- QA phải phân biệt **phân tích tĩnh** và **đã kiểm chứng ngoài website**.

---

## 8. WORDPRESS PUBLISHER — REST API, ĐÚNG DANH MỤC, KHÔNG PHÁ SEO

### Kết nối và bí mật

Repository Actions Secrets đã được người chủ thêm (không đọc/hiển thị giá trị):
- `WP_URL` → https://thuexemaynguyentu.com
- `WP_USERNAME` → WordPress username của tài khoản cấp quyền
- `WP_APPLICATION_PASSWORD` → WordPress Application Password

**Không ghi mật khẩu vào README/log/issue/commit.** Tài khoản cấp quyền thấp nhất có thể (Editor riêng nếu phù hợp); ưu tiên protected GitHub Environments, branch protection, CODEOWNERS cho workflow/config để một external writer có quyền code không thể dễ dàng sửa workflow lấy Secrets. Không chạy code PR từ người không tin cậy với secrets; kiểm soát quyền fork/PR.

### Chế độ xuất bản (giai đoạn)

1. `dry_run` — mô phỏng, không ghi WordPress.
2. `draft_only` — tạo nháp thật, readback, dành cho acceptance test.
3. `production_enabled` — **chỉ bật sau owner approval và kiểm thử**, lúc đó bài đạt PASS và taxonomy hợp lệ có thể `publish` tự động theo batch đã định.
4. `pause` / `emergency_stop` — dừng trước bài mới, không xóa gì đã đăng.

**Lô xuất bản:** đề xuất tối đa **2 bài/lượt** khi production, xử lý backlog tuần tự/tái kích hoạt có kiểm soát, không spam REST. Gộp writer push tối đa 10 draft nếu hợp lệ nhưng publisher vẫn chia lô 2. Mỗi bước lưu receipt và checkpoint. Giới hạn số bài/ngày hoặc giờ có thể chỉnh trong config một nơi; không mặc định hàng nghìn bài/ngày.

**Nếu category full path chưa tồn tại/không khớp:** đưa vào WP DRAFT (hoặc BLOCKED theo policy), báo cáo rõ category cần đối chiếu, không đoán vào Uncategorized và không tự tạo cây category hàng loạt. Trước khi publish cần mapping đúng từ WordPress REST. Không thay đổi parent-child category cũ.

**Chống xung đột:** chỉ một WordPress publisher, concurrency lock, write-ahead ledger, idempotency key, verify-before/after POST. Không có publisher đồng thời từ WPVibe, WP Agent, Git it Write, repo khác cho cùng content ID. Không tắt/xóa tích hợp cũ vô cớ — chỉ bảo đảm cùng tập bài không bị hai pipeline quản lý.

**Giữ SEO URL:** mặc định create-only. Existing content = SKIP/REPORT; các thao tác update/delete/redirect hay re-categorize legacy chỉ khi chủ duyệt riêng. Không tự chuyển các bài nháp trong WP thành publish ngoài ledger của dự án.

---

## 9. INTERNAL LINKING GRAPH + HIERARCHICAL CATEGORIES

Yêu cầu bảng dữ liệu theo URL thực:

`URL → Outgoing Links → Incoming Links → Anchor Text → Cluster → Recommended Links`

Ưu tiên: `Supporting Content → Child/Cluster Hub → Parent/Pillar → Commercial Priority URL` khi phù hợp; thêm liên kết ngang giữa sibling thật sự cùng intent, prev/next khi có bài đã publish. Homepage chỉ nhận link khi liên quan tự nhiên, không bơm anchor thương mại vào mọi bài.

- Tạo inventory URL hiện có từ WordPress REST và sitemap trước khi sinh link; chỉ liên kết tới URL public/canonical hợp lệ.
- Kiểm tra HTTP/trạng thái published của target, không tự link tới draft hoặc permalink chưa tồn tại.
- Danh mục cha/con, breadcrumbs, related posts phải tôn trọng theme đang dùng, không chèn hệ thống component trùng với Flatsome hoặc plugin.
- Mọi gợi ý reverse-link vào bài cũ phải nằm trong report `recommendations`; không tự sửa hàng nghìn URL cũ.
- Đồng bộ menu, footer, schema, breadcrumb bằng template/hook chung **nếu được chủ duyệt sửa theme**; trong phạm vi Content Factory mặc định KHÔNG tự sửa theme.

---

## 10. SCHEMA, TECHNICAL SEO VÀ QUẢN TRỊ 10.000 BÀI

- Title, meta description, canonical, robots, schema Article/Breadcrumb, OG/Twitter do template/SEO plugin hiện tại quản lý; tránh xuất ra hai schema hoặc nhiều canonical.
- Kiểm tra XML sitemap WordPress thực tế, tính phân trang của sitemap plugin, canonical/indexability và index/noindex khi mở rộng. Không tự sinh sitemap thứ hai trùng URL.
- Performance: request WordPress REST phân trang; cache inventory, exponential backoff, giới hạn batch; không query toàn bộ post/content mỗi lần.
- Hình ảnh: alt text, nguồn/giấy phép hợp lệ, kích thước/responsive, WebP/AVIF khi có hỗ trợ; không tự tạo hoặc copy ảnh vi phạm.
- Mobile/tablet/desktop, WCAG/ARIA cơ bản, Core Web Vitals kiểm tra qua sampling theo template.
- Tracking: mapping topic_id→WordPress post_id→URL→QA evidence→editorial update; tạo báo cáo orphan pages, broken links, duplicate slug/canonical, content gaps.
- **Indexing không thể được cam kết**: bài đăng không tương đương được Google index hay lên top. Dùng GSC/Bing data khi chủ kết nối và cho phép, không báo cáo giả.

---

## 11. ĐỀ XUẤT CẤU TRÚC THƯ MỤC SAU KHI WORK TRIỂN KHAI

```text
/wp-writer
  README.md                            # MASTER SPEC (tài liệu này)
  AGENTS.md                            # hợp đồng chung cho mọi AI
  .github/
    workflows/
      wp-connection-smoke.yml          # ĐÃ CÓ: smoke test nháp, giữ an toàn
      writer-qa.yml                    # ĐỀ XUẤT: QA read-only
      topic-refill.yml                 # ĐỀ XUẤT: stage candidate có gate
      wordpress-publisher.yml          # ĐỀ XUẤT: publisher duy nhất
      production-watchdog.yml          # ĐỀ XUẤT: health read-only
  config/
    production-policy.json             # publish_mode/batch/rate/active clusters
    seo-rules.json                     # QC thresholds
    writer-slots.json                  # max slots, TTL
  data/
    business-facts.json                # chuẩn NAP, giá, deposit
    taxonomy.json                      # mapping parent/child đã xác minh
    topics.jsonl                       # topic manifest có ID bất biến
    state/
      checkpoint.json
      writer-claims.json
      publication-ledger.json
      transaction.json
    qa/
      <topic_id>.json
  posts/
    drafts/
      <topic_id>.md
    archived/
      # không trùng với bài WordPress đã công khai
  scripts/
    topic-factory.py
    writer-session.py
    validate.py
    qa.py
    wp-client.py
    publisher.py
    reconcile.py
    reports.py
  tests/
    test_topic_identity.py
    test_writer_lease.py
    test_qa.py
    test_publisher_safety.py
    test_idempotency.py
    test_wp_category_mapping.py
  docs/
    WRITER-QUICKSTART.md
    ARCHITECTURE.md
    TOPIC-FACTORY.md
    QUALITY-RUBRIC.md
    PUBLISHER-RUNBOOK.md
    RECOVERY.md
    SECURITY.md
    OPERATIONS.md
  reports/
    latest.md
    dashboard.json
    topic-gaps.md
    cannibalization.md
    internal-links.csv
    publication-receipts/
```

Đây là cấu trúc **đề xuất**, không phải cây file đang tồn tại. Work có thể chọn tên file khác nếu hợp lý, nhưng phải giữ các trách nhiệm và **một owner/canonical tool cho mỗi thao tác**. Không tạo hai publish engines song song.

---

## 12. KẾ HOẠCH TRIỂN KHAI BẰNG CHATGPT WORK — LÀM MỘT LỆNH, THỰC HIỆN TỪNG CHẶNG

### Phase 0 — Audit thực tế (không thay đổi production)

- Đọc repo HEAD, workflow smoke test và log run #38886147525; xác minh kết nối hiện có.
- Đọc cấu trúc URL/danh mục/post WordPress chính hiện có qua REST, inventory/sitemap cơ bản và policy; không giả định website trắng.
- Đối chiếu với /blog và /wp-aiwriter **chỉ để học kỹ thuật**, không nhập matrix/copy bài.
- Xuất `docs/ARCHITECTURE.md`, risk register, migration/no-change boundary, Phase 0 acceptance.

### Phase 1 — Foundation + source of truth

- Tạo AGENTS.md, cấu hình NAP/bảng giá chính xác, taxonomy mapper read-only, topic manifest schema/checksum, QA contracts, basic tests, recovery/rollback.
- Preflight phát hiện trùng bài WordPress/canonical và thỏa thuận một content owner cho từng URL.
- Có thể tạo topic candidates cho **1.000** mục tiêu, nhưng chỉ đưa vào PLANNED khi qua topic gate, không giả định đủ 1.000 ý tưởng tốt lập tức.

### Phase 2 — Multi-writer + QA

- 3 slots; claim/lease/heartbeat; không ghi đè song song; writer Quickstart chỉ cần một lệnh nhận việc.
- Content QA + topic intent/duplicate/SEO/business/legal/source + REPAIR.
- Test tranh chấp đồng thời, quota/mất phiên, recover và hash evidence.

### Phase 3 — WordPress publisher an toàn

- Tận dụng chính xác ba Actions Secrets hiện có; không hỏi lại mật khẩu, không in secret.
- Test API authenticate/read only; reuse smoke test nháp ID 3861 chỉ để đối chiếu, không publish/xóa.
- Dry-run publisher → viết và xuất bản **một bài nháp kiểm thử MỚI chỉ khi chủ duyệt cụ thể** → verify; kiểm soát safe failure/timeout/duplicate/category mismatch.
- Triển khai publish gate có **production_enabled=false mặc định**. Chủ bật khi có đủ bằng chứng và phê duyệt.

### Phase 4 — Topic Factory 1.000 + Internal Linking

- Generate/chọn topic theo search intent và 35 nhóm chủ đề, map đúng WP categories có thật.
- Kế hoạch triển khai 1.000 bài bằng batch nhỏ, report progress thực; không tự tạo thin content.
- Internal links, cluster graph, suggestions, QA FAST/DEEP/FULL.

### Phase 5 — Scale đến 10.000 khi được duyệt

- Chỉ nâng capacity/queue sau khi Phase 1.000 có số liệu QA, crawl/index, traffic và hạ tầng chấp nhận được.
- Theo dõi site performance, duplicate rate, failure/retry, nguồn pháp lý cập nhật, crawling budget.
- Scale gates tại 500 / 1.000 / 2.000 / 5.000 / 10.000 là **mốc review kỹ thuật**, không quota phải lấp bằng nội dung rỗng.

### Quy tắc thực thi Work

1. **LÀM THẬT, TEST THẬT, COMMIT, PUSH** các thay đổi an toàn sau từng giai đoạn, không chỉ mô tả kế hoạch.
2. Không làm một commit quá lớn khiến khó debug; mỗi giai đoạn có test và rollback.
3. Bài viết, quyền publish, sửa site cũ, thay đổi Secrets, bật production là các hành động có thể ảnh hưởng bên ngoài — cần policy/gate/ủy quyền phù hợp; không suy "được xây workflow" thành "được spam publish 1.000 bài".
4. Không dùng API key AI, không open-source AI, không mở plugin nặng, không làm hosting bị quá tải.
5. Nếu bị giới hạn quyền/quota, báo chính xác blocker và checkpoint, không tuyên bố thành công.
6. Hoàn tất một pha phải báo: commit SHA, file thay đổi, test/log PASS/FAIL, số bài thực, WordPress ID/URL nếu có, điều gì chưa xác minh, bước kế.
7. Không tắt hoặc sửa WPVibe/WP Agent, Flatsome, blog 500 bài hay repo khác nếu không liên quan.
8. Không force push, không xóa bài, không touch Trash, không chặn index, không auto đổi SEO legacy.

---

## 13. ACCEPTANCE CRITERIA — KHÔNG BÁO "HOÀN THÀNH" KHI CHƯA ĐỦ

- [ ] Tài liệu, source of truth NAP và dữ liệu giá đã nhập đúng 100%, test riêng.
- [ ] Taxonomy/URL inventory lấy từ WordPress hiện hữu, không tạo category trùng.
- [ ] Topic manifest có identity bất biến, intent/canonical guard và refill có ngưỡng.
- [ ] 3 AI writer có thể nhận 3 nhóm ID khác nhau mà không tranh chấp.
- [ ] Writer A không thể sửa/chiếm lease còn hạn của Writer B.
- [ ] Bài lỗi content/fact/legal vào REPAIR có lý do, không bị publish.
- [ ] QA evidence có hash khớp chính xác nội dung publish.
- [ ] WordPress Secrets chỉ dùng trong publisher; không lộ vào writer, PR, log hoặc Git.
- [ ] Publish trigger không tự đăng khi production disabled.
- [ ] 1 bài thử được WP REST tạo đúng status/category và readback thành công.
- [ ] Chạy lại cùng topic không tạo post thứ hai (idempotency).
- [ ] Timeout POST không tạo duplicate khi retry/reconcile.
- [ ] Không chỉnh sửa bài cũ, URL, title/meta, theme, plugin, sitemap, Trash.
- [ ] Internal link targets public, valid và cùng search intent.
- [ ] Báo cáo đúng IDEA / PLANNED / WRITING / QA PASS / WP DRAFT / VERIFIED.
- [ ] Có pause/resume, recovery khi workflow hỏng, không mất queue đã push.
- [ ] Có test CI, tài liệu vận hành từng bước phù hợp người làm bằng điện thoại.
- [ ] Đạt và được chủ duyệt nghiệm thu giai đoạn 1 trước khi scale lớn.

---

## 14. LỆNH GIAO VIỆC CHO CHATGPT WORK / CLAUDE (COPY NGUYÊN PHẦN NÀY)

> Bạn đóng vai Principal WordPress REST API Engineer, Senior GitHub Automation Engineer, Multi-Agent Workflow Architect, Semantic SEO/AEO/GEO Architect, Content QA Lead và Security/Recovery Engineer.
>
> **ĐỌC TOÀN BỘ README.md của repository `thuexemayhanoi/wp-writer` (đặc tả này) và kiểm tra main mới nhất trước khi thao tác.**
>
> Triển khai hệ thống Universal AI Content Factory cho website **duy nhất** `https://thuexemaynguyentu.com/`: 1.000 bài chất lượng giai đoạn đầu, năng lực mở rộng 10.000; hỗ trợ đồng thời tối đa 3 external AI writers provider-neutral (Claude/ChatGPT/Gemini/Mistral/AI khác có GitHub access), GitHub Actions làm Quality Gate, serialized WordPress REST publisher, Topic Factory và Internal Link Graph.
>
> Không dùng API key AI, không dùng mô hình AI open-source, không giả vờ GitHub Actions tự viết AI. Dùng ba GitHub Actions Secrets WordPress đã có, **không xem/in/lưu lại giá trị**. Smoke test nháp ID 3861 đã xác minh trước đó — giữ nguyên.
>
> **LÀM THẬT — AUDIT → IMPLEMENT → TEST → COMMIT → PUSH → VERIFY → CONTINUE**, chia thành các commit nhỏ có QA, không chỉ đưa ra kiến nghị. Tự xử lý lỗi kỹ thuật trong phạm vi được phép, giữ checkpoint sau mỗi pha; không hỏi lại những dữ liệu NAP/chính sách đã nằm trong README.
>
> Bảo vệ tuyệt đối WordPress đang chạy và các repo `wp-aiwriter`, `blog`, `global`: không xóa/đổi URL, không sửa hàng loạt bài cũ/canonical/SEO/sitemap, không xóa Trash, không hạ QA, không đụng Flatsome/plugins nếu chưa được phê duyệt. Tạo mới nội dung chỉ khi đúng search intent, category và được QA PASS.
>
> Mặc định `production_enabled=false` trong giai đoạn triển khai. Có thể test đọc/QA/dry-run và mã nguồn; **không đăng công khai hoặc bật xuất bản tự động trước khi chủ phê duyệt chế độ production**. Khi được duyệt, publisher chạy lô nhỏ (đề xuất 2 bài), xác minh mỗi WordPress ID/URL, chống tạo trùng và lưu ledger/checkpoint.
>
> Kết thúc báo cáo rõ SHA/PR, các file đã tạo, test PASS/FAIL, số topic và bài hiện có, lỗi còn lại, hướng dẫn sử dụng một lệnh cho writer W1/W2/W3, và vị trí mở công tắc production. Không báo hoàn thành 1.000/10.000 bài nếu mới chỉ dựng framework.

---

## 15. GIỚI HẠN PHẠM VI CỦA README NÀY

README này là **bản chốt yêu cầu và nguồn hướng dẫn Work**, không tự tạo nội dung, không tự deploy và không là bằng chứng các công đoạn triển khai hoàn tất.

**Tại thời điểm cập nhật tài liệu:** repo mới kiểm tra thành công đường truyền GitHub Actions → WordPress bằng **một bài nháp #3861**. Mọi thành phần sản xuất 1.000/10.000 bài liệt kê phía trên phải được xây, test và xác nhận sau.

**Chủ sở hữu có thể sửa đổi quyết định**: số slot, kích thước batch, chế độ QA, lịch xuất bản, danh mục và thứ tự triển khai tại các tệp cấu hình trung tâm — nhưng không thay đổi dữ liệu doanh nghiệp đã được chủ xác nhận nếu chưa kiểm chứng/được chủ cập nhật.
