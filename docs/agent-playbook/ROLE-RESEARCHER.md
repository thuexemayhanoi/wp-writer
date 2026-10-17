# ROLE: RESEARCHER (Research V2) — read AGENT-GUIDE.md first
Goal: produce source-backed, genuinely distinct Topic Registry rows so writers have PLANNED topics. Quality over count: a topic that cannot be backed by two real sources, or that duplicates existing content, must be dropped.

## Setup (once)
S=/tmp/claude-0/-home-user-wp-writer/03e9c76e-0a72-5677-99b0-7955386200b3/scratchpad
git clone https://github.com/thuexemayhanoi/wp-writer $S/agents/<name>/wp-writer && cd $S/agents/<name>/wp-writer
git config user.name Claude && git config user.email noreply@anthropic.com
git switch -c research/<session> origin/main        # <session> given in your prompt, e.g. seodev-r1
(Read AGENTS.md, docs/RESEARCH-V2-GLOBAL-ADAPTATION.md, data/taxonomy.json leaf list, and skim `python3 -c "import json;[print(json.loads(l)['topic_id'],json.loads(l)['title']) for l in open('data/topics.jsonl')]"` to learn what already exists.)

## One batch = exactly 10 topics
1. Before each batch: `git fetch origin main && git merge --no-edit origin/main` (refresh the registry/inventory) .
2. Pick ideas inside your THEME (given in your prompt). Prefer sub-clusters of 3–5 questions anchored on 2–3 rich official pages (so one page read supports several distinct reader questions). Demand signal: `mcp__Ubersuggest__google_suggestions` (country "vn", language "vi", keywords list ≤10) returns real Google autocomplete — use it to phrase titles people actually search; no credits needed. Do NOT use data from other sites' projects.
3. For every idea run `similar.py` (see guide). Drop/reshape ideas whose nearest title ≥0.6 or whose intent is already answered by a published post or registry topic.
4. Read two sources per topic on different hostnames (guide §2), store them with srcnote (slug prefix = your session, e.g. r1-honda-abs), pick topic-specific VERBATIM evidence sentences (check them). One source per topic must be article-citable (guide §3).
5. Write a specs JSON for the 10 topics (copy the shape of `$S/research/batch1_part1.json`: topic_id, origin_id "SEODEV-<SESSION>-NNNN", title, primary_keyword, search_intent, intent_key, taxonomy_key, outline (5–6 items), difference_summary (concrete vs the nearest existing content), usefulness, scope_exclusions, links (2–3 exact published URLs), source_requirements, extra_review_ids (inventory ids of posts that touch the topic), sources[{slug, supports, evidence_text}]).
   Also write for each topic a FACTS NOTE for the writer at `$S/notes/<NT-ID>.md`: 10–16 bullets, each "fact in Vietnamese — [source slug] — verbatim snippet ≤200 chars" covering everything an article needs (definitions, steps, official wording, caveats, dates). Writers will write ONLY from these notes + the stored sources, so be complete and accurate; flag uncertain/conflicting facts explicitly.
6. `python3 $S/tools/build_research.py <specs.json> <out.jsonl> --session <session>` → must print `ALL PASS`. Fix everything it flags (never weaken evidence).
7. `mkdir -p data/candidates && cp <out.jsonl> data/candidates/<session>-000N.jsonl` (N = 1,2,…) then `python3 scripts/research_v2.py checkpoint --branch research/<session>` (add `--final` only when the last batch has <10 topics) and `python3 scripts/research_v2.py check --branch research/<session>`.
8. `git add data/candidates data/research/checkpoints && git commit -m "research: <session> batch N (<10 titles theme>)" -m "Co-Authored-By: Claude <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01VqMnTUZtpja4rBRZSVx9vp"` then `python3 scripts/research_v2.py push --branch research/<session>` (must print state SAVED).
9. Verify intake (≈30–90 s): `git fetch origin main` then print status of your IDs from `git show origin/main:data/topics.jsonl` (PLANNED = accepted). If a topic shows RESEARCH/REJECTED or the batch is missing, read `git show origin/main:reports/topic-qa.json` for its reasons (and `data/state/research-intake-ledger.json`). Never edit an accepted/pushed batch; fix by submitting a NEW batch with NEW IDs (and `git merge origin/main` first).
10. Repeat for the next batch (file -0002.jsonl …).
Stop after the number of batches in your prompt, or earlier if you cannot find enough genuinely distinct, well-sourced topics (then submit what you have as a `--final` batch and say so honestly).

## Final report (compact JSON): {"session":..., "batches":[{"file":..., "ids":[...], "status_on_main":{...}}], "topics":[{"id","title","taxonomy","sources":[hosts]}], "problems":[...] }
