# Research factory 1.000 — checkpoint và cách tiếp tục chỉ từ GitHub

Lệnh chủ MASTER WORK — RESEARCH FACTORY 1.000 SEO TOPICS: xây kho **1.000 chủ đề đã nghiên cứu thật**, không trùng ý định, đúng danh mục cha/con, đủ dữ liệu để W1/W2/W3 viết 1.600–5.000 từ. Giữ nguyên mọi chủ đề và bài đã đăng; chỉ bổ sung phần còn thiếu.

## Giới hạn cứng (không ai tự đổi)
- `approved_capacity` = **1.000** trong `config/production-policy.json` (chỉ chủ repo đổi). Nó đếm **mọi dòng** trong `data/topics.jsonl`: PLANNED, RESEARCH, REJECTED, đã đăng. Hiện 101 dòng (29 PLANNED/đã đăng, 72 seed RESEARCH) nên còn **899 chỗ trống**. Hai hệ quả phải nói thẳng:
  1. Một dòng nộp lên mà rớt Research QA vẫn chiếm một chỗ và vẫn giữ ý định tìm kiếm của nó (chỉ REJECTED mới nhả ý định). Vì vậy researcher chỉ push lô đã qua `check` và `intent-check` cục bộ.
  2. 72 seed chưa có bằng chứng nghiên cứu và không sửa tại chỗ được (candidate import không ghi đè topic có sẵn). Chúng chiếm chỗ nhưng không phải "chủ đề sẵn sàng". Muốn đủ 1.000 chủ đề **PLANNED** thật sự thì chủ repo phải nâng trần hoặc duyệt đường hoàn tất seed (xem `docs/RESEARCH-SEED-TRIAGE.md`).
- Bộ điều khiển (`config/refill-policy.json`): `trigger_below_ready` 900, mỗi đơn 100–200 chủ đề, lô 10, không giới hạn số đợt, tự dừng `CAPACITY_BLOCKED` khi hết trần.
- Giữ nguyên: SEO ≥85, Research QA, bộ chống trùng intent (`scripts/intent_guard.py`), taxonomy cha/con, URL/bài cũ, Publisher. Không tạo danh mục mới (chỉ nhắm các key đang ACTIVE).

## Cách đếm (không cộng lịch sử vào kho)
`reports/topic-stock.json` hoặc `python3 agent-tools/factory_status.py` xếp mỗi dòng đúng một giai đoạn:
IDEA (NTD-, chưa có dòng) → RESEARCH → PLANNED (sẵn sàng) / PLANNED_HOLD → CLAIMED → AUTHORED → QA_PASS → PUBLISHED / WP_DRAFT, và REJECTED. Chỉ PLANNED writer còn nhận được mới là "sẵn sàng". Lô nộp đi qua: nhánh `research/<session>` → Research QA → Trusted Intake trên main → chỉ dòng PASS thành PLANNED.

## Kế hoạch đợt
Mỗi session nghiên cứu = một nhãn `seodev-rN` + một dải ID riêng, tối đa 2 lô × 10 chủ đề (lô phải đủ 10; chỉ lô cuối của session được 1–9 và phải `checkpoint --final`). Không bao giờ dùng lại ID.

| Đợt | Session | Dải ID | Ghi chú |
|---|---|---|---|
| 1 | seodev-r5…r14 (10 cụm, xem `docs/RESEARCH-WAVE-2026-10-17.md`) | NT-000201–400 | đang chạy |
| 2 | seodev-r15…r24 | NT-000401–700 (30 ID/session, dư để thay ứng viên rớt) | cụm theo `next_batch_categories` của đơn đang mở |
| 3 | seodev-r25…r34 | NT-000701–1000 | |
| 4+ | seodev-r35… | NT-001001 trở đi | tiếp tục tới khi `CAPACITY_BLOCKED` |

