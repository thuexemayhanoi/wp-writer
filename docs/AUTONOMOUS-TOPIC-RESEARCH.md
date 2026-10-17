# Auto Topic Discovery → External AI Research → QA → Writers

Repository: `thuexemayhanoi/wp-writer`. WordPress site: `https://thuexemaynguyentu.com`. This is NOT `wp-aiwriter` and does not import the Nguyễn Hà Excel matrix.


Research scope is deliberately broad: competing rental businesses, vehicle brands and models, bicycles/e-bikes, motorbikes, all practical transport modes, Hanoi/Vietnam travel, destinations, culture, regulations, battery/maintenance and technical research. External AI may browse any relevant public HTTPS source, not just an allowlist. Use competitor websites for comparison/content-gap discovery, **not** for copying articles or inventing the owner's business data. One independently researched original source can justify a narrowly scoped new idea; corroborate changing or high-risk facts. The autonomous RSS scanner remains a lead generator rather than an LLM researcher.

## What genuinely runs by itself

Every six hours (or manual workflow_dispatch) `Universal Topic Discovery`:

1. Counts **claimable PLANNED** topics, excluding accepted submissions, verified WordPress posts and active Writer leases.
2. When claimable falls below the refill trigger (`trigger_below_ready` = `50` in `config/refill-policy.json`; see [self-replenishing topics](SELF-REPLENISHING-TOPICS.md)), selects neglected areas from **35 topic domains**, taxonomies and curated Vietnamese subject phrases in `config/topic-discovery.json`.
3. Optionally fetches public RSS discovery headlines over HTTPS (currently Google News RSS). These are *discovery leads only*, **not** verified primary sources, fact-checks, search-volume evidence, or permission to copy text.
4. Generates a balanced, deduplicated batch of **at most 20 research proposals** with source requirements, semantic intent hints, cluster/category hints and five human-verifiable research questions.
5. Writes immutable proposal IDs `NTD-...` to `data/research/auto/batch-NNNNNN.jsonl`, durable CAS ledger `data/state/topic-discovery-ledger.json` and `reports/topic-discovery.json`.
6. Stops when 300 proposals are awaiting research, or when the subject pool is exhausted. Never fabricates `PLANNED` topics simply to raise counters.

This queue may grow toward the **10,000 research-proposal ceiling**, but the *separate* canonical topic admission limit remains `approved_capacity=1,000` until owner approves more. Increasing a research-proposal count **does not increase published articles**.

The discovery workflow uses standard Python, public RSS, and the existing GitHub Actions token for CAS state commits. **It has no LLM, no AI API key, no direct WordPress writes, and never auto-publishes.** GitHub Actions cannot honestly be called an AI researcher without an AI model service. All public headlines and generated topic wording require independent review before article writing.

## The external AI handoff (Claude / ChatGPT / Gemini / Mistral / Work)

An external AI researcher with access to actual web sources should pick one unique `NTD-` proposal, research it and create a reviewed `data/candidates/<batch-name>.jsonl` entry. It must:

- Re-evaluate the title, keyword and **unique search intent**; avoid unrelated variants, boilerplate and thin articles.
- Search source documents and capture verifiable URLs, publication/update dates, concrete supported claims and evidence. A news feed headline alone is never legal or technical evidence.
- Compare all relevant existing published WordPress pages (and near-match old articles) by actual content, canonical and intent; record reviewed existing WordPress IDs and exact `content_hash` values. If a page is edited after you recorded its hash, Topic QA reports `reviewed full-content evidence stale or missing: <id>=<current hash>`: re-read the page, then keep the old hash and add the new one as a list (`"2572": ["<old>", "<new>"]`). A hash that matches no recorded version stays stale.
- Choose the correct `taxonomy_key` from `data/taxonomy.json`. Do not create an empty category or modify the existing URL structure.
- Complete a distinct useful outline (at least five sections) and the `research` contract with `reviewer`, `difference_summary`, `usefulness`, `scope_exclusions`, `reviewed_existing_ids` and `reviewed_content_hashes`.
- Use an unused `NT-XXXXXX` topic ID **within current approved capacity**, and set `origin_id` equal to the exact `NTD-` proposal ID; this is how the automatic discovery backlog recognizes completed research.
- Submit it through existing `topic-refill.yml` (or `python scripts/topic-factory.py --import-candidates data/candidates/<file>.jsonl` in an authorized environment). Only real Topic QA `PASS` yields a claimable `PLANNED` topic.

