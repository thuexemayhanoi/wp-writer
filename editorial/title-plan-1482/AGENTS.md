# Instructions for AI working inside editorial/title-plan-1482/

**Canonical guidance:** [../../docs/TITLE-PLAN-1482-SOP.md](../../docs/TITLE-PLAN-1482-SOP.md).

- Three `.xlsx` and `.csv` represent the same 1,482 rows in `plan.json`; never manually mutate their publication status. `status.json` is derived from a real G7 receipt only.
- AI gets the next 1–3 candidates from `python scripts/title_plan_next.py --limit 3`, or reads only those rows in `plan.json`. Do not read/print all 1,482 titles into the model context on every turn.
- A `TP-XXXX` planning row cannot be claimed as a `NT-XXXXXX` Writer topic. Research real sources (1–4), compare against live WordPress and Topic Registry, then pass Research QA → trusted intake → NT `PLANNED`.
- Preserve fixed WordPress parent/category term ID from the row and `data/taxonomy.json`; 51 wards (term 182) is a separate campaign.
- Slug from actual article topic, never from Excel filename, row ID, `TP-`, `excel`, `xlsx` or `csv`. Existing URLs remain untouched.
- W1–W9 must use valid lease/session and `docs/ARTICLE-CONTRACT.md`. SEO score and Quality score ≥85, G1–G6 PASS; genuine G7 PASS required to mark published.
- Checkpoints after quota/network loss must retain TP/NT/session/branch/last commit. No fake sources, fake publication receipts, bypassing QA, or blind WordPress POST retries.

Open the workbook's **Huong dan** sheet for a compact version of these exact rules; authoritative full explanations live in the SOP above.
