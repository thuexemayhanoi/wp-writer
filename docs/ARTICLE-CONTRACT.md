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

`primary_keyword`, intent và các identity phải lấy từ manifest, không tự suy theo ví dụ. Tính `body_sha256` bằng `hashlib.sha256(body.strip().encode()).hexdigest()` sau khi viết xong; không hash YAML. Submission receipt dùng SHA-256 **toàn bộ file** và do session tool ghi.

Nguồn có cấu trúc: `url` HTTPS công khai đã kiểm chứng (được lấy từ website hãng, đối thủ, cơ quan nhà nước, du lịch, báo chí, kỹ thuật hoặc nghiên cứu), `checked_at` YYYY-MM-DD, `supports` mô tả khẳng định được nguồn chứng minh, `evidence_text` đoạn ngắn có thật trong nguồn, `source_sha256` hash văn bản nguồn đã đọc cho QA cục bộ. QA live ưu tiên tải lại để đối chiếu; nếu lỗi mạng tạm thời, chỉ chấp nhận snapshot bằng chứng đã trùng chính xác hồ sơ nghiên cứu của chính chủ đề và ghi rõ là chưa xác thực live. Nguồn pháp lý phải là cơ quan có thẩm quyền, được kiểm tra trong hạn xác minh. Thông tin kỹ thuật theo đúng model/đời xe; không dùng manual của mẫu khác.

Business claim có thể khai `key: phone|address|hours|deposit_vnd` hoặc `price:Honda Vision:day_vnd` và value khớp chính xác business-facts. Khai đúng metadata không miễn kiểm tra nội dung; mọi con số trong bài vẫn cần nguồn/thông tin chủ cung cấp. Không bịa evidence hay trải nghiệm.

Nội dung không thêm H1 (WordPress tự dùng title), có ít nhất 4 H2 hữu ích, đoạn trả lời ngay đầu bài, ví dụ theo ngữ cảnh và internal links tới URL công khai thật. Không raw HTML, script, JSON-LD tự chèn, TODO, danh sách từ khóa kéo dài. Mọi ảnh cần alt và quyền sử dụng. Tài liệu, nguồn, code, HTML và keyword appendix không được tính vào mốc từ.


## SEO QA V2 — yêu cầu trước khi nộp bài (từ 17/10/2026)

Tất cả bài mới phải đạt **SEO score nội bộ ≥85/100**, Quality ≥85, và **PASS cả sáu gates**. Xem [bảng chấm điểm và tiêu chuẩn site chính](SEO-QA-V2.md).

- SEO title và meta description phải thể hiện đúng search intent, viết tự nhiên; đừng cố nhồi exact keyword.
- Mở bài trả lời trực tiếp, H2 liên quan thực tế và có giá trị, không lặp mẫu kéo dài.
- Nối những URL **đã xuất bản thật**, ưu tiên silo/pillar liên quan; đa dạng anchor, không spam trang chủ hay liên kết nháp.
- Không bịa giá thuê xe/phí giao/đặt cọc/kinh nghiệm người dùng/luật. Sử dụng business facts và nguồn kiểm chứng.
- Không ép bài kiến thức phải chèn FAQ, ảnh hoặc lời kêu gọi thuê xe.
- Đọc seo_checks và seo_recommendations trong data/qa/NT-XXXXXX.json. Dưới 85 là FAIL, Writer tự chỉnh và làm lại hash/QA; không đăng WordPress.
- Nếu đạt 85 nhưng trùng intent, sai category cha/con, sai canonical hoặc nguồn không đáng tin vẫn FAIL/REVIEW. Không sửa URL hoặc bài cũ để nâng điểm.

Số 85 là thang điểm nội bộ của repo, **không phải điểm Yoast hoặc điểm xếp hạng Google**. WordPress thực tế còn được xác minh sau đăng; ngưỡng mới không tự kích hoạt Production.

## AUTO-REPAIR WRITER — 10 CONTENT REVISIONS (18/10/2026)

Read docs/WRITER-AUTO-REPAIR.md (single authoritative procedure). The active Claude session first repairs owned unfinished Topic IDs; if none, it continues writing legitimately PLANNED topics. To initialize QA and a durable baseline, run python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Initial draft". After each actual edit, run the same save command with an accurate change note. QA is re-executed, SHA-256 and score/errors are stored, and the draft + checkpoint are committed to an isolated repair/SESSION/NT-XXXXXX branch. A new changed version counts as one repair, up to 10; identical bytes do not count. Use python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX after a quota interruption. Live lease ownership is always checked; no force pushes, no edited QA evidence. Genuine PASS goes through the unchanged writer-session.py push and Publisher. REAL_RISK or exhausted limit remains held, never falsely PASS. Infra/network retry stays 3, separate from content-repair limit 10. GitHub Actions never writes prose or calls an AI without an actual external model connection.
