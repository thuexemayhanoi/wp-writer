# Viết bằng Claude, ChatGPT, Gemini, Mistral hoặc AI khác

Repo duy nhất: https://github.com/thuexemayhanoi/wp-writer. WordPress duy nhất: https://thuexemaynguyentu.com. Writer chỉ cần quyền GitHub; không cần mật khẩu WordPress hay AI API key.

Đọc README, AGENTS, business-facts và topic được giao. Cài Python dependencies và sử dụng session công khai ổn định, riêng cho từng phiên:

```bash
python -m pip install -r requirements.txt
python scripts/writer-session.py begin --slot auto --count 2 --session s-your-session
```

Lệnh CAS đọc main mới nhất, chọn slot trống, nhận tối đa 10 topic; phiên đang có REPAIR phải sửa trước. Writer không tự sửa registry. Chỉ viết ID thuộc lease vừa trả về, file `posts/drafts/NT-XXXXXX.md`, tối thiểu 1.600 và tối đa 5.000 từ hữu ích. Dùng frontmatter trong `docs/ARTICLE-CONTRACT.md`.

```bash
python scripts/writer-session.py check --ids NT-000037 --session s-your-session
python scripts/writer-session.py push --ids NT-000037 --session s-your-session
python scripts/writer-session.py confirm --session s-your-session
python scripts/writer-session.py heartbeat --session s-your-session
```

Thay ID bằng ID thực đã nhận. `check`/`push` kiểm tra bằng QA chuẩn. `confirm` đọc ledger và registry mới nhất, không tự tạo nội dung. Giữ đúng session khi phục hồi sau quota. Sau khi bài đã được intake ghi receipt có hash bất biến **và QA mới tính lại đạt PASS**, `begin` được giải phóng ID đã nộp để nhận tiếp, **ngay cả khi Production OFF và WordPress chưa đăng bài**. Một submission đã chuyển qua bước này vẫn khóa ID khỏi writer khác; QA FAIL/REVIEW phải sửa qua REPAIR trước khi nhả lease. WordPress ledger/publisher vẫn chịu trách nhiệm xuất bản và đối soát riêng. Không đổi session để né REPAIR. Lease của người khác còn hạn không được chiếm; bản nháp của người khác hết lease chỉ được bàn giao sau khi chủ/coordinator cho phép.

GitHub Actions tự nhận draft đã push, kiểm tra rồi lưu QA/REPAIR. Production tự động hiện OFF (`dry_run`), dù đã có hai bài SEO công khai do chủ duyệt WPVibe trực tiếp (NT-000037/#3888 và NT-000047/#3890). Khi đủ bảo vệ + nghiệm thu và Production được bật, QA PASS kích hoạt Publisher **ngay**; xử lý tối đa 5 batch × 2 bài mỗi lượt, daily cap 1.000 (vẫn giới hạn 10 bài/lượt). Lịch :17/:47 chỉ dự phòng; không cần phiên AI còn mở để drain backlog bài **đã viết và push**. Actions không viết bài khi các phiên writer đã đóng.

AI chỉ có GitHub, không có shell: push `data/writer-requests/s-your-session.json` với nội dung sau. Actions `Universal AI writer claim requests` sẽ cấp slot và ghi kết quả trong `data/state/writer-claims.json` -> `processed_requests`.

```json
{"request_id":"2026-10-16-001","session":"s-your-session","action":"begin","slot":"auto","count":2}
```

Chờ kết quả CLAIMED, đọc Topic IDs rồi viết và push đúng các draft đó. Publisher intake tự xác minh lease và ghi receipt/hash, AI không tự sửa registry. Đổi `request_id` mỗi lần yêu cầu mới; `heartbeat` gia hạn, `release` nhả slot đã hoàn tất. Khi BLOCKED đọc reason; không tự đoán slot. GitHub API cập nhật ref phải có expected SHA và không force; nếu main đổi, đọc lại trước khi thử.

Số 8 PLANNED / 72 research là **snapshot ban đầu**, không phải số mới nhất. Luôn đọc registry + `reports/dashboard.json` cập nhật; không dùng Excel từ repo khác. Chủ đề phải PLANNED trước claim. Danh mục cha/con lấy từ `data/taxonomy.json`, không phỏng đoán hoặc tạo tự do. Coordinator nghiên cứu thêm qua `data/candidates/*.jsonl` và `topic-factory.py --import-candidates ...`.


### SEO V2 trên website chính — không chấp nhận SEO thấp

Mỗi bài phải đạt SEO ≥85/100 và quality ≥75/100; G1–G6 vẫn PASS độc lập. Xem [SEO QA V2](SEO-QA-V2.md). Khi nhận SEO_SCORE_BELOW_MIN, đọc seo_checks / seo_recommendations, cải thiện nội dung thực chất và chạy lại SHA-256 + QA rồi mới push. Không khai giả SEO score. WordPress vẫn ở dry_run đến khi hoàn thành kích hoạt bảo mật/acceptance riêng.
