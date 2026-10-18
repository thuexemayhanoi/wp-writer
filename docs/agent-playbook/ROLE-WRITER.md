# ROLE: WRITER (W1–W9) — read AGENT-GUIDE.md first
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
1. `git fetch origin main && git switch -C work origin/main` (clean working tree: preserve all unfinished drafts and repair checkpoints; never delete untracked owned drafts) then `python3 scripts/writer-session.py begin --slot auto --count 10 --session $SESSION`. If it says no claimable PLANNED topic, wait (python3 -c "import time;time.sleep(100)" with Bash timeout ≥150000) and retry up to 8 times; if still none, stop and report. Never steal/guess slots; never run `begin` with another session label.
2. For each claimed ID, print its row: `python3 - <<'EOF'\nimport json\nfor l in open('data/topics.jsonl'):\n    r=json.loads(l)\n    if r['topic_id']=='NT-XXXXXX': print(json.dumps({k:r[k] for k in ('topic_id','title','primary_keyword','search_intent','taxonomy_key','outline','internal_link_candidates','source_requirements')},ensure_ascii=False,indent=1)); print(json.dumps(r['research'],ensure_ascii=False,indent=1)[:3500])\nEOF`
3. Read the researcher's FACTS NOTE `$S/notes/<ID>.md` (+ `$S/notes/<ID>.json` for source slugs) and, where needed, passages of the stored sources: `python3 $S/tools/srcnote.py find <slug> "<regex>" 400 8`. If the notes are missing or thin, read the cited pages yourself (guide §2). You may use ONLY facts supported by notes/sources; everything else must be generic, hedged advice. If a topic cannot be written truthfully with its sources, skip it, say so, and release it at the end.
4. Write `$S/bodies/<ID>.md` and `$S/specs/<ID>.json` (shape = `$S/specs/NT-000101.json`: meta_title, meta_description, link_rationale, business_claims [], sources [{url, checked_at, supports, evidence_text VERBATIM (srcnote check), source_sha256 from $S/sources/<slug>.json}] — take them from the topic's research.external_sources (same url, sha256 and excerpt, so the research-snapshot fallback applies if the runner cannot reach the page); any safe HTTPS host is allowed, see guide §3). Choose internal links from the topic's internal_link_candidates plus other related published URLs (exact URLs from data/existing-content-inventory.json, status publish).
5. `python3 $S/tools/build_article.py <ID> --session $SESSION --slot <W1..W9 from your actual lease>` → must print status PASS, seo_score ≥85 (aim 100), word_count 1600–5000. Fix problems by editing body/spec and rebuilding. Never edit QA, thresholds, or other people's drafts.
6. After a draft prints PASS from build_article.py: re-read it once against the facts note and the stored sources (every number, date, name, quote, URL), fix anything unsupported, rebuild. Then run `python3 scripts/writer-session.py check --ids <ids> --session $SESSION` and, when it passes, `python3 scripts/writer-session.py push --ids <ids> --session $SESSION` (CAS commit to main; if it reports a state conflict it retries, otherwise `git fetch origin main` and run it again). Owner order 2026-10-17: a QA-PASS article on main is published to WordPress immediately by the Publisher. That is the intended simple flow; there is no coordinator hold, so never push a draft whose facts you could not verify. Run `heartbeat` about hourly.
7. When all your claimed IDs are pushed (or skipped), run `release` (it succeeds only when all submissions passed) and report. Do not run `begin` again unless your prompt allows another batch.
Report pushed articles as authored/QA-PASS and pushed; the Publisher decides publication, so never claim an article is live until its WordPress URL exists.

## Final report (compact JSON): {"session":..., "pushed":[{"id","title","words","seo"}], "skipped":[{"id","why"}], "problems":[...]}

## AUTO-REPAIR WRITER — 10 CONTENT REVISIONS (18/10/2026)

Read docs/WRITER-AUTO-REPAIR.md (single authoritative procedure). The active Claude session first repairs owned unfinished Topic IDs; if none, it continues writing legitimately PLANNED topics. To initialize QA and a durable baseline, run python scripts/writer-repair.py save --session SESSION --id NT-XXXXXX --note "Initial draft". After each actual edit, run the same save command with an accurate change note. QA is re-executed, SHA-256 and score/errors are stored, and the draft + checkpoint are committed to an isolated repair/SESSION/NT-XXXXXX branch. A new changed version counts as one repair, up to 10; identical bytes do not count. Use python scripts/writer-repair.py resume --session SESSION --id NT-XXXXXX after a quota interruption. Live lease ownership is always checked; no force pushes, no edited QA evidence. Genuine PASS goes through the unchanged writer-session.py push and Publisher. REAL_RISK or exhausted limit remains held, never falsely PASS. Infra/network retry stays 3, separate from content-repair limit 10. GitHub Actions never writes prose or calls an AI without an actual external model connection.
