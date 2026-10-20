# Viết bằng Claude, ChatGPT, Gemini, Mistral hoặc AI khác

> **Đề tài từ Excel 1.482:** đọc [SOP Excel A–Z](TITLE-PLAN-1482-SOP.md) trước khi gọi Writer. Một dòng TP-XXXX chưa phải một `NT-XXXXXX PLANNED` có thể claim. `python scripts/title_plan_next.py --limit 3` chỉ **đọc đề xuất**, không chiếm lease và không đăng bài. Chỉ bắt đầu Writer khi Topic Factory/Research QA đã ghi thật vào `data/topics.jsonl`.


Theo [quy trình chung W1–W9](WRITER-RESEARCH-CONTRACT.md): một nguồn gốc đã xác minh có thể đủ cho chủ đề hẹp, thêm đối chiếu khi cần. Nộp từng bài/cặp khi đạt, hết batch thì nhận tiếp cùng session theo phạm vi chủ giao, không chờ WordPress và không xin duyệt từng lượt. QA và kết nối hiện tại giữ nguyên; không thêm API AI/khóa.

**Writer pool (18/10/2026):** W1–W9 là 9 vị trí dùng chung hàng đợi. Claude App/AI App tự nhận vị trí trống bằng `--slot auto` (hoặc request GitHub), mỗi phiên giữ tối đa một vị trí và tối đa 10 Topic ID. Không cấp khóa Ed25519, không xác thực tài khoản Claude, không dùng API AI. Giữ nguyên lease còn hạn, checkpoint, chống trùng Topic ID và QA/Publisher đang chạy; Publisher tiếp tục đăng 2 bài mỗi lô.


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

Khi dùng `agent-tools/build_article.py`, luôn truyền `--slot Wn` chính xác theo vị trí đã nhận (`W1` đến `W9`) và `--session` của mình. Công cụ không tự gán W1 cho bài thật. Không có khóa Ed25519 hay API AI.

Thay ID bằng ID thực đã nhận. `check`/`push` kiểm tra bằng QA chuẩn. `confirm` đọc ledger và registry mới nhất, không tự tạo nội dung. Giữ đúng session khi phục hồi sau quota. Sau khi bài đã được intake ghi receipt có hash bất biến **và QA mới tính lại đạt PASS**, `begin` được giải phóng ID đã nộp để nhận tiếp, **không chờ WordPress đăng xong (kể cả khi chủ tạm tắt công tắc production)**. Một submission đã chuyển qua bước này vẫn khóa ID khỏi writer khác; QA FAIL/REVIEW phải sửa qua REPAIR trước khi nhả lease. WordPress ledger/publisher vẫn chịu trách nhiệm xuất bản và đối soát riêng. Không đổi session để né REPAIR. Lease của người khác còn hạn không được chiếm; bản nháp của người khác hết lease chỉ được bàn giao sau khi chủ/coordinator cho phép.

GitHub Actions tự nhận draft đã push, kiểm tra rồi lưu QA/REPAIR. Production tự động BẬT từ 17/10/2026 theo lệnh chủ (các bài #3882, #3888, #3890, #3930–#3945 trước đó đã được đăng thủ công và nằm trong ledger; #3947–#3956 do Publisher tự đăng). QA PASS kích hoạt Publisher **ngay**; xử lý tối đa 5 batch × 2 bài mỗi lượt, daily cap 1.000 (vẫn giới hạn 10 bài/lượt). Lịch :17/:47 chỉ dự phòng; không cần phiên AI còn mở để drain backlog bài **đã viết và push**. Actions không viết bài khi các phiên writer đã đóng.

AI chỉ có GitHub, không có shell: push `data/writer-requests/s-your-session.json` với nội dung sau. Actions `Universal AI writer claim requests` sẽ cấp slot và ghi kết quả trong `data/state/writer-claims.json` -> `processed_requests`.

```json
{"request_id":"2026-10-16-001","session":"s-your-session","action":"begin","slot":"auto","count":2}
```

Chờ kết quả CLAIMED, đọc Topic IDs rồi viết và push đúng các draft đó. Publisher intake tự xác minh lease và ghi receipt/hash, AI không tự sửa registry. Đổi `request_id` mỗi lần yêu cầu mới; `heartbeat` gia hạn, `release` nhả slot đã hoàn tất. Khi BLOCKED đọc reason; không tự đoán slot. GitHub API cập nhật ref phải có expected SHA và không force; nếu main đổi, đọc lại trước khi thử.

Số 8 PLANNED / 72 research là **snapshot ban đầu**, không phải số mới nhất. Luôn đọc registry + `reports/dashboard.json` cập nhật; không dùng Excel từ repo khác. Chủ đề phải PLANNED trước claim. Danh mục cha/con lấy từ `data/taxonomy.json`, không phỏng đoán hoặc tạo tự do. Coordinator nghiên cứu thêm qua `data/candidates/*.jsonl` và `topic-factory.py --import-candidates ...`.


### SEO V2 trên website chính — không chấp nhận SEO thấp

Mỗi bài phải đạt SEO ≥85/100 và quality ≥85/100; G1–G6 vẫn PASS độc lập. Xem [SEO QA V2](SEO-QA-V2.md). Khi nhận SEO_SCORE_BELOW_MIN, đọc seo_checks / seo_recommendations, cải thiện nội dung thực chất và chạy lại SHA-256 + QA rồi mới push. Không khai giả SEO score. Từ 17/10/2026 Production đã BẬT: bài push lên `main` và qua QA sẽ được Publisher đăng lên WordPress ngay, nên chỉ push khi bài đã tự rà soát nguồn và số liệu.

## AUTO-REPAIR WRITER — 10 CONTENT REVISIONS (18/10/2026)

Read docs/WRITER-AUTO-REPAIR.md (single authoritative procedure). The active Claude session first repairs owned unfinished Topic IDs; if none, it continues writing legitimately PLANNED topics. To initialize QA and a durable baseline, run python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Initial draft". After each actual edit, run the same save command with an accurate change note. QA is re-executed, SHA-256 and score/errors are stored, and the draft + checkpoint are committed to an isolated repair/SESSION/NT-XXXXXX branch. A new changed version counts as one repair, up to 10; identical bytes do not count. Use python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX after a quota interruption. Live lease ownership is always checked; no force pushes, no edited QA evidence. Genuine PASS goes through the unchanged writer-session.py push and Publisher. REAL_RISK or exhausted limit remains held, never falsely PASS. Infra/network retry stays 3, separate from content-repair limit 10. GitHub Actions never writes prose or calls an AI without an actual external model connection.
