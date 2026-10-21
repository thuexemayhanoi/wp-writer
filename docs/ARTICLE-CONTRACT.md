**OWNER UPDATE 22/10/2026 — CLAUDE CHỈ CẦN GITHUB:** Claude không cần và không được bắt buộc kết nối WordPress để nghiên cứu, nhận Topic ID/lease, viết bài, QA G1–G6 hoặc nộp. `python scripts/writer_handoff.py --session <SESSION>` kiểm tra trạng thái bàn giao chỉ qua file GitHub. Bài đã QA PASS + hash receipt hợp lệ thì Claude nhận bài tiếp, không đợi WordPress. **Chỉ Publisher GitHub Actions có quyền WordPress REST và làm G7 Live readback SAU khi đăng.** Giữ ngưỡng SEO/Quality ≥76, Research QA, chống trùng, G1–G7, ledger. Xem [quy định phân quyền Writer/Publisher](GITHUB-ONLY-WRITER-HANDOFF.md).

**QUY ĐỊNH MỚI CỦA CHỦ SỞ HỮU — 20/10/2026:** Ngưỡng SEO **≥76/100** và Quality **≥76/100** (trên 75), theo `config/qa-rules.json`. G3 nguồn ngoài là **tham khảo có cảnh báo để audit sau**, không chặn bài chỉ vì trích dẫn đổi câu chữ, ngày kiểm tra cũ, 404 hoặc nguồn tạm không mở được. Chưa đọc live phải ghi `live_checked=false`, ghi `source_advisories`; không gọi đó là đã xác minh. Giữ chặn nguồn URL không an toàn, nguồn pháp luật không có URL chính thức, giá/địa chỉ sai, bịa trải nghiệm, sai URL/canonical/danh mục, trùng bài, Writer receipt và G7. Các câu cũ ghi ngưỡng 85 hay bắt nguồn khớp nguyên văn đã **hết hiệu lực**. Không chỉnh điểm JSON, không bỏ gate.

# Markdown contract

Sao chép chính xác identity từ manifest. Metadata dưới đây là cấu trúc minh họa, phải thay bằng dữ liệu thật và nguồn đã đọc; không dùng placeholder trong bài nộp.

```yaml
---
topic_id: NT-000037
title: "Chọn nơi sửa xe máy điện: những câu hỏi nên hỏi kỹ thuật viên"
primary_keyword: "Chọn nơi sửa xe máy điện"
search_intent: "Hướng dẫn"
taxonomy_key: electric-maintenance
canonical_target: "https://thuexemaynguyentu.com/chon-noi-sua-xe-may-dien-nhung-cau-hoi-nen-hoi-ky-thuat-vien/"
writer_slot: W1
writer_session: s-your-session
meta_title: "Chọn nơi sửa xe máy điện: câu hỏi cần xác nhận"
meta_description: "Mô tả thực tế 100–180 ký tự, thể hiện đúng phạm vi bài viết và lợi ích cho người cần chọn đơn vị kiểm tra xe điện."
direct_answer: "Một đoạn trả lời trực tiếp xuất hiện nguyên văn ở đầu bài."
link_rationale: "Giải thích lý do từng URL liên quan đúng nhu cầu, không dựa riêng vào từ khóa."
business_claims: []
sources: []
editorial_review:
  reviewer: s-your-session
  body_sha256: sha256-of-trimmed-body
  intent_covered: true
  substantive: true
  facts_checked: true
  no_fabricated_experience: true
  collision_reviewed: true
---
```

**Lưu ý W1–W9:** `writer_slot: W1` phía trên chỉ là ví dụ. Phải điền **đúng W1…W9 mà lệnh `writer-session.py begin --slot auto` trả về**; không được tự gán W1 mặc định, đổi `writer_session` hoặc lấy bài của Writer khác.

`primary_keyword`, intent và các identity phải lấy từ manifest, không tự suy theo ví dụ. Tính `body_sha256` bằng `hashlib.sha256(body.strip().encode()).hexdigest()` sau khi viết xong; không hash YAML. Submission receipt dùng SHA-256 **toàn bộ file** và do session tool ghi.

