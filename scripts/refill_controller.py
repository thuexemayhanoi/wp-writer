#!/usr/bin/env python3
"""Self-replenishing topic loop: when ready PLANNED stock runs low, open a research order.

The controller DECIDES and RECORDS. It runs no AI model, makes no network call and never
touches WordPress. The research itself is done by external AI sessions through Research V2,
whose QA (independent sources, full-corpus search-intent guard) is the only road into PLANNED.

    ready PLANNED stock < trigger_below_ready  ->  open order RF-n asking for
    round_target_min..round_target_max NEW topics that pass Research QA
    accepted >= round_target_min               ->  order FULFILLED, the next round opens
                                                    whenever stock is low again (no round limit)

Only data/state/refill-orders.json (order ledger) and reports/refill-request.json (the work order
researchers read) are written, by the trusted main workflow, through the same compare-and-swap
commit every other factory bot uses. Both files carry no timestamps of their own, so an idle
hour produces no commit.
"""
import argparse
import datetime as dt
import json
import math
import os
import sys
from collections import Counter

from common import ROOT, load, save, topics
from refill_policy import policy as load_policy, stock_policy
from topic_stock import build_stock

STATE = 'data/state/refill-orders.json'
REQUEST = 'reports/refill-request.json'
INTAKE_LEDGER = 'data/state/research-intake-ledger.json'
TRUSTED_WORKFLOW = 'Self-replenishing topic controller'


def parse_time(value):
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed.astimezone(dt.timezone.utc)


def accepted_since(intake_ledger, opened_at):
    """Topic IDs the trusted intake promoted to PLANNED after the order opened."""
    start = parse_time(opened_at)
    found, last = [], None
    for batch in (intake_ledger.get('batches') or {}).values():
        at = parse_time(batch.get('at'))
        if start is None or at is None or at < start:
            continue
        found.extend(batch.get('accepted_ids') or [])
        last = at if last is None or at > last else last
    return found, last


def active_keys(taxonomy):
    return {t['taxonomy_key'] for t in taxonomy
            if t.get('status') == 'ACTIVE' and t.get('wordpress_term_id') and t['taxonomy_key'] != 'uncategorized'}


def coverage_by_key(rows, inventory, taxonomy):
    """Known URLs/topics per category: live topics (not REJECTED) plus published WordPress posts."""
    have = Counter(t['taxonomy_key'] for t in rows if t.get('topic_qa_status') != 'REJECTED')
    term_to_key = {t['wordpress_term_id']: t['taxonomy_key'] for t in taxonomy if t.get('wordpress_term_id')}
    published_urls = {t.get('canonical_target') for t in rows}
    for item in inventory:
        if item.get('type') != 'posts' or item.get('status') != 'publish' or item.get('url') in published_urls:
            continue
        for category in _category_ids(item.get('categories')):
            if category in term_to_key:
                have[term_to_key[category]] += 1
                break
    return have


def _category_ids(raw):
    if isinstance(raw, list):
        return [c['id'] if isinstance(c, dict) else c for c in raw]
    return []


def allocation_by_key(domains, keys, scale):
    totals = Counter()
    for domain in domains:
        if domain['taxonomy_key'] in keys:
            totals[domain['taxonomy_key']] += domain['capacity_allocation' if scale == 'capacity' else 'initial_allocation']
    return totals


def spread(total, deficits, max_share):
    """Largest-remainder split of ``total`` over categories, none above max_share of the total."""
    cap = max(1, math.floor(total * max_share))
    quota, pool = Counter(), {k: v for k, v in deficits.items() if v > 0}
    remaining = total
    while remaining > 0 and pool:
        weight = sum(pool.values())
        exact = {k: remaining * v / weight for k, v in pool.items()}
        grant = {k: min(math.floor(x), cap - quota[k]) for k, x in exact.items()}
        leftovers = sorted(pool, key=lambda k: (-(exact[k] - math.floor(exact[k])), k))
        given = sum(grant.values())
        for key in leftovers:
            if given >= remaining:
                break
            if quota[key] + grant[key] < cap:
                grant[key] += 1
                given += 1
        if given == 0:
            break
        for key, n in grant.items():
            quota[key] += n
        remaining -= given
        pool = {k: v for k, v in pool.items() if quota[k] < cap}
    return quota


