# Self-healing gates G1–G7 (QA thresholds unchanged)

Owner order 2026-10-17: a QA-PASS article is published at once; what can be fixed by the machine is rechecked by the machine (at most 3 times); only an article with a real risk is held; one held article never blocks another; G7 proves the result on WordPress. Nothing below lowers SEO >= 85, quality >= 75, the 1,600–5,000 word range, the duplicate checks, the category checks, the write-ahead ledger or the never-retry-an-uncertain-POST rule. GitHub Actions still runs no AI: a content defect is repaired by the writer session, the system only tracks it.

## What happens to a verdict (`scripts/gate_triage.py`, stored as `triage` and `recheck` in the QA record)
| Class | Examples | What the system does |
|---|---|---|
| `REAL_RISK` | URL/intent collision, near duplicate, wrong category, source that cannot be verified (403, 404, TLS, excerpt not in page), wrong legal/price/business fact, invented experience, a crashed evaluation, any reason nobody classified | Held. Never auto-healed. Other articles continue. |
| `WRITER_REPAIR` | SEO score, length, structure, meta length, links, editorial evidence | Returned to the writer (`reports/repair-queue.json`). One attempt per new draft version; after 3 versions `needs_owner` is set. |
| `INFRA_PENDING` | source or link fetch timed out, HTTP 408/425/429/5xx, connection reset | Rechecked by the machine: up to 3 reads inside one evaluation (1 s, 3 s back-off) and up to 3 consecutive runs; then it becomes `REAL_RISK` ("source stays unverifiable"). |

`reports/gate-recheck.json` (written by the Publisher, persisted with the other reports) carries the counters between runs; a PASS or a published article starts clean. `reports/dashboard.json` shows `held_by_class`.

## G4 evidence recheck (`qa.evidence_recheck`)
When G4 only lacks review evidence for nearest pages (a legacy page the owner edited after the research, or a page that did not exist yet), the pages are re-read against this article: text overlap (shingle Jaccard) must stay under `config/qa-rules.json › evidence_recheck.max_jaccard` (0.25) and the full-corpus intent guard must find no search-intent match with the page. Only then are the two evidence reasons lifted; the measurement (page id, hash, overlap, verdict) is stored in `evidence_recheck`. One overlapping page keeps the article held as a duplicate-intent risk. Research evidence in `data/topics.jsonl` is never rewritten by a machine.

Inventory refresh: the Publisher reads WordPress at the start of every run (authenticated) and, when anything content-relevant differs from `data/existing-content-inventory.json` (ignoring timestamps), persists the fresh inventory by CAS at the end (`save_audit.py`, `[skip ci]`). `factory-audit.yml` stays as the manual way. A draft ignores its own published post; posts the factory published (ledger) need no review evidence but still count for URL/title collision, topic-to-topic checks and the near-duplicate gate.

## G7 — post-publication proof (`publisher.verify`)
After every write the Publisher reads WordPress back and stores `g7` in the ledger record: `status` PASS/FAIL, `wp_id`, `url`, `wordpress_status`, `categories`, `canonical`, `seo_title`, `seo_description` and one boolean per check (`wordpress_status`, `slug`, `title`, `category`, `ownership_marker`, `content`, `permalink`, `public_page`, `indexable`, `seo_meta`). A failed check keeps the post in `NEEDS_RECONCILE` (never reported as published) and the failed receipt is kept. Every later run compares the live inventory with the ledger for each verified public post (status, slug, category, permalink, SEO title, SEO description, canonical, robots) and reports `EXTERNAL_WORDPRESS_DRIFT`; it never rewrites a post. `reports/dashboard.json`: `g7_pass`, `g7_not_recorded` (posts published before G7 existed).

## Isolation
`qa.evaluate_safely` turns an unexpected crash into a FAIL ticket for that article; the Publisher loop skips an article refused before any write; an earlier uncertain POST is reconciled or skipped, never retried blindly.

Tests: `tests/test_gate_triage.py`, `tests/test_self_healing_gates.py`.
