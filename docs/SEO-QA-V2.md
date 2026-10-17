# SEO Quality Gate V2 — Website chính Nguyễn Tú

**Site:** https://thuexemaynguyentu.com/ — repository thuexemayhanoi/wp-writer.

**Mandatory rule:** Each new article needs **SEO QA ≥85/100**, quality score ≥75/100, and **PASS all six independent gates** before it is eligible for WordPress publication. This is the repository's own deterministic pre-publication QA, **not** an actual Yoast score, a Google ranking, or proof of indexing.

## 100-point SEO rubric

| Pre-publication check | Weight |
|---|---:|
| SEO title relevant to approved primary search intent | 15 |
| Meta description answers the same intent | 15 |
| First paragraph addresses intended query | 15 |
| Substantive direct answer near the beginning | 10 |
| Useful H2 structure with topical coverage | 15 |
| Contextual internal links to real, public related articles | 15 |
| Descriptive internal anchor text | 5 |
| Approved canonical and slug identity | 10 |
| **Total** | **100** |

The SEO title, meta and lead get credit for meaningful overlap with the approved primary topic, without forcing an exact-match keyword phrase. Internal links get 10 points for one verified contextual target and a further five for two distinct targets. Headings are assessed for descriptive specificity and topic coverage.

The authoritative configuration is config/qa-rules.json: version 2, seo_min 85, seo_score_version intent-aware-onpage-v2. Per-article QA receipts include seo_score, seo_min_required, seo_checks, and seo_recommendations. **84/100 = FAIL. 85/100 = eligible only if all other gates also PASS.**

## Six gates still mandatory

- **G1 Topic identity:** approved topic ID, keyword, intent, slug and canonical.
- **G2 Useful on-page content:** 1,600–5,000 words, meaningful headings, SEO metadata, useful direct answer, no repetitive padding or keyword stuffing. SEO score must reach 85.
- **G3 Factual/editorial trust:** documented claims, owner-verified prices/policies and current official legal sources; fabricated customer experience or inaccurate rental facts block publication.
- **G4 Intent collision prevention:** no competing against existing service/ranking pages with duplicate intent or near-duplicate content.
- **G5 Real internal-link graph:** verified public URLs, topical anchor text, rational links supporting silo/pillar pages without homepage spam.
- **G6 WordPress-safe publication:** exact parent/child category path, WordPress inventory, lease/receipt hash and protected older URLs.

**No numerical score overrides any FAIL/REVIEW, including wrong category, fabricated claims, SEO/URL collision, noindex or broken links.**

## Outbound citations — relevant external HTTPS links allowed

- **Research remains evidence-driven:** Writers can research manufacturers, official government/legal materials, scientific/technical publications and reputable reporting. Verified evidence still belongs in article YAML `sources` / research records and must pass G3 factual QA independently.
- **No blanket external-domain ban:** Public article Markdown may link to relevant third-party sources (e.g. Honda, Yamaha, VinFast, government documents, research papers or news sites) when they genuinely help the reader verify a claim. External links do not earn SEO points merely for existing; no forced outbound-link quota.
- **G5 link safety remains:** Outbound links must use HTTPS without embedded credentials or unusual ports; known redirect-wrapper query parameters cannot conceal other destinations. Invalid, unsafe or malformed URLs fail as `UNSAFE_OUTBOUND_URL`. Internal links still need verified published URLs, natural anchor text and no broken/draft targets.
- **Editorial discipline:** Do not link to irrelevant advertisements, deceptive pages or low-quality sources. Respect image usage rights and attribution, and do not confuse the source used for factual verification with an endorsement.
- **Existing WordPress posts are unchanged.** The rule applies to new drafts and publisher live QA; no bulk rewrite of legacy posts.


## Research freedom and source checks (18 October 2026)

- External AI may research **any relevant public website**: competing motorbike rental providers, manufacturers, bike/e-bike/EV brands, maps, public transport, other vehicle modes, Hanoi and Vietnam tourism, official rules, science, technical documents and news. This grants research access, **not** permission to copy competitors or fabricate experience.
- G3 no longer requires a narrow manufacturer/government hostname list for general evidence. Legal claims still require an authoritative official source; genuine sources must have a dated, specific excerpt and a SHA-256 research snapshot. One high-quality original source may support a narrow research topic; two hosts are advice, not a universal hard gate.
- Source last-checked metadata may be up to 365 days old for general subjects; *legal* source check is limited to 90 days, and changing prices/laws/real-time information should be reconfirmed when used. Research source date is not a news publication date.
- If the GitHub runner cannot reach a URL due to a transient HTTP 403/429/5xx or network error, article QA may only rely on an **exact source URL, snapshot hash and excerpt already registered in this topic's research**. It records `live_checked: false` and `verification_method: research_snapshot_fallback`. A 404 or readable but mismatched excerpt is still REVIEW. This is documented provenance, **not** a claimed live verification.
- Public internal-link targets and orphan checks remain; the originally suggested candidate URL list and prose `link_rationale` are guidance, not an arbitrary REVIEW barrier when an appropriate published article is already linked.
- Do not link out just to satisfy an imagined Google ranking factor. Link externally only when it helps users inspect important details. Never copy competitor text, images or trademark claims without permission.

## Website-primary-site policy

- Do not turn all articles into rental advertisements. Information and safety articles must answer their real search intent, not force commercial calls to action.
- No compulsory images, FAQs, keyword-density tricks or CTA phrases. Relevant high-quality photos with attribution and alt text can improve a specific article but empty decorative content cannot earn a passing SEO score.
- Respect the business facts in data/business-facts.json. Do not make unsupported fee, insurance, service-hour or deposit claims.
- Category mismatch still routes to draft only when approved and eligible; high SEO scoring is never an excuse to publish into the wrong parent/child category.
- Publisher reevaluates QA with fresh WordPress state and checked sources/links just before posting, rather than trusting a writer's self-reported score.
- After public WordPress publication, post-publish QA independently checks actual Yoast title/description, canonical, index/follow, permalink and content. It does not replace the 85-point prepublication gate.
- Never change existing published URLs or bulk-edit already published posts due to new QA V2 scoring. New drafts failing the threshold return to Writer for repair.

## Workflow and limitation

External AI W1/W2/W3 → GitHub article intake → QA six gates + SEO V2 → PASS → Publisher live QA → WordPress category/SEO verification → published receipt. Below 85 or another gate FAIL/REVIEW → Writer REPAIR, not public WordPress.

Production has been ON since 2026-10-17 by owner order (`production_enabled=true`): a QA-PASS article is published by the Publisher right after the main-push QA run. `acceptance_passed` and `security_controls_verified` stay `false` (never performed) and no longer gate publishing. The SEO V2 rubric and the 85-point gate are unchanged.

No Excel: topic source is data/topics.jsonl, categories and full WordPress ancestry come from data/taxonomy.json plus WordPress REST.
