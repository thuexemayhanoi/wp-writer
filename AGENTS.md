# Universal writer contract — Nguyễn Tú


> **BẮT BUỘC CHO W1/W2/W3 — SEO QA V2:** Trước khi nộp bài, tối ưu tự nhiên theo intent để đạt **SEO ≥85/100** và Quality ≥75, đồng thời qua đủ G1–G6. Đọc [quy tắc điểm SEO của website chính](docs/SEO-QA-V2.md). Nếu dưới 85, sửa các mục trong seo_recommendations, cập nhật full-file writer hash và chạy lại QA; không tự sửa điểm trong JSON hoặc tắt gate. Không nhồi từ khóa, ảnh, FAQ hay CTA thuê xe vô nghĩa. **Các lỗi trùng intent, nguồn bịa, thông tin chủ sai, URL/canonical, category hoặc link sai luôn chặn xuất bản bất kể điểm.**


> **NGUỒN VÀ LIÊN KẾT NGOÀI (18/10/2026):** Writer được nghiên cứu website chính hãng, cơ quan nhà nước, tài liệu khoa học/kỹ thuật và nguồn đáng tin; lưu bằng chứng thật trong YAML `sources`. Bài viết **được dẫn link ngoài HTTPS phù hợp ngữ cảnh** đến các nguồn hữu ích (không giới hạn mạng xã hội, không cấm Honda/Yamaha/VinFast/nguồn pháp luật). G5 vẫn chặn link không an toàn, link chuyển hướng trá hình; kiểm tra link nội bộ công khai như cũ. Không bắt buộc chèn backlink ra ngoài, không tạo link quảng cáo/spam. G3 vẫn kiểm chứng nguồn thực tế, luật và thông tin doanh nghiệp. Xem `docs/SEO-QA-V2.md`.

> **QA → WordPress ngay, 2+2+2+2+2:** xem [Instant Publishing](docs/INSTANT-PUBLISHING.md). Publisher được nối sau QA PASS; không có thời gian nghỉ bắt buộc giữa các batch. **Lệnh chủ 2026-10-17: Production tự động BẬT** (`mode=production`, `production_enabled=true`) theo luồng đơn giản W1/W2/W3 → QA (≥85, kiểm tra trùng, đúng danh mục) → Publisher → WordPress công khai. `acceptance_passed` và `security_controls_verified` không còn chặn đăng; hai cờ đó vẫn `false` vì chưa có kiểm chứng tương ứng — không gán `true` giả. Các bài #3882, #3888, #3890, #3930–#3932, #3935, #3938–#3945 đã công khai thủ công (WPVibe/owner), không phải bằng Github Publisher.

**Autonomous research queue:** read [docs/AUTONOMOUS-TOPIC-RESEARCH.md](docs/AUTONOMOUS-TOPIC-RESEARCH.md) and `data/research/auto/batch-*.jsonl`. The scheduled no-key scanner creates `NTD-` proposals, **not** AI-validated `PLANNED` topics. A researching AI must independently find and verify sources, compare old WordPress content, submit a `data/candidates/*.jsonl` batch with its exact `origin_id`, and pass Topic QA. Never invent researcher citations, historical content hashes or turn an RSS headline into legal/price evidence.

**Operational reference:** read [Factory Operations V2](docs/FACTORY-OPERATIONS-V2.md) for read-only watchdog, non-green BLOCKED requests, refill that requires new researched PLANNED topics, and public post-SEO QA. Never confuse Actions SUCCESS with verified WordPress publication.

**Fast start for any external AI:** [docs/AI-START-HERE.md](docs/AI-START-HERE.md). One 10-topic claim per session; repair your FAIL/REVIEW content, do not alter policies or privileged workflows. Production is controlled only by the owner's `config/production-policy.json`; writers never edit it.

Only this repository and https://thuexemaynguyentu.com are in scope. Read the README, docs/WRITER-QUICKSTART.md, data/business-facts.json and your topic before writing. **There is NO Excel dependency in wp-writer.** The source of topic IDs, titles, intent and target taxonomy is `data/topics.jsonl`; the immutable category parent/child map is `data/taxonomy.json`, verified against WordPress REST. Never import the Nguyễn Hà matrix or `wp-aiwriter` IDs/categories. See [side-by-side workflow comparison](docs/WORKFLOW-COMPARISON-WP-AIWRITER.md).

