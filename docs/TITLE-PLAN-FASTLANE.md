# Fast lane — research reuse, stable Topic IDs, ward collision reconciliation

Scope: thuexemayhanoi/wp-writer only; production site https://thuexemaynguyentu.com/.
Owner rule: SEO and Quality each >=76; keep all G1–G7 hard gates.

## 1. Choose new Excel titles without repeating research

Run from a fresh main checkout:

    python scripts/title_plan_next.py --fast-lane --limit 3

For one leaf term:

    python scripts/title_plan_next.py --fast-lane --limit 3 --term 163

The selector reads the full WordPress inventory, canonical Topic Registry and 1,482-title plan.
For every admissible proposal, it supplies a stable proposed ID:
TP-0001 -> NT-090001; TP-1482 -> NT-091482.
Those IDs are NOT reserved when printed. A researcher must submit a real Research V2
candidate to Trusted Intake; only a strict Research QA PASS promoted to PLANNED
can be claimed. Re-reading main immediately before submission and CAS intake
are mandatory for parallel Claude accounts.

If the plan row is already tied to a registry topic, skip it. If its title or
proposed slug already exists on WordPress, return WORDPRESS_IDENTITY_COLLISION
and investigate the existing page, not a duplicate create. If a proposed ID
is occupied by a different plan row, hold it for coordinator resolution.

## 2. Reuse what was actually researched

Each fast-lane row may include research_source_suggestions from an already
admitted PLANNED/PUBLISHED topic in the same taxonomy, with related title
terms. Suggestions include the unchanged original source URL, excerpt,
original checked_at, SHA-256 and parent NT ID. No fresh check date is fabricated.
Only records satisfying Research V2 HTTPS, excerpt, provenance and date rules
are suggested; legal-source suggestions over 90 days old are omitted.

The researcher confirms the earlier excerpt supports THIS new claim, records
a genuine difference_summary, scope_exclusions, current nearest WordPress
content hashes and resolved intent collisions as needed. Different topic
angles often need new evidence even when a common source appears here.
Do not blindly paste unrelated source evidence or bypass G3/G4.

Existing research packets, hashes and sources that have not changed need
not be re-extracted solely because Claude started a fresh chat. Never
pretend the author read a source they have not reviewed.

## 3. Admit, write and publish without a second manual title-approval loop

- Researcher forms a correct candidate from the selected row and source evidence.
  Use data/candidates/<research-session>-0001.jsonl plus Research V2 checkpoint.
- Validate with scripts/research_v2.py and trusted Research Intake. The
  Topic Registry receives exactly one NT ID only when PASS.
- Writer claims free PLANNED topic with
  python scripts/writer-session.py begin --slot auto --count 3 --session s-stable-session
  Keep the returned W1–W9 lease; never take another writer's lease.
- Write 1,600–5,000 useful Vietnamese words; run Writer QA. Quality and
  SEO >=76, no true duplicate or category/slug/canonical fault.
- Push a PASS manuscript. Serialized Publisher independently checks live WP,
  publishes only eligible content, and persists WordPress receipt plus G7.
- The Excel status becomes PUBLISHED_G7_PASS only from real Publisher G7.
  Checkpoint then continue; GitHub Actions never writes the article prose.

## 4. Hanoi 51-ward campaign: three collision cases

The first batch has authored drafts for:
- NT-001101, Bồ Đề -> live WordPress identity collision #4344.
- NT-001102, Cửa Nam -> live WordPress identity collision #4345.
- NT-001103, Hoàn Kiếm -> live WordPress identity collision #4346.

Those manuscripts have high SEO scores, but FAIL G4. Never lower the
duplicate gate, manufacture receipts, or publish a second competing URL.

After refreshing authenticated inventory, run:

    python scripts/hanoi_ward_progress.py

The reconciliation now records an existing published post with the exact
slug/URL as EXISTING_WORDPRESS_NEEDS_RECONCILIATION, preserving its WP ID,
URL and categories as evidence. It does not mark a new G7 article or
increment published_new_articles. The coordinator must check the existing
post's real category (Term 182), URL/canonical, title, factual quality and
indexability. Where it already meets the ward intent, reuse and improve
that existing URL through an independent approved SEO workflow; do not
overwrite it from a duplicate draft. Preserve manuscript/research hashes
and flag the redundant draft as HOLD for editorial follow-up.

Continue other wards through the normal Research/Writer/Publisher process,
three at a time if desired. Only credit factory posts after authentic G7.

## 5. Production safety and rollback

The fast lane does not call WordPress, edit manifest/lease/ledger,
weaken QA, or change old URLs/categories. Existing topic source records
are used read-only. Merging this patch changes code/docs/tests only.
If any CI test fails, keep the branch unmerged. Revert its single merge
commit if regression is later confirmed. No database/WordPress restore needed.
