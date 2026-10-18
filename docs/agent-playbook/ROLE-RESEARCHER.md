# ROLE: RESEARCHER (Research V2) — read AGENT-GUIDE.md first
Goal: produce source-backed, genuinely distinct Topic Registry rows so writers have PLANNED topics. Follow the [shared W1–W9 contract](../WRITER-RESEARCH-CONTRACT.md): one verified original source can suffice for a narrow topic; corroborate high-risk/changing claims. Insufficient evidence or duplicate intent stays held/dropped. No AI API, new writer keys or per-batch approval.

## Setup (once)
export SESSION=s-your-unique-research-session      # stable label; reuse when resuming
export WPW_SCRATCH="${WPW_SCRATCH:-$HOME/wp-writer-scratch/$SESSION}"
S="$WPW_SCRATCH"
mkdir -p "$S"/{agents,tools,sources,notes,bodies,specs,research}
git clone https://github.com/thuexemayhanoi/wp-writer $S/agents/<name>/wp-writer && cd $S/agents/<name>/wp-writer
git config user.name Claude && git config user.email noreply@anthropic.com
git switch -c research/<session> origin/main        # <session> given in your prompt, e.g. seodev-r1
(Read AGENTS.md, docs/RESEARCH-V2-GLOBAL-ADAPTATION.md, data/taxonomy.json leaf list, and skim `python3 -c "import json;[print(json.loads(l)['topic_id'],json.loads(l)['title']) for l in open('data/topics.jsonl')]"` to learn what already exists.)

## One batch = exactly 10 topics
1. Before each batch: `git fetch origin main && git merge --no-edit origin/main` (refresh the registry/inventory) .
2. Pick ideas inside your THEME and current research order. Prefer sub-clusters of distinct questions supported by rich original pages; reuse a page only where it supports that question. Search suggestions from an available tool are optional demand signals, never a required plugin/API key. Do NOT use data from other sites' projects.
3. For every idea run `similar.py` (see guide). Drop/reshape ideas whose nearest title ≥0.6 or whose intent is already answered by a published post or registry topic.
4. Read source evidence under the shared contract (guide §2–3): one verified original source may suffice for a narrow topic; add corroboration where needed. Store it with srcnote (session slug prefix), pick topic-specific VERBATIM excerpts and check them. Do not invent evidence, require two hosts universally or reject a real source merely because the runner has a transient network failure.
5. Write a specs JSON for the 10 topics (copy the shape of `$S/research/batch1_part1.json`: topic_id, origin_id "SEODEV-<SESSION>-NNNN", title, primary_keyword, search_intent, intent_key, taxonomy_key, outline (5–6 items), difference_summary (concrete vs the nearest existing content), usefulness, scope_exclusions, links (2–3 exact published URLs), source_requirements, extra_review_ids (inventory ids of posts that touch the topic), sources[{slug, supports, evidence_text}]).
   Also write for each topic a FACTS NOTE for the writer at `$S/notes/<NT-ID>.md`: 10–16 bullets, each "fact in Vietnamese — [source slug] — verbatim snippet ≤200 chars" covering everything an article needs (definitions, steps, official wording, caveats, dates). Writers will write ONLY from these notes + the stored sources, so be complete and accurate; flag uncertain/conflicting facts explicitly.
6. `python3 $S/tools/build_research.py <specs.json> <out.jsonl> --session <session>` → must print `ALL PASS`. Fix everything it flags (never weaken evidence).
7. `mkdir -p data/candidates && cp <out.jsonl> data/candidates/<session>-000N.jsonl` (N = 1,2,…) then `python3 scripts/research_v2.py checkpoint --branch research/<session>` (add `--final` only when the last batch has <10 topics) and `python3 scripts/research_v2.py check --branch research/<session>`.
8. `git add data/candidates data/research/checkpoints && git commit -m "research: <session> batch N (<10 titles theme>)" -m "Co-Authored-By: Claude <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01VqMnTUZtpja4rBRZSVx9vp"` then `python3 scripts/research_v2.py push --branch research/<session>` (must print state SAVED).
9. Verify intake (≈30–90 s): `git fetch origin main` then print status of your IDs from `git show origin/main:data/topics.jsonl` (PLANNED = accepted). If a topic shows RESEARCH/REJECTED or the batch is missing, read `git show origin/main:reports/topic-qa.json` for its reasons (and `data/state/research-intake-ledger.json`). Never edit an accepted/pushed batch; fix by submitting a NEW batch with NEW IDs (and `git merge origin/main` first).
10. Repeat for the next batch (file -0002.jsonl …).
Continue the next batch while the owner's scope, open research order, registry capacity, real sources and session quota permit. Stop at an explicit batch limit in the prompt or when no legitimate work remains; save progress. A `--final` batch closes this research session: do not append another batch to it. No manual approval is needed between ordinary batches.

## Final report (compact JSON): {"session":..., "batches":[{"file":..., "ids":[...], "status_on_main":{...}}], "topics":[{"id","title","taxonomy","sources":[hosts]}], "problems":[...] }
