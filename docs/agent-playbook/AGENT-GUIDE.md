# AGENT GUIDE — wp-writer content factory (Nguyễn Tú, https://thuexemaynguyentu.com)

You are one worker in a multi-agent run. READ THIS FILE FULLY, then `AGENTS.md`, `docs/AI-START-HERE.md`, `docs/ARTICLE-CONTRACT.md`, `docs/SEO-QA-V2.md` and `data/business-facts.json` in your own clone. Repo scope: ONLY https://github.com/thuexemayhanoi/wp-writer. Language of articles/topics: Vietnamese.

## 0. Hard safety rules (never break)
- Work ONLY in your own clone (see your role prompt). Never edit scripts/, tests/, config/, .github/, data/taxonomy.json, data/business-facts.json, data/state/*, reports/*, data/topics.jsonl, data/existing-content-inventory.json. Never use WordPress credentials/REST. Never run `gh`. Never `git push --force`; never push to `main` except through `scripts/writer-session.py` (it does a CAS commit); research only pushes to your `research/<session>` branch through `scripts/research_v2.py push`.
- PRODUCTION IS ON (owner order 2026-10-17, config/production-policy.json): the owner's simple flow is W1/W2/W3 write -> QA (>=85, duplicate check, category) -> Publisher -> public WordPress. A QA-PASS draft that reaches `main` is published to https://thuexemaynguyentu.com by the GitHub Publisher within about 2-3 minutes, with NO coordinator hold; that is intended, and it is irreversible, so you must verify every fact against the stored sources before you push. RESEARCH agents push only to `research/<session>` (that never publishes). Do not touch config/production-policy.json.
- Never fabricate: no invented facts, prices, quotes, URLs, first-hand experience ("tôi đã thử..."), reviews, shop policies, awards. If you did not read it in a real page, do not claim it. Never write business facts other than those in data/business-facts.json; never mention no-deposit / free delivery / 24/7 offers.
- Time-sensitive facts (prices, schedules, rules) only when an official page you actually read states them; always give the read date (today = 2026-10-17 unless `date` says otherwise) and tell readers to re-check.
- Do not paste whole web pages into your context. Read big pages through saved files + python (see §1).

## 1. Shared tools (all in the scratchpad)
S=/tmp/claude-0/-home-user-wp-writer/03e9c76e-0a72-5677-99b0-7955386200b3/scratchpad
- `$S/tools/similar.py "<title or idea>" "kw1" "kw2"` → nearest published posts + ALL registry topics (any status) + full-text keyword hits. Run it for every idea.
- `$S/tools/srcnote.py save <saved_json_path> <slug> "<start marker>" "<end marker>"` store the article-body region of a page you read (when the Nimble result was auto-saved to a file); `savetext <slug> "<url>"` (stdin) for small inline results (paste only the article-body passages you actually read); `find <slug> "<regex>" [chars] [max]` print verbatim passages; `check <slug> "<sentence>"` must print VERBATIM before you use a sentence as evidence. Stores go to `$S/sources/<slug>.txt/.json` (url, checked_at, source_sha256) — shared between all agents; use your own slug prefix.
- `$S/tools/build_research.py <specs.json> <out.jsonl> --session <S>` builds registry rows from compact specs, verifies evidence is VERBATIM, computes nearest-5 inventory review hashes, and runs the same Research QA locally (prints ALL PASS or reasons). Also writes `$S/notes/<ID>.json`.
- `$S/tools/build_article.py <NT-ID> --session <S> --slot <W?>` builds `posts/drafts/<ID>.md` from `$S/bodies/<ID>.md` (markdown body; FIRST PARAGRAPH = direct answer) + `$S/specs/<ID>.json`, computes body_sha256, runs the real QA and prints status, word_count, seo points, errors. `--prefly <jsonl>` QA-tests a body before the topic is PLANNED (writes to scratchpad, not the repo).
- Exemplars to imitate (style, depth, structure): `$S/bodies/NT-000101.md … NT-000107.md` with specs in `$S/specs/`, research specs in `$S/research/batch1_part*.json`.

## 2. How to read pages
- Find URLs: `WebSearch` (mode standard; `allowed_domains` to target hosts). Read a page: `mcp__Nimble__nimble_extract` (load via ToolSearch "select:mcp__Nimble__nimble_extract,WebSearch"): url, output_format="plain_text", locale="vi", country="VN", context = 15–25 words, third person, no "I/we/you". Reuse the `conversation_id` it returns. WebFetch and Firecrawl do NOT work here; the shell cannot reach the web except GitHub.
- Results over ~25K tokens are auto-saved to a JSON file (the tool prints its path; field `content`) → run `srcnote.py save` on that path with markers around the article body. Smaller results come inline: copy only the body passages you need into `srcnote.py savetext`.
- Always check which host serves the page: if the URL redirects to another host, the QA's live fetch refuses cross-origin redirects (example: hanoimetro.net.vn → metrohanoi.vn). Pages that are PDFs or JS-only cannot be cited in articles.

## 3. QA allowlist for ARTICLE sources (frontmatter `sources` must be on these hosts, https)
honda.com.vn, yamaha-motor.com.vn, vinfastauto.com, vme.org.vn, vietnam.travel, vietnamtourism.gov.vn, ANY *.gov.vn host, (hanoimetro.net.vn is allowlisted but redirects → useless). Legal-only hosts: vbpl.vn, vanban.chinhphu.vn, moj.gov.vn, csgt.vn, mps.gov.vn. News sites (hanoimoi.vn, vnexpress…) are fine as a SECOND research source but can never be cited in an article's frontmatter. Each source needs `evidence_text` (verbatim sentence ≥4 words found in the static page text), `supports`, `checked_at` (≤30 days), `source_sha256` (from srcnote). Digits anywhere in an article body require ≥1 cited source (else REVIEW). Words luật/nghị định/mức phạt/bằng lái/giấy phép/quy định pháp in a body require a legal-host source → avoid those topics/words unless you have one.

## 4. Taxonomy leaf keys allowed for new topics (WordPress category must already exist)
rental-procedures, rental-costs, rental-50cc, ebikes, battery-charging, electric-tech, electric-maintenance, electric-transition, engine-care, road-safety, driving-licence, hanoi-travel, vietnam-travel, food-culture, trip-planning, urban-mobility, green-travel, reviews, legal. NOT: troubleshooting, uncategorized, parents (blog, sharing, destinations, maintenance, electric, rental-guide).

## 5. Topic QA facts you must respect
- One reader question per topic; titles are Vietnamese, specific, ≤ ~95 chars, pattern "Chủ đề: câu hỏi/hướng làm" (see registry). primary_keyword = the part of the title before the colon (shortish, 4–9 words) — the article's meta title/description/opening paragraph must repeat ≥70% of its (stop-word-free) tokens.
- Never duplicate: similar.py title similarity must stay < 0.6 against everything, AND the intent must be different from every published post and registry topic (read the nearest titles). No pages that duplicate commercial rental landing pages (price/location/"thuê xe máy + quận"); no keyword-variant doorway topics.
- `intent_key` must be unique (kebab-case, descriptive). Each batch = exactly 10 topics (unless final). IDs: use only your assigned range, ascending.
- Every topic needs ≥2 sources on DIFFERENT hostnames that you actually read, each with a topic-specific VERBATIM evidence sentence; at least ONE source per topic must be article-citable (§3) and statically fetchable.
- Internal-link candidates (`links` in the spec) must be 2–3 exact published URLs from data/existing-content-inventory.json that are topically related (not just any page).

## 6. ARTICLE QA facts (what the real gate enforces — every item bit someone already)
- 1,600–5,000 "words" as counted by qa.py (Vietnamese syllables count separately): aim 1,800–3,000. No H1; ≥4 H2 (each ≥4 words, distinct); at least one H2 that contains ≥3 of the primary-keyword tokens; end with `## Nguồn tham khảo` (links to the sources you read).
- First paragraph (before the first blank line) = direct answer, ≥18 words, repeating the primary-keyword tokens, and it is copied verbatim into frontmatter `direct_answer` by build_article.py.
- ≥2 DISTINCT internal links `[anchor ≥3 words](https://thuexemaynguyentu.com/…/)` to published URLs from the inventory, at least one from the topic's `internal_link_candidates`. Do NOT link to unpublished NT drafts/siblings. No homepage links.
- meta_title 15–70 chars; meta_description 100–180 chars; both must contain most primary-keyword tokens.
- No raw HTML/`<…>`, no "data:", "TODO/TBD/placeholder", no phone numbers, no repeated paragraph; no sentence repeated ≥3 times (NB: the splitter cuts at every "." so a price like "250.000 đồng" repeated in 3 places trips "Repeated sentence" — rephrase).
- Do not claim shop services; link to money pages only naturally (max 1–2) and with no prices/deposit numbers (they must match business-facts if present).
- SEO score must reach ≥85 (target 100), quality ≥75, status PASS. Fix by editing the body/spec, never by touching QA.
- Style: practical, specific, hedged for time-sensitive facts, no padding, no keyword stuffing, no marketing superlatives. Explain how to verify; give checklists; separate what the source says from your own advice.
