# AI ngoài bắt đầu tại đây — một lệnh, không xin duyệt từng bài

**Chỉ repo:** `thuexemayhanoi/wp-writer` — **WordPress đích:** `https://thuexemaynguyentu.com`.
Không trộn `wp-aiwriter` (blog.rentbikehanoi.com) và **KHÔNG sử dụng Excel Nguyễn Hà**. `data/topics.jsonl` là danh sách ID/keyword/intent/topic mới, `data/taxonomy.json` là cây danh mục cha/con; WordPress REST dùng để xác minh đầy đủ parent/slug/ID. Với mỗi bài, AI phải giữ nguyên `taxonomy_key` của Topic ID; `wordpress_category_id` chỉ là bản sao ID đã xác minh, **không thay thế quy trình đối chiếu toàn bộ cây cha/con** trong Publisher. Không tự chọn danh mục khác, không gửi bài thẳng tới WordPress bằng Git it Write. Chủ đề mới chỉ được nhận sau Topic QA thành PLANNED.

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
4. **Ngày 16/10/2026 Production vẫn OFF (`dry_run`)**. Hai bài NT-000037/#3888, NT-000047/#3890 được xuất bản bằng WPVibe trực tiếp, KHÔNG phải Publisher tự đăng. AI tiếp tục viết và QA, đừng tạo lại các Topic ID đã có trong publication ledger.
5. Lịch 30 phút là cơ chế dự phòng, **không phải** khoảng nghỉ bắt buộc giữa các cặp bài.

## Không mắc kẹt vì hạn mức AI

- Khi hết quota, lưu session ID ổn định, Topic IDs, trạng thái QA/REPAIR vào checkpoint của AI.
- Khi mở lại phiên hoặc chuyển máy, đọc registry mới nhất và tiếp tục cùng session khi có thể; **không dùng session mới để cướp lease còn hạn**.
- Nếu `BLOCKED`: đọc `data/state/writer-claims.json` → `processed_requests` để biết lý do chính xác, không sửa registry bằng tay.
- Khi backlog PLANNED thấp, `Universal Topic Discovery` tự sinh research briefs; **cần AI bên ngoài thực sự nghiên cứu và nộp candidate đạt Topic QA** trước khi viết. Đừng gọi ý tưởng chưa được xác minh là PLANNED.

**Giữ nguyên** bài WordPress cũ, sản phẩm, URL, canonical, categories, slug, sitemap. Không xóa và không auto-merge bài trùng.

## Không cần Excel, không yêu cầu duyệt lần lượt từng danh mục

Dựa hoàn toàn vào `data/topics.jsonl` + `data/taxonomy.json` (mỗi bài một topic ID, intent, parent chain). AI có thể nhận đồng thời các topic PLANNED thuộc các leaf category khác nhau. Đúng full ancestry mới đủ điều kiện public khi Production bật; thiếu category thì draft + lý do; không tự suy từ tiêu đề hay nhập file Excel. Xem [so sánh wp-aiwriter / wp-writer](WORKFLOW-COMPARISON-WP-AIWRITER.md). Bài `NT-000079` / WordPress #3882 cần kiểm tra sai khác trạng thái so với draft acceptance lịch sử trước khi đưa vào lô mới.

## Researcher — tự nghiên cứu 10 chủ đề rồi cấp cho Writer

Nếu hàng đợi PLANNED thấp, không cần tự nghĩ tiêu đề lung tung. Đọc [Research V2 Global adaptation](RESEARCH-V2-GLOBAL-ADAPTATION.md), chạy python scripts/research_v2.py hints --limit 10; AI thực sự duyệt nguồn HTTPS, đối chiếu các WordPress posts có intent gần nhất và soạn một batch 10 Topic Registry JSONL trên nhánh research/<stable-session>. Chạy checkpoint, check và push. GitHub Research QA (read-only) PASS -> trusted main auto-intake -> topic thành PLANNED cho W1/W2/W3. Khi mạng/quota gián đoạn dùng resume --apply cùng tên session. Không dùng Google News RSS làm fact source, không sử dụng Excel và không tự nhận các topic chưa PLANNED.

