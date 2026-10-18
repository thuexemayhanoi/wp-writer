# AI ngoài bắt đầu tại đây — một lệnh, không xin duyệt từng bài

Đọc [quy trình chung W1–W9](WRITER-RESEARCH-CONTRACT.md) để dùng cùng quy định nguồn và tiếp tục sau mỗi batch; không API AI, không thêm khóa hoặc bước duyệt tay. Một nguồn gốc đã đọc, đủ bằng chứng có thể đủ cho chủ đề hẹp; đối chiếu thêm khi cần.

**Writer pool (18/10/2026):** W1–W9 là 9 vị trí dùng chung hàng đợi. Claude App/AI App tự nhận vị trí trống bằng `--slot auto` (hoặc request GitHub), mỗi phiên giữ tối đa một vị trí và tối đa 10 Topic ID. Không cấp khóa Ed25519, không xác thực tài khoản Claude, không dùng API AI. Giữ nguyên lease còn hạn, checkpoint, chống trùng Topic ID và QA/Publisher đang chạy; Publisher tiếp tục đăng 2 bài mỗi lô.


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
> **CẢNH BÁO:** Plugin WordPress `Git it Write` đang cấu hình cùng repo `wp-writer` và có thể đăng `posts/**` ngoài G1–G6. Không dùng webhook, nút import hoặc đồng bộ plugin này để xuất bản. Plugin đã được kiểm tra ở trạng thái INACTIVE ngày 17/10/2026 (Production GitHub đang bật); không kích hoạt lại và không dùng nó để xuất bản.
>
> **Lưu ý:** chỉ file bài viết, request Writer và candidate nghiên cứu là
> dữ liệu Writer được sửa. **Tuyệt đối không sửa** workflows, scripts,
> policy Production, taxonomy, existing-content inventory, WordPress
> credentials hoặc publication ledger để làm QA PASS.

## Sau khi AI push, điều gì tự làm?

1. `Universal writer QA` đánh giá bài. Bài PASS đi tiếp; bài FAIL/REVIEW có biên bản REPAIR.
2. `Universal WordPress Publisher` tự kích hoạt trên kết quả QA thành công của `main` — không đợi 30 phút mới bắt đầu.
3. Production đang bật (lệnh chủ 17/10/2026): Publisher xử lý tối đa **5 nhóm × 2 bài/lượt**; category đúng mới công khai, không khớp thì nháp; ghi ledger trước REST POST và xác minh URL sau POST (biên bản G7).
4. **Từ 17/10/2026 Production BẬT theo lệnh chủ**: bài qua QA lên WordPress ngay. Các bài #3882, #3888, #3890, #3930–#3932, #3935, #3938–#3945 được xuất bản thủ công (không phải Publisher); #3947–#3956 do chính GitHub Publisher tự đăng. AI tiếp tục viết và QA, đừng tạo lại các Topic ID đã có trong publication ledger.
5. Lịch 30 phút là cơ chế dự phòng, **không phải** khoảng nghỉ bắt buộc giữa các cặp bài.

## Không mắc kẹt vì hạn mức AI

- Khi hết quota, lưu session ID ổn định, Topic IDs, trạng thái QA/REPAIR vào checkpoint của AI.
- Khi mở lại phiên hoặc chuyển máy, đọc registry mới nhất và tiếp tục cùng session khi có thể; **không dùng session mới để cướp lease còn hạn**.
- Nếu `BLOCKED`: đọc `data/state/writer-claims.json` → `processed_requests` để biết lý do chính xác, không sửa registry bằng tay.
- Khi backlog PLANNED thấp, `Universal Topic Discovery` tự sinh research briefs; **cần AI bên ngoài thực sự nghiên cứu và nộp candidate đạt Topic QA** trước khi viết. Đừng gọi ý tưởng chưa được xác minh là PLANNED.

**Giữ nguyên** bài WordPress cũ, sản phẩm, URL, canonical, categories, slug, sitemap. Không xóa và không auto-merge bài trùng.

## Không cần Excel, không yêu cầu duyệt lần lượt từng danh mục

Dựa hoàn toàn vào `data/topics.jsonl` + `data/taxonomy.json` (mỗi bài một topic ID, intent, parent chain). AI có thể nhận đồng thời các topic PLANNED thuộc các leaf category khác nhau. Đúng full ancestry mới được public (Production đang bật); thiếu category thì draft + lý do; không tự suy từ tiêu đề hay nhập file Excel. Xem [so sánh wp-aiwriter / wp-writer](WORKFLOW-COMPARISON-WP-AIWRITER.md). Bài `NT-000079` / WordPress #3882 cần kiểm tra sai khác trạng thái so với draft acceptance lịch sử trước khi đưa vào lô mới.

