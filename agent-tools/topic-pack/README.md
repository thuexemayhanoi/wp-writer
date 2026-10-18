# Topic-pack tools (one package = research record + article)

A **package** is a folder `pkgs/<NT-ID>/` with `spec.json` (research and SEO fields) and `body.md` (the Vietnamese article body).
From one package the tools build the Research V2 candidate row, simulate the real article QA offline, print the probe lines for the
GitHub runner, and later assemble `posts/drafts/<ID>.md` from the CLAIMED registry row. It is an alternative to `build_research.py` /
`build_article.py` that keeps research and article consistent because both come from the same source excerpts.

```bash
export WPW_ROOT=$PWD                                   # a clone of this repository (default: git top level)
export WPW_SCRATCH=$HOME/wp-writer-scratch             # any directory outside the repo: page store + packages
mkdir -p $WPW_SCRATCH/{sources,pkgs,rows,scout}
cp agent-tools/topic-pack/*.py $WPW_SCRATCH/ && cd $WPW_SCRATCH
python pkg.py sync                                      # rows other sessions pushed on research/* branches (collision radar)
python pkg.py intent "<title>" "<keyword>" <taxonomy_key>
python pkg.py cover  NT-000401                          # nearest posts, full-text hits, intent guard
python pkg.py check  NT-000401                          # research QA + simulated article QA + number/copy audits -> "=> READY"
python pkg.py needles NT-000401 NT-000402               # url|needle lines for .github/workflows/source-reachability.yml
python pkg.py batch --number 1 NT-000401 ... NT-000410  # writes data/candidates/<WPW_RESEARCH_SESSION>-0001.jsonl (max 10)
python pkg.py assemble NT-000401 --slot W1 --session s-your-session   # after the topic is PLANNED and claimed
```

Page store (`bench.py`): `python bench.py ingest <tool-result-file>` stores every page of a spilled extraction result with its
exact text and SHA-256; `bench.source(url, excerpt, supports)` verifies that an excerpt really occurs in the stored text.
Extraction tools may drop letters (Tavily drops "â"/"ã"): `vocab.py` flags suspicious tokens in an excerpt, and the runner probe is
the final proof that the excerpt is in the live page.

Briefs for agents: `docs/agent-playbook/TOPIC-PACK-BRIEF.md` (package writer) and `SCOUT-BRIEF.md` (topic scout).
A finished example: `example/NT-000401/`.

Same hard rules as the rest of the playbook: never edit scripts/, config/, the registry, the ledger or WordPress; research only
through `scripts/research_v2.py push`; writers only through `scripts/writer-session.py`; no invented evidence.

## Working modes (added 18/10/2026)

**Existing mode** (the topic is already PLANNED and claimed): `python pkg.py brief NT-000xxx` prints a compact work order (registered
outline, scope, source requirements, internal-link candidates, and the registered source pages; long pages are cut to the paragraphs
that matter, the Honda FAQ page to its relevant Q&A pairs; PDFs may be named but never cited). The writer then adds only a six-field
`spec.json` (`existing: true`, meta_title, meta_description, direct_answer, link_rationale, internal_links) and `body.md`;
`python pkg.py check NT-000xxx` simulates the real QA (6 gates, quality/SEO) and audits numbers and copied passages;
`python pkg.py assemble NT-000xxx --slot Wn --session <label>` writes `posts/drafts/NT-000xxx.md`, then
`python scripts/writer-repair.py save --session <label> --id NT-000xxx --note "..."` runs the real QA, stores the checkpoint branch and
submits through `writer-session.py push`. Brief for the writer agent: `docs/agent-playbook/EXISTING-MODE-BRIEF.md`.

**Scouted mode** (the topic is not in the registry yet): write the research fields in `pkgs/<ID>/spec.json` (verified excerpts via
`bench.source`), screen it with `python concept.py '[["phrase"],["a","b"]]'` (which published posts already discuss the concepts; the
lexical intent guard misses semantic duplicates) and `python pkg.py intent ...`, then `python brief_local.py <ID>` prints the work order for
a writer agent (brief: `docs/agent-playbook/SCOUTED-TOPIC-BRIEF.md`). Research batches go out through
`python pkg.py batch --number N <IDs>` followed by `scripts/research_v2.py intent-check / checkpoint / check / push` from a research worktree.

Helpers: `peek.py <url> [chars]` (article body without page chrome), `stock.py` (writer-visible stock and leases, read-only),
`python bench.py ingest <tavily-result-file>` / `python bench.py ingest-parallel <parallel-fetch-result-file>` (store pages with exact
text and SHA-256; the Parallel fetch keeps the diacritics intact, Tavily drops many "â"/"ã").
