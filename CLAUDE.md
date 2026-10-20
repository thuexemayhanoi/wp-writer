# Claude / ChatGPT / Gemini — Nguyễn Tú WP Writer

**Start here (do not reread entire repository):**
- **For the 1,482-title Excel campaign:** [docs/TITLE-PLAN-1482-SOP.md](docs/TITLE-PLAN-1482-SOP.md).
- **For an already claimed Writer topic:** [docs/WRITER-QUICKSTART.md](docs/WRITER-QUICKSTART.md) + [docs/ARTICLE-CONTRACT.md](docs/ARTICLE-CONTRACT.md).
- **For a Research batch:** [docs/RESEARCH-V2-GLOBAL-ADAPTATION.md](docs/RESEARCH-V2-GLOBAL-ADAPTATION.md).
- **For QA failures:** [docs/WRITER-AUTO-REPAIR.md](docs/WRITER-AUTO-REPAIR.md).

**User intent:** 518 WordPress publish posts were snapshotted on 2026-10-20, and three owner-approved Excel planning files contain 1,482 *proposed* Vietnamese titles, 60–80 characters, mapped to 18 existing WordPress leaf categories (82–83 each). `TP-XXXX` is a plan ID, **not** a claimable `NT-XXXXXX` Topic ID. A human/external AI must actually research 1–4 public source pages and pass Topic Factory/Research QA before Writer claim, Writer QA, Publisher and G7. GitHub Actions does not run an AI writer.

**60-second workflow:** read 1–3 planned rows (or `python scripts/title_plan_next.py --limit 3`), check semantic duplication against WordPress and registered topics, research verified sources, submit genuine candidates through Research QA, claim a valid W1–W9 lease for real `PLANNED` NT topics, create useful 1,600–5,000-word articles with SEO/Quality ≥85 and G1–G6 PASS, allow Publisher/G7 to confirm WordPress and mark Excel only with verified receipt. If offline/quota exhausted, save a factual checkpoint and resume the original session; never invent sources or approval.

**Safety:** use only `thuexemayhanoi/wp-writer` and `https://thuexemaynguyentu.com`; do not import the `wp-aiwriter` Nguyễn Hà Excel queue. Never use `excel`, `xlsx`, `csv`, `TP-XXXX`, or file names in planned article slugs. Do not rewrite existing URLs/canonicals, create categories, steal leases, manually edit QA scores, or forge Publisher/G7 ledger.

**Return concise factual progress:** `TP ID / NT ID / Writer slot / QA / WP ID / verified URL / blockage`. “GitHub push succeeded” ≠ “WordPress published”.
