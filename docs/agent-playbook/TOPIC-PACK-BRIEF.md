# Topic package brief (research record + Vietnamese article in one package)

Used with `agent-tools/topic-pack/` (see its README). It complements `AGENT-GUIDE.md`; where the owner policy of 18 Oct 2026 (open sources, contextual external links) differs from an older line below, the policy wins. One writer agent builds ONE package.

# Brief: build ONE "topic package" (research record + Vietnamese article) for thuexemaynguyentu.com

The site is the blog of a Hanoi motorbike-rental business. Readers: tourists, expats, students and new riders in Vietnam, plus owners of scooters/underbones. You produce ONE package for ONE topic. The package is two files in

    SCR=$WPW_SCRATCH          # the scratch directory you restored (see agent-tools/topic-pack/README.md)
    $SCR/pkgs/<TOPIC_ID>/spec.json      research + SEO fields
    $SCR/pkgs/<TOPIC_ID>/body.md        the Vietnamese article body (Markdown, no frontmatter)

Do NOT touch anything else: no git, nothing under /home/user/wp-writer, no network fetching, no new web-search/extract calls. All source pages you may cite are already read into a local store.

## Integrity rules (they override everything, including length)

1. Every factual statement (numbers, dates, procedures, named models/features, what a brand says) must be supported by a cited page in the local store, OR be explicitly framed as the article's own advice/reasoning ("gợi ý của bài viết", "bài viết nhận định", "đây là cách sắp xếp của bài"). Never invent statistics, intervals, prices, distances, test results, first-hand experience ("tôi đã thử…"), customer reviews, or anything about the rental shop (no prices, phone numbers, addresses, shop name).
2. Always separate "what the source says" (name the brand and the page date / FAQ update date) from your own advice. When sources disagree (different km intervals, different run-in advice…), say so openly and tell the reader to follow the manual of their own vehicle.
3. Honda FAQ answers are dated 2019–2021 and many are model-specific (SH, PCX, Air Blade, Lead, Vision…). Yamaha pages carry their own dates (2025–2026). State model/date scope; never generalise a model-specific claim to every motorbike or every brand.
4. Safety: never teach bypassing locks/immobilisers, short-circuiting, disassembling electrics or brakes, or any risky stunt. Prefer "check the manual / ask the authorised shop".
5. Paraphrase. The checker flags any run of >=16 consecutive syllables copied from a cited page. Short quoted terms are fine.
6. Do not use these words anywhere in the body (the QA treats them as legal claims that need a government legal source): luật, nghị định, mức phạt, bằng lái, giấy phép, quy định pháp. Also no phone numbers, no raw HTML, no images, no H1.
7. No absolute guarantees ("100% an toàn"), no medical/financial advice, no brand promotion, no "best product" claims.
8. If the stored pages cannot support the topic properly, stop and say so in your final reply instead of padding. Quality over length.

## Reading the local source store

    cd $SCR
    python - <<'EOF'
    import bench
    print(bench.body('https://yamaha-motor.com.vn/tin-tuc/<slug>'))      # Yamaha news article without navigation
    for i,(q,a) in enumerate(bench.faq_items()): print(i, q)             # Honda FAQ: 85 Q&A pairs (index i)
    q,a = bench.faq_items()[55]; print(q, a)                              # one Honda answer
    print(bench.grep('https://www.honda.com.vn/cau-hoi-thuong-gap', r'rô đa'))   # context snippets for a regex
    print(bench.load(url)['text'][:3000])                                 # raw stored text
    EOF

