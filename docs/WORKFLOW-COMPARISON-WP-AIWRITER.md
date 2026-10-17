# So sánh workflow: wp-aiwriter (Excel) và wp-writer (không Excel)

Trạng thái đã kiểm chứng ngày 16/10/2026. Không nhầm site đích:
- `thuexemayhanoi/wp-aiwriter` → `https://blog.rentbikehanoi.com/`.
- `thuexemayhanoi/wp-writer` → `https://thuexemaynguyentu.com/`.

## Khung xử lý giống nhau

1. AI bên ngoài chủ động nghiên cứu, viết Markdown, commit/push lên `main` (không có AI/LLM API trong GitHub Actions).
2. GitHub QA không chứa mật khẩu WordPress; fail/review không được xuất bản.
3. Chỉ QA `success` từ **push trên main** mới kích hoạt `workflow_run` Publisher. Publisher checkout `main`, chạy lại kiểm tra.
4. Khi được phê duyệt live, Publisher dùng WordPress REST, checkpoint write-ahead trước POST, chống tạo trùng và kiểm tra ID, status, slug, category, permalink sau đăng.
5. Không update/delete bài cũ, không chạm Trash, không tự merge trùng chủ đề.

## Điểm khác biệt bắt buộc giữ

| Cơ chế | wp-aiwriter | wp-writer |
|---|---|---|
| Website | blog.rentbikehanoi.com | thuexemaynguyentu.com |
| Nguồn tiêu đề/chuyên mục | 355 dòng Excel → `data/topics.json`, checksum bất biến | `data/topics.jsonl` + `data/taxonomy.json` + Topic QA, **không Excel** |
| ID bài | Excel #146–500 | `NT-XXXXXX` duy nhất |
| Quyền viết | Writer viết đúng title/category_path Excel | Writer claim W1/W2/W3 PLANNED; lease CAS + receipt SHA-256 |
| QA tối thiểu | Python tests + content QA, ≥1000 từ cho bài mới | 6 gate, 1600–5000 từ có chất lượng, evidence/editorial, duplicate guard |
| Đúng danh mục cha/con | Excel `category_path` → đầy đủ ancestry | `taxonomy_key` → `parent_key` chain → WordPress REST ID/slug/name/parent |
| Thiếu/sai taxonomy | WordPress draft + ghi lý do | WordPress draft ở fallback Blog + intended taxonomy + warning (khi production được duyệt) |
| Lặp đăng | 3–5 bài/lần × tối đa 80 vòng, **chỉ trong category hiện được duyệt** | ≤2 bài/batch × ≤5 batch/lượt, daily cap 1.000 (10/lượt), xử lý mọi topic QA-ready đúng taxonomy |
| Kích hoạt | `workflow_run` sau QA main push, `LIVE=true` | `workflow_run` + cron :17/:47 dự phòng, **Production BẬT từ 17/10/2026** |
| Ranh giới chuyên mục | Phải duyệt `active_category` tiếp theo | **Không có** Excel `active_category`/nhóm cố định; Topic Factory phân phối PLANNED khác intent |
| Sổ đăng | `data/publication-state.json` | `data/state/publication-ledger.json` + writer hashes/leases |

## Điều đã được xác minh trực tiếp

- `wp-aiwriter` hiện có QA workflow và Publisher kích hoạt live từ QA `success`, nhưng nhiều run gần nhất đang bị `cancelled` do các push mới; không đánh đồng lịch sử Actions với số bài public. Việc loop không nghỉ chỉ áp dụng khi đầu vào sẵn sàng và QA/credentials tốt.
- `wp-writer` `writer-qa.yml` và `wordpress-publisher.yml` đã nối `workflow_run` đúng; các run `success` có `DRY_RUN: no WordPress writes`. Trần chủ sở hữu đã tăng lên 1.000/ngày từ 17/10/2026; không đảm bảo có 1.000 bài QA PASS hoặc server đủ chịu tải.
- WordPress site Nguyễn Tú có category con `#160 Chăm sóc xe điện` dưới `#157 Xe Điện`, và `#161 An toàn khi di chuyển` dưới `#159 Pháp Lý & Kinh Nghiệm`. Cả 2 bài QA PASS mới đã được chủ cho phép **đăng thủ công qua WPVibe**: `NT-000037` → `#3888`, `NT-000047` → `#3890`; công khai, canonical/title/description/robots đọc được. Xem `reports/manual-wp-smoke-20261016.json`.
- PR đối soát ledger và taxonomy phải QA PASS trước merge. Hai bài thủ công không chứng minh GitHub Publisher tự đăng; không thay đổi chính sách Production, secrets hoặc bảo vệ code đặc quyền chỉ dựa vào kết quả đó.

## Triển khai tiếp để đăng liên tục không cần Excel

1. Hoàn thiện ghi nhận 2 bài thủ công vào ledger để không POST lại; rà soát `NT-000079/#3882` vì WordPress từng có trạng thái khác với report draft cũ.
2. Nguồn topic là JSONL: external AI nghiên cứu nội dung không trùng và gửi `data/candidates/*.jsonl` → Topic QA, W1/W2/W3 nhận khi PLANNED; không tự sinh 1000 bài placeholder.
3. Category `data/taxonomy.json` phải đúng full parent chain trên WordPress. Nếu leaf không có, đưa nháp với lý do; chỉ tạo category có quyền phê duyệt riêng (`allow_category_create`) khi không rỗng và quy trình có ledger.
4. Nghiệm thu **1 bài public qua chính GitHub Publisher** với live frontend SEO + ledger + idempotent rerun. Chỉ khi có bằng chứng đó mới đặt `acceptance_passed`/`security_controls_verified` thành `true`; từ lệnh chủ 17/10/2026 Production đã BẬT và hai cờ không còn chặn đăng.
5. Từ đó AI push → QA PASS → Publisher xử lý ngay theo 2+2+2+2+2, ngày trần 1.000 (10/lượt), không phải duyệt từng category Excel và không đợi 30 phút.

## Lưu ý về số liệu

- `wp-writer` dashboard chỉ thống kê bài trong ledger đã xác minh, không đồng nghĩa các bài WordPress khác được sửa/xuất bản bởi công cụ ngoài; luôn đối soát khi có manual publication.
- GitHub Actions `success` ≠ đã đăng; `VERIFIED` phải có đúng WP ID, permalink, category, hash/marker, trạng thái và SEO readback.
- AI không còn phiên làm việc thì GitHub Actions không tự sáng tác bài mới. Backlog cạn phải có researcher đang chạy để biến candidate thành PLANNED.

