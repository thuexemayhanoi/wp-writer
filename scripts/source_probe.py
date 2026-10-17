#!/usr/bin/env python3
"""Read-only probe: can the GitHub runner read a cited source like the Publisher's live QA?

Fetches each URL with the same user agent, redirect rule, timeout and visible-text
extraction as qa.verify_sources(live=True). It never writes to WordPress or the repo.
Input: PROBE_URLS, one `url|needle` per line (needle optional, normalised like QA).
"""
import os
import sys
import time
import urllib.request

from common import Redirect, norm, visible


DEFAULT_UA = 'NguyenTu-WPWriter/1.0'


def probe(url, needle='', agent=DEFAULT_UA):
    started = time.time()
    try:
        opener = urllib.request.build_opener(Redirect())
        request = urllib.request.Request(url, headers={'User-Agent': agent})
        with opener.open(request, timeout=20) as response:
            raw = response.read(8_000_000).decode('utf-8', errors='replace')
            status = response.status
        text = visible(raw)
        found = (norm(needle) in norm(text)) if needle.strip() else None
        return {'url': url, 'ua': agent[:24], 'ok': True, 'status': status, 'chars': len(text),
                'needle_found': found, 'seconds': round(time.time() - started, 1)}
    except Exception as exc:
        return {'url': url, 'ua': agent[:24], 'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)[:120],
                'seconds': round(time.time() - started, 1)}


def parse(lines):
    rows = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        url, _, needle = line.partition('|')
        rows.append((url.strip(), needle.strip()))
    return rows


def main():
    rows = parse(os.environ.get('PROBE_URLS', '').splitlines())
    if not rows:
        raise SystemExit('PROBE_URLS is empty')
    # PROBE_UAS: optional user agents separated by `||` (default: the QA's own agent).
    agents = [a.strip() for a in os.environ.get('PROBE_UAS', '').split('||') if a.strip()] or [DEFAULT_UA]
    failed = total = 0
    for url, needle in rows:
        for agent in agents:
            result = probe(url, needle, agent)
            good = result['ok'] and result.get('needle_found') is not False
            failed += not good
            total += 1
            print(('OK   ' if good else 'FAIL ') + str(result), flush=True)
    print('SOURCE_PROBE: %d/%d readable with the excerpt present' % (total - failed, total))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
