"""Work order for a locally scouted topic (spec.json with the scout fields but not yet in the registry)."""
import json
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import bench, peek, pkg

FOCUS = {  # per topic: url -> (start marker, end marker) windows of long pages
    'NT-000801': {'toan-van-luat-trat-tu': [('Điều 57. Giấy phép lái xe', 'Điều 58. Điểm của giấy phép lái xe')]},
    'NT-000802': {'toan-van-luat-trat-tu': [('Điều 58. Điểm của giấy phép lái xe', 'Điều 60. Đào tạo lái xe')]},
}


def window(text, start, end):
    i = text.find(start)
    if i < 0:
        return ''
    j = text.find(end, i + len(start))
    return text[i:j if j > 0 else i + 9000]


def main(tid, cap=7000):
    spec, _ = pkg.load_pkg(tid)
    print('# WORK ORDER (scouted topic, not yet in the registry)', tid)
    for k in ('title', 'primary_keyword', 'secondary_keywords', 'search_intent', 'taxonomy_key'):
        print('%s: %s' % (k, spec.get(k)))
    print('outline (your H2s follow it in order and meaning):')
    for o in spec['outline']:
        print('  -', o)
    print('difference_summary (what the site already says and why this article is different):', spec['difference_summary'])
    print('usefulness:', spec['usefulness'])
    print('scope_exclusions (binding):', spec['scope_exclusions'])
    print('source_requirements (binding):', spec['source_requirements'])
    print('internal link candidates (published URLs; choose 3-4, you may swap for others from inventory_links.tsv):')
    for u in spec.get('internal_links', []):
        print('  -', u)
    print()
    seen = set()
    for i, s in enumerate(spec['sources'], 1):
        url = s['url']
        if url in seen:
            print('## SOURCE %d (same page as above) supports: %s' % (i, s['supports']))
            continue
        seen.add(url)
        rec = bench.load(url)
        print('## SOURCE %d: %s' % (i, url))
        print('title:', rec.get('title'), '| page date:', rec.get('publish_date'), '| read:', rec.get('read_at'))
        print('scout excerpt (registered evidence):', s['excerpt'])
        print('scout supports:', s['supports'])
        focus = None
        for key, wins in FOCUS.get(tid, {}).items():
            if key in url:
                focus = wins
        if focus:
            print('--- the relevant provisions of this long page ---')
            for a, b in focus:
                print(window(rec['text'], a, b))
        else:
            print('--- page text (navigation removed) ---')
            print(peek.body(url, cap))
        print()


if __name__ == '__main__':
    main(sys.argv[1])
