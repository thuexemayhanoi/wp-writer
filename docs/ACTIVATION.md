# Công tắc auto-publish

**17/10/2026 — lệnh chủ repo: bài qua cổng QA thì lên WordPress ngay.** Luồng giữ đơn giản như sơ đồ: W1/W2/W3 viết bài → QA (SEO/Quality ≥85, kiểm tra trùng, đúng danh mục cha/con) → Publisher → WordPress công khai. `mode=production`, `production_enabled=true`, `owner_approval_ref` ghi lệnh chủ, `paused=false`, `emergency_stop=false`. Quy tắc QA không đổi.

**Đã gỡ khỏi đường đăng:** (1) cờ `acceptance_passed` và `security_controls_verified` không còn là điều kiện; (2) bước `production_security.py` (kiểm Ruleset thật) không còn nằm trong job Publisher; (3) bước chạy lại toàn bộ unit test trong job Publisher (test vẫn chạy trong workflow Writer QA là workflow kích hoạt Publisher).

**Chống nghẽn hàng đợi (lệnh ủy quyền của chủ, 17/10/2026):** một bài lỗi không còn chặn các bài khác. (a) `intake.py` trong job Publisher cách ly bản nháp sai và ghi `INTAKE_REJECTED` thay vì làm cả lượt chạy thất bại (nhánh Writer vẫn nghiêm ngặt); (b) `qa.py` ghi phiếu FAIL cho bản nháp không có trong registry thay vì dừng toàn bộ QA; (c) Publisher bỏ qua bài bị từ chối trước khi ghi (trùng, hash đổi, thiếu biên nhận) và bài đang `NEEDS_RECONCILE`, rồi đăng tiếp các bài còn lại; (d) nếu WordPress từ chối POST bằng HTTP 4xx (ví dụ 429) hoặc lượt chạy dừng trước khi POST (policy/bản nháp đổi), ý định ghi trước được rút lại để lượt sau thử lại sạch. Timeout, 5xx hoặc đọc lại sai vẫn là `NEEDS_RECONCILE` và không bao giờ bị POST lại mù quáng.

**Giữ nguyên:** QA G1–G6 và ≥85, ledger ghi trước POST, chống trùng, đúng category, đọc lại canonical/title/meta sau khi đăng, giới hạn 2×5 và trần 1.000 bài/ngày, `paused`/`emergency_stop` là công tắc dừng tức thì.

**Sự thật cần ghi rõ:** `acceptance_passed=false` và `security_controls_verified=false` vẫn đúng với bằng chứng (chưa có Ruleset ép quyền sửa mã đặc quyền; chưa có bài nào do chính Publisher tự đăng được nghiệm thu E2E). Chủ repo chấp nhận rủi ro đó; hai cờ chỉ còn ghi sự thật, không chặn đăng, và không được gán `true` nếu chưa có bằng chứng.

> Các đoạn bên dưới ghi "Production vẫn OFF" là lịch sử trước lệnh chủ ngày 17/10/2026, giữ lại để truy vết.



## Đơn giản hóa workflow — 17/10/2026

- **Đã bỏ hai workflow trùng/cũ:** `.github/workflows/wp-connection-smoke.yml` (trùng với xác thực mới), `.github/workflows/factory-acceptance.yml` (thử tạo nháp cũ, không phải xuất bản thật).
- **Chỉ cần một kiểm tra kết nối:** `.github/workflows/wp-environment-credential-check.yml`, đọc WordPress REST bằng Environment Secrets; đã có bằng chứng PASS sau khi owner xóa Repository Secrets.
- **Không phải chạy các workflow thử nghiệm này khi viết bài.** W1/W2/W3 chỉ nộp bài, Writer QA và Publisher tự nối nhau qua GitHub; người quản lý chỉ kiểm tra các lỗi QA thực tế.
- Không bỏ `config/production-policy.json`, `Emergency Stop`, ledger, QA ≥85, category mapping hay chống trùng. Các phần này bảo vệ website thật. **Xóa workflow phụ không đồng nghĩa Production đã được bật**; tiếp tục xử lý transport CAS và bảo vệ mã.

## Checkpoint đã hoàn thành — 17/10/2026

**Đã xác minh trực tiếp, không bắt Tổng Thống nhập lại:**

