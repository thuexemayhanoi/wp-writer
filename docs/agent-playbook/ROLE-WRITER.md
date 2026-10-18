# ROLE: WRITER (W1–W9) — read AGENT-GUIDE.md first

Follow the [shared W1–W9 contract](../WRITER-RESEARCH-CONTRACT.md): AI App only, no AI API/new keys/approval step. One verified original source can suffice for a narrow topic; corroborate where needed. Submit each genuine PASS promptly and continue within the owner's scope; QA ≥85 and duplicate/category checks stay unchanged.
Use any of W1–W9, but never invent a slot or run a draft with a different slot than the live lease. No Claude API/Ed25519 keys are needed.

Goal: turn PLANNED topics into QA-PASS articles pushed to main via the session tool. Quality over speed; one real reader question answered well per article.

## Setup (once)
export SESSION=s-your-unique-session      # unique per Claude App session; reuse this when resuming
export WPW_SCRATCH="${WPW_SCRATCH:-$HOME/wp-writer-scratch/$SESSION}"
S="$WPW_SCRATCH"   # portable scratchpad; no machine-specific /tmp path
mkdir -p "$S"/{agents,tools,sources,notes,bodies,specs,research}
if [ -d "$S/agents/wp-writer/.git" ]; then git -C "$S/agents/wp-writer" fetch origin main; else git clone https://github.com/thuexemayhanoi/wp-writer "$S/agents/wp-writer"; fi
cd "$S/agents/wp-writer"
cp agent-tools/*.py "$S/tools/"  # helpers, not WordPress publishing code
git config user.name Claude && git config user.email noreply@anthropic.com

## Loop
1. Refresh `origin/main` in your own clone, preserving every unfinished draft/checkpoint; only reset the work branch from a clean tree. Run `python3 scripts/writer-session.py begin --slot auto --count 10 --session $SESSION`. If no claimable PLANNED topics remain, inspect `research_v2.py plan` and perform legitimate research when an order is open (ROLE-RESEARCHER.md); otherwise save progress/report the reason. Never steal/guess slots or change session to avoid REPAIR.
2. For each claimed ID, print its row: `python3 - <<'EOF'\nimport json\nfor l in open('data/topics.jsonl'):\n    r=json.loads(l)\n    if r['topic_id']=='NT-XXXXXX': print(json.dumps({k:r[k] for k in ('topic_id','title','primary_keyword','search_intent','taxonomy_key','outline','internal_link_candidates','source_requirements')},ensure_ascii=False,indent=1)); print(json.dumps(r['research'],ensure_ascii=False,indent=1)[:3500])\nEOF`
3. Read the researcher's FACTS NOTE `$S/notes/<ID>.md` (+ `$S/notes/<ID>.json` for source slugs) and, where needed, passages of the stored sources: `python3 $S/tools/srcnote.py find <slug> "<regex>" 400 8`. If the notes are missing or thin, read the cited pages yourself (guide §2). You may use ONLY facts supported by notes/sources; everything else must be generic, hedged advice. If a topic cannot be written truthfully with its sources, skip it, say so, and release it at the end.
4. Write `$S/bodies/<ID>.md` and `$S/specs/<ID>.json` using docs/ARTICLE-CONTRACT.md and build_article.py: meta_title, meta_description, link_rationale, business_claims [], sources [{url, checked_at, supports, evidence_text VERBATIM, source_sha256}]. Use verified research.external_sources where appropriate; preserve exact URL/hash/excerpt for the registered fallback. Choose contextual internal links from current published inventory. Do not depend on another machine's missing sample file.
5. Re-read the body against the real sources/notes before submission, including every number, date, name, quote and URL. Run `python3 $S/tools/build_article.py <ID> --session $SESSION --slot <actual W1..W9>`. Preserve the initial draft with `python3 scripts/writer-repair.py save --session $SESSION --id <ID> --note "Initial version"`. This reruns real QA, saves the baseline/checkpoint and automatically submits via writer-session.py push when PASS; it does not write the article for you.
6. For FAIL/REVIEW read the actual errors and follow docs/WRITER-AUTO-REPAIR.md: edit only owned body/spec, rebuild and save a changed version with an accurate note, up to 10 real content revisions. PASS requires SEO/Quality ≥85, 1600–5000 useful words and all gates. A genuine PASS reaches the existing Publisher automatically; held work stays checkpointed. Never edit QA/thresholds or fabricate evidence. Run heartbeat about hourly.
7. After every batch, run `begin --slot auto --count 10` again with the SAME session to receive the next claimable batch; it clears completed IDs after real QA/admission, without waiting for WordPress. Continue while quota and the owner's scope permit; respect any explicit article/batch limit. Prefer owned REPAIR, preserve held work/checkpoints and never abandon a submitted FAIL/REVIEW by changing session. Use `release` only when ending an eligible session, and report actual results. No per-batch approval.
Report pushed articles as authored/QA-PASS and pushed; the Publisher decides publication, so never claim an article is live until its WordPress URL exists.

## Final report (compact JSON): {"session":..., "pushed":[{"id","title","words","seo"}], "skipped":[{"id","why"}], "problems":[...]}

## AUTO-REPAIR WRITER — 10 CONTENT REVISIONS (18/10/2026)

Read docs/WRITER-AUTO-REPAIR.md (single authoritative procedure). The active Claude session first repairs owned unfinished Topic IDs; if none, it continues writing legitimately PLANNED topics. To initialize QA and a durable baseline, run python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Initial draft". After each actual edit, run the same save command with an accurate change note. QA is re-executed, SHA-256 and score/errors are stored, and the draft + checkpoint are committed to an isolated repair/SESSION/NT-XXXXXX branch. A new changed version counts as one repair, up to 10; identical bytes do not count. Use python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX after a quota interruption. Live lease ownership is always checked; no force pushes, no edited QA evidence. Genuine PASS goes through the unchanged writer-session.py push and Publisher. REAL_RISK or exhausted limit remains held, never falsely PASS. Infra/network retry stays 3, separate from content-repair limit 10. GitHub Actions never writes prose or calls an AI without an actual external model connection.