### Example research candidate fields (illustrative structure, not evidence)

```json
{
  "topic_id": "NT-000081",
  "origin_id": "NTD-<exact recorded proposal id>",
  "title": "<original research-backed title>",
  "primary_keyword": "<researched primary keyword>",
  "search_intent": "informational",
  "intent_key": "<unique semantic intent>",
  "taxonomy_key": "<verified taxonomy key>",
  "proposed_slug": "<unique approved slug>",
  "canonical_target": "https://thuexemaynguyentu.com/<unique approved slug>/",
  "outline": ["<section 1>", "<section 2>", "<section 3>", "<section 4>", "<section 5>"],
  "research": {
    "reviewer": "<researcher session>",
    "difference_summary": "<concrete gap versus old URLs>",
    "usefulness": "<who benefits and why>",
    "scope_exclusions": ["<what the article does not cover>"],
    "reviewed_existing_ids": [],
    "reviewed_content_hashes": {},
    "external_sources": [
      {"url": "https://<verified public source>", "checked_at": "YYYY-MM-DD", "supports": "<specific factual claim>"}
    ]
  }
}
```

This is **not** a ready-to-import candidate; actual existing-content comparisons and non-empty evidence are normally required by Topic QA.

## Failure modes and safe recovery

- `QUEUE_HEALTHY`: enough claimable topics; no need to add ideas.
- `DISCOVERED`: at least one new, deduplicated proposal recorded to the research queue.
- `RESEARCH_BACKLOG_FULL`: external researchers must consume existing queue, rather than generating thousands of unreviewed titles.
- `NEEDS_EXTERNAL_RESEARCH`: curated subject pool exhausted; external AI must research and add new meaningful subject seeds.
- `RESEARCH_CEILING_REACHED`: stop at 10,000 research proposals until owner revises plan.
- RSS unavailable: report an explicit error, continue local *topical-gap suggestions* but do not assert sources were checked.
- A CAS conflict: fail, re-fetch the latest ledger and retry via next scheduled workflow. Never force-push, overwrite a research batch, reset a lease or create WordPress posts.
- After 1,000 topics are admitted, research may continue but **new canonical topic admission requires explicit increase of `approved_capacity`**, separate from WordPress Production owner approval.

## Useful links

[Research batches](../data/research/auto/) · [Discovery workflow](../.github/workflows/topic-discovery.yml) · [Topic Factory](../scripts/topic_factory.py) · [Production activation](ACTIVATION.md).

**Quality principle:** 10,000 generated ideas are not equivalent to 10,000 useful articles. Only researched, non-cannibalizing topics accepted by Topic QA become available to the three external Writers.

## Research V2 đã bổ sung: 10 topic/QA/checkpoint/auto-intake

Trước đây bộ quét chỉ tạo NTD research briefs. Nay AI ngoài có thể dùng [Research V2 runbook](RESEARCH-V2-GLOBAL-ADAPTATION.md) để nghiên cứu 10 chủ đề/lượt, checkpoint SHA-256 và push trên research/<session>. Research QA phải đọc source metadata, phát hiện trùng intent/URL, xác nhận WordPress inventory và danh mục. Khi QA xanh trên PUSH, Trusted Research Intake tự nhận nội dung bằng mã main được bảo vệ và đưa Topic Registry các bài PASS thành PLANNED. Điều này KHÔNG có nghĩa GitHub Actions tự chạy AI hoặc đã bật Production; lịch quét 6 giờ vẫn chỉ tìm ý tưởng chưa xác minh.

