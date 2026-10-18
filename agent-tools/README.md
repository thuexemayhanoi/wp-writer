# Agent tools (coordinator-owned helpers for external AI sessions)

Not production code and not run by any workflow. An external AI session (researcher or writer) that works from a fresh
container restores its scratchpad from here, then follows `docs/agent-playbook/`.

```bash
export WPW_SCRATCH=$HOME/wp-writer-scratch            # any directory outside the repo
mkdir -p $WPW_SCRATCH/{tools,sources,notes,bodies,specs,agents,research}
cp agent-tools/*.py $WPW_SCRATCH/tools/
cp docs/agent-playbook/*.md $WPW_SCRATCH/ && cp docs/agent-playbook/HOST-CENSUS.md $WPW_SCRATCH/sources/
```

The playbooks use `S=$WPW_SCRATCH`. On multiple computers, use a stable unique session label and set `WPW_SCRATCH` to a writable, **session-specific** directory. No fixed `/tmp/claude-*` path is required.

**Writer pool:** W1–W9. Use `python scripts/writer-session.py begin --slot auto --count 10 --session "$SESSION"` to receive the actual slot and Topic IDs; `build_article.py` requires `--slot Wn` from that active lease, rather than silently assigning W1. These tools do not call an AI API, change QA or publish to WordPress.
Tools: `similar.py` (nearest published posts and registry topics), `srcnote.py` (store/check the page text a source note was
taken from), `build_research.py` (specs -> registry rows + local Research QA), `build_article.py` (body + spec -> draft + real QA),
`body.py` (helper), `factory_status.py` (read-only status for the per-wave report: capacity, stages, ready stock, order, intake, `research/*` branches not yet ingested, category deficits).

Hard rules that still apply: never edit scripts/, tests/, config/, data/topics.jsonl, data/taxonomy.json, the inventory, the
ledger or WordPress; research pushes only through `scripts/research_v2.py push`; writers push only through
`scripts/writer-session.py`; never invent evidence.
