"""One canonical count of the topic stock; every topic row is counted in exactly one stage.

IDEA          discovery lead (NTD- proposal) nobody has researched into a topic row yet
RESEARCH      topic row waiting for researched evidence; a writer cannot use it
REJECTED      topic row that failed Topic QA
PLANNED       researched, Topic QA PASS, unclaimed, not on hold: the ready stock writers draw from
PLANNED_HOLD  Topic QA PASS but parked by the coordinator (field `hold`, e.g. sources unreadable from the runner)
CLAIMED       inside a live writer lease, no draft yet
AUTHORED      draft exists, QA is not PASS yet
QA_PASS       draft passed QA and waits for, or is inside, the Publisher (an unverified POST intent counts here)
PUBLISHED     WordPress read-back VERIFIED as public
WP_DRAFT      WordPress read-back VERIFIED as a draft (fallback category)

The lifetime PLANNED total is history, not backlog: only PLANNED counts toward the 100-topic reserve.
Read-only. It never invents topics and never runs a model.
"""
import datetime as dt
from collections import Counter

STAGES = ('IDEA', 'RESEARCH', 'REJECTED', 'PLANNED', 'PLANNED_HOLD', 'CLAIMED', 'AUTHORED',
          'QA_PASS', 'PUBLISHED', 'WP_DRAFT')
ROW_STAGES = STAGES[1:]
DEFAULT_MIN_READY = 100
DEFAULT_MAX_READY = 200


def _live_lease_ids(registry, at):
    ids = set()
    for lease in (registry.get('leases') or {}).values():
        try:
            expires = dt.datetime.fromisoformat(str(lease['expires_at']).replace('Z', '+00:00'))
        except (KeyError, TypeError, ValueError):
            continue
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=dt.timezone.utc)
        if expires > at:
            ids.update(lease.get('topic_ids') or [])
    return ids


def stage_of(topic, ctx):
    topic_id = topic['topic_id']
    status = topic.get('topic_qa_status')
    if status == 'REJECTED':
        return 'REJECTED'
    if status != 'PLANNED':
        return 'RESEARCH'  # an unknown status is never counted as ready
    record = ctx['posts'].get(topic_id)
    if record:
        if record.get('phase') == 'VERIFIED':
            return 'PUBLISHED' if record.get('status') == 'publish' else 'WP_DRAFT'
        return 'QA_PASS'  # the Publisher already holds a write-ahead intent for it
    if topic_id in ctx['drafts'] or topic_id in ctx['receipts']:
        return 'QA_PASS' if (ctx['qa'].get(topic_id) or {}).get('status') == 'PASS' else 'AUTHORED'
    if topic_id in ctx['leased']:
        return 'CLAIMED'
    if topic.get('hold'):
        return 'PLANNED_HOLD'
    return 'PLANNED'


def build_stock(rows, registry, ledger, qa_by_id, draft_ids, discovery, policy, at=None):
    at = at or dt.datetime.now(dt.timezone.utc)
    registry, ledger, discovery, policy = registry or {}, ledger or {}, discovery or {}, policy or {}
    ctx = {'posts': ledger.get('posts') or {}, 'receipts': registry.get('submissions') or {},
           'qa': qa_by_id or {}, 'drafts': set(draft_ids or ()), 'leased': _live_lease_ids(registry, at)}
    by_id = {t['topic_id']: stage_of(t, ctx) for t in rows}
    counts = Counter(by_id.values())
    used_origins = {str(t.get('origin_id')) for t in rows}
    ideas = sorted(k for k in (discovery.get('proposals') or {}) if k not in used_origins)
    stages = {name: counts.get(name, 0) for name in STAGES}
    stages['IDEA'] = len(ideas)
    ready_ids = sorted(i for i, s in by_id.items() if s == 'PLANNED')
    low = int(policy.get('min_claimable_queue', DEFAULT_MIN_READY))
    high = max(low, int(policy.get('max_claimable_queue', DEFAULT_MAX_READY)))
    return {
        'at': at.isoformat(),
        'stages': stages,
        'topic_rows': len(rows),
        'ready': len(ready_ids),
        'ready_ids': ready_ids,
        'on_hold': {t['topic_id']: t['hold'] for t in rows if by_id[t['topic_id']] == 'PLANNED_HOLD'},
        'min_ready': low,
        'max_ready': high,
        'needs_research': len(ready_ids) < low,
        'shortfall': max(0, low - len(ready_ids)),
        'room_to_target_max': max(0, high - len(ready_ids)),
        'lifetime_planned': sum(1 for t in rows if t.get('topic_qa_status') == 'PLANNED'),
        'note': ('PLANNED counts only topics a writer can still take. Published, claimed, authored, '
                 'held, RESEARCH and IDEA are never added to it.'),
    }