* External AI providers share the same W1/W2/W3 contract. No AI model, AI API key or writer is run in Actions.
* Supporting articles: **1,600–5,000 useful Vietnamese words**, excluding frontmatter, markup, keyword lists, references and navigation. This requirement supersedes the older README word minimum.
* Use only PLANNED topics, claim via scripts/writer-session.py with a stable public session label. A live lease cannot be stolen. Resume your REPAIR first. Do not edit another writer's draft. Do not invent facts or first-hand experience.
* Writer-editable inputs: owned posts/drafts/NT-XXXXXX.md and data/candidates/*.jsonl. Registry writes only through the CAS session tool. Coordinator-only: topic/taxonomy/facts/config/code/workflows/QA/checkpoints/ledger.
* Commit/push owned drafts promptly using the session tool. Follow Actions results and repair the exact ID. Do not declare publication from a push alone.
* All legacy WordPress posts/pages/products, canonical/slug, existing category ancestry, themes, plugins, sitemap, Trash and smoke-test #3861 are immutable. No update/delete/redirect/noindex operations on legacy content.
* One publisher, batch maximum 2, write-ahead remote ledger before POST, reconcile unknown outcomes. Never clear a pending intent or retry an uncertain POST blindly.
* Owner ordered on 2026-10-17: a GitHub article that passes the QA gate goes to WordPress immediately. Production is ON (`production_enabled=true`, `owner_approval_ref` set). QA (SEO/Quality ≥85, duplicate check, exact category), the write-ahead ledger, Yoast readback and `paused`/`emergency_stop` are unchanged. `acceptance_passed` and `security_controls_verified` stay `false` (never performed) and no longer gate publishing; never set them `true` without real evidence. Manual WPVibe canaries do not prove the automated publisher. Writers must never edit Production flags, secrets or WordPress settings.
* Machine QA is a technical screen, not semantic/factual proof. Missing evidence stays REVIEW. Do not lower thresholds or fabricate research evidence to fill 1,000 rows.
* Protected CODEOWNERS paths require owner review. CODEOWNERS alone is not an access control. Enforced branch/path controls are not verified and, by owner order 2026-10-17, are no longer a publishing prerequisite.
* Keep checkpoints factual. Distinguish candidate, PLANNED, authored, READY, WordPress draft, verified public, and indexed.

## Keep new WordPress posts in sync without duplicates

- Manual owner-approved canaries: `NT-000037` → WordPress `#3888` in `Blog > Xe Điện > Chăm sóc xe điện` (`#160`), and `NT-000047` → WordPress `#3890` in `Blog > Pháp Lý & Kinh Nghiệm > An toàn khi di chuyển` (`#161`). Do **not** recreate or edit them.
- Ledger `data/state/publication-ledger.json` controls publication identity. A new article's source hash, exact Topic ID, category ancestry and WordPress permalink are mandatory. Do not interpret a GitHub Actions `success` as a WordPress publish; read the ledger (`phase=VERIFIED`) and the public URL.
- No topic Excel/category boundary approvals. AI may research the next genuinely distinct search intents via `data/candidates/*.jsonl` and Topic QA, and claim new `PLANNED` topics through W1/W2/W3. Writing still requires a running external AI session.

## External Research Agent V2 — kế thừa cơ chế tốt của /global

Nguồn quy định: [Research V2 runbook](docs/RESEARCH-V2-GLOBAL-ADAPTATION.md). Nghiên cứu tối đa 10 chủ đề độc lập mỗi lượt trên nhánh research/<stable-session>, chạy scripts/research_v2.py hints/checkpoint/check/push/resume. Chỉ sửa data/candidates/<session>-NNNN.jsonl và data/research/checkpoints/<session>.json; mọi file workflow/scripts/config/ledger/WordPress được bảo vệ khỏi Research Agent. Research QA phải PASS với >=2 nguồn HTTPS đọc thật từ hai host độc lập, nguồn snapshot hash, khác intent các money pages, taxonomy parent/child đúng, full-content inventory review. RSS chỉ là lead, KHÔNG là nguồn dẫn fact. Green research push tự kích hoạt Trusted Research Intake chạy mã main và CAS import topic hợp lệ thành PLANNED, không phát hành WordPress. SEO Writer V2 >=85, code Publisher và Production OFF vẫn giữ nguyên.

## Self-replenishing topics — lệnh chủ 2026-10-17

Khi PLANNED sẵn sàng viết còn **dưới 50**, `scripts/refill_controller.py` (workflow `Self-replenishing topic controller`, không AI, không WordPress) mở đơn nghiên cứu **200–300 chủ đề mới**; **không giới hạn số đợt**. Mọi ứng viên bị `scripts/intent_guard.py` so với TOÀN BỘ bài đã đăng và mọi chủ đề đang xử lý; **chỉ dòng đạt Research QA mới thành PLANNED**. Researcher chạy `python scripts/research_v2.py plan` và `intent-check --file …` trước khi push. Số liệu nằm ở `config/refill-policy.json` (coordinator-only). Chi tiết và giới hạn thật (`approved_capacity`, không có AI trong Actions): [docs/SELF-REPLENISHING-TOPICS.md](docs/SELF-REPLENISHING-TOPICS.md). Writer/Researcher không sửa policy, script hay workflow này.
