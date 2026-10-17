#!/usr/bin/env python3
"""Store a source I actually read (from a saved Nimble extract file) as a note with a real sha256.

usage:
  srcnote.py save  <saved_json_path> <slug> <start_marker> [end_marker]   # cleans text, writes sources/<slug>.txt + .json
  srcnote.py savetext <slug> <url>                                         # text on STDIN = the passage actually read (inline results)
  srcnote.py find  <slug> <regex> [n_chars=260] [max=6]                    # print verbatim passages (for evidence_text)
  srcnote.py check <slug> <evidence_text>                                  # confirm verbatim containment (norm-based)
"""
import hashlib, json, re, sys, pathlib, datetime
import os, subprocess
SP = pathlib.Path(os.environ.get('WPW_SCRATCH') or (pathlib.Path.home() / 'wp-writer-scratch')) / 'sources'
_ROOT = os.environ.get('WPW_ROOT') or subprocess.run(['git','rev-parse','--show-toplevel'],capture_output=True,text=True).stdout.strip() or '/home/user/wp-writer'
sys.path.insert(0, _ROOT + '/scripts')
from common import norm

def clean(c):
    t = re.sub(r'[ \t\r\f\v]+', ' ', c)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return t

def main():
    cmd = sys.argv[1]
    if cmd == 'save':
        path, slug, start = sys.argv[2:5]
        end = sys.argv[5] if len(sys.argv) > 5 else None
        d = json.load(open(path))
        t = clean(d['content'])
        s = t.find(start)
        if s < 0:
            print('start marker not found'); sys.exit(1)
        e = t.find(end, s + len(start)) if end else -1
        seg = t[s:(e + len(end)) if e >= 0 else len(t)].strip()
        SP.mkdir(parents=True, exist_ok=True)
        (SP / f'{slug}.txt').write_text(seg, encoding='utf-8')
        note = {'url': d['url'], 'checked_at': datetime.date.today().isoformat(),
                'source_sha256': hashlib.sha256(seg.encode()).hexdigest(), 'chars': len(seg)}
        (SP / f'{slug}.json').write_text(json.dumps(note, ensure_ascii=False, indent=1))
        print(json.dumps(note, ensure_ascii=False))
    elif cmd == 'savetext':
        slug, url = sys.argv[2], sys.argv[3]
        seg = clean(sys.stdin.read()).strip()
        SP.mkdir(parents=True, exist_ok=True)
        (SP / f'{slug}.txt').write_text(seg, encoding='utf-8')
        note = {'url': url, 'checked_at': datetime.date.today().isoformat(),
                'source_sha256': hashlib.sha256(seg.encode()).hexdigest(), 'chars': len(seg)}
        (SP / f'{slug}.json').write_text(json.dumps(note, ensure_ascii=False, indent=1))
        print(json.dumps(note, ensure_ascii=False))
    elif cmd == 'find':
        slug, rx = sys.argv[2], sys.argv[3]
        n = int(sys.argv[4]) if len(sys.argv) > 4 else 260
        mx = int(sys.argv[5]) if len(sys.argv) > 5 else 6
        t = (SP / f'{slug}.txt').read_text()
        for i, m in enumerate(re.finditer(rx, t)):
            if i >= mx: break
            print(f'[{m.start()}]', t[m.start():m.start() + n].replace('\n', ' '))
    elif cmd == 'check':
        slug, ev = sys.argv[2], sys.argv[3]
        t = (SP / f'{slug}.txt').read_text()
        print('VERBATIM' if norm(ev) in norm(t) else 'NOT FOUND')

if __name__ == '__main__':
    main()
