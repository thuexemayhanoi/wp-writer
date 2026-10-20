"""Print the current writer-visible stock (same computation as scripts/reports.py), read-only."""
import json
import sys
from pathlib import Path

import os, subprocess
ROOT = Path(os.environ.get('WPW_ROOT') or subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() or '.')
sys.path.insert(0, str(ROOT / 'scripts'))
from common import load, topics  # noqa: E402
from refill_policy import stock_policy  # noqa: E402
from topic_stock import build_stock  # noqa: E402


def stock():
    rows = topics()
    claims = load('data/state/writer-claims.json', {'leases': {}})
    ledger = load('data/state/publication-ledger.json', {'posts': {}})
    policy = load('config/production-policy.json')
    authored = list((ROOT / 'posts/drafts').glob('NT-*.md'))
    qa = {p.stem: load('data/qa/' + p.stem + '.json', {}) for p in authored}
    disc = load('data/state/topic-discovery-ledger.json', {'proposals': {}})
    st = build_stock(rows, claims, ledger, qa, {p.stem for p in authored}, disc, stock_policy(policy))
    return rows, st, claims, ledger


if __name__ == '__main__':
    rows, st, claims, ledger = stock()
    by = {r['topic_id']: r for r in rows}
    print('stages', st['stages'])
    print('ready', st['ready'])
    for i in st['ready_ids']:
        r = by[i]
        print(i, r.get('taxonomy_key'), '|', r.get('title'), '|', r.get('primary_keyword'))
    print('hold', st['on_hold'])
    live = {k: (v.get('slot'), v.get('expires_at'), v.get('topic_ids')) for k, v in claims['leases'].items()}
    print('leases', json.dumps(live, ensure_ascii=False))
