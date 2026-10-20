#!/usr/bin/env python3
"""Deterministic 1482-title editorial queue: no WordPress writes or fabricated QA.

Sources of truth:
- baseline-518.json: an authenticated snapshot of 518 live WP titles.
- data/topics.jsonl: all existing planned/published factory titles.
- data/state/publication-ledger.json: G7 receipts for status reconciliation.

Run --build to create 3 CSV/Excel workbooks, --sync to apply genuine G7
publication receipts. This program never invents evidence or claims QA PASS.
"""
import argparse
import csv
import datetime as dt
import difflib
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'editorial'/'title-plan-1482'
TARGET=1482
SPLIT=494
STATUS_PATH=DIR/'status.json'
MASTER_PATH=DIR/'plan.json'
BASELINE_PATH=DIR/'baseline-518.json'
EXCLUDE_CATEGORY_IDS={1,69,182}
# Exact existing WordPress leaf terms (not the owner's broader topic labels).
GROUPS={
163:('Thủ tục và giao nhận','rental',"""
hợp đồng thuê xe máy|biên bản bàn giao xe|chụp ảnh xe trước khi nhận|đặt cọc thuê xe theo ngày|nhận xe tại khách sạn|nhận xe ở nhà ga|trả xe ngoài giờ hẹn|thuê xe bằng hộ chiếu|thuê xe bằng giấy tờ cá nhân|bàn giao chìa khóa dự phòng|thỏa thuận giao xe tận nơi|gia hạn hợp đồng thuê|đổi mẫu xe khi nhận|lưu giấy tờ khi thuê xe|xác nhận tiền cọc|kiểm tra phanh khi nhận xe|thuê xe cho nhóm bạn|thuê xe khi đổi lịch bay|thỏa thuận địa điểm trả xe|xử lý khi hợp đồng ghi sai
"""),
164:('Chi phí thuê xe','rental',"""
gói thuê xe máy ba ngày|gói thuê xe máy một tuần|giá thuê Honda Wave theo tuần|giá thuê Honda Vision theo ngày|cách tính tiền thuê theo giờ|phụ phí trả xe muộn|phí giao xe đến khách sạn|tiền cọc xe ga và xe số|chi phí thuê xe cho hai người|gói thuê xe trong một tháng|tiền thuê khi đổi lịch trả|thuê xe cuối tuần và ngày thường|phụ phí nhận xe ở ga|so giá gói ngày và gói tuần|chi phí thuê xe đi công tác|chi phí nhiên liệu xe thuê|giảm chi phí thuê xe dài ngày|dự trù tiền thuê và tiền cọc|hóa đơn và chứng từ thuê xe|chi phí khi đổi sang mẫu xe khác
"""),
165:('Sử dụng xe thuê 50cc','rental',"""
xe Cub 50 dùng đi học|xe ga 50cc đi làm quãng ngắn|thuê xe số 50cc lần đầu|tư thế lái xe 50cc|lốp và phanh xe 50cc|đi xe 50cc qua cầu|xe 50cc cho người thấp|chở hành lý bằng xe 50cc|xe 50cc khi trời mưa|kiểm tra đèn xe 50cc|xe 50cc đi trong phố đông|điểm nhận xe 50cc|xe ga 50cc và xe số 50cc|thuê xe 50cc ba ngày|mức tiêu hao nhiên liệu xe 50cc|cách khóa xe 50cc an toàn|xe 50cc khi leo dốc|chỗ để chân trên xe 50cc|xe 50cc cho hành trình ngắn|giấy tờ khi nhận xe 50cc
"""),
166:('Xe đạp điện','electric',"""
xe đạp điện có trợ lực bàn đạp|xe đạp điện dùng ắc quy chì|xe đạp điện dùng pin lithium|xe đạp điện bánh nhỏ|phanh cơ trên xe đạp điện|phanh đĩa xe đạp điện|xe đạp điện chở giỏ hàng|xe đạp điện đi học|xe đạp điện đi chợ|xe đạp điện cho người lớn tuổi|xe đạp điện khi trời mưa|xe đạp điện khi lên dốc|xe đạp điện có bàn đạp|xe đạp điện và xe đạp thường|xe đạp điện cho quãng đường ngắn|xe đạp điện có màn hình số|lốp không săm xe đạp điện|xe đạp điện sau thời gian cất kho|thay pin xe đạp điện|hệ thống đèn xe đạp điện
"""),
167:('Pin và sạc','electric',"""
pin LFP cho xe hai bánh|pin NMC cho xe máy điện|ắc quy chì trên xe điện|bộ sạc xe máy điện|sạc chậm pin lithium|sạc qua đêm xe điện|nhiệt độ pin lúc sạc|dây nguồn bộ sạc xe điện|chu kỳ sạc và độ sâu xả|cảnh báo nhiệt pin xe điện|đầu cắm sạc chống nước|hệ thống quản lý pin BMS|sạc tại nhà chung cư|bảo quản pin khi đi xa|pin tháo rời xe điện|kiểm tra dung lượng pin|đèn báo trạng thái sạc|pin xe điện khi trời lạnh|tự xả pin khi để lâu|đổi bộ sạc khác thông số
"""),
168:('Công nghệ xe điện','electric',"""
động cơ hub trên xe máy điện|động cơ giữa xe điện|bộ điều khiển động cơ xe điện|phanh tái sinh xe điện|cảm biến tốc độ xe điện|màn hình TFT xe máy điện|chế độ lái eco xe điện|chế độ lái sport xe điện|cập nhật phần mềm OTA|khóa thông minh xe điện|chuẩn chống nước IP|hệ thống quản lý pin thông minh|kết nối ứng dụng điện thoại|định vị chống trộm xe điện|truyền động dây curoa xe điện|hệ thống làm mát động cơ|đồng hồ đo quãng đường còn lại|cảm biến tay ga điện tử|mạch bảo vệ khi quá dòng|thu hồi năng lượng lúc giảm tốc
"""),
160:('Chăm sóc xe điện','electric',"""
vệ sinh bánh xe máy điện|làm sạch chân sạc xe điện|bảo dưỡng phanh xe máy điện|kiểm tra lốp xe điện|kiểm tra dây dẫn điện|xe điện đi qua vùng ngập|xe điện sau mùa mưa|xe điện để lâu không chạy|cập nhật ứng dụng xe điện|kiểm tra tiếng ồn động cơ điện|chăm sóc pin xe điện mùa nóng|phát hiện bộ sạc bị nóng|làm khô xe điện đúng cách|bảo quản chìa khóa thông minh|kiểm tra ổ cắm trước khi sạc|xe điện rung khi khởi hành|kiểm tra giảm xóc xe điện|kiểm tra đèn báo lỗi|xe điện có mùi khét|lịch kiểm tra xe điện định kỳ
"""),
169:('Điện hóa và hạ tầng','urban',"""
trạm sạc xe điện trong chung cư|trạm sạc xe điện ở bãi đỗ|đổi pin cho xe máy điện|bãi giữ xe có điểm sạc|quản lý phụ tải khi sạc xe|bảo vệ cháy nổ tại khu sạc|quy hoạch điểm sạc đô thị|bản đồ điểm sạc công cộng|cổng sạc dùng chung|đầu tư trạm sạc nhỏ|sạc xe điện tại cơ quan|trạm đổi pin ở khu dân cư|thói quen sạc giờ thấp điểm|thu gom pin xe điện hết hạn|tái chế pin xe hai bánh|trạm sạc tại điểm du lịch|bảo trì thiết bị sạc công cộng|biển báo khu vực sạc|vận hành trạm sạc khi mưa|khả năng tiếp cận điểm sạc
"""),
170:('Chăm sóc xe máy','mechanic',"""
dầu máy Honda Wave|dầu láp Honda Vision|dây curoa xe tay ga|lọc gió xe máy xăng|bugi xe máy bị bám muội|phanh đĩa xe tay ga|má phanh xe số|lốp xe máy không săm|áp suất lốp khi đi xa|ắc quy xe máy xăng|hệ thống làm mát xe ga|nước làm mát Air Blade|xe máy khó nổ buổi sáng|đèn pha xe máy bị yếu|xe máy rung khi tăng ga|tiếng kêu ở bánh trước|bảo dưỡng cổ phốt|kiểm tra sên xe số|xe ga bị giật khi khởi hành|mùi xăng bất thường trên xe
"""),
161:('An toàn khi di chuyển','safety',"""
đi xe máy qua vòng xuyến|phanh khi đường trơn|tránh điểm mù xe tải|đi xe máy sau cơn mưa|đường phố có vạch kẻ mờ|xe máy qua đường giao nhau|chở balo khi đi xe máy|đi xe máy trong giờ cao điểm|đèn pha khi có sương mù|qua cầu khi gió ngang mạnh|đi xe máy gần xe buýt|xử lý khi nổ lốp|giữ khoảng cách khi xe đông|tránh trượt bánh trên vạch sơn|đi xe máy ban đêm|qua đoạn đường đang sửa|đi xe máy với người ngồi sau|dừng xe khi trời mưa lớn|giảm tốc trước khúc cua|quan sát trước khi mở cửa xe
"""),
171:('Giấy phép và giấy tờ','legal',"""
giấy phép lái xe hạng A1|giấy phép lái xe hạng A|giấy phép lái xe nước ngoài|giấy phép lái xe quốc tế IDP|đổi giấy phép lái xe|cấp lại giấy phép bị mất|thời hạn hiệu lực giấy phép|kiểm tra bằng lái hợp lệ|giấy tờ mang theo khi lái xe|giấy phép và xe máy 50cc|điều kiện tuổi khi lái xe|khác biệt giữa GPLX A và A1|giấy tờ khi thuê xe của khách nước ngoài|quy định biển số xe máy|cách tra cứu văn bản luật|thủ tục điều chỉnh thông tin GPLX|giấy tờ xe máy điện|quy định mũ bảo hiểm|hiệu lực giấy phép nước ngoài|thông tin đăng ký xe trong hợp đồng
"""),
172:('Khám phá Hà Nội','travel',"""
Bảo tàng Hà Nội|Hoàng thành Thăng Long|Văn Miếu Quốc Tử Giám|Hồ Tây và đường ven hồ|Làng cổ Đường Lâm|Bảo tàng Dân tộc học|Bảo tàng Phụ nữ Việt Nam|Chùa Trấn Quốc|Công viên Thống Nhất|Cầu Long Biên|Phố bích họa Phùng Hưng|Nhà hát Lớn Hà Nội|Bảo tàng Lịch sử quốc gia|Bảo tàng Mỹ thuật Việt Nam|Phố sách 19 tháng 12|Không gian hồ Hoàn Kiếm|Làng gốm Bát Tràng|Hồ Đồng Mô|Cổ Loa|Phủ Tây Hồ
"""),
173:('Hành trình Việt Nam','travel',"""
Ninh Bình vào mùa lúa|Mai Châu vào cuối tuần|Cao Bằng mùa thác|Hà Giang đầu mùa đông|Sapa khi có sương|Mộc Châu mùa hoa|Tuyên Quang và hồ Na Hang|Hạ Long ngoài mùa cao điểm|Tam Đảo cuối tuần|Ba Vì và rừng thông|Huế mùa mưa|Hội An lúc sáng sớm|Đà Nẵng trong ba ngày|Quy Nhơn mùa biển êm|Phú Yên cung đường ven biển|Đà Lạt mùa khô|Cần Thơ cuối tuần|Bến Tre đường làng|Nghệ An điểm dừng đường dài|Thanh Hóa từ Hà Nội
"""),
174:('Ẩm thực và văn hóa','travel',"""
phở bò Hà Nội|bún thang Hà Nội|bún chả phố cổ|bánh cuốn Thanh Trì|cà phê trứng Hà Nội|bánh tôm Hồ Tây|bún riêu buổi sáng|xôi xéo Hà Nội|chả cá Hà Nội|cốm làng Vòng|nem rán Hà Nội|bánh đa cua Hải Phòng|bún bò Huế|cao lầu Hội An|mì Quảng ở Đà Nẵng|cơm cháy Ninh Bình|thắng cố Hà Giang|bánh căn Đà Lạt|bánh xèo miền Tây|chợ quê ngày phiên
"""),
175:('Lập kế hoạch chuyến đi','travel',"""
du lịch hai ngày một đêm|lịch trình ba ngày cuối tuần|chuyến đi cho nhóm bốn người|ngân sách du lịch tự túc|kế hoạch đi chơi mùa mưa|lịch trình theo giờ tàu|đặt chỗ nghỉ sát trung tâm|mang hành lý gọn nhẹ|lịch trình có trẻ nhỏ|du lịch khi thời tiết xấu|chuyến đi giữa các tỉnh|đặt xe và đặt phòng cùng lúc|dự trù phí phát sinh|chuyến đi đầu tiên bằng xe máy|ngày đi và ngày về khác nơi|du lịch không có ô tô|đổi lịch vì chuyến bay trễ|đi chơi dịp lễ đông khách|xây dựng bản đồ điểm dừng|lịch trình có người lớn tuổi
"""),
176:('Di chuyển đô thị','urban',"""
đi từ ga Hà Nội đến khách sạn|kết hợp xe buýt và đi bộ|chuyển tuyến đường sắt đô thị|qua cầu Long Biên giờ đông|tìm bãi gửi xe trong phố|đi lại ở khu phố đi bộ|xe máy trên đường một chiều|đi từ sân bay về nội đô|đường vòng khi cấm đường|dừng đỗ tại khu trung tâm|đi lại lúc giờ cao điểm|đường dành riêng cho xe buýt|định vị điểm đón xe công nghệ|kết hợp metro với xe đạp|chọn phương tiện khi trời mưa|giữ an toàn khi chờ đèn đỏ|đường ven hồ đông người|di chuyển với hành lý lớn|tìm đường khi mất mạng|đi lại sau giờ xe buýt
"""),
177:('Du lịch xanh','urban',"""
du lịch bằng xe đạp điện|đi bộ khám phá phố cổ|chọn nơi lưu trú gần metro|lên lịch trình ít di chuyển|đổi xe xăng sang xe điện|mang bình nước khi đi chơi|giảm đồ nhựa dùng một lần|tái sử dụng đồ du lịch|chia sẻ phương tiện theo nhóm|du lịch không cần ô tô|di chuyển ít phát thải|bảo vệ cảnh quan điểm đến|chọn tuyến xe buýt phù hợp|du lịch với hành lý nhẹ|lịch trình kết hợp tàu và xe đạp|giảm rác khi dã ngoại|trạm sạc trong chuyến đi|giữ yên tĩnh khu dân cư|chi phí đi lại bền vững|so sánh phương tiện theo chặng
"""),
156:('Đánh Giá & So Sánh Xe','reviews',"""
Honda Wave Alpha và Blade|Honda Vision và Yamaha Janus|Honda Air Blade và Yamaha NVX|Yamaha Grande và Honda Lead|Honda Future và Yamaha Jupiter|Yamaha Sirius và Honda Wave|Honda Scoopy và Honda Vision|Yamaha FreeGo và Honda Air Blade|xe số và xe tay ga|xe tay ga 50cc và xe số 50cc|động cơ 110cc và 125cc|Honda Cub 50 và SYM 50cc|Honda Winner X và Yamaha Exciter|xe điện và xe xăng đi phố|xe điện và xe đạp điện|cốp xe Vision và cốp xe Lead|phanh ABS và CBS trên xe ga|xe ga bánh lớn và bánh nhỏ|xe số cho người mới|xe ga cho người thấp
""")
}
# 8 distinct intent-specific angle sets. The right-hand phrase must describe an
# answerable research intent rather than a rephrased head keyword.
ANGLES={
'rental':[
('thủ tục','những giấy tờ và bước xác nhận cần chuẩn bị trước khi thuê'),
('giao nhận','cách kiểm tra tình trạng thực tế để tránh tranh cãi khi trả'),
('chi phí','so sánh chi phí theo ngày, theo tuần và khoản cần hỏi rõ'),
('tình huống','các tình huống thường gặp và cách trao đổi với cửa hàng'),
('hợp đồng','điều khoản nào cần đọc kỹ trước khi ký và nhận chìa khóa'),
('an toàn','những kiểm tra an toàn không nên bỏ qua trước khi khởi hành'),
('quy trình','quy trình từng bước giúp người thuê lần đầu đỡ bối rối'),
('kinh nghiệm','khi nào phù hợp và khi nào nên chọn phương án khác'),
('chi phí','cách tính chi phí thực tế khi lịch nhận trả thay đổi'),
('sai lầm','năm hiểu nhầm thường gặp và cách phòng tránh từ đầu'),
('đồ dùng','chuẩn bị vật dụng, điểm hẹn và thông tin liên hệ ra sao'),
('xử lý','nếu lịch trình bị đổi, nên xử lý thế nào cho hợp lý'),
('đối chiếu','những thông tin cần đối chiếu trên hóa đơn và hợp đồng'),
('địa điểm','cách chọn điểm nhận trả thuận tiện nhưng vẫn an toàn'),
('ưu nhược','điểm mạnh, hạn chế và điều cần hỏi khi lựa chọn'),
('bảo quản','cách giữ xe và bàn giao an toàn trong suốt kỳ thuê'),
('checklist','mẫu danh sách kiểm tra trước lúc nhận và trả xe'),
('dự toán','dự toán tiền thuê, nhiên liệu và phần dự phòng ra sao'),
('lựa chọn','nên ưu tiên yếu tố nào nếu chỉ sử dụng vài ngày'),
('hướng dẫn','các bước tự kiểm tra cho người chưa có kinh nghiệm'),
('thực tế','những điều nên hỏi trước khi quyết định đặt xe'),
('so sánh','khi nào thuê theo ngày có lợi hơn gói thuê tuần'),
('an toàn','nhận diện rủi ro thường gặp và cách giảm thiểu'),
('điều kiện','cách hiểu đúng điều kiện sử dụng và tiền đặt cọc')
],
'electric':[
('công nghệ','nguyên lý hoạt động và những thông số cần đọc kỹ'),
('thực tế','điều gì ảnh hưởng đến hiệu quả khi sử dụng hằng ngày'),
('an toàn','những dấu hiệu bất thường cần dừng sử dụng để kiểm tra'),
('so sánh','khác nhau giữa quảng cáo và điều kiện sử dụng thực tế'),
('giới hạn','khi nào phù hợp và trong trường hợp nào nên cân nhắc'),
('chi phí','chi phí bảo trì có thể phát sinh ở những bộ phận nào'),
('kiểm tra','các bước kiểm tra trước khi vận hành cho người mới'),
('thời tiết','sử dụng khi mưa hoặc nắng nóng cần chú ý những gì'),
('thông số','cách đọc thông số do hãng công bố để tránh nhầm lẫn'),
('tuổi thọ','yếu tố khiến tuổi thọ thay đổi theo thói quen sử dụng'),
('bảo dưỡng','lịch kiểm tra và những việc nên giao cho kỹ thuật viên'),
('cảnh báo','các tín hiệu cảnh báo và cách phản ứng an toàn'),
('lựa chọn','những câu hỏi cần đặt ra trước khi chọn thiết bị'),
('giải thích','giải thích thuật ngữ dễ hiểu cho người mới bắt đầu'),
('nguồn tin','cách đối chiếu thông tin hãng và tài liệu kỹ thuật'),
('trường hợp','ba tình huống phổ biến cần kiểm tra trước khi dùng'),
('đi xa','những yếu tố cần tính toán cho hành trình dài hơn'),
('đi phố','hiệu quả sử dụng trong đô thị khác gì đường ngoại ô'),
('vận hành','thói quen nào giúp vận hành ổn định và an toàn hơn'),
('thay thế','khi nào cần thay linh kiện, khi nào chỉ cần kiểm tra'),
('cấu tạo','cấu tạo cơ bản và các giới hạn không nên tự can thiệp'),
('sự cố','cách nhận biết sự cố mà không tự sửa phần điện nguy hiểm')
],
'mechanic':[
('nhận biết','những dấu hiệu cần kiểm tra trước khi xe hư nặng'),
('bảo dưỡng','lịch kiểm tra cơ bản và lưu ý theo hướng dẫn hãng'),
('chi phí','các khoản bảo dưỡng có thể phát sinh và cách dự trù'),
('an toàn','vì sao không nên tiếp tục chạy khi có dấu hiệu lỗi'),
('kiểm tra','những bước kiểm tra đơn giản trước mỗi chuyến đi'),
('cấu tạo','cơ chế hoạt động và lý do bộ phận có thể xuống cấp'),
('thời tiết','mưa ẩm và nắng nóng ảnh hưởng ra sao đến độ bền'),
('thói quen','các thói quen sử dụng khiến bộ phận mau hư hơn'),
('đối chiếu','cách đọc khuyến cáo bảo dưỡng từ nhà sản xuất'),
('sự cố','khi xe hoạt động bất thường cần xử lý thế nào an toàn'),
('đi xa','kiểm tra gì trước khi đi đường dài hoặc lên dốc'),
('đi phố','vận hành trong phố đông làm bộ phận chịu tải ra sao'),
('lựa chọn','những tiêu chí cần cân nhắc khi thay thế linh kiện'),
('sai lầm','những sai lầm tự sửa xe tại nhà cần tránh'),
('triệu chứng','phân biệt dấu hiệu bình thường và dấu hiệu cần sửa'),
('thực hành','hướng dẫn quan sát và ghi nhận lỗi để báo thợ'),
('chu kỳ','các yếu tố khiến chu kỳ thay thế ngắn hoặc dài'),
('hướng dẫn','người mới nên mô tả hiện tượng cho thợ như thế nào')
],
'safety':[
('đường phố','cách quan sát tình huống và chọn vị trí an toàn'),
('người mới','hướng dẫn nhận biết rủi ro cho người mới lái xe'),
('thực hành','các bước giảm tốc và xử lý tình huống an toàn'),
('tầm nhìn','làm sao giữ tầm nhìn và khoảng cách phù hợp'),
('thời tiết','trời mưa và đường trơn cần thay đổi cách lái thế nào'),
('quy tắc','những nguyên tắc quan trọng cần nhớ khi tham gia đường'),
('đi phố','tình huống thường gặp trong phố đông và cách tránh'),
('đi xa','lưu ý cho người đi xa hoặc lái xe ở nơi lạ'),
('giải thích','vì sao một thao tác nhỏ có thể dẫn đến rủi ro'),
('dấu hiệu','nhận ra tín hiệu nguy hiểm trước khi quá muộn'),
('checklist','danh sách chuẩn bị trước khi lên đường cho người mới'),
('quan sát','điểm cần quan sát để không bất ngờ ở giao lộ'),
('kỹ năng','kỹ năng cơ bản nên luyện ở nơi an toàn trước'),
('sai lầm','những thói quen sai dễ mắc phải và cách sửa'),
('xe thuê','lưu ý thêm khi lần đầu điều khiển một chiếc xe lạ'),
('tự kiểm tra','những câu hỏi tự kiểm tra trước khi tiếp tục đi')
],
'legal':[
('quy định','đọc quy định hiện hành và các trường hợp áp dụng'),
('giấy tờ','cần giấy tờ nào và tra cứu hướng dẫn ở nguồn chính thức'),
('phạm vi','trường hợp nào được áp dụng, trường hợp nào không'),
('cập nhật','cách kiểm tra hiệu lực văn bản trước khi làm thủ tục'),
('điều kiện','điều kiện cần xác nhận theo văn bản pháp luật mới nhất'),
('phân biệt','cách phân biệt với loại giấy phép hoặc thủ tục khác'),
('thủ tục','trình tự thực hiện và cơ quan giải quyết theo quy định'),
('người mới','những hiểu nhầm phổ biến người lái nên tránh'),
('tra cứu','các bước tra cứu thông tin trên cổng cơ quan nhà nước'),
('tình huống','xử lý trường hợp giấy tờ không khớp thông tin ra sao'),
('quốc tế','điều cần kiểm tra nếu là du khách nước ngoài'),
('xe điện','phân biệt yêu cầu giữa xe điện và xe động cơ xăng'),
('thời hạn','khi nào cần gia hạn hoặc làm thủ tục điều chỉnh'),
('an toàn','điều kiện tham gia giao thông cần hiểu cho đúng'),
('bằng chứng','lưu chứng từ và kết quả giải quyết như thế nào'),
('câu hỏi','giải đáp câu hỏi thường gặp dựa trên nguồn nhà nước')
],
'travel':[
('lịch trình','lịch trình trong ngày và cách phân bổ thời gian'),
('di chuyển','nên đi bộ, đi xe máy hay kết hợp phương tiện'),
('ngân sách','dự trù chi phí đi lại, ăn uống và nghỉ ngơi'),
('thời tiết','thời điểm tham quan và phương án dự phòng khi mưa'),
('trải nghiệm','những trải nghiệm phù hợp với người đi lần đầu'),
('người mới','gợi ý đi lại và chuẩn bị cho du khách tự túc'),
('địa điểm','cách chọn điểm dừng hợp lý để không quá vội'),
('văn hóa','điều nên tìm hiểu trước để tôn trọng văn hóa địa phương'),
('thời gian','đi buổi sáng hay buổi chiều hợp lý hơn'),
('đường đi','lưu ý tìm đường và bố trí điểm nghỉ an toàn'),
('gia đình','cách điều chỉnh lịch trình khi có trẻ nhỏ đi cùng'),
('đi nhóm','phân công lịch trình và quản lý ngân sách trong nhóm'),
('khám phá','gợi ý khám phá có chọn lọc thay vì chạy theo check-in'),
('thực tế','những lỗi lên kế hoạch thường gặp và cách tránh'),
('phù hợp','khi nào nên chọn chuyến ngắn thay vì đi dài'),
('an toàn','những lưu ý an toàn cơ bản trong suốt chuyến đi'),
('đặc trưng','nét đặc trưng nên biết và các lưu ý khi ghé thăm'),
('ăn uống','cách bố trí điểm ăn nghỉ thuận đường và hợp túi tiền'),
('kinh nghiệm','mẹo dành cho khách lần đầu tự tổ chức chuyến đi'),
('phương tiện','cách lựa chọn phương tiện theo từng chặng đường')
],
'urban':[
('phương tiện','chọn phương tiện nào theo quãng đường và giờ đi'),
('chi phí','so sánh chi phí đi lại và những khoản hay bị bỏ sót'),
('điểm dừng','chọn điểm dừng đỗ hợp lệ và thuận tiện ra sao'),
('tuyến đường','cách lên tuyến đường để bớt vòng và tiết kiệm'),
('giờ cao điểm','những lựa chọn giúp hạn chế kẹt xe và chờ đợi'),
('an toàn','các rủi ro khi di chuyển và cách chuẩn bị từ trước'),
('quy hoạch','những điều cần tìm hiểu từ nguồn thông tin chính thức'),
('đô thị','tác động đến người đi lại hằng ngày có thể là gì'),
('trải nghiệm','trải nghiệm thực tế cần cân nhắc khi lựa chọn'),
('môi trường','cách đánh giá lợi ích môi trường mà không phóng đại'),
('người mới','hướng dẫn cơ bản cho người lần đầu sử dụng'),
('kết nối','kết hợp các chặng đi sao cho ít phải chuyển tuyến'),
('thời tiết','khi mưa lớn cần dự phòng và thay đổi tuyến thế nào'),
('tiện ích','những tiện ích đáng hỏi trước khi sử dụng dịch vụ'),
('giới hạn','những giới hạn hạ tầng không nên bỏ qua'),
('chiến lược','cách lựa chọn phù hợp thay vì chạy theo xu hướng'),
('so sánh','ưu nhược điểm so với phương án đi lại phổ biến'),
('thủ tục','các quy tắc và chỉ dẫn cần kiểm tra ở nơi công cộng')
],
'reviews':[
('so sánh','khác nhau ở thói quen lái và nhu cầu đi lại'),
('tư thế','so chiều cao yên, chống chân và cảm giác điều khiển'),
('chi phí','nên so chi phí sử dụng theo những tiêu chí nào'),
('thực tế','khi đi phố đông mẫu nào có thể thuận tiện hơn'),
('an toàn','điểm cần kiểm tra ở phanh, lốp và đèn xe'),
('động cơ','cách đọc thông số động cơ do hãng công bố'),
('hành lý','so khả năng mang đồ và tiện ích sử dụng'),
('đường dài','đi xa cần cân nhắc những trang bị nào'),
('đi làm','phù hợp hơn với người đi làm quãng ngắn'),
('người mới','những điểm nên thử khi mới tập làm quen'),
('lựa chọn','khi nào nên chọn bên này, khi nào chọn bên kia'),
('bảo dưỡng','so yêu cầu chăm sóc định kỳ và chi phí phát sinh'),
('thời tiết','khác biệt khi sử dụng dưới mưa hoặc trời nóng'),
('tiện ích','những trang bị tiện dụng đáng so trước khi chọn'),
('độ bền','đọc thông tin độ bền ra sao để tránh ngộ nhận'),
('thực dụng','so sánh từ tình huống hằng ngày thay vì quảng cáo'),
('đánh giá','các tiêu chí cần tự kiểm tra trên xe thực tế')
]
}
EXTEND={
'rental':["khi dùng xe tại đô thị","đối với khách thuê lần đầu","trong chuyến đi tự túc"],
'electric':["trong quá trình sử dụng thực tế","với người sử dụng lần đầu","khi đi lại trong thành phố"],
'mechanic':["trong quá trình dùng xe hằng ngày","khi đi lại nhiều trong phố","với người mới sử dụng"],
'safety':["trong điều kiện giao thông đô thị","cho người lần đầu đi xe thuê","khi di chuyển trên đường lạ"],
'legal':["khi tham gia giao thông tại Việt Nam","với người điều khiển xe hai bánh","khi cần đối chiếu giấy tờ"],
'travel':["khi tự túc khám phá Việt Nam","dành cho du khách lần đầu","đối với nhóm bạn nhỏ"],
'urban':["khi di chuyển trong đô thị","cho người lần đầu sử dụng","vào các ngày đông người"],
'reviews':["khi cân nhắc chọn xe đi lại","với người mới làm quen xe","trong điều kiện đường phố"]
}
HEADERS=['Mã kế hoạch','Tiêu đề bài viết','Số ký tự','Ý định','Danh mục WordPress','Term ID','Danh mục cha','Taxonomy key','Chủ đề chính','Truy vấn nghiên cứu','Nguồn tối thiểu','Nguồn tối đa','Trạng thái','Topic ID','WP Post ID','URL đã đăng','G7','Cập nhật']
CATALOG={
163:('rental-procedures',162),164:('rental-costs',162),165:('rental-50cc',162),
166:('ebikes',157),167:('battery-charging',157),168:('electric-tech',157),
160:('electric-maintenance',157),169:('electric-transition',157),170:('engine-care',158),
161:('road-safety',159),171:('driving-licence',159),172:('hanoi-travel',126),
173:('vietnam-travel',126),174:('food-culture',126),175:('trip-planning',127),
176:('urban-mobility',127),177:('green-travel',127),156:('reviews',69)
}

