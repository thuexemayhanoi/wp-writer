# Công tắc auto-publish

Hiện tại **OFF**. Một mình `production_enabled=true` không đủ mở xuất bản.

Trước khi chủ phê duyệt cần xử lý các điều kiện còn thiếu:

1. GitHub: bật ruleset/branch protection có yêu cầu CODEOWNER review và chặn external writer sửa workflow, scripts, requirements/config/data chuẩn. Chỉ cấp quyền viết nội dung qua PR hoặc credentials giới hạn. CODEOWNERS hiện có chỉ là file, không tự bảo vệ repo. Không chia sẻ tài khoản owner/admin cho writer.
2. Bảo vệ WordPress credentials bằng GitHub Environment được giới hạn nhánh/workflow và quyền quản trị phù hợp. Nếu dùng required reviewers cho mọi deployment thì sẽ cần duyệt mỗi run; để chạy liên tục sau phê duyệt ban đầu, dùng policy nhánh và quyền writer đã khóa. Không đặt secret vào job QA/PR.
3. WordPress: health check hiện báo `_yoast_wpseo_title`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_canonical` chưa REST-writeable. Cần triển khai/kiểm thử adapter được chủ cho phép trên staging; không thể giả định excerpt sẽ thay SEO metadata. Chưa sửa theme/plugin trên site thật.
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

Các trường khác trong file phải giữ nguyên. Nếu cho phép tạo danh mục just-in-time thì chủ bật thêm `allow_category_create=true` sau khi nghiệm thu tác động. Nhánh main push policy/draft hợp lệ kích hoạt publisher; lịch `:17` và `:47` mỗi giờ tiếp tục queue theo batch 2, daily cap 10 ban đầu. Lịch chỉ là drain pipeline đã có nội dung, không sinh bài AI.

Tắt: `production_enabled=false` + `mode=dry_run`; pause/resume ở cùng file. Không cần sửa nhiều workflow hoặc đưa mật khẩu cho writer.