def quotas_for(total, rows, inventory, taxonomy, domains, max_share):
    keys = active_keys(taxonomy)
    have = coverage_by_key(rows, inventory, taxonomy)
    for scale in ('initial', 'capacity'):
        allocation = allocation_by_key(domains, keys, scale)
        deficits = {k: allocation[k] - have[k] for k in allocation}
        if any(v > 0 for v in deficits.values()):
            break
    if not any(v > 0 for v in deficits.values()):
        deficits = dict(allocation)  # everything is at budget: spread by budget weight instead
    quota = spread(total, deficits, max_share)
    return [{'taxonomy_key': k, 'quota': quota[k], 'known_now': have[k], 'allocation': allocation[k]}
            for k in sorted(quota, key=lambda k: (-quota[k], k)) if quota[k]], scale


def next_batch_slots(quotas, accepted_by_key, size, max_share):
    """Spread the next research batch of ``size`` topics over the categories still short of quota."""
    remaining = {q['taxonomy_key']: q['quota'] - accepted_by_key.get(q['taxonomy_key'], 0) for q in quotas}
    slots = spread(size, remaining, max_share)
    return dict(sorted(((k, v) for k, v in slots.items() if v > 0), key=lambda kv: (-kv[1], kv[0])))


def assess(refill, stock, rows, inventory, taxonomy, domains, intake_ledger, orders, approved_capacity, at):
    """Pure decision: returns the new order ledger plus the request researchers read."""
    orders = json.loads(json.dumps(orders or {}))
    capacity_left = max(0, approved_capacity - len(rows))
    ready = stock['ready']
    state, actions = 'HEALTHY', []
    current = next((o for o in orders.values() if o['status'] == 'OPEN'), None)
    accepted_ids, last_activity = ([], None)
    if current:
        accepted_ids, last_activity = accepted_since(intake_ledger, current['opened_at'])
        if len(accepted_ids) >= current['target_min']:
            current.update(status='FULFILLED', closed_at=at.isoformat(), accepted=len(accepted_ids))
            state = 'REFILL_FULFILLED'
            actions.append('close')
            current = None
        else:
            state = 'REFILL_IN_PROGRESS'
    if not refill['enabled']:
        state = 'DISABLED'
    elif current is None and ready < refill['trigger_below_ready']:
        rounds = len(orders)
        if refill['max_rounds'] is not None and rounds >= refill['max_rounds']:
            state = 'ROUND_LIMIT_REACHED'
        elif capacity_left < refill['research_batch_size']:
            state = 'CAPACITY_BLOCKED'
        else:
            low = min(refill['round_target_min'], capacity_left)
            high = min(refill['round_target_max'], capacity_left)
            order_id = 'RF-%04d' % (rounds + 1)
            current = {'round': rounds + 1, 'status': 'OPEN', 'opened_at': at.isoformat(), 'closed_at': None,
                       'opened_ready': ready, 'trigger_below_ready': refill['trigger_below_ready'],
                       'target_min': low, 'target_max': high,
                       'capacity_limited': low < refill['round_target_min']}
            orders[order_id] = current
            state, accepted_ids, last_activity = 'REFILL_OPENED', [], None
            actions.append('open')
    request = {'version': 1, 'state': state, 'ready_stock': ready,
               'trigger_below_ready': refill['trigger_below_ready'],
               'rounds_opened': len(orders), 'unlimited_rounds': refill['max_rounds'] is None,
               'approved_capacity': approved_capacity, 'topic_rows': len(rows), 'capacity_remaining': capacity_left}
    if state == 'CAPACITY_BLOCKED':
        request['instruction'] = ('Approved topic capacity is used up. Only the owner can raise approved_capacity '
                                  'in config/production-policy.json (hard ceiling 10,000).')
    if current:
        by_id = {t['topic_id']: t for t in rows}
        accepted_by_key = Counter(by_id[i]['taxonomy_key'] for i in accepted_ids if i in by_id)
        quotas, scale = quotas_for(current['target_min'], rows, inventory, taxonomy, domains,
                                   refill['max_taxonomy_share'])
        idle = (at - (last_activity or parse_time(current['opened_at']))).total_seconds() / 3600
        request['order'] = {
            'id': [k for k, v in orders.items() if v is current][0],
            'round': current['round'], 'target_min': current['target_min'], 'target_max': current['target_max'],
            'accepted_so_far': len(accepted_ids),
            'remaining_to_min': max(0, current['target_min'] - len(accepted_ids)),
            'remaining_to_max': max(0, current['target_max'] - len(accepted_ids)),
            'batches_still_needed': math.ceil(max(0, current['target_min'] - len(accepted_ids)) / refill['research_batch_size']),
            'batch_size': refill['research_batch_size'], 'capacity_limited': current['capacity_limited'],
            'stalled': idle > refill['stalled_after_hours'],
            'category_quotas_basis': scale,
            'category_quotas': quotas,
            'next_batch_categories': next_batch_slots(quotas, accepted_by_key, refill['research_batch_size'],
                                                       max(refill['max_taxonomy_share'], 0.2)),
        }
    inventory_live = sum(1 for i in inventory if i.get('status') == 'publish')
    by_status = Counter(t.get('topic_qa_status') or 'UNKNOWN' for t in rows)
    request['dedupe_universe'] = {
        'published_wordpress_items': inventory_live, 'topics_in_factory': len(rows),
        'topics_by_status': dict(sorted(by_status.items())),
        'rule': ('A candidate is compared with EVERY published WordPress item and EVERY topic in the factory '
                 '(any status except REJECTED), and with the other new rows of the same research run.')}
    request['how_to_research'] = [
        'python scripts/research_v2.py plan            # this order, quotas and the next batch of 10',
        'python scripts/research_v2.py intent-check --file data/candidates/<session>-NNNN.jsonl   # before every push',
        'python scripts/research_v2.py checkpoint --branch research/<session> && python scripts/research_v2.py push --branch research/<session>',
        'Only topics that pass Research QA (independent sources, search-intent guard, taxonomy) become PLANNED.']
    return orders, request, actions