def norm(s):
    s=html.unescape(str(s)).replace('đ','d').replace('Đ','D')
    s=''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')
    return ' '.join(re.findall(r'[a-z0-9]+',s))

def overlap(a,b):
    aa=set(a.split());bb=set(b.split())
    return len(aa&bb)/len(aa|bb) if aa and bb else 0

def existing_titles():
    baseline=json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    if baseline.get('total')!=518 or len(baseline.get('posts',[]))!=518:
        raise ValueError('Expected exactly 518 authenticated baseline posts')
    old=[norm(x.get('title','')) for x in baseline['posts']]
    other=ROOT/'data/topics.jsonl'
    if other.is_file():
        for line in other.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            try:
                t=json.loads(line)
                if t.get('title'):old.append(norm(t['title']))
            except json.JSONDecodeError:raise ValueError('Malformed registered topic')
    return sorted(set(old)),baseline

def make_title(subject,angle,group):
    candidate=f'{subject[0].upper()+subject[1:]}: {angle}'
    candidate=unicodedata.normalize('NFC',candidate)
    if len(candidate)<60:
        for tail in EXTEND[group]:
            option=candidate.rstrip('?.! ')+' '+tail
            if 60<=len(option)<=80:
                return option+'?' if candidate.endswith('?') else option
    return candidate

