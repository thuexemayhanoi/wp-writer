# RESEARCH ADDENDUM 2 (wave of 2026-10-17 evening) — read after AGENT-GUIDE.md and ROLE-RESEARCHER.md; it overrides them where they differ

## 0. Newest facts (read first)
- A self-replenishing controller now exists on main (docs/SELF-REPLENISHING-TOPICS.md). Run `python3 scripts/research_v2.py plan` in your clone: it prints the open order (RF-0001), the per-category quotas and `next_batch_categories` (how many topics of each taxonomy key the next 10 should cover). Treat it as a tie-breaker for choosing topics inside your cluster; do not force a topic into a category it does not fit.
- Every candidate is compared with ALL published WordPress items and ALL live registry topics by `scripts/intent_guard.py`. BEFORE checkpointing run `python3 scripts/research_v2.py intent-check --file data/candidates/<session>-000N.jsonl`. FAIL = change title/scope until it is gone (it cannot be waived). REVIEW = either change the topic, or resolve it with a written reason of at least 40 characters: spec field `resolved_intent_collisions: {"WP2521": "reason"}` and, for a WordPress page, `extra_review_ids: [2521]` so its CURRENT content hash is recorded (build_research.py passes both fields through). Never write a reason you did not verify by reading the page.
- Only a Research QA PASS row becomes PLANNED. Failing rows are registered as RESEARCH/REJECTED and still consume registry capacity (hard limit), so check carefully BEFORE pushing; a passing neighbour is no longer blocked by a failing one.
- Article policy since 18 Oct: articles MAY link contextually to external HTTPS sources; research is unchanged (>=2 independent hosts you really read, one article-citable and runner-readable).
- Thresholds are in config/refill-policy.json (reserve target: 100 ready topics).

Goal of this wave: the owner wants a reserve of >=100 researched PLANNED topics that no writer has used. Quality over count: drop any topic that cannot be backed by sources a writer can actually cite.

