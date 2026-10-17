"""Vietnamese syllable vocabulary from the site's own posts. Used to spot Tavily's dropped-'â' artifacts
('nhn', 'dn', 'đy', 'gy', 'chn'...) before an excerpt is trusted as live-page evidence."""
import collections, json, os, re, subprocess
from pathlib import Path
ROOT = Path(os.environ.get('WPW_ROOT') or subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() or '.')
INV = ROOT / 'data/existing-content-inventory.json'
_TOK = re.compile(r"[^\W\d_]+", re.UNICODE)
_VOCAB = None

def vocab():
    global _VOCAB
    if _VOCAB is None:
        c = collections.Counter()
        for p in json.loads(INV.read_text(encoding='utf-8'))['items']:
            c.update(t for t in _TOK.findall((p.get('content_text') or '').lower()))
        _VOCAB = {t for t, n in c.items() if n >= 2}
    return _VOCAB

def suspects(text, allow=()):
    v = vocab()
    allow = {a.lower() for a in allow}
    out = []
    for t in _TOK.findall(text.lower()):
        if t in v or t in allow:
            continue
        if re.fullmatch(r'[a-z]+', t) and len(t) > 3:   # plain latin word (brand / English term): not an artifact signal
            continue
        out.append(t)
    return out

if __name__ == '__main__':
    import sys
    print(len(vocab()))
    for s in sys.argv[1:]:
        print(s, '->', suspects(s))
