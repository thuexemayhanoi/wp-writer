# Factory Operations V2 — /blog + /global patterns, native WordPress controls

**New V3 extension:** [No-key autonomous public-signal topic discovery](AUTONOMOUS-TOPIC-RESEARCH.md). Scheduler proposes bounded, gap-aware research tasks; external AI must provide web research and content-collision evidence before Topic QA can promote them. No automatic AI model is launched by GitHub Actions.

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
| `SAFE_OFF` | Only when the owner switched delivery off (`mode=dry_run`): waiting articles are expected. Not the current state; Production is ON since 2026-10-17 |
| `PAUSED` | Owner emergency-stop or pause |
| `DELIVERY_PENDING` | Authenticated receipt and QA PASS awaiting next publisher within 120 minutes |
| `STALLED` | QA-PASS admitted article waiting >120 minutes despite approved delivery being ON; workflow FAIL |
| `NEEDS_RECONCILE` | WordPress POST intent unresolved; workflow FAIL, never POST again blindly |
| `CONFIG_BLOCKED` | Delivery requested but the owner approval reference or the Yoast SEO adapter flag is missing (`acceptance_passed` and `security_controls_verified` no longer count); workflow FAIL |
| `SOURCE_MISMATCH` | QA PASS snapshot differs from immutable submitted article hash; workflow FAIL |
| `NEEDS_TOPIC_EXPANSION` | Cannot assign a valid new topic; external research needed, not fake content |
| `AWAITING_WRITERS` | At least one claimable topic but no active external AI lease |
| `RUNNING` | Active Writer and no overdue delivery |
| `WRITER_REQUEST_BLOCKED` | Current writer claim request rejected; actionable status rather than green |

Run locally: `python scripts/watchdog.py --output /tmp/wp-writer-watchdog.json`. Exit 1 indicates failed delivery/reconciliation/config/request, and status always explains what happened. Exit 0 with `SAFE_OFF` is **not** evidence of production publish.

## Writer request safety

`scripts/control_requests.py` checkpoints the result of each request, including its refusal reason. A BLOCKED request now causes Actions to exit nonzero **after preserving the reason**; submitting the same rejected request again is still blocked. Mutations to leases are applied on a separate copy of the registry, so a rejected request cannot partially release another valid claim.

Push-triggered request processing uses the exact GitHub push `before`/`after` commit diff to act only on changed `data/writer-requests/*.json` files. An old, unchanged BLOCKED request still has a durable reason in the ledger but **cannot block an unrelated Writer's later push**. Manual dispatch rechecks the full request collection; a still-blocked request remains visibly failed. If the event SHA diff cannot be verified, the workflow fails closed.

The request session label remains **not an authentication factor**. GitHub branch protection, path controls and separate credentials are prerequisites before trusting multiple independent Writers with production. Refuses to claim writer identity security is complete.

## Refill and queue

`scripts/refill.py` does not create new topic prose or synthesize an SEO Matrix. It imports only externally researched `data/candidates/*.jsonl` batches; the existing Topic QA decides which topics are `PLANNED` versus `RESEARCH` or `REJECTED`. If the queue needs refill but no new batches are present, Actions now fails with `NEEDS_TOPIC_EXPANSION`. If a candidate batch results in zero additional `PLANNED` topics, the immutable research record is preserved but Actions fails (no green without actual progress).

Refill capacity is calculated from **unreserved claimable** PLANNED topics, not the lifetime PLANNED count. IDs held in live leases, immutable Writer submission receipts, or WordPress publication ledger do not qualify as available Writer queue. Expired, unsubmitted leases are reclaimable. This prevents a 100-PLANNED manifest from hiding an empty backlog.

**Incremental incumbent protection:** importing a new researched batch evaluates the *new* topic IDs against all existing IDs and the other new candidates. Previously approved `PLANNED` IDs and their stored QA verdicts are preserved verbatim, even if a new proposal uses the same title, slug or intent. Only the intruding new candidate is rejected/reviewed. This prevents a new AI idea from demoting an approved/claimed/WordPress article. Large-manifest tests exercise 10,000 incumbents with one newcomer without rerunning every old topic gate. A **full manual re-audit** still evaluates the full manifest and may be expensive.

Before adding 10,000 topics, further optimize full-audit topic comparison with proven no-false-negative collision tests, and benchmark throughput. Incremental refill does not eliminate all O(N²) work from manual full audits. Do not bypass historical-content comparisons just to make a queue counter look better.

The read-only watchdog excludes expired Writer leases when calculating claimable topics, matching the canonical claim engine. It never steals live leases.

## Self-replenishing refill (2026-10-17)

The refill trigger is now `ready PLANNED < 900` (owner order: fill the registry to the approved capacity of 1,000; single source: `config/refill-policy.json`, not `min_claimable_queue`). `scripts/refill_controller.py` opens an order for 100–200 new topics, with no round limit; every candidate is checked by `scripts/intent_guard.py` against all published items and all topics in the factory, and only Research QA PASS rows become PLANNED. The watchdog and dashboard report the refill state. Full description: [SELF-REPLENISHING-TOPICS.md](SELF-REPLENISHING-TOPICS.md).

## Public WordPress page readback (post-publish)

`.github/workflows/wordpress-post-publish-qa.yml` runs nightly and on manual dispatch. No WordPress secrets, no mutation. It reads **only** topic IDs marked `VERIFIED` + `publish` by the existing publisher ledger, samples at most 40 pages per run (newest plus rotating historical). It checks canonical, HTML title, meta description, robots/noindex and first-paragraph identity. If any readback differs, the workflow fails with an artifact identifying the topic ID; it does not attempt updates/deletes/republishing.

If there are no public campaign posts, receipt says `NO_PUBLISHED_POSTS` rather than misleading `PASS`. This is **not** a full-crawl or evidence of Google indexing.

## Dashboard facts

`reports/dashboard.json` reports active delivery mode, staging mode, confirmed public/draft counts, admitted QA-PASS backlog, source matching, pending WordPress intents, blocked writer sessions and last WordPress verified timestamp. Dynamic `reports/latest.md` no longer says `Production is OFF` when policy actually changes.

A QA-PASS source with `live_links_checked=false` is **technical QA only**. Production Publisher must perform its own live source/link/collision verification and SEO metadata adapter validation before POST.

## Safety boundaries

**Production is ON (owner order 2026-10-17): QA PASS → public WordPress.** The jobs described here (watchdog, dashboard, post-publish SEO QA, refill controller) are read-only and have no WordPress secrets; only the Publisher writes, with its write-ahead CAS ledger. They do not grant an AI GitHub user permission to alter protected code. Existing URLs, legacy posts/categories, draft #3861 and stored ledger entries remain intact.

Deploy only after green CI; do not auto-merge if tests fail. Roll back only application code, never reset remote publication or writer state.

## Research Agent V2 / global-style safe extension

Bổ sung hai workflow: External Topic Research QA (no secrets, nghiên cứu 10-topic batch và checkpoint) + Trusted Research Intake and Topic Refill (chỉ chạy mã main khi research branch PUSH QA xanh, re-check source SHA/intent/WordPress inventory/taxonomy, CAS import PLANNED). Hướng dẫn tại [Research V2](RESEARCH-V2-GLOBAL-ADAPTATION.md). Do not confuse discovery leads with AI-verified research. No Excel, no WordPress credentials, no Production activation.