## 1. What changed since the last wave
- The repo inventory was refreshed from WordPress (authenticated) at 13:50 UTC: 184 items, including the 10 newest factory posts (#3947-#3956) and the legacy pages the owner edited. ALWAYS `git fetch origin main && git merge --no-edit origin/main` before choosing ideas and again before building a batch (build_research.py hashes the nearest-5 inventory items; stale hashes make live QA stop at REVIEW).
- Published posts and every registry topic are your duplicate wall: run `similar.py` for every idea; the nearest title must stay < 0.6 AND the intent must differ (read the nearest titles). Several clusters already have published posts (E10 fuel, helmets, flooded roads, AQI, brakes CBS/ABS, coolant, long storage, parking fees) — do not repeat them.
- Research batches are accepted per topic (see section 0). Still fix everything build_research.py and intent-check flag before you push; never weaken evidence.

## 2. SOURCE READABILITY IS NOW PART OF RESEARCH (the writers' articles are re-read live by the Publisher from GitHub's runner)
- Read `$S/sources/HOST-CENSUS.md` first. Article-citable AND readable hosts: honda.com.vn, yamaha-motor.com.vn, vietnam.travel, vietnamtourism.gov.vn, mae.gov.vn, vea.mae.gov.vn, sonnmt.hanoi.gov.vn, mst.gov.vn, vov.gov.vn, mps.gov.vn, vanban.chinhphu.vn, vbpl.vn. vinfastauto.com, vme.org.vn, moj.gov.vn, csgt.vn, hanoi.gov.vn, tcvn.gov.vn, csgt.bocongan.gov.vn, cem.gov.vn and PDFs are NOT usable for articles (they may serve only as an extra research source).
- Every topic needs at least ONE article-citable source whose exact URL you have PROBED from the runner with a needle (a verbatim fragment of your evidence sentence, >=4 words). Probe recipe (one dispatch for the whole batch; ~1-3 min):
  1. `mcp__github__actions_run_trigger` {method:"run_workflow", owner:"thuexemayhanoi", repo:"wp-writer", workflow_id:"source-reachability.yml", ref:"main", inputs:{"urls":"https://host/path|needle text\nhttps://host2/path2|needle2"}}   (load the tool with ToolSearch "select:mcp__github__actions_run_trigger,mcp__github__actions_list,mcp__github__get_job_logs" first)
  2. wait ~60 s, then `mcp__github__actions_list` {method:"list_workflow_runs", owner, repo, resource_id:"source-reachability.yml", perPage:1} -> newest run id (its created_at must be after your dispatch; if status is still in_progress wait and repeat)
  3. `mcp__github__actions_list` {method:"list_workflow_jobs", owner, repo, resource_id:"<run id>", perPage:1} -> job id
  4. `mcp__github__get_job_logs` {owner, repo, job_id, return_content:true, tail_lines:80} -> one `OK`/`FAIL {...}` line per URL plus `SOURCE_PROBE: n/m readable with the excerpt present`. The job turns red whenever any URL fails; that is normal. NEVER pass perPage larger than 1-3 or call list_workflow_runs without resource_id (the output is huge).
  A line is good only when it says `'ok': True` and `'needle_found': True`. FAIL/needle_found False: replace that source or evidence sentence (JS-only text, split words such as "PM 2.5", or a different static text) and probe again.
- Append every URL result to `$S/sources/HOST-CENSUS.md` (date | URL | OK/FAIL | note) so the other agents learn from it.
- The second source (different host) must be a real page you read; it may be a news page or a non-readable official page. It only has to carry a verbatim evidence sentence.

## 3. Rules that bit earlier waves
- Time-sensitive/legal/price claims only when an official page you read says so (legal words in an article require a legal-host source: mps.gov.vn, vanban.chinhphu.vn, vbpl.vn). If you cannot read the exact legal document page from the runner, drop the topic or keep the legal part out of its scope (state it in scope_exclusions).
- No shop prices/deposit/policy claims; no topic that duplicates the commercial rental landing pages (price/district keywords); no "tôi đã thử" experience; no invented numbers.
- primary_keyword = the part of the title before the colon (4-9 words); title ≤ 95 chars; one reader question per topic; intent_key unique kebab-case.
- ID range: use ONLY your assigned range, ascending; never reuse an ID, even for a dropped idea. origin_id "SEODEV-<SESSION>-NNNN" (e.g. SEODEV-R5-0001).
- Do not touch scripts/, tests/, config/, data/topics.jsonl, data/taxonomy.json, data/existing-content-inventory.json, reports/, .github/ . Push ONLY through `python3 scripts/research_v2.py push --branch research/<session>`.
- Do not write articles. Your deliverable is accepted PLANNED topics + a facts note per topic at `$S/notes/<NT-ID>.md` (10-16 bullets "fact — [source slug] — verbatim snippet ≤200 chars", flag conflicts) + stored sources (srcnote). Writers will use only those.

## 4. Flow per batch (compact)
merge origin/main -> pick 10 ideas in your cluster (Ubersuggest google_suggestions for real phrasing) -> similar.py each -> read 2 sources/topic (Nimble) -> srcnote store + `check` evidence -> ONE runner probe of all article-citable URLs -> fix/replace failures -> write specs JSON -> build_research.py (ALL PASS) -> copy to data/candidates/<session>-000N.jsonl -> research_v2.py intent-check (no FAIL, REVIEW resolved or reshaped) -> research_v2.py checkpoint + check -> commit (trailers as in ROLE-RESEARCHER.md) -> research_v2.py push (state SAVED) -> wait ~90 s -> `git fetch origin main` and print the status of your IDs from `git show origin/main:data/topics.jsonl` (PLANNED = accepted; otherwise read `git show origin/main:reports/topic-qa.json` for the reasons).
A batch with fewer than 10 survivors is allowed (`checkpoint --final`). If your first batch ends early and you still have comfortable budget, do a second batch (file -0002) with new IDs from your range.

## 5. Final report (compact JSON, no prose around it)
{"session":..,"cluster":..,"batches":[{"file":..,"commit":..,"ids":[..],"planned_on_main":[..],"not_accepted":{id:reason}}],"topics":[{"id","title","taxonomy","article_citable_source":"url (probe OK)","second_source_host"}],"dropped":[{"idea","why"}],"problems":[..]}