def candidate_rows():
    old,baseline=existing_titles()
    old_sets=[set(x.split()) for x in old]
    proposed=[]
    for term,(name,group,multiline) in GROUPS.items():
        subjects=[x.strip() for x in multiline.split('|') if x.strip()]
        chosen=[];taken=set()
        for ix in range(len(ANGLES[group])):
            for offset in range(len(subjects)):
                # Interleave subjects and angles to avoid 80 nearly adjacent
                # variations of the same head phrase.
                sj=(offset+ix*7)%len(subjects)
                subject=subjects[sj]
                intent,angle=ANGLES[group][ix]
                title=make_title(subject,angle,group)
                key=norm(title)
                if not 60<=len(title)<=80:continue
                if 'thue xe may ha noi' in key:continue
                if key in taken or key in old:continue
                tokens=set(key.split())
                # Fail closed for exact and high-overlap published/planned angles.
                if any(len(tokens&v)/len(tokens|v)>.78 for v in old_sets if v):continue
                if any(overlap(key,norm(p['title']))>.78 for p in chosen):continue
                taken.add(key)
                chosen.append({'category_id':term,'category_name':name,'parent':CATALOG[term][1],
                    'taxonomy_key':CATALOG[term][0],'title':title,'intent':intent,
                    'subject':subject})
                if len(chosen)>=83:break
            if len(chosen)>=83:break
        proposed.append(chosen)
    # Target 82 per leaf, plus 6 leaves with 83 = 1482 total.
    if len(GROUPS)!=18:raise ValueError('Exactly 18 existing leaf categories expected')
    needed={t:82+(1 if i<6 else 0) for i,t in enumerate(GROUPS)}
    for block in proposed:
        if len(block)<needed[block[0]['category_id']] if block else True:
            term=block[0]['category_id'] if block else 'missing'
            raise ValueError(f'Insufficient high-quality 60-80-char titles for category {term}: {len(block)}')
    byterm={block[0]['category_id']:block[:needed[block[0]['category_id']]] for block in proposed}
    ordered=[]
    for i in range(83):
        for term in GROUPS:
            if i<len(byterm[term]):ordered.append(byterm[term][i])
    if len(ordered)!=TARGET:raise ValueError(f'Generated {len(ordered)} instead of {TARGET}')
    for i,row in enumerate(ordered,1):
        row['plan_id']='TP-%04d'%i
        row['research_query']=row['title'].replace(':',' ').rstrip('?')
        row['sources_min']=1
        row['sources_max']=4
        row['status']='PLANNED'
    keys=[norm(x['title']) for x in ordered]
    if len(set(keys))!=TARGET:raise ValueError('Cross-category title collision')
    return ordered,baseline

