#!/usr/bin/env python3
"""Print only article-like text lines of a saved Nimble JSON result (skip css/js chrome).
usage: body.py <saved_json_path> [min_len=50] [start_regex] [max_chars=9000]"""
import os
import json, re, sys
p = sys.argv[1]; minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 50
start = sys.argv[3] if len(sys.argv) > 3 else None
mx = int(sys.argv[4]) if len(sys.argv) > 4 else 9000
d = json.load(open(p)); c = d['content']
t = re.sub(r'[ \t\r\f\v]+', ' ', c); t = re.sub(r'\n\s*\n+', '\n', t)
print('URL:', d.get('url'), '| chars', len(c), '| clean', len(t))
out = []
pos = 0
if start:
    m = re.search(start, t)
    pos = m.start() if m else 0
    print('start at', pos)
for line in t[pos:].split('\n'):
    s = line.strip()
    if len(s) < minlen: continue
    if re.search(r'[{};]\s*$|function\s*\(|var |\$\(|document\.|window\.|@media|\.css|px;|rgba\(|!important|<script|gtag|_govaq', s): continue
    out.append(s)
txt = '\n'.join(out)
print(txt[:mx])
if len(txt) > mx: print(f'... [truncated, total {len(txt)}]')