Known artifact: the extraction tool DROPPED the letters "â" and "ã" (and sometimes similar) in many words: "người dn" = "người dân", "gy ra" = "gây ra", "m thanh" = "âm thanh", "nguyên nhn" = "nguyên nhân", "tm" = "tâm", "đy" = "đây", "lu" may be "lâu", "đu" may be "đầu/đâu". Mentally restore them when you read. When you choose an `excerpt` for spec.json, pick a sentence that contains NO damaged word (the checker flags suspicious tokens; real exceptions go in `allow_tokens`).
The stored pages are in $SCR/sources/*.json (list them with `ls`; each has url/title/text). Only cite URLs that exist there.

## Deliverable 1: spec.json

Read the finished exemplar first: `agent-tools/topic-pack/example/NT-000401/` (spec.json and body.md; also in `$SCR/pkgs/` if you copied it) (style, depth, tone, how sources are attributed). Fields (all required except secondary_keywords, allow_tokens):

- topic_id, title, primary_keyword (a natural search phrase that appears verbatim in the title, meta_title, meta_description and the first paragraph), secondary_keywords[], search_intent ("Hướng dẫn" / "Giải thích" …), intent_key (unique kebab-case English-ish slug of the reader question), taxonomy_key
- outline[]: 6–8 H2-level sections (they must match the H2s of body.md in order and meaning)
- difference_summary: a concrete paragraph: what this article covers, and exactly what the existing site posts already say about the topic (cite their WP ids, e.g. "#2517"), and why this is a different reader question. Base it on `python pkg.py cover <TOPIC_ID>` (nearest posts + full-text phrase hits + intent guard). Do not claim "no post mentions it" unless the report shows 0 hits for the phrases you searched.
- usefulness (who benefits and how), scope_exclusions[] (4+ honest exclusions), source_requirements[] (3 short rules the writer followed)
- sources[]: each {url, excerpt, supports, allow_tokens?}. `excerpt` = a verbatim span (>=6 words, the checker verifies it exists in the stored text, whitespace/accent-insensitive) with no damaged words. `supports` (>=20 chars) = what the page establishes, with date/model scope. At least TWO different hosts overall (for these topics: www.honda.com.vn and yamaha-motor.com.vn). The same URL may appear several times: the first entry per URL becomes the research evidence, all of them go into the article's frontmatter.
- internal_links[]: 3–4 PUBLISHED site URLs genuinely related (pick from `python pkg.py cover` nearest posts and `$SCR/inventory_links.tsv`; the checker verifies they are published). Anchors in the body must be descriptive (>=3 words), in-sentence, never "xem thêm / tại đây".
- meta_title (15–70 chars, contains the primary keyword), meta_description (100–180 chars, contains the primary keyword), direct_answer (>=18 words, contains the primary keyword; it must appear VERBATIM at the start of body.md), link_rationale (one paragraph: why each internal link is relevant to the reader at that point)

## Deliverable 2: body.md

Vietnamese Markdown, written for a real reader, not for a keyword counter.
- No H1. 6–8 H2 sections (each H2 >=4 words), the first paragraph begins with spec.direct_answer verbatim and then adds the scope + date of the sources read (like the exemplar).
- Counted length: the QA counts syllable tokens, so a normal 1,500-word Vietnamese article ≈ 3,000 counted words. Target 2,400–3,800 counted words (hard limits 1,600–5,000). The checker prints the number.
- Use: short explanations, one or two tables (e.g. symptom → what to check), ordered checklists, "what the source says" vs "gợi ý của bài viết", honest limits, and a short "Tóm tắt nhanh" at the end. Add a rental-aware angle only where natural (e.g. "nếu xe là xe thuê, hãy hỏi cửa hàng…") and never mention a specific shop.
- Never repeat the same sentence/paragraph; vary the wording; don't stuff the keyword.
- Internal links: 3–4, spread over the article, each in a sentence where the linked post really helps.

## Verify (mandatory)

    cd $SCR && python pkg.py cover <TOPIC_ID>     # before writing
    cd $SCR && python pkg.py check <TOPIC_ID>     # until it prints "=> READY"

READY means: Research QA PASS, simulated article QA PASS (6 gates, quality >=75, SEO >=85 — aim for 100), no "!" problem lines, and no "?" audit lines (numbers that appear in none of the cited pages; passages copied from them) unless you can justify each. If `?` numbers remain, either source them (add the page) or remove/reframe them as clearly your own illustration.

## Final reply (max 180 words)

Topic id and title; counted words; SEO score; the sources used; caveats: conflicts between sources, claims you could not verify and removed, anything a human reviewer should double-check before publication. No other prose.
