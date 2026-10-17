#!/usr/bin/env python3
"""Show what the site/registry already covers near an idea. usage: similar.py "<title or keywords>" [more keywords...]
Prints nearest published inventory titles + registry topics (title similarity) and full-text keyword hit counts."""
import os
import json, os, pathlib, subprocess, sys
ROOT = pathlib.Path(os.environ.get('WPW_ROOT') or subprocess.run(['git','rev-parse','--show-toplevel'],capture_output=True,text=True).stdout.strip() or '/home/user/wp-writer')
sys.path.insert(0, str(ROOT / 'scripts'))
from common import norm, load, topics
from topic_factory import similarity
q = sys.argv[1]
inv = load('data/existing-content-inventory.json', {}).get('items', [])
rows = topics()
print('== nearest published (inventory):')
for p in sorted(inv, key=lambda p: similarity(q, p.get('title') or ''), reverse=True)[:6]:
    print(f"  {round(similarity(q, p.get('title') or ''),2)} #{p['id']} {(p.get('title') or '')[:80]}")
print('== nearest registry topics (any status):')
for t in sorted(rows, key=lambda t: similarity(q, t['title']), reverse=True)[:6]:
    print(f"  {round(similarity(q, t['title']),2)} {t['topic_id']} [{t.get('topic_qa_status')}] {t['title'][:80]}")
kws = sys.argv[2:] or [q]
print('== full-text keyword hits (inventory bodies / titles):')
for kw in kws:
    k = norm(kw)
    body = [i['id'] for i in inv if k in norm(i.get('content_text') or '')]
    title = [i['id'] for i in inv if k in norm(i.get('title') or '')]
    tt = [t['topic_id'] for t in rows if k in norm(t['title'])]
    print(f"  '{kw}': bodies={len(body)} {body[:6]} titles={title[:4]} registry_titles={tt[:5]}")
