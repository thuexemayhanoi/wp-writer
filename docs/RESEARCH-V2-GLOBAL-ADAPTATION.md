# Research V2 — Global-style ten-topic research, QA, recovery and automatic refill

Repo: thuexemayhanoi/wp-writer → https://thuexemaynguyentu.com/.

Unlike /global, this is the Nguyen Tu MAIN commercial WordPress site. Helpful informational, travel and rental intent may be used only if distinct from existing protected service/landing pages. No Excel, no model API, no automatic LLM, no WordPress production change.

## Pipeline

    6-hourly topical gap + Google News RSS discovery (unverified leads)
        → external AI researcher reads source webpages + current WordPress inventory
        → 10 original candidate topics, one JSON object per line, on own research branch
        → checkpoint saves SHA-256 of every research batch and session
        → read-only Topic Research QA validates source, intent, collision and taxonomy
        → successful PUSH triggers Trusted Research Intake on main code
        → verify same green SHA, independent gate, immutable batch receipt, CAS commit
        → Topic Registry PLANNED → available to W1/W2/W3 Writers
        → Writer QA six gates + SEO >=85 → Publisher (currently dry_run)

Both new workflows are isolated from WordPress credentials. AI research needs an ACTIVE Claude/Mistral/ChatGPT/Gemini session; GitHub only handles ingestion, quality checks, checkpoints and state transitions. A successful workflow is not itself proof of facts or Google indexing.

## Research session — ten topics at a time

1. Read AGENTS.md, docs/AI-START-HERE.md, docs/SEO-QA-V2.md, data/topics.jsonl, data/taxonomy.json, data/existing-content-inventory.json and data/business-facts.json. Use the CLI to see the next ten unverified hints:

    python scripts/research_v2.py hints --limit 10

2. Establish a stable lowercase session branch (unique per AI session):

    git fetch origin main
    git switch -c research/claude-20261017a origin/main

3. Create exactly ten genuinely distinct researched Topic Registry objects under:

    data/candidates/claude-20261017a-0001.jsonl

   Name the next batch 0002, 0003 etc. Each row needs a unique unused NT-XXXXXX ID; original origin_id (NTD-... if from the automated discovery queue); title, primary_keyword, intent_key, search_intent, taxonomy_key, proposed_slug, exact main WordPress canonical_target, a five-section outline, and a substantial research object. The research object must include reviewer, difference_summary, usefulness, scope_exclusions, reviewed_existing_ids and reviewed_content_hashes from current inventory, and external_sources.

4. Research source contract: external_sources must include at least TWO different direct HTTPS source URLs from independent hosts, each checked_at (ISO date within 365 days), specific supports claim (20+ characters), an actual evidence_text excerpt (20+ characters), and a genuine 64-hex source_sha256 snapshot of a source actually read. RSS headlines are **not evidence**. Source metadata is statically checked, but the QA gate cannot guarantee the source excerpt is truthful without independent web verification; external AI must actually read and check the page.

5. Save a durable checkpoint and push only your own files:

    python scripts/research_v2.py checkpoint --branch research/claude-20261017a
    python scripts/research_v2.py check --branch research/claude-20261017a
    python scripts/research_v2.py push --branch research/claude-20261017a

   If a final session contains 1–9 remaining real topics, explicitly use the final option:

    python scripts/research_v2.py checkpoint --branch research/claude-20261017a --final

   After a FINAL batch do not append another batch to this session. A normal batch must have ten real topics; never fill with fake rows to reach ten. Save on GitHub after each ten, then continue the next batch.

6. Read the corresponding External Topic Research QA run and Trusted Research Intake run. On a green PUSH, the main workflow rechecks exact green branch SHA, source URLs, categories, original inventory, full intent collisions and session checkpoint hash, then imports the truly PASS topics into data/topics.jsonl as PLANNED and appends an immutable intake ledger. It never executes researcher branch code, never force-pushes and never writes to WordPress.

## Recover after lost quota, session or environment

    python scripts/research_v2.py resume --branch research/claude-20261017a
    python scripts/research_v2.py resume --branch research/claude-20261017a --apply
    python scripts/research_v2.py check --branch research/claude-20261017a

The remote research branch/checkpoint is the source of truth. A dirty clone or divergent local branch is rejected rather than overwritten. Already ingested batch files are recognized by exact SHA-256 and never submitted twice. A candidate batch edited after acceptance is refused. If a push fails, the CLI does not claim SAVED.

## Boundaries for the commercial WordPress main site

- Do not reuse SEO intents already owned by existing rental landing pages and category hubs, regardless of different title wording. Existing indexed pages/products/URLs/SEO and WordPress taxonomy are immutable.
- Compare the nearest published posts from the main site's current inventory, prove the differences with full-content hash review and justify how the article serves a unique reader question.
- Keep genuine commercial topics, but do not turn supporting content into a copy of the primary rental landing page. Do not import /global restrictions banning commercial intent.
- Verify all prices, deposit and delivery claims against data/business-facts.json; legal sources must be authoritative and current; fake first-hand experience is forbidden.
- Approved canonical capacity is currently 1,000; research proposal ceiling is 10,000 and is not permission to publish that many.
- The discovery scheduler emits up to 20 research leads/run and caps unresearched backlog at 300. They remain AWAITING_AI_RESEARCH until an external AI actually researches them.
- Topic QA PASS is separate from Writer article QA. Every newly written article must meet SEO V2 >=85, Quality >=75 and all six gates before WordPress publication can be considered.
- Production remains dry_run and security/acceptance flags remain untouched by this upgrade.

## Files

| File | Purpose |
|---|---|
| scripts/research_v2.py | hints, checkpoint, check, verified push, safe resume |
| scripts/research_intake.py | trusted-main, QA-verified research ingestion and CAS |
| .github/workflows/topic-research-qa.yml | read-only QA on research branches |
| .github/workflows/topic-research-intake.yml | automatic intake after successful research branch PUSH QA |
| data/research/auto/batch-*.jsonl | raw discovery ideas, never factual citations |
| data/candidates/SESSION-0001.jsonl | actual externally researched topic submissions |
| data/research/checkpoints/SESSION.json | batch SHA-256, session and order |
| data/state/research-intake-ledger.json | immutable imported batch receipts |
| data/topics.jsonl | canonical Topic Registry and Writer claim queue |
| data/taxonomy.json | WordPress parent/child taxonomy authority |
