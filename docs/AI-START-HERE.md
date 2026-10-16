# AI ngoài bắt đầu tại đây — một lệnh, không xin duyệt từng bài

**Chỉ repo:** `thuexemayhanoi/wp-writer` — **WordPress đích:** `https://thuexemaynguyentu.com`.
Không trộn `wp-aiwriter` (blog.rentbikehanoi.com) và không sử dụng Excel Nguyễn Hà.

## Dành cho Claude / ChatGPT Work / Gemini / Mistral / bất kỳ AI có quyền GitHub

> Vào `https://github.com/thuexemayhanoi/wp-writer`. Đọc `AGENTS.md`,
> `docs/WRITER-QUICKSTART.md`, `docs/ARTICLE-CONTRACT.md`,
> `data/business-facts.json`. Nhận tối đa **10 chủ đề PLANNED** bằng
> `python scripts/writer-session.py begin --slot auto --count 10 --session s-<stable-session>`
> (nếu chỉ có GitHub API, nộp `data/writer-requests/s-<stable-session>.json`
> với `{"request_id":"<unique>","session":"s-<stable-session>","action":"begin","slot":"auto","count":10}`
> và đợi `processed_requests` có trạng thái `CLAIMED`).
> Không tự tạo hoặc tự chiếm lease. Ưu tiên sửa những bài REPAIR thuộc
> session của mình. Với từng Topic ID hợp lệ, nghiên cứu nguồn thật, viết
> **1.600–5.000 từ tiếng Việt**, đúng metadata và taxonomy, không viết trùng
> search intent, không bịa dữ kiện. Tạo `posts/drafts/NT-XXXXXX.md`
> đúng `docs/ARTICLE-CONTRACT.md`, chạy QA/check, push từng bài hoặc từng cặp
> để QA sớm; tiếp tục cho đến hết batch 10 ID. Nếu QA FAIL/REVIEW thì đọc
> `data/qa/NT-XXXXXX.json` hoặc GitHub Actions artifact và sửa đúng bài,
> kiểm tra lại, **không lách QA**. Sau khi nộp hết, nhận batch tiếp theo
> nếu còn quota và còn chủ đề. Không hỏi duyệt từng bài; chỉ báo khi gặp
> BLOCKED, hết chủ đề, thiếu nguồn hoặc việc ngoài phạm vi.
>
> **Lưu ý:** chỉ file bài viết, request Writer và candidate nghiên cứu là
> dữ liệu Writer được sửa. **Tuyệt đối không sửa** workflows, scripts,
> policy Production, taxonomy, existing-content inventory, WordPress
> credentials hoặc publication ledger để làm QA PASS.

## Sau khi AI push, điều gì tự làm?

1. `Universal writer QA` đánh giá bài. Bài PASS đi tiếp; bài FAIL/REVIEW có biên bản REPAIR.
2. `Universal WordPress Publisher` tự kích hoạt trên kết quả QA thành công của `main` — không đợi 30 phút mới bắt đầu.
3. Khi Production thực sự bật và đã nghiệm thu, Publisher xử lý tối đa **5 nhóm × 2 bài/lượt**; category đúng mới công khai, không khớp thì nháp; ghi ledger trước REST POST và xác minh URL sau POST.
4. Khi Production chưa bật, Publisher chạy **dry-run**, AI vẫn có thể viết, QA, nộp batch và nhận bài mới. GitHub không tự sinh nội dung khi không có AI bên ngoài đang hoạt động.
5. Lịch 30 phút là cơ chế dự phòng, **không phải** khoảng nghỉ bắt buộc giữa các cặp bài.

## Không mắc kẹt vì hạn mức AI

- Khi hết quota, lưu session ID ổn định, Topic IDs, trạng thái QA/REPAIR vào checkpoint của AI.
- Khi mở lại phiên hoặc chuyển máy, đọc registry mới nhất và tiếp tục cùng session khi có thể; **không dùng session mới để cướp lease còn hạn**.
- Nếu `BLOCKED`: đọc `data/state/writer-claims.json` → `processed_requests` để biết lý do chính xác, không sửa registry bằng tay.
- Khi backlog PLANNED thấp, `Universal Topic Discovery` tự sinh research briefs; **cần AI bên ngoài thực sự nghiên cứu và nộp candidate đạt Topic QA** trước khi viết. Đừng gọi ý tưởng chưa được xác minh là PLANNED.

**Giữ nguyên** bài WordPress cũ, sản phẩm, URL, canonical, categories, slug, sitemap. Không xóa và không auto-merge bài trùng.
