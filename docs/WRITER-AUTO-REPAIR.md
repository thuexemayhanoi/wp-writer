# WRITER AUTO REPAIR — 10 LOOPS + DURABLE GIT CHECKPOINT

This document is the single operating procedure for external Claude/W1/W2/W3 sessions in thuexemayhanoi/wp-writer. WordPress target is https://thuexemaynguyentu.com/. Read README, AGENTS, AI-START-HERE, WRITER-QUICKSTART, ARTICLE-CONTRACT and the assigned topic first.

## What actually runs

W1/W2/W3 write and repair prose INSIDE their already-active Claude sessions. Python runs unchanged real G1–G6 QA and maintains revisions. GitHub Actions checks and records; it DOES NOT call Claude, an LLM or a paid API. The single trusted Publisher creates WordPress posts and runs G7. SEO >=85/100, quality >=85/100, 1,600–5,000 real words and all independent hard gates remain compulsory. Never edit config/qa-rules.json. Network/infrastructure retries remain at 3; content-repair limit is config/writer-repair.json (10).

Failing drafts and repair journals live ONLY on private-to-the-topic Git branches named repair/SESSION/NT-XXXXXX. Example: repair/claude_A/NT-000101. Checkpoint file on that branch: data/repair-checkpoints/SESSION/NT-XXXXXX.json. These branches never trigger the WordPress publishing workflow. Do not manually edit counters or claim/QA registries. Never force push.

## Claude loop — perform, do not merely describe

1. Read the latest main and legitimate live lease; claim topics through python scripts/writer-session.py begin --slot auto --count 2 --session SESSION. Keep a stable SESSION per Claude; NEVER steal a live lease.
2. Prefer unfinished owned repair before claiming new topics. Inspect using python scripts/writer-repair.py status --session SESSION --id NT-XXXXXX. Restore a missing local draft using python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX. Recovery refuses to overwrite different existing bytes and requires a currently valid lease.
3. For a new owned draft, evaluate and save a BASELINE (0 repairs) before changing the text: python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Initial version". This independently executes the existing QA and commits source + JSON checkpoint to the isolated branch.
4. For FAIL or REVIEW, read the actual JSON errors, SEO recommendations and Gates G1–G6; consult data/qa/NT-XXXXXX.json and reports/repair-queue.json when available. Revise ONLY your owned draft and truthfully state edits: python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Corrected G2 headline and G3 evidence". The CLI checks lease and frontmatter, computes SHA-256, runs QA, counts changed draft versions and pushes the checkpoint. Identical bytes do not increment repair count.
5. Repeat up to 10 actual content revisions for this Topic ID in this same stable session. If the genuine QA verdict becomes PASS, save invokes the existing writer-session.py push route, which independently validates QA and the immutable receipt before Publisher accepts the post. No owner approval per revision.
6. If source/intent/category/facts cannot safely be fixed, hold as HOLD_FOR_REVIEW. After 10 revisions, HOLD_REPAIR_LIMIT; do not skip QA or manufacture a PASS. One held article never blocks other eligible content.
7. When there is no owned REPAIR remaining, continue writing the next legitimately claimable PLANNED topic. If none exists, research/Topic QA must create a genuinely approved topic; do not invent one or steal a claim.

## Quota stop, restart, two Claude computers

Every saved revision persists a stable session ID, writer slot, topic ID, content SHA-256, QA status/SEO/quality score, historical edits and errors, latest count and next action. A Claude session can restart from the saved version after hitting quota. Recovery from revision 5 resumes at revision 5 and the next changed draft becomes revision 6; reopening Claude does NOT reset the maximum 10 edits.

Each Topic ID has a distinct Git branch and checkpoint path. Non-fast-forward push failure means another computer advanced THAT exact branch: fetch and reconcile before retrying. Do not force push, edit another Claude's draft, edit data/state/writer-claims.json manually, or reassign leases without the existing lawful handoff. Expired leases must be reacquired via authorized tooling, not bypassed.

The tool automatically handles QA, checkpoint commits, per-topic version counting, safe restoration and submission of a genuine PASS. The Claude model must actually author every content revision while it is running. Without an external AI API/active Claude session, GitHub Actions cannot spontaneously write or repair prose after quota refresh.

## Verification

- Repair journal: python scripts/writer-repair.py status --session SESSION --id NT-XXXXXX
- Restore: python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX
- Live lease/submission: python scripts/writer-session.py confirm --session SESSION
- Current QA reports: data/qa/NT-XXXXXX.json and reports/repair-queue.json or the fresh GitHub Actions artifacts
- Published proof: data/state/publication-ledger.json phase VERIFIED, public URL and G7 receipt. Workflow success alone is not proof.
- Tests with no fake WordPress posts: python -m unittest discover -s tests -v ; python scripts/validate.py

Do not confuse infrastructure retry limit (3) with content revisions (10). The main publishing flow remains Writer -> actual QA PASS -> Publisher -> verified public WordPress.
