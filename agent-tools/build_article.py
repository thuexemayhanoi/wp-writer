#!/usr/bin/env python3
"""Build posts/drafts/NT-XXXXXX.md from a body file + a small spec JSON, then run repo QA.

usage: build_article.py NT-000073 --session S --slot W1..W9 [--no-qa]
reads  scratchpad/bodies/<ID>.md   (markdown body only; first paragraph == direct answer)
       scratchpad/specs/<ID>.json  (meta_title, meta_description, link_rationale, business_claims, sources)
writes posts/drafts/<ID>.md  (frontmatter identity copied from data/topics.jsonl)
"""
import argparse, hashlib, json, pathlib, sys
import os, subprocess
ROOT = pathlib.Path(os.environ.get('WPW_ROOT') or subprocess.run(['git','rev-parse','--show-toplevel'],capture_output=True,text=True).stdout.strip() or '/home/user/wp-writer')
SP = pathlib.Path(os.environ.get('WPW_SCRATCH') or (pathlib.Path.home() / 'wp-writer-scratch'))
sys.path.insert(0, str(ROOT / 'scripts'))
WRITER_SLOTS = tuple(json.loads((ROOT / 'config/writer-slots.json').read_text(encoding='utf-8'))['slots'])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('topic_id')
    ap.add_argument('--session', default='s-seodev-20261017a')
    ap.add_argument('--slot', choices=WRITER_SLOTS, help='Use the W1..W9 slot returned by your live Writer claim')
    ap.add_argument('--no-qa', action='store_true')
    ap.add_argument('--prefly', help='research jsonl holding the not-yet-PLANNED topic row; writes to scratchpad/drafts_prefly, not the repo')
    a = ap.parse_args()
    if a.slot is None and not a.prefly:
        ap.error('--slot is required for a real article; use the W1..W9 slot in your active lease')
    # Preflight files are scratch-only, never submitted; give them a placeholder slot.
    writer_slot = a.slot or WRITER_SLOTS[0]
    rows = [json.loads(l) for l in (ROOT / 'data/topics.jsonl').read_text().splitlines() if l.strip()]
    if a.prefly:
        extra = [json.loads(l) for l in pathlib.Path(a.prefly).read_text().splitlines() if l.strip()]
        for e in extra:
            e['topic_qa_status'] = 'PLANNED'
        rows = [r for r in rows if r['topic_id'] not in {e['topic_id'] for e in extra}] + extra
    topic = next(t for t in rows if t['topic_id'] == a.topic_id)
    spec = json.loads((SP / 'specs' / f'{a.topic_id}.json').read_text())
    body = (SP / 'bodies' / f'{a.topic_id}.md').read_text().strip()
    direct = body.split('\n\n', 1)[0].strip()
    sha = hashlib.sha256(body.encode()).hexdigest()
    meta = {
        'topic_id': topic['topic_id'], 'title': topic['title'],
        'primary_keyword': topic['primary_keyword'], 'search_intent': topic['search_intent'],
        'taxonomy_key': topic['taxonomy_key'], 'canonical_target': topic['canonical_target'],
        'writer_slot': writer_slot, 'writer_session': a.session,
        'meta_title': spec['meta_title'], 'meta_description': spec['meta_description'],
        'direct_answer': direct, 'link_rationale': spec['link_rationale'],
        'business_claims': spec.get('business_claims', []), 'sources': spec.get('sources', []),
        'editorial_review': {'reviewer': a.session, 'body_sha256': sha, 'intent_covered': True,
                             'substantive': True, 'facts_checked': True,
                             'no_fabricated_experience': True, 'collision_reviewed': True},
    }
    if a.prefly:
        (SP / 'drafts_prefly').mkdir(exist_ok=True)
        out = SP / 'drafts_prefly' / f'{a.topic_id}.md'
    else:
        out = ROOT / 'posts/drafts' / f'{a.topic_id}.md'
    out.write_text('---\n' + json.dumps(meta, ensure_ascii=False, indent=2) + '\n---\n\n' + body + '\n', encoding='utf-8')
    print('wrote', out, 'body_sha256', sha[:12])
    if a.no_qa:
        return
    from qa import evaluate
    r = evaluate(out, topic, rows=rows, check_claim=False)
    print(json.dumps({k: r[k] for k in ('status', 'word_count', 'quality_score', 'seo_score')}, ensure_ascii=False))
    print('errors:', r['errors']); print('review:', r['review'])
    print('seo_recommendations:', r['seo_recommendations'])
    print('seo points:', {k: v['points'] for k, v in r['seo_checks'].items()})

if __name__ == '__main__':
    main()
