#!/usr/bin/env python3
"""Read-only status of the topic factory for the per-wave report (no network except `git ls-remote`).

    git pull --ff-only origin main && python3 agent-tools/factory_status.py [--json]

Reads the files on disk only: data/topics.jsonl, data/state/*, reports/*, config/*. It counts the same way as
reports/topic-stock.json (only PLANNED that a writer can still take is "ready"; published, claimed, held,
RESEARCH and IDEA are never added to it) and compares every taxonomy key with its allocation in
data/topic-domains.json. It never writes, never edits the registry, never touches WordPress.
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import refill_controller  # noqa: E402
import research_v2  # noqa: E402
from common import load, topics  # noqa: E402


def branches():
    try:
        out = subprocess.run(['git', 'ls-remote', '--heads', 'origin', 'research/*'], cwd=ROOT, capture_output=True,
                             text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    return {line.split('refs/heads/')[1]: line.split()[0] for line in out.splitlines() if 'refs/heads/' in line}


def status():
    inputs = refill_controller.build_inputs()
    rows, stock = inputs['rows'], inputs['stock']
    # Same count as the refill order's quotas: live topics plus published WordPress posts per category.
    have = refill_controller.coverage_by_key(rows, inputs['inventory'], inputs['taxonomy'])
    ready = Counter(t['taxonomy_key'] for t in rows if t['topic_id'] in set(stock['ready_ids']))
    allocation = Counter()
    for domain in inputs['domains']:
        allocation[domain['taxonomy_key']] += domain['initial_allocation']
    ledger = (inputs['intake_ledger'] or {}).get('batches', {})
    heads = branches()
    ingested = {b.get('research_branch'): b.get('research_commit') for b in ledger.values()}
    plan = research_v2.refill_plan()
    return {
        'approved_capacity': inputs['approved_capacity'], 'topic_rows': len(rows),
        'capacity_remaining': inputs['approved_capacity'] - len(rows),
        'rows_by_status': dict(Counter(t.get('topic_qa_status') for t in rows)),
        'stages': stock['stages'], 'ready_for_writers': stock['ready'], 'ready_ids': stock['ready_ids'],
        'on_hold': sorted(stock['on_hold']),
        'order': plan['order'], 'refill_state': plan['state'], 'next_batch_categories': plan['next_batch_categories'],
        'intake': {'batches': len(ledger),
                   'accepted_topics': sum(len(b.get('accepted_ids') or []) for b in ledger.values()),
                   'not_accepted': {k: v for b in ledger.values() for k, v in (b.get('not_accepted') or {}).items()}},
        'research_branches': {b: {'head': h[:7], 'ingested': ingested.get(b) == h} for b, h in sorted(heads.items())},
        'by_category': {k: {'allocation': allocation[k], 'known_now': have.get(k, 0), 'ready': ready.get(k, 0),
                            'deficit': max(0, allocation[k] - have.get(k, 0))}
                        for k in sorted(allocation, key=lambda k: -max(0, allocation[k] - have.get(k, 0)))},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    data = status()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    print('capacity: %d rows of %d approved (%d free)' % (data['topic_rows'], data['approved_capacity'],
                                                          data['capacity_remaining']))
    print('rows by status:', data['rows_by_status'])
    print('stages:', data['stages'])
    print('ready for writers: %d   on hold: %s' % (data['ready_for_writers'], data['on_hold'] or '-'))
    order = data['order']
    print('refill: %s order=%s accepted=%s/%s (min) batches still needed=%s' % (
        data['refill_state'], order.get('id'), order.get('accepted_so_far'), order.get('target_min'),
        order.get('batches_still_needed')))
    print('intake: %(batches)d batches, %(accepted_topics)d topics accepted, not accepted: %(not_accepted)s' % data['intake'])
    print('research branches:')
    for name, info in data['research_branches'].items():
        print('  %-22s %s %s' % (name, info['head'], 'ingested' if info['ingested'] else 'NOT ingested'))
    print('next batch categories:', data['next_batch_categories'])
    print('%-22s %5s %5s %5s %7s' % ('category', 'alloc', 'known', 'ready', 'deficit'))
    for key, v in data['by_category'].items():
        print('%-22s %5d %5d %5d %7d' % (key, v['allocation'], v['known_now'], v['ready'], v['deficit']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
