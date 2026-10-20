"""Decide whether the Publisher should dispatch itself again to keep draining the READY backlog.

Called as the last step of the Publisher job. It never touches WordPress and never fails the job: when it decides
"continue" it asks GitHub (gh workflow run with the job's own token) for one more Publisher run; the workflow's
concurrency group serializes that run behind the current one, so there is still exactly one WordPress writer.

Continue only when all of these hold (owner policy `publisher_chain`, config/production-policy.json):
  - the chain is enabled and the stop switches are off
  - this run actually posted something (attempted > 0): a run that posted nothing (held, blocked, daily cap, WP
    refused) must not loop on the same obstacle; the five-minute QA sweep and the :17/:47 cron remain the retry path
  - QA-PASS, receipt-valid articles still wait (ready_backlog > 0)
  - the chain depth is below `max_depth` (bounded, never an infinite loop)
  - `pause_seconds` have been waited, so the host gets a breather between batches of up to 10 posts
"""
import json
import os
import subprocess
import sys
import time

from common import ROOT, load, now, save

DEFAULTS = {'enabled': True, 'max_depth': 12, 'pause_seconds': 45}


def settings(policy):
    value = policy.get('publisher_chain')
    if value is None:
        return dict(DEFAULTS)
    if not isinstance(value, dict):
        raise ValueError('publisher_chain must be an object')
    out = dict(DEFAULTS)
    out.update({k: value[k] for k in DEFAULTS if k in value})
    if type(out['max_depth']) is not int or not 0 <= out['max_depth'] <= 100:
        raise ValueError('publisher_chain.max_depth must be 0..100')
    if type(out['pause_seconds']) is not int or not 0 <= out['pause_seconds'] <= 600:
        raise ValueError('publisher_chain.pause_seconds must be 0..600')
    return out


def decision(policy, latest, depth, ready_backlog):
    """Return (continue: bool, reason). Pure; no I/O."""
    chain = settings(policy)
    if policy.get('paused') or policy.get('emergency_stop'):
        return False, 'owner stop switch is on'
    if not chain['enabled']:
        return False, 'publisher_chain disabled'
    if not isinstance(latest, dict) or latest.get('production') is not True:
        return False, 'no production run result to continue from'
    if int(latest.get('attempted') or 0) <= 0:
        return False, 'this run posted nothing; the scheduled sweep/cron retries later'
    if int(ready_backlog or 0) <= 0:
        return False, 'ready backlog is empty'
    if depth >= chain['max_depth']:
        return False, 'chain depth %d reached max_depth %d' % (depth, chain['max_depth'])
    return True, 'posted %s, %d ready article(s) remain' % (latest.get('attempted'), ready_backlog)


def dispatch(depth, workflow='wordpress-publisher.yml', ref='main'):
    cmd = ['gh', 'workflow', 'run', workflow, '--ref', ref, '-f', 'chain_depth=' + str(depth + 1)]
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def main():
    try:
        depth = int(os.environ.get('CHAIN_DEPTH') or 0)
    except ValueError:
        depth = 0
    policy = load('config/production-policy.json', {}) or {}
    latest = load('reports/publisher-latest.json', {}) or {}
    try:
        from pipeline_board import ready_backlog
        backlog = ready_backlog()
    except Exception as exc:  # the board is derived; never fail the publisher job over it
        backlog = int(latest.get('ready_backlog') or 0)
        print('CHAIN_BOARD_UNAVAILABLE: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    go, reason = decision(policy, latest, depth, backlog)
    record = {'at': now(), 'depth': depth, 'continue': go, 'reason': reason, 'ready_backlog': backlog,
              'attempted': latest.get('attempted')}
    if go:
        pause = settings(policy)['pause_seconds']
        if pause and os.environ.get('GITHUB_ACTIONS'):
            time.sleep(pause)
        result = dispatch(depth)
        record['dispatch_rc'] = result.returncode
        record['dispatch_output'] = (result.stdout + result.stderr)[-300:]
    save('reports/publisher-chain.json', record)
    print('PUBLISHER_CHAIN: ' + json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
