# Quy trình chung W1–W9 — AI App nghiên cứu và viết liên tục

> **Điểm vào cho Excel Nguyễn Tú (1.482 tiêu đề):** [TITLE-PLAN-1482-SOP](TITLE-PLAN-1482-SOP.md). Excel là kế hoạch gợi ý; `data/topics.jsonl` là Topic Registry đã được Research QA duyệt; chỉ NT đã PLANNED mới được W1–W9 claim, viết/QA/Publisher. 51 phường giữ độc lập. Không lấy tên Excel làm slug hoặc hạ bất kỳ gate nào.


Lệnh chủ 18/10/2026: giữ quy trình đơn giản, viết nhiều và nhanh; không thêm API AI, khóa Writer, xác thực tài khoản AI hay bước duyệt tay. Tài liệu này thống nhất cách vận hành cho README, AGENTS, Quickstart và các role playbook; hướng dẫn cũ mâu thuẫn phải theo tài liệu này. Tham số thật vẫn lấy từ config và mã QA hiện có.

## Luồng duy nhất

**AI App nghiên cứu → Research QA → PLANNED → W1–W9 viết → QA ≥85 + chống trùng + đúng danh mục → Publisher → WordPress công khai → G7 xác minh.**

- Claude/ChatGPT/AI App đang chạy thực hiện nghiên cứu, viết và sửa. GitHub Actions chạy chương trình kiểm tra, tiếp nhận và đăng bài; không gọi mô hình AI.
- Mỗi phiên dùng một session ổn định, nhận một vị trí trống bằng `--slot auto`, tối đa 10 Topic ID. Đó là phân công để các máy không viết trùng bài, không phải khóa API hay xác thực Claude.
- SEO ≥85, Quality ≥85, 1.600–5.000 từ hữu ích và G1–G6 giữ nguyên. Trùng intent/URL, sai nguồn/dữ kiện/danh mục/liên kết vẫn bị giữ riêng.
- Publisher đang bật, đăng 2 bài/lô, tối đa 5 lô mỗi lần chạy; QA trên main kích hoạt Publisher, lịch :17/:47 dự phòng. Xác minh công khai bằng ledger `phase=VERIFIED` và URL; không suy từ Actions success.

## Một quy định nguồn cho cả Researcher và Writer

- **Một nguồn gốc đáng tin, đã đọc thật, đủ chứng minh các dữ kiện được dùng có thể đủ cho chủ đề hẹp.** Không bắt mọi chủ đề phải có hai nguồn hoặc hai tên miền.
- Thêm nguồn đối chiếu khi dữ kiện pháp lý, an toàn, biến động hoặc có tranh cãi; nguồn bổ sung phải giải quyết được điểm cần kiểm chứng. Nếu bằng chứng vẫn thiếu, thu hẹp phạm vi hoặc giữ REVIEW, không tự gán PASS.
- Luật cần nguồn chính thức có thẩm quyền, kiểm tra trong 90 ngày; nguồn tổng quát trong 365 ngày. Giá, lịch, luật và dữ kiện biến động phải được xác nhận khi dùng. Giá/chính sách Nguyễn Tú lấy từ `data/business-facts.json`.
- Ghi đúng URL HTTPS, ngày đọc, khẳng định được hỗ trợ, trích đoạn ngắn nguyên văn và hash văn bản thực đã đọc. Không tạo nguồn/hash/kinh nghiệm giả; RSS chỉ là gợi ý. Cùng một tài liệu có thể phục vụ nhiều câu hỏi khác intent khi thật sự có bằng chứng tương ứng.
- Được nghiên cứu các website công khai phù hợp, gồm hãng xe, cơ quan nhà nước, kỹ thuật, báo chí, du lịch và đối thủ; không sao chép hay lấy giá/đánh giá đối thủ làm dữ kiện Nguyễn Tú. Link ngoài HTTPS dùng theo ngữ cảnh; không áp danh sách tên miền đóng cho nội dung tổng quát.
- GitHub không mở được nguồn vì 403/429/5xx/lỗi mạng chỉ được dùng cơ chế snapshot hiện có khi URL + hash + đoạn trích khớp hồ sơ nghiên cứu của chính chủ đề; ghi `live_checked: false`. 404 hoặc nguồn đọc được nhưng không khớp trích đoạn vẫn REVIEW. Không bắt buộc probe host trước mọi bài.
- Hai liên kết **nội bộ** công khai là yêu cầu riêng của Article QA, không phải yêu cầu hai nguồn ngoài.

## Viết và nghiên cứu tiếp, không chờ duyệt từng đợt

1. Researcher đọc `research_v2.py plan`, lấy chủ đề khác intent, đọc nguồn và nộp từng batch 10 qua `intent-check`, `checkpoint`, `check`, `push`. Lô cuối 1–9 chủ đề dùng `--final`; không thêm lô mới vào session đã FINAL. Dừng tại giới hạn chủ giao, hết nguồn phù hợp, hết quota hoặc trần kho.
2. Writer nhận tối đa 10 PLANNED bằng `writer-session.py begin --slot auto --count 10 --session SESSION`, viết từng bài. Dùng source/ghi chú đã nghiên cứu; nếu thiếu phải đọc nguồn thật. Các ghi chú ở máy khác có thể chưa có trên máy này; dữ liệu nguồn trong topic registry mới là hồ sơ bàn giao trên GitHub.
3. Rà soát thực tế dữ kiện trước khi nộp. Dùng `build_article.py` dựng bài; `writer-repair.py save` lưu baseline/checkpoint, tự QA và nộp qua `writer-session.py push` nếu PASS. FAIL/REVIEW thì sửa đúng lỗi, lưu phiên bản và chạy lại, tối đa 10 lượt; chi tiết ở [WRITER-AUTO-REPAIR.md](WRITER-AUTO-REPAIR.md).
4. Nộp từng bài hoặc từng cặp ngay khi đạt. Hoàn tất batch thì `begin` lại cùng session để nhận tiếp; không chờ Publisher đăng hết, không mặc định dừng sau một batch. Nếu lệnh chủ giới hạn số bài/lượt thì tôn trọng giới hạn đó. `confirm` xem tình trạng đăng là bước đọc, không giữ Writer đứng chờ.
5. Ưu tiên sửa bài REPAIR của mình; bài có rủi ro thật hoặc hết 10 lượt giữ riêng. Không bỏ qua QA, xóa bài giữ lại hoặc sửa registry/ledger bằng tay. Không đổi session để né REPAIR; không nhận bài đang được phiên khác giữ.
6. Hết PLANNED thì xem đơn nghiên cứu và chuyển sang Researcher khi có đơn hợp lệ; nếu không có việc hợp lệ thì lưu tiến độ và báo lý do. Hết quota/mất mạng thì giữ session + Topic ID + checkpoint; mở lại tiếp tục bằng `resume`, không làm lại từ đầu.

## Phạm vi đồng bộ

Không thêm hệ thống đo quota, dịch vụ AI, API key hoặc lớp khóa/bảo mật mới. Kết nối GitHub và kết nối Publisher–WordPress đang hoạt động được dùng tiếp. QA, chống trùng, phân công Topic ID, hash/checkpoint, ledger, taxonomy, URL cũ và chính sách xuất bản giữ nguyên.
