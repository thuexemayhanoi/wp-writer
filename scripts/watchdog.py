#!/usr/bin/env python3
"""Read-only factory liveness watchdog inspired by /blog, adapted for WordPress.

This file NEVER imports a WordPress client, claims a writer slot, or mutates git state.
Reports semantic progress separately from an Actions green checkmark.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

from common import ROOT, load, topics


def parse_time(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.replace(tzinfo=dt.timezone.utc) if not parsed.tzinfo else parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def elapsed_minutes(then, now):
    t = parse_time(then)
    return None if t is None else max(0, (now-t).total_seconds()/60)


def assess(policy, registry, ledger, topic_rows, qa_by_id, at=None, stall_minutes=120):
    at = at or dt.datetime.now(dt.timezone.utc)
    if at.tzinfo is None:
        raise ValueError('watchdog requires timezone-aware time')
    posts = ledger.get('posts', {})
    receipts = registry.get('submissions', {})
    finished = {i for i, record in posts.items() if record.get('phase') == 'VERIFIED'}
    uncertain = sorted(i for i, record in posts.items() if
                       record.get('phase') in ('POST_INTENT', 'VERIFY_PENDING', 'NEEDS_RECONCILE'))
    source_mismatches = []
    ready = []
    for topic_id, receipt in receipts.items():
        q = qa_by_id.get(topic_id, {})
        if (topic_id in finished or topic_id in uncertain or q.get('status') != 'PASS'):
            continue
        if receipt.get('sha256') != q.get('source_sha256'):
            source_mismatches.append(topic_id)
            continue
        ready.append({'topic_id': topic_id, 'minutes_waiting': elapsed_minutes(receipt.get('submitted_at'), at)})

    live_leases = {}
    for slot, lease in registry.get('leases', {}).items():
        exp = parse_time(lease.get('expires_at'))
        if exp is not None and exp > at:
            live_leases[slot] = {'session': lease.get('session'), 'topics': len(lease.get('topic_ids', []))}
    blocked = sorted(s for s, info in registry.get('processed_requests', {}).items()
                     if info.get('status') == 'BLOCKED')
    planned = [t for t in topic_rows if t.get('topic_qa_status') == 'PLANNED']
    claimable = [t for t in planned if t['topic_id'] not in receipts
                 and all(t['topic_id'] not in v.get('topic_ids', []) for v in registry.get('leases', {}).values())]
    statuses = [record for record in posts.values() if record.get('phase') == 'VERIFIED']
    progress_at = max((parse_time(v.get('verified_at')) or parse_time(v.get('updated_at'))
                       for v in statuses if parse_time(v.get('verified_at')) or parse_time(v.get('updated_at'))),
                      default=None)
    stopped = bool(policy.get('paused') or policy.get('emergency_stop'))
    public_enabled = (policy.get('mode') == 'production' and policy.get('production_enabled') is True
        and bool(policy.get('owner_approval_ref')) and policy.get('acceptance_passed') is True
        and policy.get('security_controls_verified') is True and policy.get('seo_adapter_verified') is True)
    staging_enabled = (policy.get('mode') == 'draft_only' and policy.get('production_enabled') is False
        and policy.get('draft_staging_enabled') is True and bool(policy.get('draft_staging_approval_ref'))
        and policy.get('security_controls_verified') is True)
    enabled = not stopped and (public_enabled or staging_enabled)

    if uncertain:
        state, detail = 'NEEDS_RECONCILE', 'Uncertain WordPress POST intents require manual reconciliation; never retry blindly.'
    elif source_mismatches:
        state, detail = 'SOURCE_MISMATCH', 'A QA-PASS file does not match its immutable writer receipt; reject delivery.'
    elif stopped:
        state, detail = 'PAUSED', 'Owner pause/emergency-stop prevents delivery.'
    elif policy.get('mode') == 'dry_run' and not policy.get('production_enabled') and not policy.get('draft_staging_enabled'):
        state, detail = 'SAFE_OFF', 'Production and unattended staging are off; no WordPress delivery expected.'
    elif not enabled:
        state, detail = 'CONFIG_BLOCKED', 'Requested WordPress delivery mode is missing explicit safety prerequisites.'
    elif any(v['minutes_waiting'] is None or v['minutes_waiting'] >= stall_minutes for v in ready):
        state, detail = 'STALLED', 'Admitted QA-PASS posts have waited beyond the delivery threshold.'
    elif ready:
        state, detail = 'DELIVERY_PENDING', 'QA-PASS posts are waiting within the grace window.'
    elif blocked:
        state, detail = 'WRITER_REQUEST_BLOCKED', 'Blocked writer requests require an explicit new request or investigation.'
    elif not planned or (not claimable and not live_leases):
        state, detail = 'NEEDS_TOPIC_EXPANSION', 'No claimable researched topics remain; an external AI must research candidates.'
    elif not live_leases:
        state, detail = 'AWAITING_WRITERS', 'Topics exist, but no active external writer session.'
    else:
        state, detail = 'RUNNING', 'External writer leases exist; no overdue delivery.'
    return {
        'state': state, 'detail': detail,
        'delivery_enabled': enabled, 'production_enabled': public_enabled,
        'timestamp': at.isoformat(), 'stall_threshold_minutes': stall_minutes,
        'candidate_topics': len(topic_rows), 'planned_topics': len(planned),
        'claimable_topics': len(claimable), 'active_writer_slots': live_leases,
        'qa_pass_waiting': ready, 'queued_count': len(ready),
        'uncertain_post_ids': uncertain, 'source_mismatch_ids': sorted(source_mismatches), 'blocked_sessions': blocked,
        'verified_wp_posts': len(statuses),
        'last_verified_at': progress_at.isoformat() if progress_at else None,
        'healthy': state not in ('NEEDS_RECONCILE', 'SOURCE_MISMATCH', 'CONFIG_BLOCKED', 'STALLED', 'WRITER_REQUEST_BLOCKED'),
        'note': 'RUN_SUCCESS is not PROGRESS_SUCCESS; this is a read-only snapshot. No content is generated.'
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', help='Optional JSON output outside tracked git tree')
    parser.add_argument('--stall-minutes', type=int, default=120)
    args = parser.parse_args()
    if args.stall_minutes < 1:
        raise ValueError('stall threshold must be positive')
    policy = load('config/production-policy.json', {})
    registry = load('data/state/writer-claims.json', {})
    ledger = load('data/state/publication-ledger.json', {})
    rows = topics()
    qa = {p.stem: load(str(p.relative_to(ROOT)), {})
          for p in (ROOT/'data/qa').glob('NT-*.json')}
    report = assess(policy, registry, ledger, rows, qa, stall_minutes=args.stall_minutes)
    serialized = json.dumps(report, indent=2, ensure_ascii=False)+'\n'
    print(serialized)
    if args.output:
        path = Path(args.output).resolve()
        if path.is_relative_to(ROOT.resolve()):
            raise ValueError('watchdog report must not alter a tracked repository file')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write('## WordPress Factory watchdog\n\n')
            f.write('**'+report['state']+'** — '+report['detail']+'\n\n')
            f.write('QA PASS waiting: '+str(report['queued_count'])+
                    '; uncertain POST intents: '+str(len(report['uncertain_post_ids']))+
                    '; claimable topics: '+str(report['claimable_topics'])+'\n')
    if not report['healthy']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
