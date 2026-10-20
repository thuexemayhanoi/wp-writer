# Brief: write ONE article for a topic that the coordinator has already researched and scouted (spec.json holds the research fields)

The site thuexemaynguyentu.com is the blog of a Hanoi motorbike-rental business. Readers: tourists, expats, students, new riders in Vietnam, plus owners of scooters/underbones. The coordinator has already scouted the topic: `pkgs/<TOPIC_ID>/spec.json` already holds the research fields (title, keywords, outline, difference summary, scope exclusions, source requirements, verified source excerpts, candidate internal links). Your job: the Vietnamese article body plus five writer fields in that same spec.json. Everything else (frontmatter, sources section, research record, QA wiring, claiming, pushing) is done by the coordinator.

    SCR=$WPW_SCRATCH   # scratch directory that holds the page store, pkgs/ and these tools

You edit/write exactly two files per topic and nothing else (no git, nothing under /home/user/wp-writer, no network fetching, no web search):

    $SCR/pkgs/<TOPIC_ID>/spec.json      (already exists: ADD five fields, change nothing else)
    $SCR/pkgs/<TOPIC_ID>/body.md        (you write it)

## Step 1 — read the work order (it contains everything you may use)

    cd $SCR && python brief_local.py <TOPIC_ID>

It prints the title, keywords, outline, difference summary, scope exclusions, source requirements, the internal-link candidates (published URLs) and the text of every source page (navigation lines removed; for the long law page only the relevant articles). These pages are the ONLY sources you may cite. For one topic that is ~35–55K characters: read it once, completely. Then skim the style exemplar once: `$SCR/pkgs/NT-000401/body.md` (ignore its spec.json format; yours is smaller, see below).

Known artifact of the page store: the extraction tool DROPPED the letters "â" and "ã" (and sometimes similar) in many words: "người dn" = "người dân", "gy ra" = "gây ra", "tm" = "tâm", "đy" = "đây". Mentally restore them; never copy a damaged word into your article.

## Step 2 — add these five fields to the existing spec.json (keep every other field exactly as it is)

    {
      ...existing scout fields untouched...,
      "meta_title": "...",          // 15-70 characters, contains the primary keyword verbatim
      "meta_description": "...",    // 100-180 characters, contains the primary keyword verbatim, a real summary for a search result
      "direct_answer": "...",       // >= 18 words, contains the primary keyword verbatim, answers the reader's question in 1-2 sentences; it becomes the START of body.md, verbatim
      "link_rationale": "...",      // one paragraph: why each internal link helps the reader at that point of the article
      "internal_links": ["https://thuexemaynguyentu.com/...", "..."]   // replace the candidate list by the 3-4 PUBLISHED URLs you really use (candidates in the work order, or inventory_links.tsv); each must also appear in body.md as an in-sentence link
    }

## Step 3 — body.md (Vietnamese Markdown, for a real reader, not a keyword counter)

- No H1. 6-8 H2 sections (each H2 >= 4 words) that follow the REGISTERED OUTLINE in order and meaning (you may tighten the wording). The first paragraph begins with `direct_answer` verbatim, then adds the scope and the dates of the sources read (when a source is a news article: outlet + date; Honda FAQ answers: their own update date; Yamaha pages: their date).
- Counted length: the QA counts syllable tokens, so a normal 1,500-word Vietnamese article = ~3,000 counted words. Target 2,600-3,800 (hard limits 1,600-5,000). `check` prints the number.
- Structure that works: short explanation paragraphs, 1-2 tables (e.g. situation -> what to do / what the source says -> what it means), ordered checklists, a short "Tóm tắt nhanh" at the end. Add a rental-aware angle only where natural (e.g. a rider who borrowed/rented a bike unfamiliar to them), never a specific shop, price, phone number or address.
- Distinguish clearly "what the source says" (name the outlet/author and the page date) from "gợi ý của bài viết" (your own reasoning). If sources differ (different seconds, different braking advice...), say so openly and tell the reader to use the actual conditions and their own vehicle's manual.
- Internal links: 3-4 in total, spread over the article, each inside a sentence where the linked post really helps; anchor text >= 3 descriptive words; never "xem thêm", "tại đây", "click".
- Do NOT write a "Nguồn tham khảo" section and no frontmatter: the coordinator appends the sources section.
- Never repeat the same sentence or paragraph; vary the wording; do not stuff the keyword (use it naturally ~5-8 times in the whole body).

## Integrity rules (they override length)

1. Every factual statement (numbers, seconds, distances, dates, procedures, named features, what an institution says) must be supported by one of the registered pages, OR be explicitly framed as the article's own advice ("gợi ý của bài viết", "bài viết nhận định"). Never invent statistics, intervals, prices, distances, test results, first-hand experience ("tôi đã thử..."), customer reviews, or anything about the rental shop.
2. Paraphrase. The checker flags any run of >= 16 consecutive syllables copied from a source page. Short quoted terms are fine.
3. Legal topics (NT-000801, NT-000802): the words luật / nghị định / giấy phép / bằng lái are the subject, and they are allowed because an official government page (xaydungchinhsach.chinhphu.vn, mps.gov.vn) is cited; for every other topic they are forbidden in the body. Never state fines or penalty amounts ("mức phạt" stays out), never invent article/clause numbers: quote only the article and clause numbers visible in the work order, always attribute legal statements to the page and its date, add one sentence that the article summarises the pages read on 18/10/2026, is not legal advice, and that the reader should check the current text with the competent authority. No phone numbers, raw HTML, images, H1.
4. Safety: never teach bypassing locks/immobilisers, risky stunts, disassembling brakes/electrics. Prefer "xem sách hướng dẫn / hỏi cửa hàng, đại lý ủy quyền". No absolute guarantees ("100% an toàn"), no medical advice beyond what a cited page attributes to a named authority, no brand promotion, no "best product" claims.
5. A source written for drivers in general (car/truck/bus) must be reported as such; a source about one model must not be generalised to every motorbike or brand. Honda FAQ answers are dated 2019-2021 and often model-specific.
6. The work order's `source_requirements` and `scope_exclusions` are binding. A PDF listed in the work order may be named in the text as "tài liệu huấn luyện của Honda Việt Nam" and its content used; never link it.
7. If the stored pages cannot support part of the registered outline, narrow that section honestly (say what the pages do not cover) instead of padding or inventing. Quality over length.

## Step 4 — verify (mandatory)

    cd $SCR && python pkg.py check <TOPIC_ID>        # repeat until the last line is "=> READY" (it also validates the research record)

READY means: simulated article QA PASS (6 gates, quality >= 75, SEO >= 85; aim for 100), no "!" problem lines, and no "?" audit lines (numbers that appear in none of the registered pages; passages copied from them) unless you can justify each. A "?" number that is really your own illustration or comes from the PDF must be reframed as clearly yours or named as from the Honda training document; otherwise remove it.

## Final reply (max 120 words)

Topic id; counted words; SEO score; sources actually used; any claim you could not verify and removed; any place where sources conflict. No other prose.
