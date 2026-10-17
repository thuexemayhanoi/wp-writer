# Research wave 2026-10-17 — checkpoint and how to continue from GitHub alone

Goal (owner): a reserve of at least 100 researched PLANNED topics that no writer has used, kept between 100 and 200, built in batches of at most 10, each batch pushed as soon as it passes. Writers keep writing from the reserve in parallel.

## Counting (never add history to the reserve)
`reports/topic-stock.json` (written by the dashboard job, also in the watchdog) puts every topic row in exactly one stage:
IDEA (NTD- lead, no row yet) → RESEARCH → PLANNED (ready) / PLANNED_HOLD → CLAIMED → AUTHORED → QA_PASS → PUBLISHED / WP_DRAFT, plus REJECTED.
Only PLANNED counts toward the reserve. Thresholds: `config/refill-policy.json` (`trigger_below_ready` 100, order of 100–200 new topics). Order and quotas: `python scripts/research_v2.py plan`.

## Done (commits on main)
- `051dcb0` inventory refreshed from authenticated WordPress (184 items, includes the 10 factory posts #3947–#3956).
- `97550f4` stock ladder, per-topic research acceptance (a failing topic never blocks passing ones), `hold` parking for topics whose sources the runner cannot read (NT-000111/113/116/117), factory-post evidence exemption in local QA.
- This commit: reserve thresholds 100 / 100–200, agent playbook and tools stored in the repo (`docs/agent-playbook/`, `agent-tools/`).

## Researcher clusters (one session label and one ID range each; extend the table, never reuse an ID)
| Session | IDs | Cluster | Taxonomy keys |
|---|---|---|---|
| seodev-r5 | NT-000201–220 | Xe số / xe côn: vận hành, chạy rà, chọn xe | reviews, engine-care, road-safety |
| seodev-r6 | NT-000221–240 | Xe tay ga: smart key, idling stop, đèn báo, vận hành | reviews, engine-care, road-safety |
| seodev-r7 | NT-000241–260 | Xe 50cc và người mới lái | rental-50cc, road-safety, driving-licence, reviews |
| seodev-r8 | NT-000261–280 | Bảo dưỡng định kỳ: dầu nhớt, lọc gió, bugi, ắc quy | engine-care |
| seodev-r9 | NT-000281–300 | Lốp, phanh, giảm xóc, điện: kiểm tra kỹ thuật | engine-care, road-safety |
| seodev-r10 | NT-000301–320 | Xe điện / xe đạp điện, pin, sạc (sources thin: VinFast host is 403 from the runner) | ebikes, battery-charging, electric-tech, electric-maintenance, electric-transition |
| seodev-r11 | NT-000321–340 | Kỹ năng lái an toàn theo tình huống | road-safety |
| seodev-r12 | NT-000341–360 | Giấy tờ, quy định, thủ tục (legal host sources only, probed) | driving-licence, road-safety, rental-procedures, legal |
| seodev-r13 | NT-000361–380 | Du lịch từ Hà Nội bằng xe máy | hanoi-travel, vietnam-travel, trip-planning |
| seodev-r14 | NT-000381–400 | Di chuyển đô thị, văn hóa, ẩm thực Hà Nội | urban-mobility, food-culture, hanoi-travel, green-travel, trip-planning |

Status of the sessions is in `data/research/checkpoints/<session>.json` and `data/state/research-intake-ledger.json`. The first launch of all ten agents (14:00 UTC) died at once on the account's five-hour usage limit before any batch existed: nothing was lost, nothing was pushed. The relaunch starts from zero for every session whose checkpoint file does not exist.

## Continue (fresh session, no chat memory needed)
1. `export WPW_SCRATCH=$HOME/wp-writer-scratch; mkdir -p $WPW_SCRATCH/{tools,sources,notes,bodies,specs,agents,research}; cp agent-tools/*.py $WPW_SCRATCH/tools/; cp docs/agent-playbook/*.md $WPW_SCRATCH/; cp docs/agent-playbook/HOST-CENSUS.md $WPW_SCRATCH/sources/` and read `docs/agent-playbook/AGENT-GUIDE.md`, `ROLE-RESEARCHER.md`, `RESEARCH-ADDENDUM-2.md` (replace the old absolute scratchpad path with `$WPW_SCRATCH`).
2. `python scripts/research_v2.py plan` — if the state is not REFILL_OPENED / REFILL_IN_PROGRESS there is no order: stop.
3. For each cluster above without an accepted batch: `python scripts/research_v2.py resume --branch research/<session> --apply` if the branch exists, otherwise create it from `origin/main`; research ten topics (two real sources from different hosts, one article-citable and probed from the runner), `build_research.py`, `research_v2.py intent-check`, `checkpoint`, `check`, `push`. Verify the topic status on main afterwards.
4. Writers: `python scripts/writer-session.py begin --session <label> --ids NT-…` (only PLANNED, never a `hold` topic), write with `agent-tools/build_article.py`, `check`, `push`; the Publisher posts QA-PASS drafts; verify the public URL and the ledger (`phase=VERIFIED`).
5. Never edit the registry, config, ledger or old WordPress content by hand.
