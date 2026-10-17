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