def stable_rows():
    path=MASTER_PATH
    if path.exists():
        rows=json.loads(path.read_text(encoding='utf-8'))['rows']
        if len(rows)!=TARGET:raise ValueError('Invalid committed plan count')
        return rows
    rows,baseline=candidate_rows()
    return rows

def save_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def workbook_export(path,rows,part,total_counts):
    from artifact_tool import Workbook, SpreadsheetFile
    wb=Workbook.create()
    sheet=wb.worksheets.add('Tieu de')
    sheet.get_range('A1:R1').values=[HEADERS]
    values=[]
    for row in rows:
        values.append([row['plan_id'],row['title'],len(row['title']),row['intent'],
                       row['category_name'],row['category_id'],row['parent'],
                       row['taxonomy_key'],row['subject'],row['research_query'],
                       row['sources_min'],row['sources_max'],row['status'],
                       row.get('topic_id',''),row.get('wp_post_id',''),
                       row.get('wp_url',''),row.get('g7_status',''),
                       row.get('updated_at','')])
    sheet.get_range(f'A2:R{len(rows)+1}').values=values
    sheet.get_range('A1:R1').format={
        'fill':'#164E63','font':{'bold':True,'color':'#FFFFFF'},
        'row_height':32,'vertical_alignment':'center'
    }
    sheet.freeze_panes.freeze_rows(1)
    for col,width in {'A':13,'B':57,'C':12,'D':18,'E':29,'F':11,
                      'G':12,'H':25,'I':35,'J':54,'K':12,'L':12,'M':23,
                      'N':16,'O':14,'P':48,'Q':18,'R':22}.items():
        sheet.get_range(f'{col}:{col}').format.column_width=width
    sheet.get_range(f'A2:R{len(rows)+1}').format.row_height=23
    sheet.get_range(f'A2:R{len(rows)+1}').format.vertical_alignment='center'
    sheet.get_range(f'B2:B{len(rows)+1}').format.wrap_text=True
    sheet.get_range(f'M2:M{len(rows)+1}').data_validation={
        'rule':{'type':'list','values':['PLANNED','RESEARCHING','WRITER_QA','QA_REVIEW','PUBLISHED_G7_PASS','EXTERNAL_REVIEW']}
    }
    summary=wb.worksheets.add('Tong quan')
    summary.get_range('A1:B7').values=[
        ['LÔ TIÊU ĐỀ SEO '+str(part), 'GIÁ TRỊ'],
        ['Số tiêu đề trong lô',len(rows)],
        ['Số danh mục hiện hữu',len(set(x['category_id'] for x in rows))],
        ['Đã xuất bản G7',sum(x['status']=='PUBLISHED_G7_PASS' for x in rows)],
        ['Chưa xử lý',sum(x['status']=='PLANNED' for x in rows)],
        ['Tổng kế hoạch ba lô',TARGET],
        ['Đã có bài WordPress gốc (snapshot)',518],
    ]
    summary.get_range('A1:B1').format={'fill':'#164E63','font':{'bold':True,'color':'#FFFFFF'},'row_height':28}
    summary.get_range('A:A').format.column_width=46
    summary.get_range('B:B').format.column_width=22
    instructions=wb.worksheets.add('Huong dan')
    rules=[
      ['Nguyên tắc','Chi tiết'],
      ['Nguồn sự thật','plan.json + status.json; Excel/CSV là bản xuất để xem.'],
      ['Phạm vi','18 danh mục có thật, đúng Term ID, không tạo danh mục mới.'],
      ['SEO chính','Không sinh thêm tiêu đề chứa cụm Thuê xe máy Hà Nội.'],
      ['Phường Hà Nội','Giữ độc lập 51 phường ở chiến dịch riêng (Term 182).'],
      ['Nghiên cứu','Đọc 1–4 nguồn phù hợp; các nhận định pháp lý phải có nguồn chính thức.'],
      ['Tình trạng','Chỉ đánh dấu PUBLISHED_G7_PASS khi có ledger G7 đủ kiểm chứng.'],
      ['Publisher','Không bỏ QA ≥85, không tạo nháp, không đổi policy hoặc Writer leases.'],
      ['Bảo vệ bài cũ','Kiểm tra slug/intent với 518 bài và registry mới nhất trước khi viết.'],
      ['Thời gian','Snapshot danh sách bài gốc: 2026-10-20.'],
    ]
    instructions.get_range(f'A1:B{len(rules)}').values=rules
    instructions.get_range('A1:B1').format={'fill':'#164E63','font':{'bold':True,'color':'#FFFFFF'}}
    instructions.get_range('A:A').format.column_width=27
    instructions.get_range('B:B').format.column_width=90
    SpreadsheetFile.export_xlsx(wb).save(str(path))

