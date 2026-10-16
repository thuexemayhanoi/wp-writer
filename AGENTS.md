# Universal writer contract — Nguyễn Tú

**Autonomous research queue:** read [docs/AUTONOMOUS-TOPIC-RESEARCH.md](docs/AUTONOMOUS-TOPIC-RESEARCH.md) and `data/research/auto/batch-*.jsonl`. The scheduled no-key scanner creates `NTD-` proposals, **not** AI-validated `PLANNED` topics. A researching AI must independently find and verify sources, compare old WordPress content, submit a `data/candidates/*.jsonl` batch with its exact `origin_id`, and pass Topic QA. Never invent researcher citations, historical content hashes or turn an RSS headline into legal/price evidence.

**Operational reference:** read [Factory Operations V2](docs/FACTORY-OPERATIONS-V2.md) for read-only watchdog, non-green BLOCKED requests, refill that requires new researched PLANNED topics, and public post-SEO QA. Never confuse Actions SUCCESS with verified WordPress publication.

Only this repository and https://thuexemaynguyentu.com are in scope. Read the README, docs/WRITER-QUICKSTART.md, data/business-facts.json and your topic before writing. Never import the Nguyễn Hà matrix.

* External AI providers share the same W1/W2/W3 contract. No AI model, AI API key or writer is run in Actions.
* Supporting articles: **1,600–5,000 useful Vietnamese words**, excluding frontmatter, markup, keyword lists, references and navigation. This requirement supersedes the older README word minimum.
* Use only PLANNED topics, claim via scripts/writer-session.py with a stable public session label. A live lease cannot be stolen. Resume your REPAIR first. Do not edit another writer's draft. Do not invent facts or first-hand experience.
* Writer-editable inputs: owned posts/drafts/NT-XXXXXX.md and data/candidates/*.jsonl. Registry writes only through the CAS session tool. Coordinator-only: topic/taxonomy/facts/config/code/workflows/QA/checkpoints/ledger.
* Commit/push owned drafts promptly using the session tool. Follow Actions results and repair the exact ID. Do not declare publication from a push alone.
* All legacy WordPress posts/pages/products, canonical/slug, existing category ancestry, themes, plugins, sitemap, Trash and smoke-test #3861 are immutable. No update/delete/redirect/noindex operations on legacy content.
* One publisher, batch maximum 2, write-ahead remote ledger before POST, reconcile unknown outcomes. Never clear a pending intent or retry an uncertain POST blindly.
* Production remains disabled until the owner approves activation and acceptance evidence is complete. Do not enable production, change secrets or modify website settings while building the factory.
* Machine QA is a technical screen, not semantic/factual proof. Missing evidence stays REVIEW. Do not lower thresholds or fabricate research evidence to fill 1,000 rows.
* Protected CODEOWNERS paths require owner review. CODEOWNERS alone is not an access control. Production requires enforced branch/path controls and a protected environment verified by the owner.
* Keep checkpoints factual. Distinguish candidate, PLANNED, authored, READY, WordPress draft, verified public, and indexed.
