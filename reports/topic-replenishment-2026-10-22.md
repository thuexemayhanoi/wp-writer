# Bổ sung chủ đề 22/10/2026 — nhật ký nghiên cứu và danh sách HOLD

Báo cáo tiến độ do phiên điều phối `seodev` ghi, **không phải** bản ghi Topic Registry, ledger hay trạng thái kế hoạch Excel. Chỉ để phiên sau không nghiên cứu lại những hàng đã bị loại. Mọi số liệu "đã đăng" lấy từ ledger `phase=VERIFIED`; cập nhật lần cuối ở cuối tệp.

## 1. Mốc đầu vào (22/10/2026 03:32 UTC)

| Chỉ số | Giá trị |
|---|---|
| Bài `VERIFIED` trong ledger | 627 |
| Dòng Topic Registry | 725 |
| `capacity_remaining` (approved_capacity 2000) | 1.275 |
| Lệnh nạp RF-0005 | đã nhận 29, còn 71 tới mức tối thiểu 100 |

## 2. Kế hoạch 1.482 tiêu đề: giới hạn thực tế

Bộ kiểm tra ý định `intent_guard` (xác định, không dùng mô hình) chạy trên 1.457 hàng chưa có topic:

- Chỉ **305 hàng** có chủ đề (`subject`) duy nhất trong danh mục và không bị FAIL với bài/topic hiện có (214 PASS, 91 REVIEW). Các hàng còn lại hoặc cùng chủ đề với hàng khác, hoặc trùng ý định với bài đã đăng.
- Luật của kế hoạch (SOP §2, bước 2) chỉ cho một ý định mỗi chủ đề. Với tỷ lệ qua nguồn thật quan sát được, kế hoạch chỉ đủ cho khoảng 160–180 chủ đề, **không đủ cho 500**. Phần còn lại phải nghiên cứu ngoài kế hoạch (cụm tự do có nguồn chính thức).
- Hàng nào đã qua nghiên cứu mà bị loại được ghi ở §3. `status.json` của kế hoạch **không** bị sửa.

## 3. Hàng TP đã nghiên cứu: tạo topic và HOLD

| Lô | Danh mục | Topic tạo | TP bị HOLD (lý do ngắn) |
|---|---|---|---|
| r46 | rental-costs (164) | TP-0128→NT-001421, TP-0146→NT-001422 | TP-0020 (đã có #4441, #4350…), TP-0038 và TP-0182 (cùng chủ đề, #4361), TP-0056 và TP-0164 (#4053 FAIL không waive), TP-0074 và TP-0092 (#4048, #4361, #4374), TP-0110 (không có nguồn độc lập tại VN cho thuê theo giờ) |
| r47 | ebikes (166) | TP-0058→NT-001451, TP-0112→NT-001452, TP-0148→NT-001453, TP-0166→NT-001454, TP-0184→NT-001455 | TP-0022 (cùng chủ đề TP-0112), TP-0040 (FAIL cùng chủ đề TP-0184), TP-0076 (#4197, #4195, #4218), TP-0094 (FAIL với NT-090004), TP-0130 (FAIL với WP4221/4214) |
| r48 | driving-licence (171) | TP-0065→NT-001481, TP-0137→NT-001482, TP-0173→NT-001483, TP-0191→NT-001484 | TP-0029 (#4388, #4100, #4440), TP-0047 và TP-0083 (#2559, #2352), TP-0101 (NT-001228–1230, #4555), TP-0119 (cùng chủ đề TP-0173), TP-0155 (#4389) |
| r49 | rental-50cc (165) | TP-0021→NT-001511, TP-0093→NT-001512, TP-0075→NT-001513, TP-0057→NT-001514 | TP-0039 (#4513, #2556), TP-0183 (cùng chủ đề TP-0039), TP-0111 (NT-000018), TP-0129 (#2586), TP-0147 (NT-000018, #2580), TP-0165 (#4351) |
| r50 | green-travel (177) | TP-0017→NT-001541, TP-0161→NT-001542 | (các TP còn lại của lô bị loại, chi tiết trong báo cáo researcher) |
| r51 | electric-transition (169) | TP-0152→NT-001571, TP-0026→NT-001572 | TP-0044 (#4337), TP-0062 (#4494, #4253), TP-0080 (#4378), TP-0098 (#4253, #4257), TP-0116 (cùng chủ đề TP-0098), TP-0134 (nguồn hãng không đọc được), TP-0170 (thiếu toàn văn QCVN 32:2026/BCT), TP-0188 (#2362) |

## 4. Mục cần quyết định của chủ (không tự sửa)

1. **NT-001395** ("VinBus Hà Nội … tuyến 179 và 180"): tiền đề sai — tuyến 179/180 là tuyến buýt điện VinBus ở TP.HCM (Báo Lao Động 21/9/2026, trang VinBus TP.HCM). Phần Hà Nội thật chỉ có E03, E08, E11. Writer không viết. Đề xuất: đổi tiêu đề sang phạm vi Hà Nội hoặc bỏ topic qua quy trình registry hợp lệ. Topic đang `PLANNED`, chưa ai nên claim.
2. **WP#2572** (bảo hiểm xe máy bắt buộc): viết "không có hoặc không mang theo" cùng mức phạt, trong khi điểm a khoản 2 Điều 18 NĐ 168/2024 chỉ nêu "không mang theo" cho xe kinh doanh vận tải và điểm b mới là "không có". Đề xuất chủ rà soát sửa bài (phiên này không có quyền ghi WordPress).
3. **Blog riêng** blog.thuexemaynguyentu.com có bài "tư thế lái xe" (11/10/2026) không nằm trong inventory WordPress — nguy cơ chồng chéo với NT-001512.
4. **Host pháp lý của QA bài**: chỉ `.gov.vn`/`.gov`, `vbpl.vn`, `vanban.chinhphu.vn`, `moj.gov.vn`, `csgt.vn`, `mps.gov.vn` được coi là nguồn cơ quan chính thức; `xaydungchinhsach.chinhphu.vn`, `baochinhphu.vn`, `luatvietnam.vn` không được tính. Researcher nên đăng ký ít nhất một nguồn thuộc danh sách chính thức cho chủ đề pháp lý.
5. **Công cụ ngoài bị lỗi**: Firecrawl hết credit; Ubersuggest `google_suggestions` trả 429 (token hết hạn) nên các lô gần đây không có tín hiệu nhu cầu tìm kiếm.
6. **Ba topic ward NT-001101–1103** vẫn bị giữ vì trùng URL với WP 4344–4346 (REAL_RISK); đây là việc của phiên ward.

## 5. Cập nhật tiến độ

Số topic mới đếm bằng số dòng `data/topics.jsonl` vượt mốc 725 (không tính topic của phiên ward). Mục này được viết tại thời điểm tạo tệp; số liệu hiện hành xem `data/state/publication-ledger.json`, `data/topics.jsonl` và `reports/pipeline-board.json`.

- 03:55 UTC: **+6 topic mới vượt mốc 725** (NT-001511–1514 của r49, NT-001571–1572 của r51), tất cả `PLANNED`. NT-001481–1484 (r48) và NT-001541–1542 (r50) đã nằm sẵn trong mốc 725. Các lô r52–r60 đang chạy; researcher được yêu cầu đẩy lô nhỏ (≥3 chủ đề) bằng phiên con `--final` thay vì chờ đủ 10.