## Cơ hội SEO có dữ liệu thật — ưu tiên nghiên cứu (18/10/2026)

Trước khi lấy những gợi ý RSS chung, đọc [25 chủ đề SEO và 10 URL/nhóm từ khóa nên củng cố](../data/research/seo-opportunities-2026-10-18.json). Dữ liệu GSC từ SiteGuru (16/09–15/10/2026) và Ubersuggest thị trường Việt Nam; các con số trên từng gợi ý **thuộc từ khóa cha**, không phải lượng tìm kiếm đã xác minh của tiêu đề bài dự kiến. Không cam kết trang 1 sau vài tháng.

Khi chạy `python scripts/research_v2.py hints --limit 10`, hệ thống hiện **ưu tiên cơ hội SEO-...** chưa tiếp nhận/nộp trước các đề xuất NTD từ RSS. Người nghiên cứu chỉ nhận ý tưởng, kiểm tra trùng với toàn bộ WordPress/Topic Registry và bằng chứng nguồn, rồi nộp qua đúng research batch + Research QA → Trusted Intake; **không** thêm trực tiếp vào PLANNED hoặc đăng WordPress. Nếu cùng intent với URL cũ, **bỏ ý tưởng tạo bài** và ghi nhận nhu cầu nâng cấp URL hiện có: trang chủ cho "thuê xe máy Hà Nội", trang 50cc, danh mục xe điện, sản phẩm và trang thuê tháng. Không được viết trang khu vực hàng loạt theo kiểu doorway.

Danh sách `existing_url_priorities` chỉ dành để phân tích/bổ sung có kiểm soát, không qua Writer xuất bản bài mới. Không thay đổi title/meta trang chủ, URL, canonical, menu, chính sách, flag Production hay gate QA. Sau khi AI nộp hoặc chủ đề đã vào registry, gợi ý sẽ được loại khỏi `hints` nhờ `origin_id` ổn định; tránh lấy lại chủ đề đã xử lý.

## Researcher — tự nghiên cứu 10 chủ đề rồi cấp cho Writer

Khi PLANNED sẵn sàng viết còn dưới 900 (mục tiêu kho 1.000 chủ đề trong trần đã duyệt), bộ điều khiển tự mở đơn 100–200 chủ đề, hết đợt này mở đợt khác ([hệ thống tự bổ sung](SELF-REPLENISHING-TOPICS.md)): chạy `python scripts/research_v2.py plan` để xem đơn, quota danh mục và batch kế tiếp, và `python scripts/research_v2.py intent-check --file data/candidates/<session>-NNNN.jsonl` trước mỗi lần push. Nếu hàng đợi PLANNED thấp, không cần tự nghĩ tiêu đề lung tung. Đọc [Research V2 Global adaptation](RESEARCH-V2-GLOBAL-ADAPTATION.md), chạy python scripts/research_v2.py hints --limit 10; AI thực sự duyệt nguồn HTTPS, đối chiếu các WordPress posts có intent gần nhất và soạn một batch 10 Topic Registry JSONL trên nhánh research/<stable-session>. Chạy checkpoint, check và push. GitHub Research QA (read-only) PASS -> trusted main auto-intake -> topic thành PLANNED cho W1–W9. Khi mạng/quota gián đoạn dùng resume --apply cùng tên session. Không dùng Google News RSS làm fact source, không sử dụng Excel và không tự nhận các topic chưa PLANNED.

## AUTO-REPAIR WRITER — 10 CONTENT REVISIONS (18/10/2026)

Read docs/WRITER-AUTO-REPAIR.md (single authoritative procedure). The active Claude session first repairs owned unfinished Topic IDs; if none, it continues writing legitimately PLANNED topics. To initialize QA and a durable baseline, run python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Initial draft". After each actual edit, run the same save command with an accurate change note. QA is re-executed, SHA-256 and score/errors are stored, and the draft + checkpoint are committed to an isolated repair/SESSION/NT-XXXXXX branch. A new changed version counts as one repair, up to 10; identical bytes do not count. Use python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX after a quota interruption. Live lease ownership is always checked; no force pushes, no edited QA evidence. Genuine PASS goes through the unchanged writer-session.py push and Publisher. REAL_RISK or exhausted limit remains held, never falsely PASS. Infra/network retry stays 3, separate from content-repair limit 10. GitHub Actions never writes prose or calls an AI without an actual external model connection.