Nguồn có cấu trúc: `url` HTTPS công khai đã kiểm chứng (được lấy từ website hãng, đối thủ, cơ quan nhà nước, du lịch, báo chí, kỹ thuật hoặc nghiên cứu), `checked_at` YYYY-MM-DD, `supports` mô tả khẳng định được nguồn chứng minh, `evidence_text` đoạn ngắn có thật trong nguồn, `source_sha256` hash văn bản nguồn đã đọc cho QA cục bộ. Khi xuất bản, QA không buộc đối chiếu lại từng chữ nguồn hay ngày kiểm tra; ghi `source_advisories` và `live_checked=false` để audit sau. Nguồn pháp lý vẫn cần URL cơ quan có thẩm quyền, nhưng nguồn cũ hoặc tạm lỗi không tự chặn bài. Thông tin kỹ thuật theo đúng model/đời xe; không dùng manual của mẫu khác.

Business claim có thể khai `key: phone|address|hours|deposit_vnd` hoặc `price:Honda Vision:day_vnd` và value khớp chính xác business-facts. Khai đúng metadata không miễn kiểm tra nội dung; mọi con số trong bài vẫn cần nguồn/thông tin chủ cung cấp. Không bịa evidence hay trải nghiệm.

Nội dung không thêm H1 (WordPress tự dùng title), có ít nhất 4 H2 hữu ích, đoạn trả lời ngay đầu bài, ví dụ theo ngữ cảnh và internal links tới URL công khai thật. Không raw HTML, script, JSON-LD tự chèn, TODO, danh sách từ khóa kéo dài. Mọi ảnh cần alt và quyền sử dụng. Tài liệu, nguồn, code, HTML và keyword appendix không được tính vào mốc từ.


## SEO QA V2 — yêu cầu trước khi nộp bài (từ 17/10/2026)

Tất cả bài mới phải đạt **SEO score nội bộ ≥76/100**, Quality ≥76, và **PASS cả sáu gates**. Xem [bảng chấm điểm và tiêu chuẩn site chính](SEO-QA-V2.md).

- SEO title và meta description phải thể hiện đúng search intent, viết tự nhiên; đừng cố nhồi exact keyword.
- Mở bài trả lời trực tiếp, H2 liên quan thực tế và có giá trị, không lặp mẫu kéo dài.
- Nối những URL **đã xuất bản thật**, ưu tiên silo/pillar liên quan; đa dạng anchor, không spam trang chủ hay liên kết nháp.
- Không bịa giá thuê xe/phí giao/đặt cọc/kinh nghiệm người dùng/luật. Sử dụng business facts và nguồn kiểm chứng.
- Không ép bài kiến thức phải chèn FAQ, ảnh hoặc lời kêu gọi thuê xe.
- Đọc seo_checks và seo_recommendations trong data/qa/NT-XXXXXX.json. dưới 76 là FAIL, Writer tự chỉnh và làm lại hash/QA; không đăng WordPress.
- Nếu đạt 76 nhưng trùng intent, sai category cha/con, sai canonical hoặc nguồn không đáng tin vẫn FAIL/REVIEW. Không sửa URL hoặc bài cũ để nâng điểm.

Số 76 là ngưỡng của thang điểm nội bộ của repo, **không phải điểm Yoast hoặc điểm xếp hạng Google**. WordPress thực tế còn được xác minh sau đăng; ngưỡng mới không tự kích hoạt Production.

## AUTO-REPAIR WRITER — 10 CONTENT REVISIONS (18/10/2026)

Read docs/WRITER-AUTO-REPAIR.md (single authoritative procedure). The active Claude session first repairs owned unfinished Topic IDs; if none, it continues writing legitimately PLANNED topics. To initialize QA and a durable baseline, run python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Initial draft". After each actual edit, run the same save command with an accurate change note. QA is re-executed, SHA-256 and score/errors are stored, and the draft + checkpoint are committed to an isolated repair/SESSION/NT-XXXXXX branch. A new changed version counts as one repair, up to 10; identical bytes do not count. Use python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX after a quota interruption. Live lease ownership is always checked; no force pushes, no edited QA evidence. Genuine PASS goes through the unchanged writer-session.py push and Publisher. REAL_RISK or exhausted limit remains held, never falsely PASS. Infra/network retry stays 3, separate from content-repair limit 10. GitHub Actions never writes prose or calls an AI without an actual external model connection.
