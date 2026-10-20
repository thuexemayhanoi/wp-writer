"""One status board for every article in flight: WRITING -> QA -> READY -> PUBLISHING -> VERIFIED (+ REPAIR / HELD).

Read-only. Derived from the lease registry, the drafts on main, the stored QA records, the writer receipts and the
publication ledger; it never changes any of them and never talks to WordPress.

States (each topic is in exactly one):
  WRITING     inside a live writer lease, no draft committed yet
  QA          draft committed but no hash-valid QA record for this draft version yet (waiting for the next sweep)
  READY       QA PASS, writer receipt matches the draft hash, not yet in the ledger: the Publisher backlog
  REPAIR      QA FAIL/REVIEW the writer (or a machine re-check) can fix: WRITER_REPAIR / INFRA_PENDING
  HELD        QA FAIL/REVIEW classified REAL_RISK, or PASS without a valid receipt (quarantined draft)
  PUBLISHING  write-ahead intent recorded (POST_INTENT, VERIFY_PENDING, NEEDS_RECONCILE)
  VERIFIED    WordPress read-back verified (public post or fallback draft)
"""
import datetime as dt
import json

from common import ROOT, digest, load, now, save, topics

STATES = ('WRITING', 'QA', 'READY', 'REPAIR', 'HELD', 'PUBLISHING', 'VERIFIED')
PUBLISHING_PHASES = ('POST_INTENT', 'VERIFY_PENDING', 'NEEDS_RECONCILE')


def _live_leases(registry, at):
    out = {}
    for slot, lease in (registry.get('leases') or {}).items():
        try:
            expires = dt.datetime.fromisoformat(str(lease['expires_at']).replace('Z', '+00:00'))
        except (KeyError, TypeError, ValueError):
            continue
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=dt.timezone.utc)
        if expires > at:
            for topic_id in lease.get('topic_ids') or []:
                out[topic_id] = {'slot': slot, 'session': lease.get('session')}
    return out


def classify(topic_id, draft_sha, qa, receipt, ledger_record, leased):
    """Return (state, reason). draft_sha is None when no draft exists."""
    if ledger_record:
        phase = ledger_record.get('phase')
        if phase == 'VERIFIED':
            return 'VERIFIED', ledger_record.get('status') or 'verified'
        if phase in PUBLISHING_PHASES:
            return 'PUBLISHING', phase
        return 'PUBLISHING', 'ledger phase ' + str(phase)
    if draft_sha is None:
        if topic_id in leased:
            return 'WRITING', 'leased to ' + str(leased[topic_id].get('session'))
        return None, 'not in flight'
    if not isinstance(qa, dict) or qa.get('source_sha256') != draft_sha:
        return 'QA', 'no QA record for this draft version yet'
    status = qa.get('status')
    if status == 'PASS':
        if (receipt or {}).get('sha256') != draft_sha:
            return 'HELD', 'PASS without a matching writer receipt (quarantined draft)'
        return 'READY', 'QA PASS; waiting for the Publisher'
    hold = (qa.get('triage') or {}).get('hold_class') or 'REAL_RISK'
    reasons = list(qa.get('errors') or []) + list(qa.get('review') or [])
    reason = (hold + ': ' + '; '.join(str(r) for r in reasons[:2]))[:300]
    if hold in ('WRITER_REPAIR', 'INFRA_PENDING'):
        return 'REPAIR', reason
    return 'HELD', reason


def build(root=None, at=None):
    root = ROOT if root is None else root
    at = at or dt.datetime.now(dt.timezone.utc)
    rows = topics()
    registry = load('data/state/writer-claims.json', {}) or {}
    ledger = (load('data/state/publication-ledger.json', {}) or {}).get('posts', {})
    receipts = registry.get('submissions') or {}
    leased = _live_leases(registry, at)
    drafts = {p.stem: digest(p.read_bytes()) for p in (root / 'posts/drafts').glob('NT-*.md')}
    items = []
    for topic in rows:
        topic_id = topic['topic_id']
        qa = load('data/qa/' + topic_id + '.json') if topic_id in drafts else None
        state, reason = classify(topic_id, drafts.get(topic_id), qa, receipts.get(topic_id), ledger.get(topic_id), leased)
        if state is None:
            continue
        record = ledger.get(topic_id) or {}
        lease = leased.get(topic_id) or {}
        items.append({'topic_id': topic_id, 'state': state, 'reason': reason, 'title': topic.get('title'),
                      'slot': lease.get('slot') or (receipts.get(topic_id) or {}).get('slot'),
                      'session': lease.get('session') or (receipts.get(topic_id) or {}).get('session'),
                      'wp_id': record.get('wp_id'), 'url': record.get('url'),
                      'qa_status': (qa or {}).get('status') if qa else None,
                      'seo_score': (qa or {}).get('seo_score') if qa else None})
    counts = {s: sum(1 for i in items if i['state'] == s) for s in STATES}
    order = {s: n for n, s in enumerate(STATES)}
    items.sort(key=lambda i: (order[i['state']], i['topic_id']))
    return {'at': now(), 'counts': counts, 'ready_backlog': counts['READY'],
            'in_flight': sum(v for k, v in counts.items() if k != 'VERIFIED'),
            'items': items}


def ready_backlog(root=None):
    """How many QA-PASS, receipt-valid drafts still wait for the Publisher (what a self-continuing run looks at)."""
    return build(root)['ready_backlog']


def markdown(board):
    lines = ['# Pipeline board', '', 'Generated ' + board['at'] + ' from leases, drafts, QA records, receipts and the ledger.',
             '', '| State | Count |', '|---|---|']
    lines += ['| ' + s + ' | ' + str(board['counts'][s]) + ' |' for s in STATES]
    lines += ['', 'Ready backlog (QA PASS waiting for the Publisher): **' + str(board['ready_backlog']) + '**', '',
              '## Articles not yet VERIFIED', '', '| Topic | State | Slot | Session | Reason |', '|---|---|---|---|---|']
    for item in board['items']:
        if item['state'] == 'VERIFIED':
            continue
        lines.append('| ' + item['topic_id'] + ' | ' + item['state'] + ' | ' + str(item.get('slot') or '') + ' | ' +
                     str(item.get('session') or '') + ' | ' + str(item.get('reason') or '').replace('|', '/') + ' |')
    return '\n'.join(lines) + '\n'


def run():
    board = build()
    save('reports/pipeline-board.json', board)
    (ROOT / 'reports/pipeline-board.md').write_text(markdown(board), encoding='utf-8')
    print(json.dumps({'counts': board['counts'], 'ready_backlog': board['ready_backlog']}, ensure_ascii=False))
    return board


if __name__ == '__main__':
    run()
