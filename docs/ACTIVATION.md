# Công tắc auto-publish

Hiện tại **OFF trên `main`** (kiểm tra 2026-10-16). Một mình `production_enabled=true` không đủ mở xuất bản.

## Checkpoint đã xác minh — không làm lại kết nối

- GitHub main đã `protected=true`. Ruleset `WP Writer - Main Protection` ID `25248247` đang **Active**, cấm xóa nhánh và force-push, **bypass list trống**. Hai quy tắc này vẫn cho phép mọi tài khoản có quyền Write cập nhật mã Publisher trên main; KHÔNG chứng minh `security_controls_verified`.
- PR [#15](https://github.com/thuexemayhanoi/wp-writer/pull/15) đã merge: CODEOWNERS thu hẹp bảo vệ đường dẫn mã đặc quyền và không còn bao phủ bài viết Writer. CODEOWNERS chưa được enforce vì Ruleset chưa yêu cầu PR + code owner review.
- WordPress draft REST acceptance: `reports/acceptance-rest.json` PASS với bản nháp #3870 (chạy lại không tạo trùng); `reports/article-acceptance.json` PASS bài thật NT-000079 → WordPress **draft** #3882. Không có bài public được nghiệm thu trong hai report này.
- Yoast title/description REST readback: [GitHub Actions 38910018718](https://github.com/thuexemayhanoi/wp-writer/actions/runs/38910018718) PASS; chỉ `seo_adapter_verified=true` có đủ chứng cứ.
- Chủ sở hữu đã yêu cầu Production ngày 2026-10-16; thay đổi `mode=production`, `production_enabled=true`, owner approval nằm trong [PR #14](https://github.com/thuexemayhanoi/wp-writer/pull/14) **draft, chưa merge**. QA PR #14 PASS: run 38922311356. Không merge tới khi bảo vệ quyền đặc biệt và full public canary được nghiệm thu.

## Việc còn lại để tự đăng mà KHÔNG duyệt từng bài

1. Phải thực thi *phân quyền mã đặc quyền thực tế* (không chỉ CODEOWNERS). Nếu chọn Ruleset yêu cầu PR + code owner review trên `main`, trước tiên điều chỉnh luồng nhận Writer + các GitHub Actions hiện push trực tiếp `main` để dùng PR tự hợp nhất hoặc nhánh state riêng; bật PR ngay khi chưa điều chỉnh sẽ chặn pipeline. Hoặc cách ly Publisher tại trusted workflow/repository/branch dùng GitHub Environment với secrets chỉ khả dụng cho luồng tin cậy; writer main chỉ có quyền cung cấp nội dung đã qua QA.
2. Yêu cầu thay đổi GitHub Ruleset/Environment/secrets thực hiện trong phiên **Admin đăng nhập**. GitHub connector hiện chỉ đọc được Ruleset, không có action ghi bảo vệ; browser cloud kiểm tra 2026-10-16 chưa đăng nhập. Không xác nhận an toàn giả bằng cách đổi các cờ xác minh.
3. Nghiệm thu 1 bài public mới đúng taxonomy, 1.600–5.000 từ và QA PASS với full public frontend canonical/title/meta + WordPress ID + durable ledger + idempotent rerun. Chỉ xác nhận `acceptance_passed` sau khi kiểm tra thật.
4. Khi cả hai điều kiện đã có chứng cứ, merge thay đổi config nghiệm thu vào main, xác nhận GitHub Actions QA → Publisher → WordPress VERIFIED `publish`, cap 2×5 và tối đa 10 bài/ngày. Không dùng bài cũ #3870 hoặc #3882 để tự nâng cấp từ draft lên public.


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

Các trường khác trong file phải giữ nguyên. Nếu cho phép tạo danh mục just-in-time thì chủ bật thêm `allow_category_create=true` sau khi nghiệm thu tác động. Writer QA PASS trên `main` tự kích hoạt Publisher qua `workflow_run`, tối đa **5 lượt × 2 bài trong một lần chạy** (daily cap 10); lịch `:17` và `:47` là cơ chế dự phòng, không bắt Writer chờ 30 phút giữa hai cặp. `main` hiện có Ruleset chống xóa/force-push nhưng chưa chặn sửa mã đặc quyền; vì vậy Production vẫn OFF. Lịch chỉ là drain pipeline đã có nội dung, không sinh bài AI.

Tắt: `production_enabled=false` + `mode=dry_run`; pause/resume ở cùng file. Không cần sửa nhiều workflow hoặc đưa mật khẩu cho writer.
