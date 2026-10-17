# Rà soát 72 chủ đề RESEARCH (seed) — 2026-10-17

Phạm vi: chỉ đọc. Không đổi `data/topics.jsonl`. Công cụ: `scripts/intent_guard.py` chạy trên toàn bộ inventory WordPress hiện tại (184 mục, gồm 10 bài factory #3947–#3956) và mọi hàng topic còn sống trong kho. Máy chỉ là bộ lọc từ vựng, không chứng minh khác ý định.

## Kết quả

- 72 seed: **71 không trùng ý định** với bất kỳ URL hoặc topic nào, **1 REVIEW** (NT-000001 so với WP2588, độ chồng từ vựng 0,218: chỉ giống ở "một … ba"; cần ghi lý do tách ý định trước khi nghiên cứu).
- Không seed nào có bằng chứng nghiên cứu (`research` = null). Vì vậy chưa seed nào đủ điều kiện PLANNED và **không seed nào được tính vào kho 100**.
- Candidate import không sửa được topic đã có ("Existing topic immutable"), nên researcher không thể hoàn tất seed tại chỗ. Seed là kho ý tưởng: researcher chọn góc khác (ID mới `NT-0002xx+`) hoặc, khi cần, chủ repo duyệt đường "hoàn tất seed tại chỗ" (xem dưới).
- Seed ở trạng thái RESEARCH vẫn giữ ý định trong bộ chống trùng: một chủ đề mới giống seed sẽ bị FAIL `intent collision:NT-0000xx`. Đây là chủ ý (không để hai URL tranh một câu hỏi).

## Phân bổ theo cụm

| Taxonomy key | Số seed | Cụm nghiên cứu phụ trách góc tương tự |
|---|---:|---|
| rental-procedures | 8 | r12 (phần thủ tục/cọc/hợp đồng) |
| reviews | 7 | r5/r6 (xe số, xe tay ga) và r10 (xe điện vs xăng) |
| electric | 6 | r10 |
| urban-mobility | 6 | r14 |
| ebikes | 5 | r10 |
| rental-costs | 4 | không cụm nào (cần số giá xác nhận từ chủ cửa hàng) |
| battery-charging | 4 | r10 |
| driving-licence | 4 | r12 |
| engine-care | 4 | r8/r9 |
| food-culture | 4 | r14 |
| rental-50cc | 3 | r7 |
| hanoi-travel | 3 | r13 |
| vietnam-travel | 3 | r13 |
| electric-transition | 3 | r10 |
| electric-maintenance | 2 | r10 |
| road-safety | 2 | r11 |
| trip-planning | 2 | r13 |
| green-travel | 1 | r14 |
| legal | 1 | r12 |

## Từng seed

| ID | Tiêu đề seed | Key | Bộ chống trùng |
|---|---|---|---|
| NT-000001 | Thuê xe máy một ngày hay ba ngày ở Hà Nội: các khoản phí cần hỏi trước | rental-procedures | REVIEW vs WP2588 |
| NT-000002 | Gia hạn hợp đồng thuê xe máy đang sử dụng: những câu hỏi cần xác nhận | rental-procedures | PASS |
| NT-000003 | Trả xe máy thuê trước thời hạn: cần trao đổi những gì với cửa hàng? | rental-procedures | PASS |
| NT-000004 | Kiểm tra biên nhận đặt cọc xe máy: các thông tin nên có | rental-procedures | PASS |
| NT-000005 | Thuê xe máy theo tuần cho người đi công tác: lập ngân sách thế nào? | rental-procedures | PASS |
| NT-000006 | Cách ghi nhận tình trạng xe trước khi nhận và khi hoàn trả | rental-procedures | PASS |
| NT-000007 | Không nhớ vị trí trả xe: cách thống nhất điểm hẹn và thời gian trước chuyến đi | rental-procedures | PASS |
| NT-000008 | Người nước ngoài cần xác nhận những giấy tờ nào trước khi thuê xe máy ở Việt Nam? | rental-procedures | PASS |
| NT-000009 | So sánh tổng chi phí thuê Honda Wave và Vision trong một tuần | rental-costs | PASS |
| NT-000010 | Giá thuê xe máy theo ngày và tháng: cách tính chi phí thực tế khi thay đổi lịch | rental-costs | PASS |
| NT-000011 | Hỏi giá thuê xe máy điện: cần biết thêm chi phí nào ngoài giá thuê? | rental-costs | PASS |
| NT-000012 | Thuê xe máy khi ở Hà Nội hai tuần: cách so sánh các phương án thuê | rental-costs | PASS |
| NT-000013 | Tư thế lái xe số và xe ga khi di chuyển chặng 30 km: điều cần lưu ý | reviews | PASS |
| NT-000014 | Xe tay ga có cốp rộng: cách ước lượng đồ mang theo trong chuyến đi Hà Nội | reviews | PASS |
| NT-000015 | Chọn xe máy theo chiều cao người lái: lưu ý yên, chân chống và trọng lượng | reviews | PASS |
| NT-000016 | Xe số bán tự động khác xe côn tay ở cách vận hành như thế nào? | reviews | PASS |
| NT-000017 | Xe 50cc chạy trong đường phố đông: cách lên kế hoạch quãng đường hợp lý | rental-50cc | PASS |
| NT-000018 | Xe ga 50cc và xe số 50cc khác nhau ra sao khi leo dốc, chở đồ? | rental-50cc | PASS |
| NT-000019 | Những lỗi dễ gặp khi mới làm quen thao tác xe ga 50cc | rental-50cc | PASS |
| NT-000020 | Hướng dẫn đọc chỉ báo pin trên bảng đồng hồ xe máy điện | electric | PASS |
| NT-000021 | Sạc xe máy điện khi đi công tác: cách tìm điểm sạc phù hợp và lập kế hoạch | electric | PASS |
| NT-000022 | Để xe điện lâu không dùng: các bước bảo quản pin và bộ sạc | electric | PASS |
| NT-000023 | Đường dốc và tải trọng ảnh hưởng quãng đường xe điện thế nào? | electric | PASS |
| NT-000024 | Khi nào cần kiểm tra đầu cắm sạc xe máy điện? | electric | PASS |
| NT-000025 | Kiểm tra thông số bộ sạc theo xe máy điện: những ký hiệu cơ bản | electric | PASS |
| NT-000026 | Xe đạp điện khác xe máy điện ở công suất và cách sử dụng thế nào? | ebikes | PASS |
| NT-000027 | Đi xe đạp điện trong thành phố: cách phân bổ pin cho hành trình nhiều điểm dừng | ebikes | PASS |
| NT-000028 | Cách kiểm tra phanh và lốp xe đạp điện trước giờ đi học | ebikes | PASS |
| NT-000029 | Bảo quản pin xe đạp điện qua mùa mưa ẩm: lưu ý cần biết | ebikes | PASS |
| NT-000030 | Xe đạp điện gấp và xe đạp điện phổ thông: ưu nhược điểm khi mang lên phương tiện khác | ebikes | PASS |
| NT-000031 | Chu kỳ sạc pin lithium xe điện: hiểu đúng và tránh mẹo truyền miệng | battery-charging | PASS |
| NT-000032 | Cách nhận biết pin xe điện có dấu hiệu cần kiểm tra chuyên môn | battery-charging | PASS |
| NT-000033 | Pin xe máy điện sau mùa nóng: khi nào nên nhờ kỹ thuật viên kiểm tra? | battery-charging | PASS |
| NT-000034 | Sạc xe điện tại khu chung cư: những thông tin cần hỏi ban quản lý | battery-charging | PASS |
| NT-000035 | Vệ sinh xe máy điện sau khi đi đường bụi: các bộ phận nên tránh xịt trực tiếp | electric-maintenance | PASS |
| NT-000036 | Vì sao xe điện báo lỗi trên màn hình và khi nào cần dừng sử dụng? | electric-maintenance | PASS |
| NT-000038 | Dùng xe điện hay xe xăng khi có lịch di chuyển đột xuất nhiều điểm? | reviews | PASS |
| NT-000039 | Bảo trì cơ bản xe máy điện và xe máy xăng khác nhau ở công việc nào? | reviews | PASS |
| NT-000040 | Tổng thời gian nạp năng lượng: sạc điện và đổ xăng khác nhau ra sao? | reviews | PASS |
| NT-000041 | Mang giấy tờ nào khi điều khiển xe máy thuê tại Việt Nam? | driving-licence | PASS |
| NT-000042 | Người nước ngoài có bằng lái quốc tế: cách kiểm tra tính phù hợp tại Việt Nam | driving-licence | PASS |
| NT-000043 | Đi xe máy cùng trẻ em: các điều kiện an toàn cần kiểm tra trước khi đi | driving-licence | PASS |
| NT-000044 | Lái xe máy qua nút giao có đèn tín hiệu mũi tên: cách đọc biển báo | driving-licence | PASS |
| NT-000045 | Đường Hà Nội trơn sau cơn mưa đầu mùa: các bước xử lý khi giảm tốc | road-safety | PASS |
| NT-000046 | Chạy xe máy qua tuyến đường có xe buýt dừng đỗ: quan sát điểm mù thế nào? | road-safety | PASS |
| NT-000048 | Đèn báo lỗi động cơ trên xe tay ga: khi nào nên ngừng di chuyển? | engine-care | PASS |
| NT-000049 | Dấu hiệu bugi xe máy cần kiểm tra: phân biệt với lỗi ắc quy | engine-care | PASS |
| NT-000050 | Bảo dưỡng xe máy trước chuyến đi mùa đông miền Bắc: lưu ý thực tế | engine-care | PASS |
| NT-000051 | Vệ sinh lọc gió xe máy: khi nào cần hỏi thợ về việc thay thế? | engine-care | PASS |
| NT-000052 | Giờ cao điểm qua cầu Chương Dương: cách dự trù thời gian hợp lý | urban-mobility | PASS |
| NT-000053 | Đi từ Bồ Đề tới ga Hà Nội bằng xe máy: điểm lưu ý trên hành trình | urban-mobility | PASS |
| NT-000054 | Kết hợp đi bộ và xe máy khi tham quan khu vực Hồ Gươm | urban-mobility | PASS |
| NT-000055 | Kết hợp xe buýt với xe đạp điện: kiểm tra quy định và điểm gửi xe | urban-mobility | PASS |
| NT-000057 | Đi xe buýt từ Long Biên tới khu vực Hồ Tây: cách tìm tuyến và phương án dự phòng | urban-mobility | PASS |
| NT-000059 | Lịch trình khám phá làng gốm Bát Tràng từ Long Biên trong nửa ngày | hanoi-travel | PASS |
| NT-000060 | Dạo quanh các không gian sáng tạo tại Hà Nội trong một buổi chiều | hanoi-travel | PASS |
| NT-000061 | Đi thăm khu vực Thành Cổ Loa trong một buổi sáng: lưu ý di chuyển | hanoi-travel | PASS |
| NT-000062 | Chuẩn bị giấy tờ cho hành trình xe máy liên tỉnh: checklist tối giản | vietnam-travel | PASS |
| NT-000063 | Lập lịch trình xe máy Hà Nội đến Tam Đảo: cách tính điểm nghỉ | vietnam-travel | PASS |
| NT-000064 | Chọn thời điểm đi du lịch vùng núi phía Bắc bằng xe máy theo điều kiện thời tiết | vietnam-travel | PASS |
| NT-000065 | Kiểm tra lộ trình qua đèo khi dự báo sương mù: khi nào nên đổi phương án? | trip-planning | PASS |
| NT-000067 | Khi di chuyển qua đường miền núi có công trình: cách theo dõi cảnh báo giao thông | trip-planning | PASS |
| NT-000068 | Khám phá món ăn quanh chợ Đồng Xuân: cách chọn điểm dừng phù hợp | food-culture | PASS |
| NT-000069 | Ẩm thực buổi sáng khu vực Long Biên: gợi ý các nhóm món địa phương | food-culture | PASS |
| NT-000070 | Những điều nên biết khi tham quan đình làng ở Hà Nội | food-culture | PASS |
| NT-000071 | Ứng xử khi tham quan không gian tín ngưỡng tại Hà Nội | food-culture | PASS |
| NT-000072 | Biển báo tiếng Việt thường gặp với du khách đi xe máy: các nhóm nên nhận diện | urban-mobility | PASS |
| NT-000074 | Du lịch Hà Nội không dùng xe cá nhân: cách kết hợp đi bộ, bus và metro | green-travel | PASS |
| NT-000076 | Bãi gửi xe máy điện có điểm sạc: điều cần xác nhận trước khi gửi | electric-transition | PASS |
| NT-000077 | Trạm sạc công cộng và điểm đổi pin khác nhau thế nào trong trải nghiệm sử dụng? | electric-transition | PASS |
| NT-000078 | Xe máy điện trong đô thị mật độ cao: vấn đề bãi đỗ, sạc và an toàn | electric-transition | PASS |
| NT-000080 | Phân biệt tiêu chuẩn an toàn sản phẩm và quy định sử dụng xe điện trên đường | legal | PASS |

## Cách dùng tiếp (không cần quyết định cho từng seed)

1. Mặc định: giữ nguyên làm kho ý tưởng; researcher dùng làm gợi ý góc, không chép tiêu đề (bộ chống trùng sẽ FAIL).
2. Nếu kho PLANNED vẫn dưới 100 sau vòng nghiên cứu thứ hai: chủ repo có thể duyệt một đường coordinator "hoàn tất seed tại chỗ" (thêm `research` cho đúng ID, chạy Research QA nghiêm ngặt rồi `topic_factory.py`). Chưa làm vì sẽ sửa luồng intake đang chạy và chưa cần thiết.
3. Seed `rental-costs` và một phần `rental-procedures` cần giá/điều khoản thật của cửa hàng (`data/business-facts.json`); không ai được tự đặt giá. Giữ nguyên cho đến khi chủ cửa hàng cung cấp.
