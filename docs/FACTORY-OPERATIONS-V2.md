# Factory Operations V2 — /blog + /global patterns, native WordPress controls

These capabilities were adapted conceptually after reading the actual `thuexemayhanoi/blog` liveness/refill/watchdog workflows and `thuexemayhanoi/global` writer-pool/topic-factory/post-publish-qa workflows. Nothing is copied into this repository wholesale.

## The two kinds of success

- `RUN_SUCCESS`: GitHub Actions job exited 0. This is not proof that any article was written or published.
- `PROGRESS_SUCCESS`: an admitted immutable writer receipt, a new `PLANNED` research-approved topic, or a WordPress record read back and marked `VERIFIED` in its durable ledger.
- Writer is always an **external AI session**. GitHub Actions never calls an LLM API, invents topics, or generates placeholder posts.

## Read-only liveness

`.github/workflows/factory-watchdog.yml` runs hourly and by manual dispatch. It uses **no WordPress credentials**, `contents: read`, and outputs a temporary JSON artifact + step summary. It never writes tracked files, edits WordPress, claims a writer slot, or wakes production automatically.

Supported statuses:

| Status | Interpretation |
|---|---|
| `SAFE_OFF` | Production and unattended staging are OFF; waiting articles are expected |
| `PAUSED` | Owner emergency-stop or pause |
| `DELIVERY_PENDING` | Authenticated receipt and QA PASS awaiting next publisher within 120 minutes |
| `STALLED` | QA-PASS admitted article waiting >120 minutes despite approved delivery being ON; workflow FAIL |
| `NEEDS_RECONCILE` | WordPress POST intent unresolved; workflow FAIL, never POST again blindly |
| `CONFIG_BLOCKED` | Delivery requested but security/owner/SEO acceptance flags not all met; workflow FAIL |
| `SOURCE_MISMATCH` | QA PASS snapshot differs from immutable submitted article hash; workflow FAIL |
| `NEEDS_TOPIC_EXPANSION` | Cannot assign a valid new topic; external research needed, not fake content |
| `AWAITING_WRITERS` | At least one claimable topic but no active external AI lease |
| `RUNNING` | Active Writer and no overdue delivery |
| `WRITER_REQUEST_BLOCKED` | Current writer claim request rejected; actionable status rather than green |

Run locally: `python scripts/watchdog.py --output /tmp/wp-writer-watchdog.json`. Exit 1 indicates failed delivery/reconciliation/config/request, and status always explains what happened. Exit 0 with `SAFE_OFF` is **not** evidence of production publish.

## Writer request safety

`scripts/control_requests.py` checkpoints the result of each request, including its refusal reason. A BLOCKED request now causes Actions to exit nonzero **after preserving the reason**; submitting the same rejected request again is still blocked. Mutations to leases are applied on a separate copy of the registry, so a rejected request cannot partially release another valid claim.

The request session label remains **not an authentication factor**. GitHub branch protection, path controls and separate credentials are prerequisites before trusting multiple independent Writers with production. Refuses to claim writer identity security is complete.

## Refill and queue

`scripts/refill.py` does not create new topic prose or synthesize an SEO Matrix. It imports only externally researched `data/candidates/*.jsonl` batches; the existing Topic QA decides which topics are `PLANNED` versus `RESEARCH` or `REJECTED`. If the queue needs refill but no new batches are present, Actions now fails with `NEEDS_TOPIC_EXPANSION`. If a candidate batch results in zero additional `PLANNED` topics, the immutable research record is preserved but Actions fails (no green without actual progress).

Refill capacity is calculated from **unreserved claimable** PLANNED topics, not the lifetime PLANNED count. IDs held in live leases, immutable Writer submission receipts, or WordPress publication ledger do not qualify as available Writer queue. Expired, unsubmitted leases are reclaimable. This prevents a 100-PLANNED manifest from hiding an empty backlog.

Before adding 10,000 topics, optimize topic comparison with proven no-false-negative collision tests, and benchmark throughput. Do not bypass historical-content comparisons just to make a queue counter look better.

## Public WordPress page readback (post-publish)

`.github/workflows/wordpress-post-publish-qa.yml` runs nightly and on manual dispatch. No WordPress secrets, no mutation. It reads **only** topic IDs marked `VERIFIED` + `publish` by the existing publisher ledger, samples at most 40 pages per run (newest plus rotating historical). It checks canonical, HTML title, meta description, robots/noindex and first-paragraph identity. If any readback differs, the workflow fails with an artifact identifying the topic ID; it does not attempt updates/deletes/republishing.

If there are no public campaign posts, receipt says `NO_PUBLISHED_POSTS` rather than misleading `PASS`. This is **not** a full-crawl or evidence of Google indexing.

## Dashboard facts

`reports/dashboard.json` reports active delivery mode, staging mode, confirmed public/draft counts, admitted QA-PASS backlog, source matching, pending WordPress intents, blocked writer sessions and last WordPress verified timestamp. Dynamic `reports/latest.md` no longer says `Production is OFF` when policy actually changes.

A QA-PASS source with `live_links_checked=false` is **technical QA only**. Production Publisher must perform its own live source/link/collision verification and SEO metadata adapter validation before POST.

## Safety boundaries

**Production remains OFF.** All new jobs are read-only and have no WordPress secrets. The existing WordPress publisher retains its write-ahead CAS ledger and strict owner gating. These changes do not grant an AI GitHub user permission to alter protected code, and do not bypass CODEOWNERS limitations, site protection, SEO REST compatibility or the need for a real E2E trial. Existing URLs, legacy posts/categories, draft #3861 and stored ledger entries remain intact.

Deploy only after green CI; do not auto-merge if tests fail. Roll back only application code, never reset remote publication or writer state.