- GitHub `wordpress-production`: nhánh triển khai **chỉ `main`**, do owner cài trên màn hình Settings.
- Cả ba **Environment Secrets**: `WP_URL`, `WP_USERNAME`, `WP_APPLICATION_PASSWORD` đã tạo. GitHub Actions [read-only run 39022902385](https://github.com/thuexemayhanoi/wp-writer/actions/runs/39022902385) **PASS** với `ENVIRONMENT_CREDENTIALS_OK`; không ghi vào WordPress.
- [PR #35](https://github.com/thuexemayhanoi/wp-writer/pull/35) **đã merge**, [QA run 39023486840](https://github.com/thuexemayhanoi/wp-writer/actions/runs/39023486840) **PASS**. Tất cả job cần WP credentials đều khai báo `environment: wordpress-production`; smoke test cũ được thay bằng GET chỉ đọc. Các audit/acceptance có secrets chỉ còn `workflow_dispatch`, không tự ghi draft khi workflow file thay đổi.
- [PR #37](https://github.com/thuexemayhanoi/wp-writer/pull/37) **đã merge**: nhánh Writer `writer/*` có QA **không Secrets** và Intake dùng `main` đã được tin cậy, chỉ nạp `posts/drafts/NT-*.md` tối đa 10 bài, kiểm tra đúng commit SHA, lease, QA G1–G6 + SEO ≥85, nhận bài qua CAS và cấm file mã/quyền. Đường cũ vẫn chạy; chưa được bật Ruleset ép PR vì state CAS `main` còn phụ thuộc direct push. Đọc `docs/WRITER-BRANCH-INTAKE.md`.
- [PR #38](https://github.com/thuexemayhanoi/wp-writer/pull/38) **đã merge**: Production preflight yêu cầu Ruleset PR thực thi **CODEOWNER review** và không bypass, đồng thời kiểm tra file CODEOWNERS bao phủ đường dẫn đặc quyền. Cho phép **0 generic approvals** khi `require_code_owner_review=true`: theo GitHub, PR thay đổi file đã gán CODEOWNER vẫn phải được owner duyệt; PR bài viết không gán CODEOWNER không cần duyệt cá nhân. **Chưa mở Ruleset / Production**, vẫn cần chuyển hết writer claims/state/ledger sang đường hỗ trợ protected main và chạy E2E.
- **Protected-main preflight bổ sung:** mã `scripts/git_state.py` hiện vẫn đẩy các giao dịch CAS vào `refs/heads/main`; workflow `factory-audit.yml` đã được chuyển qua chung `RemoteState` CAS, không còn `git push origin HEAD:main` riêng. **Chỉ còn một giao diện CAS** cần nâng cấp thành transport tương thích với Ruleset (hiện vẫn ghi trực tiếp `main`). Một Ruleset PR/CODEOWNER thực thi vẫn sẽ chặn CAS chung đó. Công cụ read-only `scripts/protected_main_readiness.py` và GitHub Actions `Protected main migration readiness` công khai các blocker vào artifact, không tự mở Production, không ghi WordPress. `production_security.py` sẽ chặn xuất bản ngay cả khi Ruleset trông xanh nếu đường lưu state chưa tương thích. Việc giải quyết các state writes là nhiệm vụ kỹ thuật tiếp theo; không yêu cầu chủ repo bật Ruleset ngay.\n- **Kiểm tra WordPress trực tiếp sau PR #38:** bài `publish=150` qua WP-CLI; plugin **Git it Write 2.1 hiện INACTIVE**, không tự nhập bài. Option `giw_repositories` vẫn lưu cấu hình cũ trỏ repo `wp-writer`; phải xác minh plugin không bị kích hoạt lại trước lúc Production ON.

- 8 bài QA PASS được owner duyệt công khai qua WP REST và đọc lại Yoast SEO, đã đối soát ledger `NT-000075/101–107`, WordPress IDs **3938–3945**. Tổng số bài public đã kiểm tra: **150**. Đây là **manual canary**, KHÔNG phải kiểm thử GitHub Publisher tự POST công khai.
- Chủ repo **đã xóa đủ 3 bản sao Repository Secrets** ngày 17/10; ảnh Settings hiển thị `This repository has no secrets`. Vẫn còn đúng 3 Environment Secrets trong `wordpress-production`. Trước đó REST GET đã PASS; sẽ chạy lại read-only test để xác nhận độc lập sau khi xóa bản cũ. Không đưa giá trị Secrets vào chat, log hoặc commit.
- GitHub Rule ID **25248247** hiện chỉ có `deletion` + `non_fast_forward`. Đây **không phải** kiểm soát quyền sửa `.github/workflows`, `scripts`, `config`. `security_controls_verified=false` là đúng. GitHub public repo không có push ruleset chặn đường dẫn như private/internal Team; không tự nhận tính năng chưa có.
- **QUAN TRỌNG — chưa được bật Require Pull Request ngay:** các Writer W1/W2/W3 và một số trusted CAS/state workflow hiện push trực tiếp `main`; bật PR bắt buộc mà không đổi đường đi sẽ làm nghẽn Factory. Trước hết xây và kiểm thử Writer branch → PR → QA → chỉ auto-merge PR nội dung (không cần owner duyệt từng bài), và route state CAS qua đường tin cậy. Sau đó owner mới bật Ruleset có **CODEOWNER review** cho đặc quyền, không bypass tuỳ tiện; phải kiểm nghiệm W1/W2/W3 không bị khóa.
- Git it Write vẫn lưu cấu hình repo `wp-writer` nhưng plugin đã được WPVibe xác minh **INACTIVE** ngày 17/10. Không thay đổi plugin/site lúc này; chỉ cần bảo đảm nó không bật lại (hoặc xoá đúng repo mapping bằng plugin-native API sau approval) trước Production.
- **Production vẫn OFF** (đã chọn `mode=production`, nhưng `production_enabled=false`, `acceptance_passed=false`, `security_controls_verified=false`). Chỉ bật sau Ruleset có bằng chứng thực tế, thử GitHub Publisher public canary + frontend Yoast + durable ledger + rerun không trùng. Không dùng thành công của manual WPVibe để gán cờ E2E giả.

**Việc AI/Work có thể làm tiếp mà KHÔNG cần Tổng Thống điền thêm Secrets:** thiết kế luồng Writer PR tự hợp nhất có kiểm tra riêng mã đặc quyền, thử nghiệm GitHub không ảnh hưởng `main`, xử lý CAS/state, viết unit tests; báo lại đúng 1 thao tác GitHub Ruleset cần chủ tài khoản thực hiện sau khi đường Writer đã chuyển đổi và QA PASS. Trong khi làm, giữ W1/W2/W3 đang chạy bình thường và không đổi URL, category, theme, bài viết WordPress.

## Checkpoint đã xác minh — không làm lại kết nối

- GitHub main đã `protected=true`. Ruleset `WP Writer - Main Protection` ID `25248247` đang **Active**, cấm xóa nhánh và force-push, **bypass list trống**. Hai quy tắc này vẫn cho phép mọi tài khoản có quyền Write cập nhật mã Publisher trên main; KHÔNG chứng minh `security_controls_verified`.
- PR [#15](https://github.com/thuexemayhanoi/wp-writer/pull/15) đã merge: CODEOWNERS thu hẹp bảo vệ đường dẫn mã đặc quyền và không còn bao phủ bài viết Writer. CODEOWNERS chưa được enforce vì Ruleset chưa yêu cầu PR + code owner review.
- WordPress draft REST acceptance: `reports/acceptance-rest.json` PASS với bản nháp #3870; `reports/article-acceptance.json` từng ghi nhận NT-000079 → **draft** #3882. **Đã đọc lại ngày 16/10: #3882 hiện ở trạng thái publish, danh mục #159, khác bản draft acceptance trước; không tự sửa/ghi đè mà phải báo drift.**
- Yoast title/description REST readback: [GitHub Actions 38910018718](https://github.com/thuexemayhanoi/wp-writer/actions/runs/38910018718) PASS; chỉ `seo_adapter_verified=true` có đủ chứng cứ.
- **Kiểm thử công khai thủ công:** hai bài thật QA PASS đã được xuất bản qua WPVibe và đọc lại frontend SEO/canonical/index: NT-000037 → WordPress #3888 (category #160), NT-000047 → #3890 (category #161), xem `reports/manual-wp-smoke-20261016.json`. Đây là proof WordPress REST hoạt động, **chưa chứng minh workflow Publisher GitHub tự ghi bài public**.
- Chủ sở hữu đã yêu cầu Production ngày 2026-10-16; thay đổi `mode=production`, `production_enabled=true`, owner approval nằm trong [PR #14](https://github.com/thuexemayhanoi/wp-writer/pull/14) **draft, chưa merge**. QA PR #14 PASS: run 38922311356. Không merge tới khi bảo vệ quyền đặc biệt và full public canary được nghiệm thu.

## Rủi ro nhập WordPress ngoài workflow (xác minh 17/10/2026)

- **Git it Write INACTIVE** qua WP-CLI ngày 17/10; dữ liệu option `giw_repositories` vẫn chứa repo `thuexemayhanoi/wp-writer`, branch `main`, folder `posts`. Nếu plugin được bật lại, đường đồng bộ có thể vượt QA/ledger. Không đồng nhất với Publisher REST vẫn `dry_run`.
- Trước Production kiểm tra lại plugin vẫn INACTIVE hoặc loại đúng liên kết repo `wp-writer` theo giao diện/plugin-native API; không cần sửa plugin WordPress khi nó vẫn INACTIVE.
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

Công tắc đăng tự động nằm ở **một** file `config/production-policy.json` (từ 17/10/2026 chỉ cần các trường dưới đây):

```json
{
  "mode": "production",
  "production_enabled": true,
  "owner_approval_ref": "tham-chiếu-lệnh-chủ",
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
