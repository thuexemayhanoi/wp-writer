# Writer GitHub-only; G7 is a Publisher responsibility

**Owner decision, 22 October 2026.** Claude has GitHub access, but is not
authenticated against https://thuexemaynguyentu.com/ WordPress. This is
normal, not a publishing blocker or a reason to request WordPress credentials.

## Two independent actors

| Actor | Required access | Responsible for | May claim |
| --- | --- | --- | --- |
| External Claude / GitHub Writer W1–W9 | GitHub files / repository; public references | Select an already PLANNED NT ID, own a Writer lease, write Markdown, review facts, pass G1–G6 and submit immutable hash | WRITER_QA_PASS, or GITHUB_SUBMITTED_PENDING_QA |
| GitHub Actions Trusted Writer QA / Intake | GitHub files only; **no WP secrets** | Revalidate lease, original SHA and article G1–G6; save a genuine PASS or REPAIR receipt on main | WRITER_QA_PASS_AWAITING_PUBLISHER |
| GitHub Actions WordPress Publisher | GitHub plus owner-configured WordPress REST credentials | Fresh live inventory and duplicate check, exact parent/child category, site SEO adapter, write-ahead POST_INTENT, create, verify G7 live permalink/content/Yoast/robots/canonical | WORDPRESS_G7_VERIFIED, or PUBLISHER_RECONCILE_PENDING |
| Post-publish audit / dashboard | Ledger plus actual live evidence | Flag drift, repairs and actual published URL | Does not forge a Writer receipt |

**One key rule:** Writer does NOT wait for WordPress G7 to write, submit
or take the next authorized topic. A successful Writer QA and valid submission
receipt are the Writer completion point. Publication is asynchronous to Claude,
performed by the existing serialized Publisher. G7 can only happen AFTER
WordPress writes, so it must never be a prerequisite to Writer claims.

## Actions available to a Claude with GitHub only

If using Python and a local repo:

    python scripts/title_plan_next.py --fast-lane --limit 3
    python scripts/writer-session.py begin --slot auto --count 3 --session s-unique-session
    # Write the actual leased posts/drafts/NT-XXXXXX.md files
    python scripts/writer-session.py check --ids NT-XXXXXX --session s-unique-session
    python scripts/writer-session.py push --ids NT-XXXXXX --session s-unique-session
    python scripts/writer_handoff.py --session s-unique-session

The new read-only handoff command requires no WP credential, network,
API key or REST call. It checks GitHub topic identity, submission SHA,
article QA receipts, configured 76/100 scores and Publisher ledger **only**.
It never marks WordPress VERIFIED based on local QA.

If Claude has **GitHub API access but no shell**, write only to an allowed
writer branch and submit an actual Writer request in
data/writer-requests/s-unique-session.json per AI-START-HERE. The branch QA,
trusted intake and main QA run on GitHub Actions. Read the true result in
data/state/writer-claims.json, data/qa/NT-XXXXXX.json and the latest
data/state/publication-ledger.json. Do not impersonate a WordPress readback.

Read-only status examples:
- WRITER_NOT_SUBMITTED — draft is not a trusted registered submission.
- GITHUB_QA_PENDING — receipt exists, QA not yet available/current. Check again from GitHub.
- WRITER_QA_REPAIR — fix the real G1–G6 errors; do not lower 76.
- WRITER_QA_PASS_AWAITING_PUBLISHER — Writer has finished. **Continue other topics**; no WordPress login needed.
- PUBLISHER_RECONCILE_PENDING — Publisher alone resolves uncertain writes; NEVER POST blindly.
- WORDPRESS_G7_VERIFIED — only an actual Publisher receipt with a WordPress ID/URL and G7 PASS proves publication.

## Guardrails unchanged

Research QA must have admitted the topic as PLANNED; a suggested
NT-09XXXX from Excel is not a reserved Topic ID. Claim only valid W1–W9
leases. Retain source authenticity, no duplicate search intent or URL,
1,600–5,000 words, SEO and Quality each >=76, category/slug/canonical,
Yoast adapter, G1–G6 and Publisher G7. The Publisher still checks fresh
authenticated WP content and rejects collisions, even if Writer QA passed
against a slightly older GitHub inventory snapshot.

G7 verification is NOT removed, relabeled or bypassed. WordPress credentials
stay in GitHub Publisher secrets; never copy them to Claude, a Writer branch,
local environment, a draft, or a shared conversation. Do not add direct
WordPress create/update operations to Writer tooling. Keep old content,
permalinks, canonical, sitemap and category tree unchanged.

For the Hanoi 51-ward campaign, externally verified pre-existing posts
(#4344, #4345, #4346) remain separate from Publisher-created G7 receipts.
No duplicate publication or fake receipt is allowed. The independent live
evidence is recorded in editorial/seo-51-phuong/existing-live-evidence.json.
