"""Research workbench: a local store of the exact text of every page read (scratch directory, never committed).

Stores the EXACT text of every page read through a spilled Tavily tool-result file, hashes it,
and verifies evidence excerpts programmatically so no excerpt is ever retyped from memory.
"""
import datetime as dt, hashlib, json, os, re, sys, unicodedata
from pathlib import Path
SCRATCH = Path(os.environ.get('WPW_SCRATCH') or Path(__file__).resolve().parent)
SRC = SCRATCH / 'sources'
SRC.mkdir(exist_ok=True)
TODAY = dt.date.today().isoformat()

def key(url): return hashlib.sha1(url.encode()).hexdigest()[:16]

def norm(value):
    value = unicodedata.normalize('NFD', str(value).lower().replace('đ', 'd'))
    value = ''.join(c for c in value if unicodedata.category(c) != 'Mn')
    return ' '.join(re.findall(r'[a-z0-9]+', value))

def ingest(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    done, failed = [], [f.get('url') for f in data.get('failed_results', [])]
    for r in data.get('results', []):
        text = r.get('raw_content') or ''
        rec = {'url': r['url'], 'title': r.get('title'), 'text': text,
               'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
               'chars': len(text), 'read_at': TODAY, 'tool': 'tavily_extract(format=text)',
               'spill_file': str(path)}
        (SRC / (key(r['url']) + '.json')).write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
        done.append((r['url'], len(text), rec['sha256'][:12], r.get('title')))
    return done, failed

def ingest_parallel(path):
    """Parallel web_fetch(full_content=true) spill file: {results:[{url,title,full_content}], errors:[{url,error_type}]}."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    done, failed = [], [f.get('url') for f in data.get('errors', [])]
    for r in data.get('results', []):
        text = r.get('full_content') or ''
        rec = {'url': r['url'], 'title': (r.get('title') or '').strip(), 'text': text,
               'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
               'chars': len(text), 'read_at': TODAY, 'tool': 'parallel web_fetch(full_content)',
               'spill_file': str(path), 'publish_date': r.get('publish_date')}
        (SRC / (key(r['url']) + '.json')).write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
        done.append((r['url'], len(text), rec['sha256'][:12], rec['title']))
    return done, failed


def load(url):
    p = SRC / (key(url) + '.json')
    if not p.exists(): raise KeyError('not read: ' + url)
    return json.loads(p.read_text(encoding='utf-8'))

def grep(url, pattern, width=150, limit=6):
    rec = load(url)
    out = []
    for m in re.finditer(pattern, rec['text'], flags=re.I):
        s = max(0, m.start() - width); e = min(len(rec['text']), m.end() + width)
        out.append(rec['text'][s:e].replace('\n', ' '))
        if len(out) >= limit: break
    return out

def source(url, excerpt, supports):
    """Build one external_sources entry; the excerpt must exist verbatim (normalised) in the saved text."""
    rec = load(url)
    if norm(excerpt) not in norm(rec['text']):
        raise ValueError('excerpt not found in saved text of ' + url + ': ' + excerpt[:60])
    return {'url': url, 'checked_at': rec['read_at'], 'supports': supports,
            'evidence_text': excerpt, 'source_sha256': rec['sha256']}

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'ingest':
        done, failed = ingest(sys.argv[2])
        for d in done: print(d)
        print('FAILED:', failed)
    elif cmd == 'ingest-parallel':
        done, failed = ingest_parallel(sys.argv[2])
        for d in done: print(d)
        print('FAILED:', failed)
    elif cmd == 'grep':
        for line in grep(sys.argv[2], sys.argv[3]): print('-', line)


def body(url, end_markers=('Bài viết liên quan', 'Tin liên quan', 'Có thể bạn quan tâm', 'Thông tin có giúp ích')):
    """Article text without the site navigation (Yamaha news pages): from the last 'Ngày đăng' marker."""
    t = load(url)['text']
    i = t.rfind('Ngày đăng')
    if i < 0:
        return t
    t = t[i:]
    cut = len(t)
    for m in end_markers:
        j = t.find(m)
        if 0 < j < cut:
            cut = j
    return t[:cut]


HONDA_FAQ = 'https://www.honda.com.vn/cau-hoi-thuong-gap'

def faq_items(url=HONDA_FAQ):
    """Split the Honda FAQ page into (question, answer) pairs."""
    t = load(url)['text']
    parts = t.split('icon_question\n')[1:]
    out = []
    for p in parts:
        q, _, rest = p.partition('\n')
        ans = rest.split('Thông tin có giúp ích cho bạn không?')[0]
        ans = re.sub(r'^\s*Trả lời\s*', '', ans).strip()
        out.append((q.strip(), ans))
    return out
