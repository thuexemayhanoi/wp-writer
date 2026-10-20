**Chính sách QA 20/10/2026:** SEO/Quality từ **76/100** được xét qua QA; G3 nguồn HTTPS là tham khảo và lưu cảnh báo audit nếu trích dẫn đã đổi hoặc không mở được. Không đổi các gate kiểm sai thông tin doanh nghiệp, luật không có nguồn chính thức, slug/canonical, danh mục, trùng URL, lease/receipt hoặc G7. Lệnh 85 trong hướng dẫn cũ hết hiệu lực.

# Nộp bài theo nhánh Writer — bước chuẩn bị khóa Publisher

**Áp dụng cho repo `thuexemayhanoi/wp-writer`. Chưa thay đường Writer đang chạy trên main.**

## Vì sao cần đường này?

Khi mã Publisher và Secrets được bảo vệ bằng quyền duyệt GitHub, Writer không thể tiếp tục sửa và đẩy thẳng vào `main`. Đường mới cho Writer gửi **chỉ file bài viết** ở nhánh `writer/<session>`; mã tin cậy từ `main` độc lập kiểm tra rồi mới đưa bài vào kho nội dung.

- Dữ liệu được phép: `posts/drafts/NT-XXXXXX.md` thuộc lease hợp lệ, không quá 10 bài/nhánh/lượt, tối đa 400 KB/file.
- Cấm Writer gửi `scripts/`, `.github/`, `config/`, `data/state/`, danh mục, file Secrets và mọi đường dẫn khác; cấm xóa và đổi tên.
- QA trên nhánh không có mật khẩu WordPress và dùng **mã Python từ `main`**, không chạy mã từ nhánh Writer. Mỗi bài phải qua G1–G6 và SEO ≥76.
- Sau khi QA nhánh xanh, job Intake riêng kiểm tra lại **đúng mã commit**, mã gốc `main`, lease, source hash và chống trùng. Nếu hợp lệ mới cập nhật article và receipt qua cơ chế CAS. Luồng Writer QA/Pubisher cũ trên `main` tiếp tục xử lý.
- Các phiên Writer khác vẫn commit vào `main` (registry nằm trong gần như mọi commit). Nếu `main` đổi trong lúc job Intake đang kiểm tra bài, bước CAS từ chối ghi đè (`State conflict`): job **không đỏ ngay** mà lấy `main` mới nhất của runner (`git fetch` + `reset --hard origin/main`, chỉ trong GitHub Actions) rồi kiểm tra và nhập lại, tối đa 4 lần. Lỗi khác (QA không đạt, nhánh đã đổi, đường dẫn bị cấm) không bao giờ được thử lại.
- Mọi thao tác WordPress vẫn theo Publisher cũ; `emergency_stop=true` và `production_enabled=false` **không bị thay đổi** bởi nâng cấp này.

## Khi sử dụng thử

1. Writer dùng session/lease đã được cấp bởi quy trình hiện tại.
2. Từ `main`, tạo nhánh `writer/<session>` và thêm/sửa đúng bài `posts/drafts/NT-XXXXXX.md`.
3. Push nhánh. Đọc Actions `External Writer Branch QA (read-only)`. FAIL/REVIEW phải sửa bài trong cùng nhánh và Push lại; không sửa điểm.
4. Chỉ khi QA xanh, `Trusted Writer Branch Intake` mới thử đưa bài lên `main`. Sau khi repo kiểm chứng `main` đã nhận bài, Writer không tự push lại một bản khác để tránh trùng.
5. Một receipt thành công chưa phải WordPress `publish`; phải đợi Publisher ledger `phase=VERIFIED` + kiểm tra URL công khai.

## Giới hạn đang còn

**Chưa bật GitHub Ruleset yêu cầu pull request.** Đường branch mới **chỉ giải quyết đầu vào bài viết**, chưa thay thế hết các luồng CAS ghi trạng thái, claim, refill và ledger đang trực tiếp cập nhật `main`. Cần chuyển luồng trạng thái tương thích quy tắc bảo vệ, kiểm thử W1–W9 và QA xanh **trước khi bật Ruleset**. Không ép Ruleset hiện tại và không tự đặt `security_controls_verified=true`.

GitHub `wordpress-production` đã được giới hạn `main` và 3 Environment Secrets đã thử REST đọc thành công. Không cần cấu hình lại, không đưa mật khẩu cho Writer.
