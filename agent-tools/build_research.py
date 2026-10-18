#!/usr/bin/env python3
"""Assemble Topic Registry rows for a research batch from compact specs + stored source notes.

usage: build_research.py <specs.json> <out.jsonl> [--session SESSION]
specs.json = list of {topic_id, origin_id, title, primary_keyword, search_intent, intent_key, taxonomy_key,
  secondary_keywords?, outline[>=5], difference_summary, usefulness, scope_exclusions[], links[urls],
  source_requirements[], priority?, extra_review_ids?[], resolved_intent_collisions?{WPid: reason>=40 chars},
  sources:[{slug, supports, evidence_text}]}
Computes slug/canonical, pillar/hub/silo, nearest-5 inventory review (ids+content hashes), verifies each
evidence_text is VERBATIM in the stored source, then runs research_v2.validate_candidates locally.
"""
import argparse, datetime as dt, json, pathlib, sys
import os, subprocess
ROOT = pathlib.Path(os.environ.get('WPW_ROOT') or subprocess.run(['git','rev-parse','--show-toplevel'],capture_output=True,text=True).stdout.strip() or '/home/user/wp-writer')
SP = pathlib.Path(os.environ.get('WPW_SCRATCH') or (pathlib.Path.home() / 'wp-writer-scratch'))
sys.path.insert(0, str(ROOT / 'scripts'))
from common import SITE, slugify, norm, now, load, topics
from topic_factory import similarity
import research_v2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('specs'); ap.add_argument('out')
    ap.add_argument('--session', default='s-seodev-20261017a')
    a = ap.parse_args()
    specs = json.loads(pathlib.Path(a.specs).read_text())
    inv_doc = load('data/existing-content-inventory.json', {})
    inv = inv_doc.get('items', [])
    inv_updated = inv_doc.get('updated_at')
    tax = {t['taxonomy_key']: t for t in load('data/taxonomy.json')['items']}
    published = {p['url'] for p in inv if p.get('status') == 'publish'}
    today = dt.date.today().isoformat()
    rows = []
    for s in specs:
        t = tax[s['taxonomy_key']]
        parent = t.get('parent_key') or s['taxonomy_key']
        slug = slugify(s['title'])
        nearest = sorted(inv, key=lambda p: similarity(s['title'], p.get('title') or ''), reverse=True)[:5]
        extra = [p for p in inv if str(p['id']) in {str(x) for x in s.get('extra_review_ids', [])} and p not in nearest]
        reviewed = nearest + extra
        ext = []
        for src in s['sources']:
            note = json.loads((SP / 'sources' / f"{src['slug']}.json").read_text())
            text = (SP / 'sources' / f"{src['slug']}.txt").read_text()
            if norm(src['evidence_text']) not in norm(text):
                raise SystemExit(f"EVIDENCE NOT VERBATIM for {s['topic_id']} / {src['slug']}: {src['evidence_text'][:80]}")
            ext.append({'url': note['url'], 'checked_at': note['checked_at'], 'supports': src['supports'],
                        'evidence_text': src['evidence_text'], 'source_sha256': note['source_sha256']})
        bad = [u for u in s['links'] if u not in published]
        if bad:
            raise SystemExit(f"links not in public inventory for {s['topic_id']}: {bad}")
        row = {
            'topic_id': s['topic_id'], 'origin_id': s['origin_id'], 'title': s['title'],
            'primary_keyword': s['primary_keyword'], 'secondary_keywords': s.get('secondary_keywords', []),
            'search_intent': s['search_intent'], 'intent_key': s['intent_key'], 'topic_role': 'supporting',
            'pillar': parent, 'hub': parent, 'silo': s['taxonomy_key'], 'taxonomy_key': s['taxonomy_key'],
            'wordpress_category_id': t.get('wordpress_term_id'),
            'word_target_min': 1600, 'word_target_max': 5000,
            'canonical_target': f'{SITE}/{slug}/', 'proposed_slug': slug,
            'related_existing_urls': s['links'], 'internal_link_candidates': s['links'],
            'source_requirements': s.get('source_requirements', ['Chỉ dùng nguồn chính thức đã đọc; không bịa số liệu']),
            'priority': s.get('priority', 'P2'), 'writer_claim': None, 'topic_qa_status': None,
            'qa_status': 'NOT_AUTHORED', 'publication_status': 'NOT_SUBMITTED', 'wp_post_id': None,
            'wp_permalink': None, 'source_hash': None, 'timestamps': {'created_at': now()},
            'research': {
                'reviewer': a.session, 'reviewed_at': now(), 'inventory_updated_at': inv_updated,
                'method': 'đọc toàn văn nguồn chính thức qua trích xuất trang và lưu hash văn bản đã đọc; đối chiếu tiêu đề và content_hash của 5 bài gần nhất theo độ tương đồng tiêu đề; tìm toàn văn từ khóa chính trong toàn bộ inventory WordPress để phát hiện bài đã nhắc; không dựa vào RSS; không phải dữ liệu lượng tìm kiếm',
                'difference_summary': s['difference_summary'], 'usefulness': s['usefulness'],
                'scope_exclusions': s['scope_exclusions'],
                'reviewed_existing_ids': [p['id'] for p in reviewed],
                'reviewed_content_hashes': {str(p['id']): p.get('content_hash') for p in reviewed},
                'resolved_topic_collisions': {}, 'external_sources': ext,
                'resolved_intent_collisions': s.get('resolved_intent_collisions', {})},
            'outline': s['outline'],
        }
        rows.append(row)
        (SP / 'notes').mkdir(exist_ok=True)
        (SP / 'notes' / f"{s['topic_id']}.json").write_text(json.dumps({'topic_id': s['topic_id'], 'title': s['title'], 'source_slugs': [x['slug'] for x in s['sources']], 'facts_hint': s.get('facts_hint', '')}, ensure_ascii=False, indent=1))
        print(f"{s['topic_id']} nearest:", [(p['id'], round(similarity(s['title'], p.get('title') or ''), 2), (p.get('title') or '')[:48]) for p in nearest[:3]])
    pathlib.Path(a.out).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    res = research_v2.validate_candidates(rows)
    for r in res:
        print(r['topic_id'], r['status'], r['errors'], r['review'])
    print('ALL PASS' if all(r['status'] == 'PASS' for r in res) else 'NOT ALL PASS')

if __name__ == '__main__':
    main()