def outputs(rows,write_xlsx=True):
    DIR.mkdir(parents=True,exist_ok=True)
    for part in range(3):
        chunk=rows[part*SPLIT:(part+1)*SPLIT]
        if len(chunk)!=SPLIT:raise ValueError('Wrong workbook size')
        name=f'seo-tieu-de-{part+1:02d}-494'
        with (DIR/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as fh:
            writer=csv.writer(fh)
            writer.writerow(HEADERS)
            for x in chunk:
                writer.writerow([x['plan_id'],x['title'],len(x['title']),x['intent'],
                    x['category_name'],x['category_id'],x['parent'],x['taxonomy_key'],
                    x['subject'],x['research_query'],x['sources_min'],x['sources_max'],
                    x['status'],x.get('topic_id',''),x.get('wp_post_id',''),
                    x.get('wp_url',''),x.get('g7_status',''),x.get('updated_at','')])
        if write_xlsx:workbook_export(DIR/(name+'.xlsx'),chunk,part+1,Counter(x['status'] for x in rows))

def reconcile(rows):
    ledger=json.loads((ROOT/'data/state/publication-ledger.json').read_text(encoding='utf-8'))
    topics={}
    for line in (ROOT/'data/topics.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            t=json.loads(line)
            topics[t.get('title_plan_id')]=t
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    changed=0
    for x in rows:
        topic=topics.get(x['plan_id'])
        if not topic:continue
        if topic.get('taxonomy_key')!=x['taxonomy_key'] or topic.get('wordpress_category_id')!=x['category_id']:
            raise ValueError('Wrong title-plan category: '+x['plan_id'])
        record=ledger.get('posts',{}).get(topic['topic_id']) or {}
        if record.get('phase')!='VERIFIED':continue
        g7=record.get('g7') or {}
        required=('wordpress_status','slug','title','category','ownership_marker','content',
                  'permalink','public_page','indexable','seo_meta')
        if not (g7.get('status')=='PASS' and all(g7.get('checks',{}).get(v) is True for v in required)
                and g7.get('categories')==[x['category_id']]
                and record.get('status')=='publish' and record.get('category_id')==x['category_id']
                and record.get('url')==topic.get('canonical_target')):
            continue
        if x['status']=='PUBLISHED_G7_PASS':continue
        x.update(status='PUBLISHED_G7_PASS',topic_id=topic['topic_id'],
                 wp_post_id=record.get('wp_id'),wp_url=record['url'],
                 g7_status='PASS',updated_at=now)
        changed+=1
    return changed

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--build',action='store_true')
    p.add_argument('--sync',action='store_true')
    p.add_argument('--no-xlsx',action='store_true')
    args=p.parse_args()
    if args.build and MASTER_PATH.exists():
        raise ValueError('Refuse to overwrite an existing planned queue')
    if args.build:
        rows,baseline=candidate_rows()
        save_json(MASTER_PATH,{'schema_version':1,'snapshot_count':518,
            'total':TARGET,'category_count':len(GROUPS),'rows':rows})
        save_json(STATUS_PATH,{'schema_version':1,'total':TARGET,
            'status':{r['plan_id']:{'status':'PLANNED'} for r in rows}})
        outputs(rows,not args.no_xlsx)
        print(json.dumps({'generated':len(rows),'files':3,
                          'categories':len(GROUPS),'range':'60-80'}))
        return
    data=json.loads(MASTER_PATH.read_text(encoding='utf-8'))
    rows=data['rows']
    if len(rows)!=TARGET:raise ValueError('Invalid plan')
    changed=reconcile(rows) if args.sync else 0
    if changed:
        save_json(MASTER_PATH,data)
        save_json(STATUS_PATH,{'schema_version':1,'total':TARGET,
            'status':{r['plan_id']:{'status':r['status'],'topic_id':r.get('topic_id'),
              'wp_post_id':r.get('wp_post_id'),'wp_url':r.get('wp_url')} for r in rows}})
        outputs(rows,not args.no_xlsx)
    print(json.dumps({'changed':changed,'total':len(rows),
         'published':sum(r['status']=='PUBLISHED_G7_PASS' for r in rows)}))

if __name__=='__main__':
    main()
