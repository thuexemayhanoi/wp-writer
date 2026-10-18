# Hệ thống tự bổ sung chủ đề (self-replenishing topics)

Nghiên cứu và Writer theo [quy trình chung W1–W9](WRITER-RESEARCH-CONTRACT.md): một nguồn gốc đủ bằng chứng có thể đủ cho chủ đề hẹp, thêm đối chiếu khi cần; không API AI, không thêm khóa hoặc bước duyệt tay. QA giữ nguyên.

Lệnh chủ MASTER WORK 1.000 chủ đề (2026-10-17): kho phải được lấp tới trần đã duyệt `approved_capacity` = 1.000 dòng. Khi **PLANNED sẵn sàng viết** còn **dưới 900**, hệ thống mở một đợt nghiên cứu **100–200 chủ đề mới** và mở tiếp đợt sau cho tới khi hết trần (`CAPACITY_BLOCKED`; chỉ chủ repo được nâng trần). Luôn áp dụng: kiểm tra trùng search intent với **toàn bộ bài đã đăng và chủ đề đang xử lý**; **chỉ chủ đề đạt Research QA mới vào PLANNED**; **không giới hạn số đợt**; không tạo nội dung trùng lặp; không sửa URL cũ. (Lịch sử: các bản dán của lệnh từng ghi "dưới 50 / 200–300", "dưới 30 / 100–200" và "dưới 100 / 100–200" (kho dự phòng); lệnh MASTER WORK 1.000 thay thế chúng; muốn đổi chỉ sửa `config/refill-policy.json`.)

## Vòng lặp

```text
ready PLANNED < 900 ──► scripts/refill_controller.py mở đơn RF-n (100–200 chủ đề)
        ▲                       │  reports/refill-request.json  (quota theo danh mục, batch kế tiếp)
        │                       ▼
        │        AI nghiên cứu ngoài: 10 chủ đề/batch, nguồn thật theo quy định chung
        │                       │  python scripts/research_v2.py plan | intent-check | checkpoint | push
        │                       ▼
        │        Research QA (read-only) ──► Trusted Intake trên main ──► CHỈ dòng PASS → PLANNED
        │                       │
        └── đơn đóng khi ≥100 chủ đề được nhận ◄─┘     (mở đơn mới ngay khi stock lại < 900, không giới hạn số đợt, dừng ở trần 1.000)
```

GitHub Actions **không chạy AI**: bộ điều khiển chỉ **quyết định và ghi lại**; việc nghiên cứu do phiên AI ngoài thực hiện (xem "Tự động hóa người nghiên cứu").

## Thành phần

| Thành phần | Vai trò |
|---|---|
| `config/refill-policy.json` | Nguồn số duy nhất: `trigger_below_ready=100`, `round_target_min/max=100/200`, `research_batch_size=10`, `max_rounds=null` (không giới hạn), ngưỡng intent guard |
| `scripts/refill_policy.py` | Đọc/kiểm tra policy; chuyển ngưỡng cho stock ladder, watchdog, dashboard, discovery |
| `scripts/refill_controller.py` + `.github/workflows/topic-refill-controller.yml` | Mỗi giờ, sau mỗi lần intake và khi đổi policy: mở/theo dõi/đóng đơn. Chỉ ghi `data/state/refill-orders.json` và `reports/refill-request.json` bằng CAS; không AI, không WordPress, không secret |
| `scripts/intent_guard.py` | Kiểm tra trùng search intent với toàn bộ kho (xem dưới) |
| `scripts/topic_factory.py`, `research_v2.py`, `research_intake.py` | Research QA dùng intent guard; intake truyền verdict nghiêm ngặt |
| `python scripts/research_v2.py plan` | Đơn đang mở, quota từng danh mục, 10 chủ đề kế tiếp nên rơi vào danh mục nào |
| `python scripts/research_v2.py intent-check --file …` | Soát trùng intent trước khi push (không cần nguồn); xét cả hàng chờ của các nhánh `research/*` khác chưa được tiếp nhận (`--no-peers` để tắt khi offline). Bài nhà máy đăng sau mốc snapshot nghiên cứu không bị tính là REVIEW (FAIL thì không bao giờ được miễn) |

