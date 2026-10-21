# Factory-state — nhánh riêng cho sổ xuất bản và các Writer

**Trạng thái (17/10/2026): ĐÃ TẠO NHÁNH + ĐÃ VIẾT BỘ CAS RIÊNG, CHƯA CHUYỂN NGUỒN TRẠNG THÁI SANG NHÁNH NÀY** (Production vẫn đăng bình thường từ `main` theo lệnh chủ 17/10/2026).

- Nhánh đã tồn tại: [factory-state](https://github.com/thuexemayhanoi/wp-writer/tree/factory-state).
- Nhánh kỹ thuật chạy chương trình: `main` (QA + Publisher + Topic Factory). `factory-state` **không được dùng để chạy mã**; chỉ được đọc các file dữ liệu đã kiểm tra.
- Adapter `FactoryStateCAS` trong `scripts/git_state.py` chỉ cho ghi danh sách hẹp: `data/state/*.json`, `data/qa/NT-XXXXXX.json`, các báo cáo trực tiếp `reports/*.json|csv|md`. **CẤM** sửa bài, taxonomy, Topic Registry, scripts, workflow, Secrets, policy. Kiểm tra trước CAS và ngay trước push, không force-push.
- Kiểm thử dùng Git bare repo thật: Writer đồng thời cập nhật bài trên `main` không mất bài, hai Writer ghi cùng file trạng thái thì phát hiện conflict, `POST_INTENT` chỉ ghi lên nhánh dữ liệu, `main` không đổi, không thể ghi mã Publisher qua adapter, không có WordPress POST.

## Chưa được bật một cách thiếu kiểm chứng

Adapter hiện là **tính năng chuẩn bị**; các workflow Writer/Publisher cũ vẫn gọi `RemoteState` và lưu ledger lên `main`. Chỉ tạo nhánh `factory-state` không tự chuyển nguồn đọc trạng thái hoặc mở khóa Production.

Để chuyển thật, cần phối hợp **đọc và ghi cùng một nguồn**:
1. Tạo và thực thi quy tắc chặn người viết bài sửa `factory-state`, chỉ cho hệ thống tin cậy cập nhật; nếu sử dụng GitHub App/deploy key, phải có quyền riêng và được owner phê duyệt. Không cấu hình bypass rộng cho toàn bộ Writer.
2. Đưa `writer-claims`, `publication-ledger`, các báo cáo QA và checkpoints sang `factory-state`; tải về từ đúng nhánh trước khi một job kiểm tra claim, phát hiện duplicate hay ghi `POST_INTENT`. **Không để hai ledger hoạt động song song.**
3. Luồng nộp bài `writer/*` phải đưa file bài lên `main` theo Pull Request phù hợp với branch protection. Các luồng refill/research thay đổi taxonomy/topics cũng phải tương thích hoặc chạy theo approval rõ ràng. Không bật bắt buộc PR trên `main` trước bước này.
4. Kiểm tra real E2E: một bài QA ≥76 qua Publisher REST → đúng category/canonical/Yoast → ledger `VERIFIED` trong `factory-state`; chạy lại chính ID không POST lại; crash/retry không trùng.
5. Chỉ sau các bằng chứng đó mới đặt `security_controls_verified`, `acceptance_passed` thành `true`. Hai cờ này chỉ ghi sự thật; từ lệnh chủ 17/10/2026 chúng không còn chặn đăng và Production đã BẬT.

### Owner phải làm gì?

**Chưa cần bấm nút GitHub hoặc tạo Secrets nào lúc này.** Khi kỹ thuật hoàn tất, người chủ sẽ được gửi một link chính xác đến GitHub Rulesets để kiểm soát `factory-state`. Không bảo vệ nhánh bằng một rule không tương thích với GitHub Actions khi chưa kiểm thử quyền ghi thật.

**Không xóa** `data/state/publication-ledger.json`, `config/production-policy.json`, `Emergency Stop` hoặc hàng đợi QA. Đó là chìa khóa chống đăng trùng hàng loạt.
