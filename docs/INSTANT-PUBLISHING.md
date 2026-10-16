# Instant QA → WordPress publishing (Owner approved, activation gated)

Owner requested **2026-10-16**: "Writer viết xong, qua QA là lên WordPress luôn; mười bài thì 2+2+2+2+2". The request is recorded in `config/production-policy.json` as `owner_publish_request`. This is approval of the **desired behavior**, NOT evidence that technical security/SEO prerequisites are satisfied.

## Fast path

1. External AI W1/W2/W3 claims up to TEN unique `PLANNED` topic IDs, writes each 1,600–5,000 useful words on own approved branch/session and submits immutable hash receipts. GitHub does not invent content, call an LLM or simulate a Writer.
2. `Universal writer QA (no WordPress credentials)` runs independent unit tests, invariants, article content QA. FAIL/REVIEW posts go to the repair queue and remain owned by their Writer. QA never bypasses the review.
3. After a **successful main-push QA run**, `Universal WordPress Publisher` now receives a `workflow_run` event. The publisher refuses failed/pr-event QA and checks that the QA head SHA belongs to the current main history. Direct draft-push launch into Publisher was removed to prevent racing QA. Manual dispatch and 30-minute schedule remain **fallbacks**, not mandatory pauses between pairs.
4. When production prerequisites are actually verified and mode is active, Publisher audits live WordPress, reevaluates factual/source/link/taxonomy/collision QA **live per article**, checks immutable receipt/hash and a fresh main policy, writes durable `POST_INTENT` *before* each WordPress create. It refuses blind retry and reconciles uncertain POST intents.
5. It executes five consecutive 2-article batches, at most **10 new WordPress posts per run**, under `max_new_posts_daily=10`; first pair doesn't wait 30 minutes before the next. `max_batches_per_run=5` and `batch_size=2`. If category is mismatched, the article becomes a **WordPress draft** under a verified existing fallback category rather than public; no old URLs or posts are overwritten.
6. Every published article must pass readback: public permalink, canonical, browser title, meta description, indexable status, matching content and correct category. A public POST that fails verification remains `NEEDS_RECONCILE` (not silently "SUCCESS").
7. If a batch contains fewer than 10 QA-PASS items, only the available qualified items are posted. FAIL/REVIEW stays in REPAIR and does not block other articles. Writers must revise drafts themselves; GitHub Actions has no AI model to perform textual auto-repair after a chat/agent ends.

## Production activation — do not falsify PASS flags

As of Oct 16 2026, verified facts:
- Owner authorizes *automated publication after QA* to **https://thuexemaynguyentu.com**, not to blog.rentbikehanoi.com.
- GitHub `main` is returned by GitHub API as `protected: false`, rulesets: empty. Existing external Writer sessions can potentially modify workflow code. **Security controls NOT VERIFIED**. Protect the privileged Publisher and production secrets without breaking Git CAS state writes; separate trusted deployment environment/repo or path-limited, reviewed code access + branch controls. Merely adding CODEOWNERS text is not enough. Do not mark `security_controls_verified=true` until tested.
- Yoast SEO title and description were confirmed REST-writeable on isolated draft #3870 via the user's WordPress connector; `_yoast_wpseo_canonical` is not exposed as REST meta. Published sample #2634 has Yoast default canonical = its public permalink. Publisher now writes title+description and uses Yoast generated canonical, but rechecks frontend canonical/title/description for every new public article. **GitHub Actions WP secrets/adapter must still pass an isolated write/readback acceptance test on the actual publishing credentials**, then mark `seo_adapter_verified=true`.
- Draft-only factory acceptance tests existed (draft #3870, factory article #3882). They do **not** establish permission to publish every blog article. Current `acceptance_passed` remains false.
- **Production stays OFF** until all prerequisites are met; do not set the flags merely to make CI green.

Once verified, owner can set the explicit `owner_approval_ref`, `mode=production`, `production_enabled=true`, `acceptance_passed=true`, `security_controls_verified=true`, `seo_adapter_verified=true` together via reviewed configuration change. New posts will then publish quickly without waiting for each 30-minute cron window. The WP credentials are only scoped to the privileged job execution and are not sent to W1/W2/W3 branches. A successful QA workflow by itself grants no WordPress privileges.

## Stop and recovery

Owner can immediately set `emergency_stop=true` or `paused=true` (though an already-issued WordPress POST cannot be undone automatically). Maintain a durable ledger; never erase it, force-push state, or replay uncertain POSTs. `workflows/wordpress-post-publish-qa.yml` samples and reports public SEO drift without silently rewriting published content.

**Current status must be read from live GitHub Actions and WordPress**, not assumed from this document. Do not advertise public articles until there are new `VERIFIED, status=publish` ledger records and frontend readback.