Cụm của mỗi đợt lấy từ `python3 agent-tools/factory_status.py` (cột deficit theo danh mục, đã tính cả bài WordPress cũ) và `python scripts/research_v2.py plan` (quota danh mục và lô kế tiếp). Không nghiên cứu key chưa ACTIVE.

## Chuẩn một chủ đề đạt (Research QA đã bắt)
Tiêu đề và từ khóa chính riêng, intent rõ, dàn ý ≥5 phần hữu ích, `difference_summary`, `usefulness`, `scope_exclusions`, link nội bộ có thật trong inventory công khai, đúng `taxonomy_key`, slug/canonical không trùng, và nguồn:
- chủ đề hẹp: **một** nguồn đọc thật, có `source_sha256` và câu trích nguyên văn (`evidence_text`);
- pháp luật, an toàn, dữ liệu biến động (giá, quy định, thông số đổi theo thời gian): thêm nguồn đối chiếu; luật cần nguồn chính thức đọc trong 90 ngày, nguồn thường 365 ngày;
- được học từ đối thủ và hãng xe nhưng không chép nội dung, đánh giá hay giá của họ làm dữ liệu Nguyễn Tú; RSS chỉ là gợi ý, không phải nguồn dẫn fact;
- nguồn khó đọc từ runner GitHub chỉ được dùng khi snapshot ghi đúng URL + sha + đoạn trích, công khai là không kiểm tra live.

## Báo cáo sau mỗi đợt (mẫu)
Số chủ đề đã nghiên cứu · số PASS được tiếp nhận · số REVIEW cần sửa · số trùng đã loại · tổng số dòng trong kho trên 1.000 · số chủ đề sẵn sàng cho Writer · commit GitHub và tình trạng workflow. Số liệu lấy từ `factory_status.py`, không từ trí nhớ.

## Tiếp tục khi hết quota hoặc phiên dừng
1. Khôi phục công cụ: `export WPW_SCRATCH=$HOME/wp-writer-scratch; mkdir -p $WPW_SCRATCH/{tools,sources,notes,bodies,specs,agents,research}; cp agent-tools/*.py $WPW_SCRATCH/tools/; cp docs/agent-playbook/*.md $WPW_SCRATCH/; cp docs/agent-playbook/HOST-CENSUS.md $WPW_SCRATCH/sources/` rồi đọc `docs/agent-playbook/AGENT-GUIDE.md`, `ROLE-RESEARCHER.md`, `RESEARCH-ADDENDUM-2.md` (thay đường dẫn scratchpad cũ bằng `$WPW_SCRATCH`).
2. `git pull --ff-only origin main && python3 agent-tools/factory_status.py`: xem đơn đang mở, nhánh `research/*` nào chưa được tiếp nhận (`NOT ingested`), session nào còn dải ID.
3. Với session đã có nhánh: `python scripts/research_v2.py resume --branch research/<session> --apply`, **không nghiên cứu lại** chủ đề đã nằm trong `data/candidates/<session>-NNNN.jsonl` hoặc checkpoint.
4. Với cụm chưa có session: tạo nhánh từ `origin/main`, nghiên cứu 10 chủ đề, `build_research.py`, `research_v2.py intent-check`, `checkpoint`, `check`, `push`; kiểm tra trạng thái trên main bằng `factory_status.py`.
5. Lô REVIEW: sửa đúng lý do (thường là nguồn, ý định hoặc bằng chứng đọc lại) và nộp **lô mới với ID mới** nếu dòng cũ đã vào kho; không tự gán PASS.
6. Không sửa registry, config, ledger, workflow hay bài WordPress cũ bằng tay.

## Writer chạy song song
Writer không chờ nghiên cứu xong: `python scripts/writer-session.py begin --session <nhãn> --ids NT-…` (chỉ PLANNED, không `hold`), viết bằng `agent-tools/build_article.py`, `check`, `push`; Publisher đăng bài QA PASS; kiểm tra ledger `phase=VERIFIED` và URL công khai.
