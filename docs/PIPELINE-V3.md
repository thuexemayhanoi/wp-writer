**CẬP NHẬT 20/10/2026 — ƯU TIÊN QUY ĐỊNH NÀY:** Chủ duyệt **SEO ≥76/100, Quality ≥76/100**, giữ đủ G1–G7. G3 chỉ kiểm nguồn URL HTTPS an toàn/nguồn chính thức khi nói luật; nội dung trích dẫn thay đổi hoặc link cũ/khó mở sẽ ghi **cảnh báo audit sau**, không tự giữ bài. Trạng thái `source_advisories` và `live_checked=false` phải trung thực; không bịa nguồn, luật, giá, trải nghiệm. Giữ Writer lease, chống trùng URL/intent, parent/child, canonical, ledger, công tắc Production và G7. Mọi chỗ còn nhắc 85 là hướng dẫn cũ đã thay bởi cấu hình hiện hành.

# Pipeline v3 — hàng đợi bền vững, QA tăng dần, Publisher tự nối chuỗi (20/10/2026)

Nâng cấp theo lệnh chủ **MASTER WORK — EMERGENCY WP-WRITER PIPELINE UPGRADE** (19–20/10/2026). Tiêu chuẩn QA
(SEO ≥76, Quality ≥76, G1–G7, kiểm tra trùng, đúng danh mục, nguồn thật) **không đổi**; không dùng API LLM trả phí,
không thêm dịch vụ bên thứ ba. Mọi trạng thái vẫn nằm trong repo (`posts/drafts`, `data/qa`, `data/state`, `reports`).

## 1. Nguyên nhân ùn tắc đã đo được

| Thời điểm (UTC) | Quan sát | Nguyên nhân |
|---|---|---|
| 19/10 16:10–16:25 | 22 run `queued`, 0 run chạy; 9 bài đã push không được QA/đăng | Mỗi lần push bản thảo mở một run QA riêng, mỗi run QA xong lại mở một run Publisher; cộng với các run kiểm tra nguồn và Research QA → vượt số job chạy song song của tài khoản và hàng đợi GitHub nghẽn |
| 19/10 19:57 | Chủ chuyển QA sang cron `*/5` và tách Publisher sang nhóm concurrency riêng | Giảm trùng run, nhưng toàn bộ nhịp đăng bài phụ thuộc vào `schedule` |
| 19/10 21:25 → 20/10 00:33 → 03:35 | Cron `*/5` chỉ được GitHub giao **2 lần trong 6 giờ**; cron Publisher `:17/:47` chỉ chạy 21:45 và 00:42 | GitHub giao sự kiện `schedule` trễ hoặc bỏ qua khi tải cao; không phải SLA |
| Mọi lượt QA | `qa_gate.py` xóa toàn bộ `data/qa/*.json` rồi chấm lại **cả 308 bản thảo, trong đó 307 bài đã VERIFIED** (134,6 s/lượt tại 308 bài, O(N²) so trùng) | Tại 2.000 bài ước tính ~45 phút/lượt → vượt `timeout-minutes` → QA không bao giờ xanh → Publisher không được kích hoạt |

## 2. Thiết kế mới

```
W1–W9 push bản thảo ──► hàng đợi bền vững (posts/drafts + biên nhận hash data/state/writer-claims.json)
        │
        ▼ (push posts/drafts/** hoặc writer-claims.json; nhóm concurrency gộp nhiều push thành 1 run; cron */5 chỉ là dự phòng)
Universal writer QA — quét TĂNG DẦN (scripts/qa_incremental.py)
   FROZEN : bài đã VERIFIED trên WordPress cùng hash → giữ nguyên record, không chấm lại
   CACHED : bản thảo + quy tắc + dòng chủ đề không đổi, record < 24 h, không phải INFRA_PENDING → giữ record
   FRESH  : bài mới / bài đổi / quy tắc đổi / hết hạn / lỗi tạm thời → chấm lại
   → qa_gate.validate_complete vẫn kiểm tra hash của TỪNG record (không có record "cũ" nào lọt)
        │ workflow_run thành công
        ▼
Universal WordPress Publisher (1 writer duy nhất: concurrency group wp-writer-publisher + .factory-lock)
   intake biên nhận → qa_gate (tăng dần) → chấm LIVE từng bài READY → 2 bài/lô, tối đa 5 lô/lượt
   nhịp: post_interval_seconds sau mỗi bài, batch_pause_seconds sau mỗi lô (config/production-policy.json)
   ledger ghi POST_INTENT trước POST; G7 đọc lại; NEEDS_RECONCILE không bao giờ POST lại mù
        │ scripts/publisher_chain.py (bước cuối, chỉ khi job thành công)
        ▼
   còn READY > 0 và lượt này đã đăng ≥1 và depth < publisher_chain.max_depth → `gh workflow run` chính nó
   (chain_depth+1); vẫn xếp hàng sau run đang chạy; một lượt không đăng được gì thì KHÔNG nối chuỗi
```

### Bảng trạng thái (`reports/pipeline-board.json`, `reports/pipeline-board.md`)

