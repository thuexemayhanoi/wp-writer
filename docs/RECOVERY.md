# Recovery

Pause: sửa `config/production-policy.json` -> `paused: true`. Emergency stop: `emergency_stop: true`. Commit/push; publisher nạp lại policy ở từng điểm an toàn. Một POST đã tới WordPress cần được đối soát, không thể thu hồi bằng cờ pause.

Không xóa ledger, registry, QA evidence; không reset POST_INTENT/NEEDS_RECONCILE/VERIFY_PENDING. Ledger đã push trước mỗi POST. Sau crash, chạy publisher lại: chỉ đọc và xác minh marker/topic/hash/status/category rồi ghi VERIFIED. Nếu không tìm thấy post hoặc thấy nhiều hơn một, giữ BLOCKED để điều tra; không tự POST lại.

Chạy `python scripts/reconcile.py` với WordPress credentials trong môi trường vận hành được cấp phép để tạo báo cáo đọc-only trên WordPress. Chỉ commit reconciliation bằng CAS và đối chiếu ledger mới nhất; không chạy bản local stale. Không đụng Trash. Post bị xóa/chuyển Trash không được tự tái tạo.

Category đã tạo nhưng bài lỗi: ledger categories giữ `CREATED_PENDING_ARTICLE` và term ID. Reconcile nhận diện term theo slug + parent; bài READY được ưu tiên chạy lại. Không tự xóa category và không tạo lại term cùng slug. Tồn tại category rỗng chưa xử lý là một violation cần hiển thị, không đánh dấu hoàn tất.

Mất quota: draft đã push vẫn ở queue. Sau khi intake lưu receipt hash chính xác và QA kiểm tra lại đạt PASS, writer dùng lại chính session với `begin` để nhận chủ đề mới ngay cả khi Production OFF; không chờ WordPress publish. QA FAIL/REVIEW vẫn yêu cầu REPAIR trước khi đổi bài. Bản đã nộp giữ nguyên, không đổi session để né lỗi; lease còn hạn của người khác bị từ chối. Không force push. State CAS conflict -> fetch lại, đọc nguyên nhân; không rebase mù checkpoint/ledger.

Rollback engine: revert commit code bằng commit mới, giữ nguyên toàn bộ ledger và URL đã tạo; không rollback state để chạy POST lần nữa. Smoke #3861 và acceptance #3870 chỉ là draft kiểm thử được bảo vệ, không phải nội dung chiến dịch.
