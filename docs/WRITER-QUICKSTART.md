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

Thay ID bằng ID thực đã nhận. `check`/`push` kiểm tra bằng QA chuẩn. `confirm` đọc ledger và registry mới nhất, không tự tạo nội dung. Giữ đúng session khi phục hồi sau quota. Sau khi receipt VERIFIED, `begin` giải phóng ID hoàn tất và nhận tiếp. Không đổi session để né REPAIR. Lease của người khác còn hạn không được chiếm; bản nháp của người khác hết lease chỉ được bàn giao sau khi chủ/coordinator cho phép.

GitHub Actions tự nhận draft đã push, kiểm tra rồi lưu QA/REPAIR. Production hiện OFF: không có bài SEO công khai tự đăng. Khi nghiệm thu và được chủ bật production, publisher tự chạy batch tối đa 2; lịch 30 phút tiếp tục drain backlog, không cần phiên AI còn mở. Actions không viết bài khi các phiên writer đã đóng.

AI chỉ có GitHub, không có shell: push `data/writer-requests/s-your-session.json` với nội dung sau. Actions `Universal AI writer claim requests` sẽ cấp slot và ghi kết quả trong `data/state/writer-claims.json` -> `processed_requests`.

```json
{"request_id":"2026-10-16-001","session":"s-your-session","action":"begin","slot":"auto","count":2}
```

Chờ kết quả CLAIMED, đọc Topic IDs rồi viết và push đúng các draft đó. Publisher intake tự xác minh lease và ghi receipt/hash, AI không tự sửa registry. Đổi `request_id` mỗi lần yêu cầu mới; `heartbeat` gia hạn, `release` nhả slot đã hoàn tất. Khi BLOCKED đọc reason; không tự đoán slot. GitHub API cập nhật ref phải có expected SHA và không force; nếu main đổi, đọc lại trước khi thử.

Hiện có 8 topic PLANNED ban đầu; 72 candidate chưa đủ bằng chứng. Không gọi 80 candidate là 80 bài sẵn sàng viết. Coordinator nghiên cứu thêm qua `data/candidates/*.jsonl` và `topic-factory.py --import-candidates ...`.