| Trạng thái | Nghĩa |
|---|---|
| WRITING | chủ đề trong lease còn hạn, chưa có bản thảo |
| QA | bản thảo đã commit, chưa có record QA đúng hash (chờ lượt quét) |
| READY | QA PASS, biên nhận đúng hash, chưa có trong ledger → hàng đợi Publisher |
| REPAIR | FAIL/REVIEW loại WRITER_REPAIR hoặc INFRA_PENDING (writer sửa / máy tự chấm lại) |
| HELD | REAL_RISK (trùng intent, sai danh mục, nguồn không xác minh được, sai pháp lý/giá) hoặc PASS không có biên nhận |
| PUBLISHING | ledger POST_INTENT / VERIFY_PENDING / NEEDS_RECONCILE |
| VERIFIED | WordPress đọc lại đúng (công khai hoặc bản nháp dự phòng) |

`python scripts/pipeline_board.py` in ra số lượng; `reports.py` ghi bảng này mỗi lượt Publisher cùng dashboard.

### Chống trùng (không đổi, chỉ nhắc lại)
- Mỗi Topic ID chỉ có một bản thảo và một dòng ledger; `POST_INTENT` ghi và push lên `main` **trước** REST POST.
- `duplicate()` so slug, tiêu đề, marker `wp-writer:topic=` và canonical với toàn bộ inventory WordPress trước mỗi POST.
- POST không bao giờ được thử lại; 4xx thì rút intent, timeout/5xx/đọc lại lỗi thì `NEEDS_RECONCILE` và chỉ được
  đối chiếu bằng marker ở lượt sau.
- Một lượt chạy chỉ có một Publisher (nhóm concurrency + khóa file); self-dispatch vẫn xếp hàng trong nhóm đó.

### Khôi phục sau lỗi / hết hạn mức
- Lỗi tạm thời (nguồn timeout, 5xx, 429): record INFRA_PENDING được chấm lại tối đa 3 lần rồi chuyển REAL_RISK.
- WordPress 429/5xx: run dừng, không POST thêm; ledger giữ intent; lượt sau (QA sweep, cron, hoặc dispatch tay) tiếp tục.
- Phiên AI hết hạn mức: bản thảo/biên nhận đã push vẫn nằm trong hàng đợi; Publisher tự xử lý; writer resume cùng ID.
- Chuỗi self-dispatch có trần `max_depth` (mặc định 12 lượt ≈ 120 bài) và nghỉ `pause_seconds` giữa hai lượt.

## 3. Tệp đã thêm / sửa

| Tệp | Thay đổi |
|---|---|
| `scripts/qa_incremental.py` (mới) | kế hoạch FROZEN / CACHED / FRESH, `incremental_key` = sha(bản thảo) + sha(quy tắc) + sha(dòng chủ đề) |
| `scripts/qa.py` | cờ `--incremental`: giữ record hợp lệ, chấm bài FRESH, ghi `incremental_key`, giữ bộ đếm recheck |
| `scripts/qa_gate.py` | chỉ xóa record không còn hợp lệ; bật theo `config/qa-rules.json` `incremental_sweep` |
| `scripts/pipeline_board.py` (mới) | bảng trạng thái 7 bậc; `ready_backlog()` |
| `scripts/publisher_chain.py` (mới) | quyết định nối chuỗi có trần; `gh workflow run` bằng token của job |
| `scripts/publisher.py` | `pacing()` (nghỉ giữa bài/lô), `ready_backlog` trong `reports/publisher-latest.json` |
| `scripts/reports.py` | ghi `reports/pipeline-board.*` mỗi lượt |
| `.github/workflows/writer-qa.yml` | push `posts/drafts/**` + `writer-claims.json` đánh thức quét (gộp bằng concurrency), checkout `main`, timeout 15 phút, cron giữ làm dự phòng |
| `.github/workflows/wordpress-publisher.yml` | `actions: write`, input `chain_depth`, bước cuối `publisher_chain.py` (sau công tắc an toàn, chỉ khi thành công) |
| `config/qa-rules.json` | `incremental_sweep: true`, `incremental_max_age_hours: 24` (ngưỡng điểm không đổi) |
| `config/production-policy.json` | `post_interval_seconds: 3`, `batch_pause_seconds: 20`, `publisher_chain {enabled, max_depth 12, pause_seconds 45}` |
| `tests/test_qa_incremental.py`, `tests/test_pipeline_board.py`, `tests/test_publisher_chain.py` (mới) | hợp đồng mới; `tests/test_qa_publisher_backpressure.py` cập nhật hợp đồng gộp sự kiện |

## 4. Vận hành

- Dispatch tay một lượt Publisher: Actions → *Universal WordPress Publisher* → Run workflow (để `chain_depth` = 0).
- Dừng khẩn cấp: `emergency_stop=true` trong `config/production-policy.json` (Publisher đọc trước mỗi POST và ở bước
  đầu job); self-dispatch cũng dừng theo. Tắt riêng chuỗi: `publisher_chain.enabled=false`.
- Kiểm tra nhanh: `python scripts/qa_incremental.py` (bao nhiêu bài sẽ được chấm lại), `python scripts/pipeline_board.py`.
- Bài REAL_RISK (HELD) không chặn bài khác; writer sở hữu sửa bản thảo (`writer-repair.py`) rồi push lại, record mới
  được chấm lại ở lượt quét kế tiếp.