**Ready stock** = chủ đề PLANNED mà writer còn nhận được: chưa claim, chưa có bản nháp/receipt, chưa đăng, không bị `hold`. Lịch sử PLANNED không được cộng vào.

## Vòng đời đơn (`reports/refill-request.json`)

| `state` | Ý nghĩa |
|---|---|
| `HEALTHY` | ready ≥ 100 và không có đơn mở |
| `REFILL_OPENED` | vừa mở đơn mới; cần 100–200 chủ đề đạt Research QA |
| `REFILL_IN_PROGRESS` | đơn đang chạy; `accepted_so_far`, `remaining_to_min`, `stalled` (im lặng quá `stalled_after_hours`) |
| `REFILL_FULFILLED` | đủ `target_min` chủ đề được nhận; đơn đóng |
| `CAPACITY_BLOCKED` | còn < 10 chỗ trong `approved_capacity` (xem "Giới hạn thật") |
| `ROUND_LIMIT_REACHED` | chỉ khi chủ đặt `max_rounds` số nguyên |
| `DISABLED` | `enabled=false` |

Tiến độ đếm từ `data/state/research-intake-ledger.json` (chỉ chủ đề intake đã chuyển thành PLANNED sau thời điểm mở đơn). File request **không chứa mốc thời gian** nên giờ rảnh không tạo commit.

## Intent guard — kiểm tra trùng search intent toàn bộ

Mỗi ứng viên được so với **mọi** mục WordPress (bài, trang, sản phẩm) và **mọi** chủ đề đang nằm trong nhà máy (PLANNED, RESEARCH, đã claim, đã viết, đã đăng; trừ REJECTED), và với các dòng mới khác trong cùng lượt nghiên cứu.

- Từ được tách có nhận dấu (giá ≠ gia hạn), bỏ từ đệm và khung câu hỏi ("như thế nào", "bao lâu"), tính trọng số IDF: thực thể hiếm (tên xe, địa danh, số hiệu văn bản) nặng hơn "xe máy Hà Nội".
- Mỗi tiêu đề / SEO title / từ khóa chính được so riêng, và mệnh đề đầu của tiêu đề dạng "Câu hỏi: phụ đề", nên phụ đề dài của bài cũ không che được việc tiêu đề đã trả lời đúng câu hỏi.
- **FAIL** (không thể miễn): cùng từ ngữ sau khi bỏ từ đệm, hoặc cùng loại câu hỏi (giá, cách làm, pháp lý, thời điểm…) với từ ngữ gần như bao trùm. Cần đổi tiêu đề/đổi phạm vi.
- **REVIEW**: trùng đáng kể nhưng khác thực thể hoặc khác loại câu hỏi. Chỉ được giải quyết bằng `research.resolved_intent_collisions = {"WP2521": "lý do ≥40 ký tự"}`; với trang WordPress còn phải có hash nội dung hiện tại trong `research.reviewed_content_hashes`. Khi nhiều dòng mới trùng nhau, **ID nhỏ nhất giữ intent**, dòng sau bị đánh dấu.
- Hiệu chỉnh trên 160 tiêu đề thật: 80% không vướng, 16% REVIEW, 3% FAIL (đều là các trang thuê xe thương mại chồng lấn sẵn có). Fixture đóng băng trong `tests/fixtures/intent_corpus.json`.

Đây là **màn lọc máy**, không phải bằng chứng ngữ nghĩa: lý do miễn REVIEW do người nghiên cứu tự khai, và bằng chứng đọc toàn văn 5 bài gần nhất của `topic_factory.gate` vẫn áp dụng. Guard chạy khi nhận chủ đề; QA bài viết vẫn giữ kiểm tra G4 theo nội dung.

## Chỉ Research QA PASS mới thành PLANNED