def build_inputs():
    registry = load('data/state/writer-claims.json', {})
    ledger = load('data/state/publication-ledger.json', {})
    rows = topics()
    drafts = {p.stem for p in (ROOT / 'posts/drafts').glob('NT-*.md')}
    qa = {p.stem: load('data/qa/' + p.name, {}) for p in (ROOT / 'data/qa').glob('NT-*.json')}
    discovery = load('data/state/topic-discovery-ledger.json', {'proposals': {}})
    refill = load_policy()
    production = load('config/production-policy.json', {})
    stock = build_stock(rows, registry, ledger, qa, drafts, discovery, stock_policy(production, refill))
    return {'refill': refill, 'stock': stock, 'rows': rows,
            'inventory': load('data/existing-content-inventory.json', {}).get('items', []),
            'taxonomy': load('data/taxonomy.json', {}).get('items', []),
            'domains': load('data/topic-domains.json', {}).get('domains', []),
            'intake_ledger': load(INTAKE_LEDGER, {'batches': {}}),
            'orders': (load(STATE, {'version': 1, 'orders': {}}) or {}).get('orders', {}),
            'approved_capacity': int(production.get('approved_capacity', 1000))}


def run(apply=False):
    inputs = build_inputs()
    at = dt.datetime.now(dt.timezone.utc)
    orders, request, actions = assess(at=at, **inputs)
    summary = {'state': request['state'], 'actions': actions, 'ready_stock': request['ready_stock'],
               'order': request.get('order', {}).get('id'), 'accepted_so_far': request.get('order', {}).get('accepted_so_far')}
    if not apply:
        print(json.dumps({'summary': summary, 'request': request}, ensure_ascii=False, indent=2))
        return summary
    # Only the trusted main workflow may write the order ledger.
    if not (os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('GITHUB_WORKFLOW') == TRUSTED_WORKFLOW
            and os.environ.get('GITHUB_REPOSITORY') == 'thuexemayhanoi/wp-writer'
            and os.environ.get('GITHUB_REF') == 'refs/heads/main'):
        raise ValueError('Trusted Actions main required for applying the refill controller')
    from git_state import RemoteState
    paths = [STATE, REQUEST]
    state = RemoteState()
    state.remember(paths)
    save(STATE, {'version': 1, 'orders': orders})
    save(REQUEST, request)
    commit = state.persist(paths, 'chore: refill controller %s [skip ci]' % request['state'])
    print(json.dumps({**summary, 'commit': commit}, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--apply', action='store_true', help='persist (trusted GitHub Actions on main only)')
    args = parser.parse_args()
    run(apply=args.apply)
    return 0


if __name__ == '__main__':
    sys.exit(main())
