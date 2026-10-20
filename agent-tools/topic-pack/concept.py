import sys, re
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import pkg
from common import norm

def screen(concepts, limit=6, min_count=1):
    """concepts: list of phrases; a post matches when it contains ALL phrases; prints best matches by total count."""
    inv = pkg.inventory()
    rows = []
    for p in inv:
        text = norm(p.get('content_text') or '')
        counts = [text.count(norm(c)) for c in concepts]
        if all(n >= min_count for n in counts):
            rows.append((sum(counts), p['id'], p.get('title'), counts, len((p.get('content_text') or '').split())))
    rows.sort(reverse=True)
    return rows[:limit]

if __name__ == '__main__':
    import json
    for spec in json.loads(sys.argv[1]):
        print('##', spec)
        for tot, pid, title, counts, words in screen(spec):
            print('   %-5s total=%-3d %s words=%d  %s' % (pid, tot, counts, words, (title or '')[:80]))