Trước đây `topic_factory.run()` chỉ dùng cổng danh tính (`gate`): dòng thiếu nguồn, sai khoảng số từ hoặc sai `topic_role` vẫn thành PLANNED nếu cùng batch có một dòng PASS. Nay `research_intake` và `refill.py` truyền verdict của `validate_candidates` vào `run(..., verdicts)`; dòng không PASS (hoặc thiếu verdict) chỉ có thể là `RESEARCH`/`REJECTED`. `topic-factory.py --import-candidates` cũng tự tính verdict nên không còn đường tắt.

## Giới hạn thật (không che giấu)

1. **Không có AI trong Actions** (lệnh chủ có trước): bộ điều khiển không tự "nghiên cứu". Để vòng lặp chạy không cần người, cần một phiên AI định kỳ — xem mục dưới.
2. **Số đợt không giới hạn**, nhưng tổng số chủ đề được nhận bị chặn bởi `approved_capacity` (hiện 1.000, trần cứng 10.000) trong `config/production-policy.json` — quyết định của chủ, không bị file này thay đổi. Hết chỗ → `CAPACITY_BLOCKED` kèm hướng dẫn; đơn cuối được thu nhỏ vừa phần còn lại.
3. Chủ đề bị `REJECTED` vẫn chiếm một dòng registry (hành vi cũ), nên nghiên cứu kỹ trước khi push để không đốt chỗ.
4. `min_claimable_queue` / `refill_target` trong `production-policy.json` là giá trị cũ, **đã bị `config/refill-policy.json` thay thế** ở mọi nơi dùng.
5. Nguồn bài viết phải đọc được từ runner GitHub (Publisher đọc lại nguồn trực tiếp); xem `source-reachability.yml` trước khi chọn nguồn.

## Tự động hóa người nghiên cứu

Hai cách hợp lệ (không API key trong Actions):

- **Phiên AI thủ công / định kỳ**: Claude Code Routine (cron) hoặc bất kỳ AI có quyền GitHub. Prompt chuẩn:

> Đọc AGENTS.md, docs/SELF-REPLENISHING-TOPICS.md và docs/WRITER-RESEARCH-CONTRACT.md. Chạy `python scripts/research_v2.py plan`. Nếu `state` không phải `REFILL_OPENED` hoặc `REFILL_IN_PROGRESS`, báo "không có đơn nghiên cứu"; Writer vẫn có thể viết PLANNED hợp lệ. Nếu có đơn: tạo hoặc `resume --apply` nhánh `research/<session ổn định>`; mỗi batch 10 chủ đề theo `next_batch_categories`, đọc nguồn thật theo quy định chung (một nguồn gốc đủ cho phạm vi hẹp, thêm đối chiếu khi cần), đối chiếu bài cũ, chạy `intent-check`, `checkpoint`, `check`, `push`. Sau Research QA/Trusted Intake, chạy lại `plan`, tiếp tục trong đơn hiện tại hoặc đơn kế tiếp đã mở, tới giới hạn chủ giao/trần kho hoặc hết hạn mức phiên; lưu session/checkpoint. Không bịa nguồn/hash; không sửa script, workflow, config, URL cũ.

- Nhiều phiên song song được phép: intake chạy tuần tự dưới `wp-writer-state`, dòng trùng của phiên đến sau bị guard chặn.

## Kiểm tra thủ công

```bash
python scripts/refill_controller.py                    # dry-run: quyết định hiện tại
python scripts/research_v2.py plan                     # đơn, quota, batch kế
python scripts/research_v2.py intent-check --file data/candidates/<session>-0001.jsonl
python -m unittest tests.test_intent_guard tests.test_refill_controller tests.test_strict_research_intake
```

Chạy thật chỉ ở workflow `Self-replenishing topic controller` trên `main` (`--apply` bị từ chối ở nơi khác). Không thao tác nào ở đây chạm WordPress, URL, canonical, danh mục, flag Production hay bài đã đăng.
