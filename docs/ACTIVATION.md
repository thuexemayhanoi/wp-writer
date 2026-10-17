# Công tắc auto-publish

Hiện tại **OFF trên `main`** (kiểm tra 2026-10-16). Một mình `production_enabled=true` không đủ mở xuất bản.

## Checkpoint đã hoàn thành — 17/10/2026

**Đã xác minh trực tiếp, không bắt Tổng Thống nhập lại:**

- GitHub `wordpress-production`: nhánh triển khai **chỉ `main`**, do owner cài trên màn hình Settings.
- Cả ba **Environment Secrets**: `WP_URL`, `WP_USERNAME`, `WP_APPLICATION_PASSWORD` đã tạo. GitHub Actions [read-only run 39022902385](https://github.com/thuexemayhanoi/wp-writer/actions/runs/39022902385) **PASS** với `ENVIRONMENT_CREDENTIALS_OK`; không ghi vào WordPress.
- [PR #35](https://github.com/thuexemayhanoi/wp-writer/pull/35) **đã merge**, [QA run 39023486840](https://github.com/thuexemayhanoi/wp-writer/actions/runs/39023486840) **PASS**. Tất cả job cần WP credentials đều khai báo `environment: wordpress-production`; smoke test cũ được thay bằng GET chỉ đọc. Các audit/acceptance có secrets chỉ còn `workflow_dispatch`, không tự ghi draft khi workflow file thay đổi.
- 8 bài QA PASS được owner duyệt công khai qua WP REST và đọc lại Yoast SEO, đã đối soát ledger `NT-000075/101–107`, WordPress IDs **3938–3945**. Tổng số bài public đã kiểm tra: **150**. Đây là **manual canary**, KHÔNG phải kiểm thử GitHub Publisher tự POST công khai.
- Các bản sao **Repository Secrets cũ vẫn còn** sau khi chuyển; chủ repo cần xóa 3 bản sao ở `Settings → Secrets and variables → Actions → Repository secrets` **sau khi xác minh toàn bộ workflow sử dụng Environment**. Không đưa giá trị Secrets vào chat, log hoặc commit.
- GitHub Rule ID **25248247** hiện chỉ có `deletion` + `non_fast_forward`. Đây **không phải** kiểm soát quyền sửa `.github/workflows`, `scripts`, `config`. `security_controls_verified=false` là đúng. GitHub public repo không có push ruleset chặn đường dẫn như private/internal Team; không tự nhận tính năng chưa có.
- **QUAN TRỌNG — chưa được bật Require Pull Request ngay:** các Writer W1/W2/W3 và một số trusted CAS/state workflow hiện push trực tiếp `main`; bật PR bắt buộc mà không đổi đường đi sẽ làm nghẽn Factory. Trước hết xây và kiểm thử Writer branch → PR → QA → chỉ auto-merge PR nội dung (không cần owner duyệt từng bài), và route state CAS qua đường tin cậy. Sau đó owner mới bật Ruleset có **CODEOWNER review** cho đặc quyền, không bypass tuỳ tiện; phải kiểm nghiệm W1/W2/W3 không bị khóa.
- Git it Write trên WordPress trước đó được phát hiện cấu hình trỏ vào cùng repository `wp-writer`. Cần vô hiệu **đúng liên kết nhập đồng bộ từ repo này** và xác minh lại trước auto-public, tránh đường xuất bản ngoài QA. Không vô hiệu tuỳ tiện toàn bộ plugin nếu có site/repo khác dùng.
- **Production vẫn OFF** (`dry_run`, `paused=true`, `emergency_stop=true`), `acceptance_passed=false` và `security_controls_verified=false`. Chỉ bật sau Ruleset có bằng chứng thực tế, thử GitHub Publisher public canary + frontend Yoast + durable ledger + rerun không trùng. Không dùng thành công của manual WPVibe để gán cờ E2E giả.

**Việc AI/Work có thể làm tiếp mà KHÔNG cần Tổng Thống điền thêm Secrets:** thiết kế luồng Writer PR tự hợp nhất có kiểm tra riêng mã đặc quyền, thử nghiệm GitHub không ảnh hưởng `main`, xử lý CAS/state, viết unit tests; báo lại đúng 1 thao tác GitHub Ruleset cần chủ tài khoản thực hiện sau khi đường Writer đã chuyển đổi và QA PASS. Trong khi làm, giữ W1/W2/W3 đang chạy bình thường và không đổi URL, category, theme, bài viết WordPress.

## Checkpoint đã xác minh — không làm lại kết nối

- GitHub main đã `protected=true`. Ruleset `WP Writer - Main Protection` ID `25248247` đang **Active**, cấm xóa nhánh và force-push, **bypass list trống**. Hai quy tắc này vẫn cho phép mọi tài khoản có quyền Write cập nhật mã Publisher trên main; KHÔNG chứng minh `security_controls_verified`.
- PR [#15](https://github.com/thuexemayhanoi/wp-writer/pull/15) đã merge: CODEOWNERS thu hẹp bảo vệ đường dẫn mã đặc quyền và không còn bao phủ bài viết Writer. CODEOWNERS chưa được enforce vì Ruleset chưa yêu cầu PR + code owner review.
- WordPress draft REST acceptance: `reports/acceptance-rest.json` PASS với bản nháp #3870; `reports/article-acceptance.json` từng ghi nhận NT-000079 → **draft** #3882. **Đã đọc lại ngày 16/10: #3882 hiện ở trạng thái publish, danh mục #159, khác bản draft acceptance trước; không tự sửa/ghi đè mà phải báo drift.**
- Yoast title/description REST readback: [GitHub Actions 38910018718](https://github.com/thuexemayhanoi/wp-writer/actions/runs/38910018718) PASS; chỉ `seo_adapter_verified=true` có đủ chứng cứ.
- **Kiểm thử công khai thủ công:** hai bài thật QA PASS đã được xuất bản qua WPVibe và đọc lại frontend SEO/canonical/index: NT-000037 → WordPress #3888 (category #160), NT-000047 → #3890 (category #161), xem `reports/manual-wp-smoke-20261016.json`. Đây là proof WordPress REST hoạt động, **chưa chứng minh workflow Publisher GitHub tự ghi bài public**.
- Chủ sở hữu đã yêu cầu Production ngày 2026-10-16; thay đổi `mode=production`, `production_enabled=true`, owner approval nằm trong [PR #14](https://github.com/thuexemayhanoi/wp-writer/pull/14) **draft, chưa merge**. QA PR #14 PASS: run 38922311356. Không merge tới khi bảo vệ quyền đặc biệt và full public canary được nghiệm thu.

## Rủi ro nhập WordPress ngoài workflow (xác minh 17/10/2026)

- **Git it Write ACTIVE** trên WordPress; cấu hình `giw_repositories` có repo `thuexemayhanoi/wp-writer`, branch `main`, folder `posts`, post type `post`. Mã plugin mặc định `post_status=publish` nếu không có frontmatter trạng thái và có thể duyệt thư mục con. Khi webhook hoặc đồng bộ thủ công kích hoạt, plugin có thể tạo bài mà không qua G1–G6/ledger. Không đồng nhất với Publisher REST GitHub đang `dry_run`.
- Trước Production cần ngắt repo này khỏi Git it Write hoặc deactivate plugin một cách có xác nhận và xác minh lại trạng thái. **Chưa thực hiện** thao tác này; không tự nhận là hoàn tất.
- Phát hiện WPVibe HTTP 429 trong audit. PR #26 đã merge xử lý GET với 60 giây cooldown/Retry-After và 1 retry; POST không retry. Không thể khẳng định host sẽ chấp nhận lưu lượng 1.000 bài/ngày.
- 16 term mới đã được xác minh WordPress ID 162–177 và đồng bộ vào taxonomy; PR #27 đã điền 65 topic WordPress IDs. `Xử lý sự cố` tiếp tục PLANNED/chưa tạo.

## Việc còn lại để tự đăng mà KHÔNG duyệt từng bài

1. Phải thực thi *phân quyền mã đặc quyền thực tế* (không chỉ CODEOWNERS). Nếu chọn Ruleset yêu cầu PR + code owner review trên `main`, trước tiên điều chỉnh luồng nhận Writer + các GitHub Actions hiện push trực tiếp `main` để dùng PR tự hợp nhất hoặc nhánh state riêng; bật PR ngay khi chưa điều chỉnh sẽ chặn pipeline. Hoặc cách ly Publisher tại trusted workflow/repository/branch dùng GitHub Environment với secrets chỉ khả dụng cho luồng tin cậy; writer main chỉ có quyền cung cấp nội dung đã qua QA.
2. Yêu cầu thay đổi GitHub Ruleset/Environment/secrets thực hiện trong phiên **Admin đăng nhập**. GitHub connector hiện chỉ đọc được Ruleset, không có action ghi bảo vệ; browser cloud kiểm tra 2026-10-16 chưa đăng nhập. Không xác nhận an toàn giả bằng cách đổi các cờ xác minh.
3. Nghiệm thu 1 bài public mới đúng taxonomy, 1.600–5.000 từ và QA PASS với full public frontend canonical/title/meta + WordPress ID + durable ledger + idempotent rerun. Chỉ xác nhận `acceptance_passed` sau khi kiểm tra thật.
4. Khi các điều kiện đã có chứng cứ, merge thay đổi config nghiệm thu vào main, xác nhận GitHub Actions QA → Publisher → WordPress VERIFIED `publish`, cap 2×5 và trần 1.000 bài/ngày (tối đa 10 mỗi run). Không dùng bài cũ #3870 hoặc #3882 để tự nâng cấp từ draft lên public.


Nâng cấp pipeline đã có chính sách định tuyến: bài đúng full category → public khi Production được duyệt; category thiếu/sai → WordPress DRAFT tại Blog với nhãn lý do; QA FAIL/REVIEW → không tạo post. **Không bật staging/production khi branch/security và WordPress API chưa nghiệm thu.** Xem [WORDPRESS-AUTO-DELIVERY.md](WORDPRESS-AUTO-DELIVERY.md).

Trước khi chủ phê duyệt cần xử lý các điều kiện còn thiếu:

1. GitHub: bật ruleset/branch protection có yêu cầu CODEOWNER review và chặn external writer sửa workflow, scripts, requirements/config/data chuẩn. Chỉ cấp quyền viết nội dung qua PR hoặc credentials giới hạn. CODEOWNERS hiện có chỉ là file, không tự bảo vệ repo. Không chia sẻ tài khoản owner/admin cho writer.
2. Bảo vệ WordPress credentials bằng GitHub Environment được giới hạn nhánh/workflow và quyền quản trị phù hợp. Nếu dùng required reviewers cho mọi deployment thì sẽ cần duyệt mỗi run; để chạy liên tục sau phê duyệt ban đầu, dùng policy nhánh và quyền writer đã khóa. Không đặt secret vào job QA/PR.
3. WordPress: **đã PASS kiểm tra Yoast REST bằng đúng GitHub Actions credentials** tại [run #38910018718](https://github.com/thuexemayhanoi/wp-writer/actions/runs/38910018718). Title/description ghi và đọc lại trên nháp thử #3870. `_yoast_wpseo_canonical` không cần REST-writeable: site hiện sinh canonical đúng từ permalink; Publisher bắt buộc đối chiếu canonical/title/description frontend sau khi đăng. `seo_adapter_verified=true` có bằng chứng, không đồng nghĩa đã nghiệm thu xuất bản bài công khai.
4. Chạy thử với **bài thật 1.600–5.000 từ** đạt sáu gate, mapping đúng và metadata readback/frontend; REST draft #3870 chỉ chứng minh kết nối, giao dịch và chạy lại không trùng. Chưa chứng minh full editorial-to-public end-to-end.
5. Hoàn tất nghiệm thu và ghi approval ref thật. Bổ sung nghiên cứu chủ đề: mới 8 PLANNED, còn thiếu 992 so với chỉ tiêu.

Sau khi các điều kiện được chứng minh và chủ duyệt, cập nhật **một** file `config/production-policy.json`:

```json
{
  "mode": "production",
  "production_enabled": true,
  "owner_approval_ref": "tham-chiếu-phê-duyệt-thật",
  "acceptance_passed": true,
  "security_controls_verified": true,
  "seo_adapter_verified": true,
  "paused": false,
  "emergency_stop": false,
  "batch_size": 2
}
```

Các trường khác trong file phải giữ nguyên. Nếu cho phép tạo danh mục just-in-time thì chủ bật thêm `allow_category_create=true` sau khi nghiệm thu tác động. Writer QA PASS trên `main` tự kích hoạt Publisher qua `workflow_run`, tối đa **5 lượt × 2 bài trong một lần chạy** (daily cap 1.000); lịch `:17` và `:47` là cơ chế dự phòng, không bắt Writer chờ 30 phút giữa hai cặp. `main` hiện có Ruleset chống xóa/force-push nhưng chưa chặn sửa mã đặc quyền; vì vậy Production vẫn OFF. Lịch chỉ là drain pipeline đã có nội dung, không sinh bài AI.

Tắt: `production_enabled=false` + `mode=dry_run`; pause/resume ở cùng file. Không cần sửa nhiều workflow hoặc đưa mật khẩu cho writer.

## Trước khi bật (checkpoint mới)

- `/wp-writer` **không sử dụng Excel**: Topic Registry `data/topics.jsonl` + taxonomy `data/taxonomy.json` + WordPress REST để xác minh full ancestry. Không sao chép `active_category` theo Excel từ `wp-aiwriter`.
- Sau khi PR đối soát được merge, Publisher ledger sẽ biết #3888/#3890 đã tồn tại để không tạo lại. Tránh tự chỉnh trạng thái #3882; báo chênh lệch so với sổ khi chạy đối soát.
- Ưu tiên sửa mọi hàng chờ cần `NEEDS_RECONCILE`; đừng gán `acceptance_passed` chỉ từ manual publication. Quyền cấp cho Writer cần cách ly với quyền sửa Publisher và GitHub Actions secrets.
