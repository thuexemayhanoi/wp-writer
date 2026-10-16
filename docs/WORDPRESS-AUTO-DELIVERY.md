# Nâng cấp luồng Writer → WordPress (không sao chép /wp-aiwriter)

## Luồng dữ liệu

```text
W1 / W2 / W3 (AI bên ngoài)
       |
   topic PLANNED + live lease
       |
   posts/drafts/NT-XXXXXX.md → GitHub main
       |
   intake receipt + 6 cổng QA
       |
   Publisher: xem lại hash, kiểm kê WP live, collision, liên kết, taxonomy
       |
       +-- Chưa được duyệt staging/production: DRY RUN, KHÔNG gọi WP
       +-- Đã duyệt staging: đúng category hoặc thiếu → WP DRAFT
       +-- Đã duyệt production:
             +-- đúng full parent/child category → WP PUBLISH
             +-- sai/thiếu/không chắc chắn category → WP DRAFT (Blog)
             +-- category creation approved + readback khớp → WP PUBLISH
       |
   Ghi remote ledger trước POST, xác minh WP, ghi WP ID và receipt
```

**Địa chỉ WordPress duy nhất:** https://thuexemaynguyentu.com. Không đưa bài qua blog.rentbikehanoi.com, không nhập Excel Nguyễn Hà, không sao chép workflow/source code của wp-aiwriter.

### Khi nào được gọi API WordPress

`mode=dry_run` vẫn là chế độ mặc định. Không thể chỉ sửa `mode` để vượt qua chốt an toàn.

**Chế độ staging (nháp tự động trên WP):**
- `mode=draft_only`, `production_enabled=false`.
- `draft_staging_enabled=true`, `draft_staging_approval_ref` là tham chiếu phê duyệt thật.
- `security_controls_verified=true` sau khi kiểm tra quyền repo, bảo vệ main, bảo vệ secrets/environment.
- Chế độ staging *không bao giờ đăng public*, kể cả bài có đúng danh mục. Có thể dùng để kiểm thử pipeline và nhờ người biên tập chỉnh WordPress.

**Chế độ production (tự public bài đạt QA):**
- `mode=production`, `production_enabled=true`, owner approval, nghiệm thu E2E, security controls và Yoast SEO adapter phải *đều* được xác minh.
- Khi category chuẩn khớp chính xác toàn bộ đường dẫn cha/con, bài PASS mới được public.
- Khi category không tồn tại, sai parent/slug/name hoặc chưa rõ ràng: `on_category_mismatch=draft` chuyển bài vào category Blog (ID được xác minh lại từ WordPress), trạng thái WordPress draft. Ledger ghi `intended_taxonomy_key`, `category_warning`, `category_resolution=FALLBACK_DRAFT`, và WP ID.
- Nếu category `uncategorized`, từ chối. Không tự tạo category chỉ vì có bài. Tạo đúng parent/child chỉ khi đã bật riêng `allow_category_create=true` và có ledger trước POST. Mọi kết quả POST category không chắc chắn đều chặn để reconcile, không fallback bừa.
- Giới hạn 2 bài/lần chạy mặc định; riêng tổng tạo bài mới mỗi ngày giới hạn `max_new_posts_daily` hoặc `max_new_drafts_daily` theo trạng thái.
- Có lịch chạy định kỳ và push-trigger: phiên Writer hoàn tất rồi rời khỏi máy không làm mất queue.

**Không đưa mật khẩu WP cho Writer.** External Writer không cần WP login hay AI API. Nhưng nếu Writer có quyền ghi main hoặc thay đổi workflow/config thì repo hiện **chưa an toàn** để bật WordPress secrets. CODEOWNERS **không tự bảo vệ** file. Cần bảo vệ nhánh, bắt buộc duyệt sửa engine/workflow, và GitHub Environment secrets trước khi kích hoạt cả staging lẫn production.

### Không tự thay đổi nội dung cũ

Publisher chỉ dùng endpoint tạo mới. Một draft đã tạo được lưu ledger là `VERIFIED`, không tự chuyển sang public khi cấu hình đổi về sau. Nếu muốn chỉnh danh mục/đăng bài nháp đã tạo, người quản trị có thể dùng WordPress, nhưng phải đối soát lại ledger và Yoast/canonical trước khi coi là đã public. Không tạo một bài mới thay thế cho bản nháp đó, không tự ghi đè, không đổi URL cũ.

Nếu QA FAIL/REVIEW, nguồn pháp lý không xác minh, thiếu receipt đúng session/hash, duplicate/cannibalization hoặc đứt internal link → KHÔNG gửi WP. Test QA là rào chắn kỹ thuật, không thay thế đánh giá chuyên môn thực tế.

### Điều kiện kích hoạt còn thiếu

Theo trạng thái audit 16/10/2026:
1. Repo rulesets trả về rỗng, branch protection chưa xác minh, WordPress secrets chưa có Environment được bảo vệ và xác nhận.
2. Yoast title/description/canonical chưa REST-writeable; cần adapter được nghiệm thu với site/staging trước public.
3. Bài thật đã thử tạo nháp, nhưng chưa có nghiệm thu full editorial-to-public E2E.
4. Topic Factory mới có 8 chủ đề PLANNED và 2 bài QA PASS; không gọi 10.000 capacity là 10.000 bài viết.

Không chỉnh cờ `security_controls_verified`, `seo_adapter_verified` hay `acceptance_passed` sang true nếu chưa có bằng chứng. Nghiệm thu test phải riêng biệt, không dùng bài cũ hay xóa bài kiểm tra.
