# Scout brief (find topics and read their sources into the local store)

Used with `agent-tools/topic-pack/`. A scout proposes topics; it never writes articles.


Context: thuexemaynguyentu.com is the blog of a Hanoi motorbike-rental business (readers: tourists, expats, students, new riders; also owners of scooters and e-bikes). We are about to write ~100 distinct informational articles (Vietnamese, ~1,300–2,000 words each). Each article must be grounded in pages from AUTHORITATIVE, ALLOWLISTED hosts that were really read. You are a scout for ONE source family: your job is to (1) discover pages, (2) read them into the local store, (3) propose distinct topics that those pages can support. You do NOT write articles.

    SCR=$WPW_SCRATCH          # the scratch directory you restored (see agent-tools/topic-pack/README.md)

## Hard constraints

1. Source hosts (owner policy of 18 Oct 2026: the old host allowlist is gone): ANY safe public HTTPS page that you really read may be cited, but prefer authority: government (*.gov.vn), tourism boards (vietnam.travel, vietnamtourism.gov.vn), manufacturers, established news (vnexpress.net, thanhnien.vn, tuoitre.vn, vov.gov.vn, baochinhphu.vn), reputable references (Wikipedia is acceptable for background facts but never the only source of a topic). Competitor rental sites only to understand content gaps, never as a source of facts for us and never copied. Legal/price/regulation facts need an official page and a page date; avoid such topics unless the page is readable and recent.
   Hosts the GitHub runner can read (probed): www.honda.com.vn, yamaha-motor.com.vn, vietnam.travel, vietnamtourism.gov.vn (deep pages only), vbpl.vn, vanban.chinhphu.vn, mps.gov.vn, mae.gov.vn, vea.mae.gov.vn, sonnmt.hanoi.gov.vn, mst.gov.vn, vov.gov.vn, chinhphu.vn, baochinhphu.vn, suckhoedoisong.vn, vnexpress.net, thanhnien.vn. NOT readable from the runner (403/timeouts/redirect): vinfastauto.com, vme.org.vn, moj.gov.vn, csgt.vn, hanoi.gov.vn, mt.gov.vn, sogtvt.hanoi.gov.vn, hanoimetro.net.vn (redirects cross-origin to metrohanoi.vn), PDFs, JavaScript-only pages. For a not-readable host the article QA falls back to the research snapshot (allowed, but flagged "not live-checked"), so give EVERY topic at least ONE source on a runner-readable host and a second source (any host) whenever the claim is a number, safety-critical, contested or time-sensitive.
2. Prefer server-rendered static HTML (the publisher fetches pages with plain HTTP, no JavaScript, 20 s timeout, and looks for a quoted sentence in the visible text; a readable page that lacks the excerpt makes the article HELD). Pages whose text only appears after JavaScript, PDFs and images are unusable. A page that Tavily extracts as real article text is a good sign but not proof (a later probe from GitHub confirms).
3. ANOTHER Claude session researches the same repository in parallel with 10 clusters (xe số/côn, xe tay ga, 50cc, bảo dưỡng, lốp/phanh, EV/pin/sạc, kỹ năng lái, giấy tờ, du lịch từ Hà Nội bằng xe máy, di chuyển đô thị/văn hóa/ẩm thực). To avoid collisions choose LONG-TAIL, specific reader questions rather than the obvious head topics, run `cd $SCR && python pkg.py sync` first (it lists rows other sessions have already pushed on research branches) and screen every candidate with `pkg.py intent` (it includes those rows). Readers' benefit first; every topic must be a distinct search question, not a variant of an existing post. Existing coverage: 160 published posts (see `$SCR/inventory_links.tsv`: id, url, title) and 101 registry topics. Screen EVERY candidate with
       cd $SCR && python pkg.py intent "<title>" "<primary keyword>" <taxonomy_key>
   Keep only PASS results (FAIL/REVIEW = already covered; re-scope the idea or drop it). Then also skim `inventory_links.tsv` yourself for close neighbours.
4. Avoid time-sensitive facts that go stale quickly (ticket prices, opening hours, fines, tariffs, phone numbers, exact schedules) unless the page is recent and the article could state "as of <page date>". Prefer durable, explanatory content. Avoid legal advice topics unless a legal host page is readable and recent.
5. Honesty: only facts that the pages really say. No invented numbers. If a page is promotional, note it.
6. No topic about the rental business itself (prices, deposits, delivery): those are covered elsewhere.

## Reading pages into the local store (so later writers can quote them verifiably)

- Find pages: tavily_search (use include_domains for allowlisted hosts; max_results 10), tavily_map (small limits, select_paths regex) for URL lists.
- Read pages: tavily_extract with format "text", ALWAYS in batches of 8–12 URLs. A big result spills to a file whose path the tool prints ("Output has been saved to …"); then run
       cd $SCR && python bench.py ingest <that file path>
  which stores every page's exact text + SHA-256 under $SCR/sources/. A small result that comes back inline CANNOT be ingested: do not retype it; re-run the extraction with more URLs in the batch. Only pages that were ingested may be cited.
- Read stored pages (run inside $SCR): python -c "import bench; print(bench.load('<url>')['text'][:4000])"  or  bench.grep('<url>', r'regex')  or, for Yamaha-style news pages with a 'Ngày đăng' marker, bench.body('<url>').
- The extraction tool DROPS the letters "â" and "ã" in many words ("người dn" = "người dân", "gy" = "gây", "tm" = "tâm"). Mentally restore; when you pick an `excerpt`, choose a sentence with no damaged word. `bench.source(url, excerpt, supports)` verifies that an excerpt exists verbatim in the stored text (raises otherwise) — call it for every excerpt you put in your output.
- Stay inside budget: roughly 25–40 tool calls in total. Do not crawl whole sites. Prefer 2–3 source-rich hubs, then pick the best articles.

## Deliverable

Write `$SCR/scout/<NAME>.json` (create the folder) — a JSON list of 20–25 topic proposals, best first:

    {
      "title": "<Vietnamese article title, 60–100 chars, a real search question/need>",
      "primary_keyword": "<natural phrase present verbatim in the title>",
      "secondary_keywords": ["..",".."],
      "taxonomy_key": "<one of: hanoi-travel vietnam-travel food-culture destinations trip-planning urban-mobility green-travel battery-charging electric-tech electric-maintenance electric-transition ebikes electric engine-care road-safety driving-licence legal rental-guide rental-procedures rental-costs rental-50cc reviews>",
      "reader_need": "<one sentence: who asks this and why>",
      "sources": [ {"url": "...", "host": "...", "page_date": "<date on page or null>", "supports": "<what this page establishes, specific>", "excerpt": "<verbatim >=8-word sentence without damaged words, verified with bench.source>"} ],   // >=2 pages on >=2 different hosts (hostnames differ), all ingested
      "key_facts": ["<fact> (page url short name)", "... 6–12 bullets, each traceable to an ingested page"],
      "time_sensitive": ["<anything that will go stale>"],
      "risks": ["<promotional tone / conflicts between pages / thin page / anything a writer must handle carefully>"],
      "intent_check": "<verdict + nearest item from pkg.py intent>"
    }

Also include in the same file a top-level object? No: keep the file a plain JSON list. Put a short free-text summary (what hosts worked, what failed or was JS-only, anything surprising) in your final reply (max 200 words).
Quality bar: a topic is only worth proposing if two ingested pages together contain enough solid, specific content for ~1,300+ words of useful, non-speculative Vietnamese text. Fewer strong topics beat many weak ones; but aim for at least 20.
